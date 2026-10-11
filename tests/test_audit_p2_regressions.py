import copy
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from control.managed_project_contract import (
    classify_external_ci,
    decide_ci_dispatch,
    policy_sha256,
    reconcile_legacy_checkpoint_liveness,
    reconcile_operational_access_discovery,
    reconcile_external_ci_wait,
    verify_managed_task_against_control_policy,
)
from control.runtime_execution import (
    AMBIGUOUS_WRITE_RECONCILED,
    EFFECT_ALREADY_APPLIED,
    ExecutionTrace,
    bounded_state_preflight,
    execute_verified_effect,
    reconcile_internal_operation,
    run_external_ci_cycle,
)
from control.validate_records import (
    validate_project_policy,
    validate_standing_authority,
    validate_task,
)

ROOT = Path(__file__).resolve().parents[1]
CONTROL_REPOSITORY = "martaxi-boss/Project-leader"
TARGET_REPOSITORY = "owner/project"


def valid_task():
    return {
        "schema_version": "2.0",
        "task_id": "TASK-P2-001",
        "project": "TEST",
        "repository": TARGET_REPOSITORY,
        "created_at": "2026-10-07T09:00:00Z",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
            "summary": "bounded test task",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/task-p2-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["src/app.py"],
        "allowed_actions": ["edit_project_files"],
        "prohibited_actions": [
            "merge_to_main",
            "branch_protection_or_ruleset_change",
            "release_or_publish",
            "production_deploy",
            "destructive_data_change",
            "repository_or_history_deletion",
            "production_secret_change",
            "irreversible_infrastructure_change",
            "paid_service_activation",
        ],
        "required_validation": [
            "Project architecture scope audit",
            "Mutation scope audit",
            "GitHub evidence verification",
        ],
        "required_ci": [],
        "policy": {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "generic-project-v1",
            "path": "control/generic-project-policy.json",
            "repository": CONTROL_REPOSITORY,
            "revision": "c" * 40,
            "sha256": "d" * 64,
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "done",
        "privacy": {
            "contains_secrets": False,
            "contains_private_conversation_text": False,
        },
        "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        "transition_controls": [
            {"action": action, "requires_authority_resolution": True}
            for action in (
                "merge_to_main",
                "branch_protection_or_ruleset_change",
                "release_or_publish",
                "production_deploy",
                "destructive_data_change",
                "repository_or_history_deletion",
                "production_secret_change",
                "irreversible_infrastructure_change",
                "paid_service_activation",
            )
        ],
    }


def managed_task_for_path(path, policy_raw):
    task = valid_task()
    task["mutation_scope"] = [path]
    task["policy"]["sha256"] = policy_sha256(policy_raw)
    return task


def legacy_checkpoint():
    return {
        "schema_version": "1.0",
        "task_id": "LEGACY-P2-001",
        "repository": TARGET_REPOSITORY,
        "updated_at": "2026-10-07T09:00:00Z",
        "last_durable_step": "read state",
        "action_fingerprint": "legacy|p2",
        "attempt_count": 1,
        "identical_failure_count": 0,
        "no_progress_iterations": 0,
        "strategy": "reconstruct",
        "strategy_generation": 1,
        "last_error": None,
        "next_step": "continue",
        "status": "ACTIVE",
    }


