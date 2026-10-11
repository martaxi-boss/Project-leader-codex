import copy
import json
import unittest
from pathlib import Path

from control.validate_records import (
    validate_checkpoint,
    validate_pair,
    validate_result,
    validate_scope,
    validate_task,
    validate_transition_authorization,
    validate_transition_pair,
    validate_transition_result,
)

ROOT = Path(__file__).resolve().parents[1]

def valid_task():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "project": "TEST",
        "repository": "owner/repo",
        "created_at": "2026-10-02T21:30:00Z",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "Test bounded control task",
            "source": "CURRENT_OWNER_INSTRUCTION",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/test-control-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": ["control/**"],
        "allowed_actions": ["create_branch", "create_commit"],
        "prohibited_actions": ["merge_to_main"],
        "human_gates": [{"action": "merge_to_main", "requires_owner_approval": True}],
        "required_validation": ["unit"],
        "required_ci": ["CI"],
        "terminal_condition": "PR green; no merge.",
        "privacy": {"contains_secrets": False, "contains_private_conversation_text": False},
    }

def valid_result():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "terminal_status": "TERMINAL_SUCCESS",
        "repository": "owner/repo",
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "authorization_record": ".project-leader/tasks/TEST-CONTROL-001.json",
        "implementation_head_sha": "b" * 40,
        "branch": "builder/test-control-001",
        "pr_number": 1,
        "recorded_at": "2026-10-02T21:40:00Z",
        "state_observed_at": "2026-10-02T21:39:00Z",
        "superseded_by": None,
        "post_transition_record": None,
        "changes": ["example"],
        "validation": [{"name": "unit", "status": "PASS", "evidence": "local"}],
        "ci": [{"name": "CI", "status": "SUCCESS", "run_id": 1}],
        "artifacts": [],
        "material_non_effects": ["no merge"],
        "residual_blockers": [],
    }

def valid_v2_task():
    record = valid_task()
    record["schema_version"] = "2.0"
    record["transition_controls"] = [
        {"action": item["action"], "requires_authority_resolution": True}
        for item in record.pop("human_gates")
    ]
    record["integrity_mode"] = "IMMUTABLE_AUTHORIZATION_V1"
    record["recovery"] = {"mode": "APPEND_ONLY_V1"}
    record["policy"] = {
        "binding_mode": "LOCAL_BASE_V1",
        "profile": "project-leader-v1",
        "path": "projects/policies/project-leader.json",
        "base_sha": record["starting_state"]["base_sha"],
        "sha256": "d" * 64,
    }
    return record


def valid_v2_result():
    record = valid_result()
    record["schema_version"] = "2.0"
    record["authorization_commit_sha"] = "c" * 40
    record["authorization_sha256"] = "e" * 64
    return record


def valid_checkpoint():
    return {
        "schema_version": "1.0",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "updated_at": "2026-10-02T21:41:00Z",
        "last_durable_step": "task authorization persisted",
        "action_fingerprint": "TEST-CONTROL-001|owner/repo|ci|run",
        "attempt_count": 1,
        "identical_failure_count": 0,
        "no_progress_iterations": 0,
        "strategy": "run required checks",
        "strategy_generation": 1,
        "last_error": None,
        "next_step": "audit CI",
        "status": "ACTIVE",
    }

def valid_transition_authorization():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-CONTROL-001-MERGE",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "created_at": "2026-10-02T21:50:00Z",
        "action": "merge_to_main",
        "effect_class": "E2_CONSEQUENTIAL_TRANSITION",
        "authority": {
            "source": "CURRENT_OWNER_INSTRUCTION",
            "summary": "Owner authorizes merge of the exact reviewed PR head.",
            "binding_mode": "EXACT_REVISION_BOUND",
        },
        "target": {
            "kind": "pull_request",
            "identifier": "#1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
    }

def valid_transition_result():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-CONTROL-001-MERGE",
        "task_id": "TEST-CONTROL-001",
        "repository": "owner/repo",
        "terminal_status": "SUCCESS",
        "authorization_record": ".project-leader/transitions/TEST-CONTROL-001-MERGE.authorization.json",
        "action": "merge_to_main",
        "target": {
            "kind": "pull_request",
            "identifier": "#1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
        "observed_at": "2026-10-02T21:55:00Z",
        "final_state": {"status": "MERGED", "revision": "c" * 40},
        "evidence": ["PR #1 merged", "main=c"],
        "residual_blockers": [],
    }

class ControlContractTests(unittest.TestCase):
    def assertInvalidTask(self, mutate):
        record = valid_task()
        mutate(record)
        with self.assertRaises(ValueError):
            validate_task(record)

    def assertInvalidResult(self, mutate):
        record = valid_result()
        mutate(record)
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_schemas_are_valid_json_and_require_core_fields(self):
        task = json.loads((ROOT / "control/task-authorization.schema.json").read_text())
        result = json.loads((ROOT / "control/worker-result.schema.json").read_text())
        checkpoint = json.loads((ROOT / "control/recovery-checkpoint.schema.json").read_text())
        transition_auth = json.loads((ROOT / "control/transition-authorization.schema.json").read_text())
        transition_result = json.loads((ROOT / "control/transition-result.schema.json").read_text())
        self.assertIn("task_id", task["required"])
        self.assertIn("transition_controls", task["required"])
        self.assertNotIn("human_gates", task["properties"])
        self.assertIn("implementation_head_sha", result["required"])
        self.assertIn("material_non_effects", result["required"])
        self.assertIn("attempt_count", checkpoint["required"])
        self.assertIn("authority", transition_auth["required"])
        self.assertIn("authorization_record", transition_result["required"])

    def test_plugins_use_same_required_github_connector(self):
        pl = json.loads((ROOT / "plugins/project-leader/.app.json").read_text())
        rg = json.loads((ROOT / "plugins/recovery-guardian/.app.json").read_text())
        self.assertTrue(pl["apps"]["github"]["required"])
        self.assertEqual(pl["apps"]["github"]["id"], rg["apps"]["github"]["id"])

    def test_historical_records_remain_valid(self):
        task = json.loads((ROOT / ".project-leader/tasks/PROJECT-LEADER-CONTROL-HARDENING-003.json").read_text())
        result = json.loads((ROOT / ".project-leader/results/PROJECT-LEADER-CONTROL-HARDENING-003.json").read_text())
        self.assertTrue(validate_task(task))
        self.assertTrue(validate_result(result))

    def test_valid_pair(self):
        self.assertTrue(validate_pair(valid_task(), valid_result()))

    def test_unknown_field_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("unexpected", True))

    def test_invalid_authority_kind_fails(self):
        self.assertInvalidTask(lambda r: r["authority"].__setitem__("kind", "MAGIC"))

    def test_invalid_date_time_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("created_at", "yesterday"))

    def test_duplicate_array_item_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("mutation_scope", ["control/**", "control/**"]))

    def test_malformed_repository_fails(self):
        self.assertInvalidTask(lambda r: r.__setitem__("repository", "owner/repo/extra"))

    def test_nested_unknown_field_fails(self):
        self.assertInvalidTask(lambda r: r["authority"].__setitem__("extra", "nope"))

    def test_legacy_human_gate_false_fails(self):
        self.assertInvalidTask(lambda r: r["human_gates"][0].__setitem__("requires_owner_approval", False))

    def test_active_v2_transition_control_false_fails(self):
        record = valid_v2_task()
        record["transition_controls"][0]["requires_authority_resolution"] = False
        with self.assertRaises(ValueError):
            validate_task(record)

    def test_result_invalid_sha_fails(self):
        self.assertInvalidResult(lambda r: r.__setitem__("implementation_head_sha", "abc"))

    def test_result_unknown_validation_field_fails(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("extra", "nope"))

    def test_terminal_success_with_failed_validation_fails(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("status", "FAIL"))

    def test_terminal_success_with_pending_ci_fails(self):
        self.assertInvalidResult(lambda r: r["ci"][0].__setitem__("status", "PENDING"))

    def test_terminal_success_requires_nonempty_validation(self):
        self.assertInvalidResult(lambda r: r.__setitem__("validation", []))

    def test_terminal_success_requires_positive_pass(self):
        self.assertInvalidResult(lambda r: r["validation"][0].__setitem__("status", "SKIPPED"))

    def test_skipped_validation_requires_justification(self):
        record = valid_result()
        record["validation"].append({"name": "optional", "status": "SKIPPED"})
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_duplicate_validation_name_fails(self):
        record = valid_result()
        record["validation"].append(copy.deepcopy(record["validation"][0]))
        with self.assertRaises(ValueError):
            validate_result(record)

    def test_pair_task_id_mismatch_fails(self):
        result = valid_result()
        result["task_id"] = "OTHER-TASK-001"
        result["authorization_record"] = ".project-leader/tasks/OTHER-TASK-001.json"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_repository_mismatch_fails(self):
        result = valid_result()
        result["repository"] = "owner/other"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_branch_mismatch_fails(self):
        result = valid_result()
        result["branch"] = "builder/other"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_authorization_path_mismatch_fails(self):
        result = valid_result()
        result["authorization_record"] = ".project-leader/tasks/wrong.json"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_pair_pr_mismatch_fails_when_task_binds_pr(self):
        task = valid_task()
        task["starting_state"]["pr_number"] = 99
        with self.assertRaises(ValueError):
            validate_pair(task, valid_result())

    def test_required_validation_cannot_be_skipped(self):
        result = valid_result()
        result["validation"][0]["status"] = "SKIPPED"
        result["validation"].append({"name": "other", "status": "PASS", "evidence": "ok"})
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_required_ci_must_exist(self):
        result = valid_result()
        del result["ci"]
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_required_ci_must_be_success(self):
        result = valid_result()
        result["ci"][0]["status"] = "NOT_APPLICABLE"
        with self.assertRaises(ValueError):
            validate_pair(valid_task(), result)

    def test_scope_validation_accepts_authorized_paths(self):
        self.assertTrue(validate_scope(valid_task(), ["control/validate_records.py", "control/x/y.json"]))

    def test_scope_validation_rejects_outside_paths(self):
        with self.assertRaises(ValueError):
            validate_scope(valid_task(), ["control/validate_records.py", "README.md"])

    def test_checkpoint_limits_are_enforced(self):
        checkpoint = valid_checkpoint()
        self.assertTrue(validate_checkpoint(checkpoint))
        checkpoint["attempt_count"] = 4
        with self.assertRaises(ValueError):
            validate_checkpoint(checkpoint)

    def test_transition_pair_is_exact_revision_bound(self):
        self.assertTrue(validate_transition_pair(valid_transition_authorization(), valid_transition_result()))

    def test_successful_transition_requires_authorization_record(self):
        result = valid_transition_result()
        result["authorization_record"] = None
        with self.assertRaises(ValueError):
            validate_transition_result(result)

    def test_historical_transition_gap_is_recordable_without_fake_authorization(self):
        result = valid_transition_result()
        result["terminal_status"] = "HISTORICAL_OBSERVED"
        result["authorization_record"] = None
        result["residual_blockers"] = ["No durable Owner authorization record exists in the repository."]
        self.assertTrue(validate_transition_result(result))

    def test_transition_authorization_binding_mode_is_exact(self):
        auth = valid_transition_authorization()
        auth["authority"]["binding_mode"] = "OBJECTIVE_SCOPE_BOUND"
        with self.assertRaises(ValueError):
            validate_transition_authorization(auth)

    def test_contracts_reference_durable_authorization(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text()
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text()
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text()
        control = (ROOT / "control/README.md").read_text()
        self.assertIn(".project-leader/tasks/<task-id>.json", project)
        self.assertIn("Task Authorization Record", skill)
        self.assertIn(".project-leader/checkpoints/<task-id>.json", recovery)
        self.assertIn("Consequential transition authorization/result", control)


    def test_v2_central_policy_revision_can_differ_from_target_base(self):
        task = valid_v2_task()
        task["policy"] = {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "managed-v1",
            "path": "projects/policies/managed.json",
            "repository": "owner/control",
            "revision": "c" * 40,
            "sha256": "d" * 64,
        }
        self.assertNotEqual(task["starting_state"]["base_sha"], task["policy"]["revision"])
        self.assertTrue(validate_task(task))

    def test_v2_central_policy_requires_repository_and_revision(self):
        task = valid_v2_task()
        task["policy"] = {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "managed-v1",
            "path": "projects/policies/managed.json",
            "repository": "owner/control",
            "sha256": "d" * 64,
        }
        with self.assertRaises(ValueError):
            validate_task(task)

    def test_blocked_v2_result_can_truthfully_have_no_changes_or_ci(self):
        result = valid_v2_result()
        result["terminal_status"] = "BLOCKED"
        result["changes"] = []
        result["validation"] = []
        result["ci"] = []
        result["residual_blockers"] = ["Central policy binding is unavailable."]
        self.assertTrue(validate_result(result))

    def test_blocked_v2_result_requires_a_residual_blocker(self):
        result = valid_v2_result()
        result["terminal_status"] = "BLOCKED"
        result["changes"] = []
        result["validation"] = []
        result["ci"] = []
        result["residual_blockers"] = []
        with self.assertRaises(ValueError):
            validate_result(result)

    def test_immutable_v2_pair_requires_authorization_digest_and_commit(self):
        task = valid_v2_task()
        result = valid_v2_result()
        del result["authorization_sha256"]
        with self.assertRaises(ValueError):
            validate_pair(task, result)



    def test_skill_resolves_main_merge_through_standing_authority(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Before any merge, inspect the live PR base and exact head.", skill)
        self.assertIn("Development-branch merges remain bounded by explicit `merge_development_branch` task authority.", skill)
        self.assertIn("A merge to `main` remains a consequential transition", skill)
        self.assertIn("it is not by itself a Human Gate", skill)
        self.assertIn("STANDING_OWNER_GRANT", skill)

    def test_project_leader_converges_before_human_gate(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("DETECT -> AUDIT -> CORRECT -> VALIDATE -> CONTINUE", skill)
        self.assertIn("convergence preflight", skill)
        self.assertIn("exhaust covered audit, remediation, reconciliation, CI/evidence repair, recovery, and consequential transitions", skill)
        self.assertIn("A transition-control entry does not mean \"ask the Owner now\"", project)
        self.assertIn("If controls are not yet satisfied, route to Builder/Recovery for remediation and validation.", project)
        self.assertIn("An audit finding is an input to remediation", project)
        self.assertIn("If controls do not yet pass, remediate/recover and revalidate instead of asking the Owner.", runbook)

    def test_project_leader_requires_access_discovery_before_access_human_gate(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")

        for content in (project, runbook, recovery, skill, guardian):
            self.assertIn("FORCED_OPERATIONAL_ACCESS_DISCOVERY", content)
        self.assertIn("Missing a direct shell, SSH client", project)
        self.assertIn("Read-only inspection of an adjacent operational repository does not violate", project)
        self.assertIn("ACCESS_DISCOVERY_INCOMPLETE", runbook)
        self.assertIn("ACCESS_PATH_REQUIRES_SEPARATE_TASK", runbook)
        self.assertIn("ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION", runbook)
        self.assertIn("ACCESS_PATH_UNAVAILABLE", runbook)
        self.assertIn("Search for operational paths, not secret values.", runbook)
        self.assertIn("Test 17 — Forced Operational Access Discovery", smoke)
        self.assertIn("asks the Owner to copy commands into a VPS", smoke)

    def test_project_leader_exhausts_noninteractive_tool_fallback_before_owner_consent(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")

        for content in (project, runbook, recovery, skill, guardian):
            self.assertIn("NONINTERACTIVE_FALLBACK_INCOMPLETE", content)
            self.assertIn("NONINTERACTIVE_PATH_FOUND", content)
            self.assertIn("DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK", content)
            self.assertIn("DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION", content)
            self.assertIn("NONINTERACTIVE_FALLBACK_EXHAUSTED", content)
            self.assertIn("PLATFORM_CONSENT_REQUIRED", content)
        self.assertIn("native capability inventory", project)
        self.assertIn("workflow-run metadata, jobs, step summaries, job logs, run artifacts", project)
        self.assertIn("self-provisioned diagnostics", project)
        self.assertIn("repository-return", project)
        self.assertIn("The Owner must never be used as a routing mechanism", runbook)
        self.assertIn("universal self-provisioning check", recovery)
        self.assertIn("asking the Owner to approve an alternate browser/tool", skill)
        self.assertIn("universal managed-project rule", skill)
        self.assertIn("Test 18 — Non-interactive diagnostic fallback before tool consent", smoke)
        self.assertIn("Test 19 — Universal autonomous diagnostic bridge for future projects", smoke)
        self.assertIn('autorizas usar o navegador?', smoke)
        self.assertIn("pre-existing registry entry", smoke)

    def test_project_leader_recovers_stale_external_ci_wait(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("STALE_WAIT_STATE", project)
        self.assertIn("STALE_WAIT_STATE", runbook)
        self.assertIn("STALE_WAIT_STATE", recovery)
        self.assertIn("STALE_WAIT_STATE", skill)
        self.assertIn("STALE_WAIT_STATE", guardian)
        self.assertIn("exact live run IDs", project)
        self.assertIn("all-success routes immediately to Supervisor audit/validate/continue", recovery)
        self.assertIn("chat/UI spinner", recovery)
        self.assertIn("LIVENESS_RECONCILE_REQUIRED", project)
        self.assertIn("LIVENESS_RECONCILE_REQUIRED", runbook)
        self.assertIn("LIVENESS_RECONCILE_REQUIRED", recovery)
        self.assertIn("LIVENESS_RECONCILE_REQUIRED", skill)
        self.assertIn("LIVENESS_RECONCILE_REQUIRED", guardian)
        self.assertIn("passive Work/UI blocking primitive", project)
        self.assertIn("Active Work liveness guard", recovery)
        self.assertIn("Active Work external-CI liveness", (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8"))

    def test_project_leader_recovers_stalled_internal_operation(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        supervisor = (ROOT / "roles/SUPERVISOR.md").read_text(encoding="utf-8")
        role = (ROOT / "roles/RECOVERY_GUARDIAN.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        skill_recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        guardian_recovery = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/references/recovery-protocol.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")
        builder_prompt = (ROOT / "AGENT_BUILDER_PROMPT.md").read_text(encoding="utf-8")

        for content in (project, runbook, recovery, supervisor, role, skill, skill_recovery, guardian, guardian_recovery, builder_prompt):
            self.assertIn("INTERNAL_OPERATION_STALLED", content)
            self.assertIn("LIVENESS_RECONCILE_REQUIRED", content)

        self.assertIn("legitimate external wait", skill)
        self.assertIn("internal operations", skill)
        self.assertIn("two liveness observations", recovery)
        self.assertIn("existing evidence is already sufficient", skill)
        self.assertIn("smaller/bounded read strategy", runbook)
        self.assertIn("Never retry an ambiguous write merely to test liveness", role)
        self.assertIn("host runtime or connector call itself is frozen", skill)
        self.assertIn("Test 20 — Universal internal-operation liveness", smoke)
        self.assertTrue((ROOT / "control/runtime_execution.py").is_file())
    
    def test_project_leader_uses_bounded_state_preflight_before_broad_internal_reads(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        skill_recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")

        for content in (project, runbook, recovery, skill, skill_recovery):
            self.assertIn("BOUNDED_STATE_PREFLIGHT", content)
            self.assertIn("default-branch HEAD", content)
            self.assertIn("open PRs", content)
            self.assertIn("active workflow runs", content)

        self.assertIn("must not trigger a target-project repository compare/diff", skill)
        self.assertIn("Repository hygiene is background maintenance", skill)
        self.assertIn("enter `LIVENESS_RECONCILE_REQUIRED` immediately", skill)
        self.assertIn("Test 22 — Bounded reconstruction and hygiene separation", smoke)

    def test_project_leader_uses_canonical_runtime_bootstrap_when_loaded_skill_is_stale(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")
        marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))

        for content in (project, runbook, skill):
            self.assertIn("CANONICAL_RUNTIME_BOOTSTRAP", content)
            self.assertIn("RUNTIME_SYNC_STALE", content)
            self.assertIn("RUNTIME_CANONICAL_OVERRIDE_ACTIVE", content)

        self.assertIn("plugins/project-leader/plugin.json", skill)
        self.assertIn("plugins/project-leader/skills/project-leader/SKILL.md", skill)
        self.assertIn("Do not ask the Owner to resync", skill)
        self.assertIn("Test 21 — Canonical runtime bootstrap after marketplace lag", smoke)

        project_leader_entry = next(item for item in marketplace["plugins"] if item["name"] == "project-leader")
        # This marketplace intentionally adopts an already-installed plugin, not a new one.
        self.assertRegex(project_leader_entry["pluginId"], r"^Plugin_[0-9a-f]{32}$")
        self.assertEqual(
            {"source": "local", "path": "./plugins/project-leader"},
            project_leader_entry["source"],
        )
        guardian_entry = next(item for item in marketplace["plugins"] if item["name"] == "recovery-guardian")
        self.assertNotIn("pluginId", guardian_entry)
        self.assertEqual("./plugins/recovery-guardian", guardian_entry["source"]["path"])

    def test_project_leader_compacts_ordinary_e1_recovery_and_keeps_durable_rerun_proof(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")
        control = (ROOT / "control/standing_authority.py").read_text(encoding="utf-8")

        for content in (project, skill, recovery, guardian):
            self.assertIn("Recovery Compaction", content)
            self.assertIn("DERIVED_COMPLETION_AUTHORITY", content)
            self.assertIn("FAIL -> DIAGNOSE -> REMEDIATE -> TEST -> VERIFY -> CONTINUE", content)
        self.assertIn("COMPACT_RECOVERY", control)
        self.assertIn("RECOVERY_REPLAN_REQUIRED", control)
        self.assertIn("run_attempt > 1", recovery)
        self.assertIn("Terminal certification must fail", recovery)
        self.assertIn("retroactive event is invalid", recovery)
        self.assertIn("control-only", project)
        self.assertIn("Test 24 — Universal Recovery Compaction / execution efficiency", smoke)


    def test_legacy_active_checkpoint_requires_live_corroboration(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("STALE_LEGACY_CHECKPOINT", project)
        self.assertIn("STALE_LEGACY_CHECKPOINT", recovery)
        self.assertIn("STALE_LEGACY_CHECKPOINT", skill)
        self.assertIn("STALE_LEGACY_CHECKPOINT", guardian)
        self.assertIn("live branch", recovery)
        self.assertIn("open PR", recovery)

    def test_recovery_preserves_standing_authority_and_only_emits_real_human_gates(self):
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        role = (ROOT / "roles/RECOVERY_GUARDIAN.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        guardian_ref = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/references/recovery-protocol.md").read_text(encoding="utf-8")
        project_ref = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")

        self.assertIn("technical errors, failed CI, unsatisfied controls, stale evidence, ambiguous writes, and bounded justified retries are recovery/remediation work, not Owner authorization requests", recovery)
        self.assertIn("must not discard existing standing authority", role)
        self.assertIn("Recovery preserves the existing standing authority", skill)
        self.assertIn("not Owner permission requests", guardian)
        self.assertNotIn("Legacy checklist label", guardian)
        for text in (recovery, role, guardian, guardian_ref, project_ref):
            self.assertIn("EXCLUSIVE_HUMAN_INTERVENTION", text)
            self.assertIn("NEW_UNCOVERED_MATERIAL_DECISION", text)
        self.assertIn("STANDING_OWNER_GRANT", guardian_ref)
        self.assertIn("STANDING_OWNER_GRANT", project_ref)
        self.assertNotIn("Never automatically cross merge-to-main", guardian_ref)

    def test_evidence_only_descendant_ci_does_not_reopen_task_recovery(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        recovery = (ROOT / "RECOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        skill_recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        guardian = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(encoding="utf-8")
        guardian_recovery = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/references/recovery-protocol.md").read_text(encoding="utf-8")
        for text in (project, runbook, recovery, skill, skill_recovery, guardian, guardian_recovery):
            self.assertIn("evidence-only descendant", text)
        self.assertIn("non-certifying", project)
        self.assertIn("merge-governance condition", runbook)
        self.assertIn("Loss of chat state never authorizes replacement CI", skill)
        self.assertIn("reconstruct the existing run set", guardian_recovery)

    def test_repository_hygiene_is_bounded_to_safe_branch_cleanup(self):
        workflow = (ROOT / ".github/workflows/repository-hygiene.yml").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("- main", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("pull-requests: read", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("github.event.pull_request.head.ref != 'main'", workflow)
        self.assertIn("if (branch.name === 'main') continue;", workflow)
        self.assertIn("state: 'open'", workflow)
        self.assertIn("openPrHeads.has(branch.name)", workflow)
        self.assertIn("delete_owner_authorized_superseded_non_main_branch_refs", workflow)
        self.assertIn("CURRENT_OWNER_INSTRUCTION", workflow)
        self.assertIn("EXACT_REVISION_BOUND", workflow)
        self.assertIn("grants.has(branch.commit.sha)", workflow)
        self.assertIn("no exact live-SHA purge grant", workflow)
        self.assertIn("branch.name.startsWith('control/merge-authorization-')", workflow)
        self.assertIn("durable transition-evidence ref", workflow)
        self.assertIn("merge_base_commit", workflow)
        self.assertIn("mergeBase === branch.commit.sha", workflow)
        self.assertIn("per_page: 1", workflow)
        self.assertIn("not fully contained in main; no exact purge authorization", workflow)
        self.assertIn("--force-with-lease=refs/heads/", workflow)
        self.assertIn("branchHasOpenPull", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertNotIn("github.rest.git.deleteRef", workflow)
        self.assertNotIn("getPathState", workflow)
        self.assertNotIn("branchDelta", workflow)
        self.assertNotIn("deletedByEquivalence", workflow)
        self.assertNotIn("files.length >= 300", workflow)
        self.assertNotIn("byte-identical", runbook)
        self.assertIn("Canonicalizing evidence files alone does not establish ancestry or exact purge authority", runbook)
        self.assertIn("Do not restore broad content-equivalence traversal removed by task 058R", runbook)
        self.assertIn("Verify the live refs after that run before reporting cleanup complete", runbook)
        self.assertIn("Repository hygiene is non-blocking maintenance", runbook)
        self.assertIn("never target `main`", runbook)

    def test_runtime_contract_documents_are_consistent_for_v2_managed_projects(self):
        project = (ROOT / "PROJECT_LEADER.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        builder = (ROOT / "AGENT_BUILDER_PROMPT.md").read_text(encoding="utf-8")
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
        recovery = (ROOT / "plugins/project-leader/skills/project-leader/references/recovery-protocol.md").read_text(encoding="utf-8")
        self.assertIn("CENTRAL_CONTROL_V1", project)
        self.assertIn("CENTRAL_CONTROL_V1", runbook)
        self.assertIn("CENTRAL_CONTROL_V1", builder)
        self.assertIn("CENTRAL_CONTROL_V1", skill)
        self.assertIn("IMMUTABLE_AUTHORIZATION_V1", project)
        self.assertIn("IMMUTABLE_AUTHORIZATION_V1", builder)
        self.assertIn("WAITING_EXTERNAL_CI", recovery)
        self.assertNotIn("whose central profile declares a control contract", builder)


    def test_active_runtime_is_registry_free(self):
        for path in (
            "PROJECT_LEADER.md",
            "RUNBOOK.md",
            "RECOVERY_PROTOCOL.md",
            "AGENT_BUILDER_PROMPT.md",
            "projects/README.md",
            "README.md",
            "PLUGIN_SETUP.md",
            "roles/CONSULTANT.md",
            "roles/SUPERVISOR.md",
            "roles/BUILDER.md",
            "roles/RECOVERY_GUARDIAN.md",
            "plugins/project-leader/skills/project-leader/SKILL.md",
            "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md",
        ):
            text = (ROOT / path).read_text(encoding="utf-8")
            self.assertNotIn("projects/registry.yaml", text, path)

        workflow = (ROOT / ".github/workflows/validate-control-plane.yml").read_text(encoding="utf-8")
        self.assertNotIn("test -f projects/registry.yaml", workflow)
        self.assertNotIn("validate_registry_profile_consistency", workflow)
        self.assertIn("test ! -e projects/registry.yaml", workflow)

    def test_active_task_schema_is_transition_controls_only_and_legacy_v2_is_archived(self):
        active = json.loads((ROOT / "control/task-authorization.schema.json").read_text(encoding="utf-8"))
        legacy = json.loads((ROOT / "control/task-authorization.v2.schema.json").read_text(encoding="utf-8"))
        self.assertIn("transition_controls", active["required"])
        self.assertIn("transition_controls", active["properties"])
        self.assertNotIn("human_gates", active["properties"])
        self.assertIn("human_gates", legacy["required"])
        self.assertIn("human_gates", legacy["properties"])

    def test_final_smoke_contract_requires_autonomous_transition_and_real_human_gate(self):
        smoke = (ROOT / "SMOKE_TESTS.md").read_text(encoding="utf-8")
        self.assertIn("Autonomous covered implementation and transition", smoke)
        self.assertIn("does **not** stop merely to ask whether it may merge", smoke)
        self.assertIn("EXCLUSIVE_HUMAN_INTERVENTION", smoke)
        self.assertIn("NEW_UNCOVERED_MATERIAL_DECISION", smoke)
        self.assertIn("New-project bootstrap without registration", smoke)

    def test_plugin_versions_mark_autonomous_runtime_generation(self):
        project_leader = json.loads((ROOT / "plugins/project-leader/plugin.json").read_text(encoding="utf-8"))
        recovery = json.loads((ROOT / "plugins/recovery-guardian/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(project_leader["version"], "0.7.0")
        self.assertEqual(recovery["version"], "0.6.0")
        self.assertIn("standing authority", project_leader["description"].lower())
        self.assertIn("standing-authority", recovery["description"].lower())

    def test_both_packaged_recovery_references_match_canonical_protocol(self):
        canonical = (ROOT / "RECOVERY_PROTOCOL.md").read_bytes()
        for name in ("project-leader", "recovery-guardian"):
            reference = ROOT / f"plugins/{name}/skills/{name}/references/recovery-protocol.md"
            with self.subTest(plugin=name):
                self.assertEqual(reference.read_bytes(), canonical)



    def test_obsolete_central_project_registry_artifacts_are_removed(self):
        for path in (
            "projects/registry.yaml",
            "projects/policy-profiles.json",
            "projects/pink-iptv.md",
            "projects/fadego.md",
            "projects/vcam-pro.md",
            "projects/policies/pink-iptv.json",
            "projects/policies/fadego.json",
            "projects/policies/vcam-pro.json",
        ):
            self.assertFalse((ROOT / path).exists(), path)

    def test_project_leader_policy_uses_transition_controls_and_allows_final_root_doc_cleanup(self):
        policy = json.loads((ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8"))
        for effect in policy["effect_policies"].values():
            self.assertIn("required_transition_controls", effect)
            self.assertNotIn("required_human_gates", effect)
        e1_scope = set(policy["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]["allowed_scope_patterns"])
        self.assertIn("README.md", e1_scope)
        self.assertIn("PLUGIN_SETUP.md", e1_scope)


if __name__ == "__main__":
    unittest.main()
