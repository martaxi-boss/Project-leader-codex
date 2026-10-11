import unittest
from datetime import datetime, timezone

from control.managed_project_contract import (
    classify_external_ci,
    classify_post_implementation_descendant,
    decide_ci_dispatch,
    reconcile_external_ci_wait,
    reconcile_external_ci_liveness,
    reconcile_noninteractive_tool_fallback,
    reconcile_operational_access_discovery,
    reconcile_legacy_checkpoint_liveness,
    validate_managed_result,
    validate_managed_task,
)

REPOSITORY = "owner/project"
CONTROL_REPOSITORY = "owner/control"


def task(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "project": "TEST",
        "repository": REPOSITORY,
        "created_at": "2026-10-03T01:00:00Z",
        "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "bounded managed task",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/task-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["src/**", ".project-leader/tasks/**", ".project-leader/results/**"],
        "allowed_actions": ["create_branch", "edit_project_files", "create_commits", "run_ci", "open_or_update_pull_request"],
        "prohibited_actions": ["merge_to_main"],
        "transition_controls": [{"action": "merge_to_main", "requires_authority_resolution": True}],
        "required_validation": ["Mutation scope audit", "GitHub evidence verification"],
        "required_ci": ["Project CI"],
        "policy": {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "repository": CONTROL_REPOSITORY,
            "revision": "c" * 40,
            "sha256": "d" * 64,
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "green PR",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }


def legacy_checkpoint(status="ACTIVE"):
    return {
        "schema_version": "1.0",
        "task_id": "LEGACY-TASK-001",
        "repository": REPOSITORY,
        "updated_at": "2026-10-03T01:00:00Z",
        "last_durable_step": "legacy step",
        "action_fingerprint": "legacy|task|ci",
        "attempt_count": 1,
        "identical_failure_count": 0,
        "no_progress_iterations": 0,
        "strategy": "legacy recovery",
        "strategy_generation": 1,
        "last_error": None,
        "next_step": "inspect current durable state",
        "status": status,
    }


def result(version="2.0"):
    return {
        "schema_version": version,
        "task_id": "TASK-001",
        "repository": REPOSITORY,
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "authorization_record": ".project-leader/tasks/TASK-001.json",
        "authorization_commit_sha": "b" * 40,
        "authorization_sha256": "e" * 64,
        "implementation_head_sha": "f" * 40,
        "branch": "builder/task-001",
        "terminal_status": "TERMINAL_SUCCESS",
        "changes": ["src/app.py"],
        "validation": [
            {"name": "Mutation scope audit", "status": "PASS", "evidence": "diff checked"},
            {"name": "GitHub evidence verification", "status": "PASS", "evidence": "live evidence checked"},
        ],
        "ci": [{"name": "Project CI", "status": "SUCCESS", "run_id": 123}],
        "material_non_effects": ["no merge"],
        "residual_blockers": [],
    }


class ManagedProjectContractTests(unittest.TestCase):
    def test_new_managed_task_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_task(task("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_central_policy_binding(self):
        item = task()
        item["policy"] = {
            "binding_mode": "LOCAL_BASE_V1",
            "profile": "project-v1",
            "path": "projects/policies/project.json",
            "base_sha": "a" * 40,
            "sha256": "d" * 64,
        }
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_immutable_authorization(self):
        item = task()
        del item["integrity_mode"]
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_requires_append_only_recovery(self):
        item = task()
        item["recovery"]["mode"] = "MUTABLE_CHECKPOINT"
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_task_allows_empty_ci_when_selected_policy_does_not_require_workflows(self):
        item = task()
        item["required_ci"] = []
        self.assertTrue(validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY))

    def test_managed_task_rejects_malformed_ci_entries(self):
        item = task()
        item["required_ci"] = [""]
        with self.assertRaises(ValueError):
            validate_managed_task(item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_v1_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_managed_result(task(), result("1.0"), REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_requires_authorization_binding(self):
        item = result()
        del item["authorization_sha256"]
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_terminal_success_requires_real_run_id(self):
        item = result()
        item["ci"][0]["run_id"] = None
        with self.assertRaises(ValueError):
            validate_managed_result(task(), item, REPOSITORY, CONTROL_REPOSITORY)

    def test_managed_result_reuses_common_pair_invariants(self):
        cases = []

        branch_mismatch = result()
        branch_mismatch["branch"] = "builder/other"
        cases.append((task(), branch_mismatch))

        effect_mismatch = result()
        effect_mismatch["effect_class"] = "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED"
        cases.append((task(), effect_mismatch))

        authorization_mismatch = result()
        authorization_mismatch["authorization_record"] = ".project-leader/tasks/OTHER.json"
        cases.append((task(), authorization_mismatch))

        missing_validation = result()
        missing_validation["validation"] = [
            item for item in missing_validation["validation"]
            if item["name"] != "GitHub evidence verification"
        ]
        cases.append((task(), missing_validation))

        task_with_pr = task()
        task_with_pr["starting_state"]["pr_number"] = 99
        missing_pr = result()
        cases.append((task_with_pr, missing_pr))

        for task_item, result_item in cases:
            with self.assertRaises(ValueError):
                validate_managed_result(
                    task_item, result_item, REPOSITORY, CONTROL_REPOSITORY
                )

    def test_legacy_active_checkpoint_without_live_workstream_is_stale(self):
        state = reconcile_legacy_checkpoint_liveness(legacy_checkpoint())
        self.assertEqual(state["state"], "STALE_LEGACY_CHECKPOINT")
        self.assertFalse(state["actionable"])

    def test_legacy_active_checkpoint_with_live_branch_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_live_branch=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")
        self.assertTrue(state["actionable"])

    def test_legacy_active_checkpoint_with_open_pr_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_open_pr=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")

    def test_legacy_active_checkpoint_with_active_ci_is_corroborated(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_active_ci=True
        )
        self.assertEqual(state["state"], "LEGACY_ACTIVE_CORROBORATED")

    def test_terminal_result_supersedes_legacy_active_checkpoint(self):
        state = reconcile_legacy_checkpoint_liveness(
            legacy_checkpoint(), has_live_branch=True, has_terminal_result=True
        )
        self.assertEqual(state["state"], "STALE_LEGACY_CHECKPOINT")
        self.assertFalse(state["actionable"])

    def test_non_active_legacy_checkpoint_is_historical_terminal_state(self):
        state = reconcile_legacy_checkpoint_liveness(legacy_checkpoint("COMPLETE"))
        self.assertEqual(state["state"], "LEGACY_CHECKPOINT_TERMINAL")
        self.assertFalse(state["actionable"])

    def test_evidence_only_descendant_does_not_reopen_certification_recovery(self):
        state = classify_post_implementation_descendant(
            [
                ".project-leader/results/TASK-001.json",
                ".project-leader/recovery-events/TASK-001/0001.json",
            ],
            "TASK-001",
        )
        self.assertEqual(state["state"], "EVIDENCE_ONLY_DESCENDANT")
        self.assertEqual(state["route"], "CERTIFICATION_UNCHANGED")
        self.assertFalse(state["certification_ci_required"])

    def test_evidence_only_descendant_can_require_separate_final_head_governance_checks(self):
        state = classify_post_implementation_descendant(
            [".project-leader/results/TASK-001.json"],
            "TASK-001",
            final_head_checks_required=True,
        )
        self.assertEqual(state["state"], "EVIDENCE_ONLY_DESCENDANT")
        self.assertEqual(state["route"], "FINAL_HEAD_GOVERNANCE_CHECK")
        self.assertFalse(state["certification_ci_required"])
        self.assertTrue(state["final_head_checks_required"])

    def test_material_descendant_requires_new_implementation_ci(self):
        state = classify_post_implementation_descendant(
            [
                ".project-leader/results/TASK-001.json",
                "docs/AUDIT.md",
            ],
            "TASK-001",
        )
        self.assertEqual(state["state"], "MATERIAL_DESCENDANT")
        self.assertEqual(state["route"], "FRESH_IMPLEMENTATION_CI")
        self.assertTrue(state["certification_ci_required"])
        self.assertEqual(state["material_files"], ["docs/AUDIT.md"])

    def test_ci_dispatch_is_required_when_no_exact_run_exists(self):
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", []
        )
        self.assertEqual(decision["decision"], "DISPATCH_REQUIRED")

    def test_ci_dispatch_reuses_exact_active_run(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "in_progress",
            "conclusion": None,
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_ACTIVE_RUN")
        self.assertEqual(decision["run_id"], 101)

    def test_ci_dispatch_reuses_exact_successful_run(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_SUCCESSFUL_RUN")

    def test_ci_dispatch_routes_exact_failure_to_recovery(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "failure",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "ROUTE_RECOVERY")

    def test_ci_dispatch_uses_latest_exact_context_run(self):
        runs = [
            {
                "id": 101,
                "name": "Project CI",
                "head_sha": "a" * 40,
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-03T01:00:00Z",
            },
            {
                "id": 102,
                "name": "Project CI",
                "head_sha": "a" * 40,
                "event": "workflow_dispatch",
                "status": "completed",
                "conclusion": "success",
                "created_at": "2026-10-03T01:01:00Z",
            },
        ]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "REUSE_SUCCESSFUL_RUN")
        self.assertEqual(decision["run_id"], 102)

    def test_ci_dispatch_does_not_reuse_different_event_context(self):
        runs = [{
            "id": 101,
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }]
        decision = decide_ci_dispatch(
            "Project CI", "a" * 40, "workflow_dispatch", runs
        )
        self.assertEqual(decision["decision"], "DISPATCH_REQUIRED")

    def test_recent_in_progress_ci_is_wait_not_failure(self):
        run = {"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:25:12Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "WAITING_EXTERNAL_CI")

    def test_old_in_progress_ci_requires_investigation_not_retry(self):
        run = {"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-02T22:00:00Z"}
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        self.assertEqual(classify_external_ci(run, now), "INVESTIGATE_STALE_CI")

    def test_completed_success_is_terminal_success(self):
        self.assertEqual(classify_external_ci({"id": 101, "status": "completed", "conclusion": "success"}), "COMPLETED_SUCCESS")


    def test_external_ci_wait_remains_wait_only_while_bound_run_is_active(self):
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        runs = [{"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:30:00Z"}]
        state = reconcile_external_ci_wait([101], runs, now=now)
        self.assertEqual(state["state"], "WAITING_EXTERNAL_CI")
        self.assertEqual(state["route"], "WAIT")

    def test_terminal_success_invalidates_previous_wait_and_routes_continue(self):
        runs = [{"id": 101, "status": "completed", "conclusion": "success"}]
        state = reconcile_external_ci_wait([101], runs, previous_state="WAITING_EXTERNAL_CI")
        self.assertEqual(state["state"], "STALE_WAIT_STATE")
        self.assertEqual(state["route"], "AUDIT_CONTINUE")
        self.assertEqual(state["failed_run_ids"], [])

    def test_terminal_failure_invalidates_previous_wait_and_routes_recovery(self):
        runs = [{"id": 101, "status": "completed", "conclusion": "failure"}]
        state = reconcile_external_ci_wait([101], runs, previous_state="WAITING_EXTERNAL_CI")
        self.assertEqual(state["state"], "STALE_WAIT_STATE")
        self.assertEqual(state["route"], "RECOVERY")
        self.assertEqual(state["failed_run_ids"], [101])

    def test_mixed_active_and_terminal_runs_do_not_redispatch_early(self):
        now = datetime(2026, 10, 3, 0, 33, 0, tzinfo=timezone.utc)
        runs = [
            {"id": 101, "status": "completed", "conclusion": "success"},
            {"id": 102, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:30:00Z"},
        ]
        state = reconcile_external_ci_wait([101, 102], runs, now=now)
        self.assertEqual(state["state"], "WAITING_EXTERNAL_CI")
        self.assertEqual(state["route"], "WAIT")
        self.assertEqual(state["active_run_ids"], [102])

    def test_missing_bound_run_requires_investigation_not_new_dispatch(self):
        state = reconcile_external_ci_wait([101, 102], [{"id": 101, "status": "completed", "conclusion": "success"}])
        self.assertEqual(state["state"], "INVESTIGATE_CI_STATE")
        self.assertEqual(state["route"], "INVESTIGATE")
        self.assertEqual(state["missing_run_ids"], [102])

    def test_observed_stale_spinner_sequence_routes_immediately_after_ci_success(self):
        started = datetime(2026, 10, 3, 0, 30, 0, tzinfo=timezone.utc)
        waiting = reconcile_external_ci_liveness(
            [101],
            [{"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:30:00Z"}],
            last_progress_at=started,
            now=datetime(2026, 10, 3, 0, 34, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(waiting["state"], "WAITING_EXTERNAL_CI")
        self.assertEqual(waiting["liveness_action"], "POLL_AGAIN")

        completed = reconcile_external_ci_liveness(
            [101],
            [{"id": 101, "status": "completed", "conclusion": "success", "updated_at": "2026-10-03T00:36:00Z"}],
            previous_state=waiting["state"],
            last_progress_at=started,
            now=datetime(2026, 10, 3, 0, 36, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(completed["state"], "STALE_WAIT_STATE")
        self.assertEqual(completed["route"], "AUDIT_CONTINUE")
        self.assertEqual(completed["liveness_action"], "ROUTE_IMMEDIATELY")

    def test_live_work_forces_reconstruction_after_two_poll_intervals_without_progress(self):
        state = reconcile_external_ci_liveness(
            [101],
            [{"id": 101, "status": "in_progress", "conclusion": None, "updated_at": "2026-10-03T00:39:00Z"}],
            last_progress_at="2026-10-03T00:30:00Z",
            now=datetime(2026, 10, 3, 0, 40, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(state["state"], "LIVENESS_RECONCILE_REQUIRED")
        self.assertEqual(state["route"], "INVESTIGATE")
        self.assertEqual(state["liveness_action"], "RECONSTRUCT_AND_REPOLL")

    def test_terminal_ci_wins_over_liveness_timeout(self):
        state = reconcile_external_ci_liveness(
            [101],
            [{"id": 101, "status": "completed", "conclusion": "success"}],
            previous_state="WAITING_EXTERNAL_CI",
            last_progress_at="2026-10-03T00:00:00Z",
            now=datetime(2026, 10, 3, 1, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(state["state"], "STALE_WAIT_STATE")
        self.assertEqual(state["route"], "AUDIT_CONTINUE")
        self.assertEqual(state["liveness_action"], "ROUTE_IMMEDIATELY")

    def test_access_discovery_does_not_stop_when_required_surfaces_are_unsearched(self):
        state = reconcile_operational_access_discovery(
            ["direct_session_capabilities"],
            [],
            direct_access_available=False,
        )
        self.assertEqual(state["state"], "ACCESS_DISCOVERY_INCOMPLETE")
        self.assertEqual(state["route"], "CONTINUE_DISCOVERY")
        self.assertIn("operational_repository_discovery", state["missing_surfaces"])

    def test_access_discovery_accepts_read_only_cross_repository_channel(self):
        state = reconcile_operational_access_discovery(
            [
                "direct_session_capabilities",
                "native_tool_capability_inventory",
                "target_repository_automation",
                "operational_repository_discovery",
                "existing_access_history",
            ],
            [
                {
                    "name": "github-actions-to-vps",
                    "usable": True,
                    "requires_mutation": False,
                    "authority_covered": False,
                }
            ],
        )
        self.assertEqual(state["state"], "ACCESS_PATH_FOUND")
        self.assertEqual(state["route"], "CONTINUE")
        self.assertEqual(state["selected_channel"], "github-actions-to-vps")

    def test_access_discovery_routes_cross_repository_write_to_separate_task(self):
        state = reconcile_operational_access_discovery(
            [
                "direct_session_capabilities",
                "native_tool_capability_inventory",
                "target_repository_automation",
                "operational_repository_discovery",
                "existing_access_history",
            ],
            [
                {
                    "name": "ops-repository-pr-trigger",
                    "usable": True,
                    "requires_mutation": True,
                    "authority_covered": True,
                }
            ],
        )
        self.assertEqual(state["state"], "ACCESS_PATH_REQUIRES_SEPARATE_TASK")
        self.assertEqual(state["route"], "BOUND_OPERATIONS_TASK")

    def test_access_discovery_resolves_authority_before_human_gate(self):
        state = reconcile_operational_access_discovery(
            [
                "direct_session_capabilities",
                "native_tool_capability_inventory",
                "target_repository_automation",
                "operational_repository_discovery",
                "existing_access_history",
            ],
            [
                {
                    "name": "ops-repository-pr-trigger",
                    "usable": True,
                    "requires_mutation": True,
                    "authority_covered": False,
                }
            ],
        )
        self.assertEqual(state["state"], "ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION")
        self.assertEqual(state["route"], "SUPERVISOR_AUTHORITY_RESOLUTION")

    def test_access_human_gate_is_only_candidate_after_discovery_exhaustion(self):
        state = reconcile_operational_access_discovery(
            [
                "direct_session_capabilities",
                "native_tool_capability_inventory",
                "target_repository_automation",
                "operational_repository_discovery",
                "existing_access_history",
            ],
            [],
        )
        self.assertEqual(state["state"], "ACCESS_PATH_UNAVAILABLE")
        self.assertEqual(state["route"], "HUMAN_GATE_CANDIDATE")

    def test_noninteractive_fallback_prefers_native_diagnostics_over_browser_consent(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [
                {
                    "name": "github-workflow-job-logs",
                    "usable": True,
                    "requires_user_consent": False,
                },
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                },
            ],
        )
        self.assertEqual(state["state"], "NONINTERACTIVE_PATH_FOUND")
        self.assertEqual(state["route"], "CONTINUE_DIAGNOSTIC")
        self.assertEqual(state["selected_channel"], "github-workflow-job-logs")

    def test_noninteractive_fallback_does_not_request_consent_before_exhaustion(self):
        state = reconcile_noninteractive_tool_fallback(
            ["native_tool_capability_inventory", "workflow_run_metadata"],
            [
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                }
            ],
        )
        self.assertEqual(state["state"], "NONINTERACTIVE_FALLBACK_INCOMPLETE")
        self.assertEqual(state["route"], "CONTINUE_DIAGNOSTIC_DISCOVERY")
        self.assertIn("workflow_jobs_steps_logs", state["missing_surfaces"])

    def test_self_provisioning_is_mandatory_before_browser_consent(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                }
            ],
        )
        self.assertEqual(state["state"], "NONINTERACTIVE_FALLBACK_INCOMPLETE")
        self.assertEqual(state["route"], "CONTINUE_DIAGNOSTIC_DISCOVERY")
        self.assertEqual(state["missing_surfaces"], ["self_provisioned_diagnostic_bridge"])

    def test_covered_self_provisioned_bridge_beats_browser_consent(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                }
            ],
            self_provisioning_checked=True,
            self_provision_candidates=[
                {
                    "name": "ephemeral-github-diagnostic-workflow",
                    "provisionable": True,
                    "authority_covered": True,
                }
            ],
        )
        self.assertEqual(state["state"], "DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK")
        self.assertEqual(state["route"], "BOUND_DIAGNOSTIC_BRIDGE_TASK")
        self.assertEqual(state["selected_channel"], "ephemeral-github-diagnostic-workflow")

    def test_uncovered_self_provisioned_bridge_routes_to_supervisor_not_owner(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                }
            ],
            self_provisioning_checked=True,
            self_provision_candidates=[
                {
                    "name": "operations-repository-diagnostic-bridge",
                    "provisionable": True,
                    "authority_covered": False,
                }
            ],
        )
        self.assertEqual(state["state"], "DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION")
        self.assertEqual(state["route"], "SUPERVISOR_AUTHORITY_RESOLUTION")

    def test_platform_consent_is_candidate_only_after_noninteractive_exhaustion(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [
                {
                    "name": "cloud-browser",
                    "usable": True,
                    "requires_user_consent": True,
                }
            ],
            self_provisioning_checked=True,
            self_provision_candidates=[],
        )
        self.assertEqual(state["state"], "PLATFORM_CONSENT_REQUIRED")
        self.assertEqual(state["route"], "HUMAN_GATE_CANDIDATE")

    def test_noninteractive_fallback_reenters_access_discovery_when_no_diagnostic_path_remains(self):
        state = reconcile_noninteractive_tool_fallback(
            [
                "native_tool_capability_inventory",
                "workflow_run_metadata",
                "workflow_jobs_steps_logs",
                "workflow_artifacts_checks_annotations",
                "repository_return_path",
                "historical_diagnostic_evidence",
            ],
            [],
            self_provisioning_checked=True,
            self_provision_candidates=[],
        )
        self.assertEqual(state["state"], "NONINTERACTIVE_FALLBACK_EXHAUSTED")
        self.assertEqual(state["route"], "REENTER_ACCESS_DISCOVERY")

    def test_duplicate_wait_run_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_external_ci_wait([101, 101], [])


if __name__ == "__main__":
    unittest.main()