class AuditP2SemanticTests(unittest.TestCase):
    def test_fixed_policy_rejects_partial_active_target_mode(self):
        policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        policy["repository_mode"] = "ACTIVE_TARGET"
        with self.assertRaisesRegex(ValueError, "partial or mixed"):
            validate_project_policy(policy)

    def test_valid_fixed_and_dynamic_policies_remain_valid(self):
        fixed = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        dynamic = json.loads(
            (ROOT / "control/generic-project-policy.json").read_text(encoding="utf-8")
        )
        self.assertTrue(validate_project_policy(fixed))
        self.assertTrue(validate_project_policy(dynamic))

    def test_generic_policy_protects_root_secrets_and_nested_env(self):
        policy_raw = (ROOT / "control/generic-project-policy.json").read_bytes()
        policy = json.loads(policy_raw)
        for path in ("secrets.json", "services/api/.env.production"):
            task = managed_task_for_path(path, policy_raw)
            with self.assertRaisesRegex(ValueError, "protected paths"):
                verify_managed_task_against_control_policy(
                    task,
                    policy,
                    policy_raw,
                    actual_target_base_sha="a" * 40,
                    changed_files=[path],
                    control_repository=CONTROL_REPOSITORY,
                    control_revision="c" * 40,
                    expected_policy_path="control/generic-project-policy.json",
                )

    def test_boolean_const_does_not_accept_integer_one(self):
        task = valid_task()
        task["transition_controls"][0]["requires_authority_resolution"] = 1
        with self.assertRaisesRegex(ValueError, "expected constant True"):
            validate_task(task)

    def test_task_id_trailing_newline_is_rejected(self):
        task = valid_task()
        task["task_id"] = "TASK-P2-001\n"
        with self.assertRaisesRegex(ValueError, "does not match pattern"):
            validate_task(task)

    def test_basic_iso_datetime_is_rejected_in_favor_of_rfc3339(self):
        task = valid_task()
        task["created_at"] = "20261007T090000+00:00"
        with self.assertRaisesRegex(ValueError, "RFC3339"):
            validate_task(task)

    def test_standing_authority_requires_the_full_canonical_control_set(self):
        record = json.loads(
            (ROOT / "projects/standing-authority.json").read_text(encoding="utf-8")
        )
        record["required_controls"] = ["invented_control"]
        with self.assertRaises(ValueError):
            validate_standing_authority(record)

    def test_versioned_schema_ids_are_unique(self):
        paths = [
            "control/task-authorization.schema.json",
            "control/task-authorization.v1.schema.json",
            "control/task-authorization.v2.schema.json",
            "control/worker-result.schema.json",
            "control/worker-result.v1.schema.json",
        ]
        ids = [
            json.loads((ROOT / path).read_text(encoding="utf-8"))["$id"]
            for path in paths
        ]
        self.assertEqual(len(ids), len(set(ids)))

    def test_false_text_is_not_treated_as_boolean_access_evidence(self):
        with self.assertRaisesRegex(ValueError, "direct_access_available must be boolean"):
            reconcile_operational_access_discovery([], [], direct_access_available="false")
        with self.assertRaisesRegex(ValueError, "has_live_branch must be boolean"):
            reconcile_legacy_checkpoint_liveness(
                legacy_checkpoint(), has_live_branch="false"
            )

    def test_hygiene_sweep_caches_task_record_reads(self):
        workflow = (ROOT / ".github/workflows/repository-hygiene.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("const taskCache = new Map();", workflow)
        self.assertIn("async function readTaskOnce(taskPath)", workflow)
        self.assertIn("const task = await readTaskOnce(taskPath);", workflow)

    def test_maintenance_docs_record_event_policy_and_license_boundary(self):
        sources = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        setup = (ROOT / "PLUGIN_SETUP.md").read_text(encoding="utf-8")

        self.assertIn("2026-11-02", sources)
        self.assertIn("pull_request_target", runbook)
        self.assertIn("Report a vulnerability", security)
        self.assertIn("plugin-manifest.json", setup)
        self.assertIn("proprietary / All Rights Reserved", changelog)
        self.assertNotIn("Owner has not chosen a project license", changelog)

    def test_ci_payload_requires_real_positive_run_id_and_progress_time(self):
        base = {
            "name": "Project CI",
            "head_sha": "a" * 40,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-07T09:00:00Z",
        }
        for invalid_id in (True, None, 0):
            run = dict(base, id=invalid_id)
            with self.assertRaises(ValueError):
                decide_ci_dispatch(
                    "Project CI", "a" * 40, "workflow_dispatch", [run]
                )

        active = dict(base, id=101, status="in_progress", conclusion=None)
        active.pop("created_at")
        with self.assertRaisesRegex(ValueError, "progress timestamp"):
            classify_external_ci(active)

        with self.assertRaises(ValueError):
            reconcile_external_ci_wait([True], [])


class AuditP2ObservableRuntimeTests(unittest.TestCase):
    def test_bounded_preflight_has_observable_minimum_read_sequence(self):
        calls = []
        state, trace = bounded_state_preflight(
            lambda: calls.append("head") or "a" * 40,
            lambda: calls.append("prs") or [],
            lambda: calls.append("runs") or [],
            lambda: calls.append("task") or "b" * 40,
        )
        self.assertEqual(["head", "prs", "runs", "task"], calls)
        self.assertEqual("a" * 40, state["default_head"])
        self.assertEqual(
            [
                "READ_DEFAULT_HEAD",
                "READ_OPEN_PRS",
                "READ_ACTIVE_RUNS",
                "READ_TASK_HEAD",
                "BOUNDED_STATE_PREFLIGHT_COMPLETE",
            ],
            [item["event"] for item in trace.events],
        )

    def test_two_no_progress_observations_route_to_liveness_reconcile(self):
        first = reconcile_internal_operation(
            prior_progress_token="same",
            current_progress_token="same",
            prior_stall_observations=0,
        )
        self.assertEqual("OBSERVE_AGAIN", first["route"])
        second = reconcile_internal_operation(
            prior_progress_token="same",
            current_progress_token="same",
            prior_stall_observations=first["stall_observations"],
        )
        self.assertEqual("INTERNAL_OPERATION_STALLED", second["state"])
        self.assertEqual("LIVENESS_RECONCILE_REQUIRED", second["route"])

    def test_lost_write_response_is_reconciled_and_restart_does_not_duplicate_effect(self):
        durable = {"applied": False, "writes": 0}

        def observe(_key):
            return durable["applied"]

        def perform(_key):
            durable["writes"] += 1
            durable["applied"] = True
            raise ConnectionError("response lost after durable write")

        first = execute_verified_effect("merge:76", observe, perform)
        self.assertEqual(AMBIGUOUS_WRITE_RECONCILED, first["state"])
        self.assertEqual(1, durable["writes"])

        restarted = execute_verified_effect("merge:76", observe, perform)
        self.assertEqual(EFFECT_ALREADY_APPLIED, restarted["state"])
        self.assertFalse(restarted["performed"])
        self.assertEqual(1, durable["writes"])

    def test_timeout_without_observed_effect_is_not_blindly_retried(self):
        durable = {"applied": False, "writes": 0}

        def observe(_key):
            return durable["applied"]

        def perform(_key):
            durable["writes"] += 1
            raise TimeoutError("provider timeout before durable effect")

        with self.assertRaises(TimeoutError):
            execute_verified_effect("deploy:test", observe, perform)
        self.assertEqual(1, durable["writes"])
        self.assertFalse(durable["applied"])

    def test_active_ci_without_progress_baseline_requires_reconciliation(self):
        now = datetime(2026, 10, 7, 9, 5, tzinfo=timezone.utc)
        state = run_external_ci_cycle(
            [101],
            lambda ids: [{
                "id": 101,
                "status": "in_progress",
                "conclusion": None,
                "updated_at": "2026-10-07T09:04:00Z",
            }],
            now=now,
        )
        self.assertEqual("LIVENESS_RECONCILE_REQUIRED", state["state"])
        self.assertEqual("INVESTIGATE", state["route"])
        self.assertEqual("ESTABLISH_PROGRESS_BASELINE", state["liveness_action"])

    def test_ci_cycle_waits_for_active_run_and_routes_failed_run_to_recovery(self):
        now = datetime(2026, 10, 7, 9, 5, tzinfo=timezone.utc)
        active = run_external_ci_cycle(
            [101],
            lambda ids: [{
                "id": 101,
                "status": "in_progress",
                "conclusion": None,
                "updated_at": "2026-10-07T09:04:00Z",
            }],
            last_progress_at="2026-10-07T09:04:00Z",
            now=now,
        )
        self.assertEqual("WAITING_EXTERNAL_CI", active["state"])
        self.assertEqual("WAIT", active["route"])

        failed = run_external_ci_cycle(
            [101],
            lambda ids: [{
                "id": 101,
                "status": "completed",
                "conclusion": "failure",
            }],
            now=now,
        )
        self.assertEqual("STALE_WAIT_STATE", failed["state"])
        self.assertEqual("RECOVERY", failed["route"])


if __name__ == "__main__":
    unittest.main()
