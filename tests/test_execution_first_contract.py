import json
import unittest
from pathlib import Path

from control.managed_project_contract import (
    CANCEL_AND_HYGIENIZE,
    CONTINUE_REQUIRED,
    CONTROL_MODE_DURABLE,
    CONTROL_MODE_FAST_E1,
    DIAGNOSIS_BUYS_DECISION,
    FIRST_SUFFICIENT_SAFE_PASS_STOP,
    KEEP_RUNNING,
    FOCUSED_VALIDATION,
    FULL_VALIDATION,
    MATERIAL_VALIDATION_UNCHANGED,
    PROBE_NO_DECISION_VALUE,
    REGRESSION_FIRST,
    SAFE_ROLLBACK,
    SUPERSEDED,
    classify_superseded_work,
    evaluate_diagnostic_probe,
    resolve_control_mode,
    resolve_e1_validation_preflight,
    resolve_regression_strategy,
    resolve_terminal_action,
    resolve_validation_sequence,
)
from control.trusted_gate import verify_fast_path_against_base_policy

ROOT = Path(__file__).resolve().parents[1]


class ExecutionFirstContractTests(unittest.TestCase):
    def test_normal_e1_uses_fast_path_without_durable_records(self):
        decision = resolve_control_mode("E1_RECOVERABLE_PROJECT_LOCAL")
        self.assertEqual(CONTROL_MODE_FAST_E1, decision["mode"])
        self.assertFalse(decision["durable_records_required"])
        self.assertIn("EXECUTE", decision["route"])

    def test_material_boundary_keeps_durable_control(self):
        for kwargs in (
            {"architecture_change": True},
            {"destructive": True},
            {"permission_change": True},
            {"irreversible": True},
            {"ambiguous_write_replay_risk": True},
        ):
            with self.subTest(kwargs=kwargs):
                decision = resolve_control_mode("E1_RECOVERABLE_PROJECT_LOCAL", **kwargs)
                self.assertEqual(CONTROL_MODE_DURABLE, decision["mode"])
                self.assertTrue(decision["durable_records_required"])

    def test_diagnosis_must_buy_a_decision(self):
        useless = evaluate_diagnostic_probe(
            "Which hypothesis is true?",
            ["A", "B"],
            {"A": "apply same fix", "B": "apply same fix"},
        )
        self.assertFalse(useless["execute_probe"])
        self.assertEqual(PROBE_NO_DECISION_VALUE, useless["reason"])

        useful = evaluate_diagnostic_probe(
            "Which subsystem regressed?",
            ["A", "B"],
            {"A": "revert A", "B": "repair B"},
        )
        self.assertTrue(useful["execute_probe"])
        self.assertEqual(DIAGNOSIS_BUYS_DECISION, useful["reason"])

    def test_regression_first_and_safe_rollback(self):
        first = resolve_regression_strategy(
            last_known_good="good",
            first_known_bad="bad",
            recent_change=True,
        )
        self.assertEqual(REGRESSION_FIRST, first["decision"])
        self.assertEqual(["good", "bad"], first["compare"])

        rollback = resolve_regression_strategy(
            last_known_good="good",
            first_known_bad="bad",
            recent_change=True,
            regression_confirmed=True,
        )
        self.assertEqual(SAFE_ROLLBACK, rollback["decision"])


    def test_e1_focuses_validation_before_full_final_certification(self):
        plan = resolve_validation_sequence(
            "E1_RECOVERABLE_PROJECT_LOCAL",
            focused_validation_relevant=True,
            full_validation_required=True,
        )
        self.assertEqual(
            [
                "FOCUSED_VALIDATION",
                "FULL_VALIDATION",
                "FINAL_EXACT_STATE_CERTIFICATION",
            ],
            plan["steps"],
        )
        self.assertEqual("FAST_VALIDATION_BEFORE_FULL_VALIDATION", plan["route"])
        self.assertTrue(plan["full_validation_required"])
        self.assertTrue(plan["final_exact_state_required"])

        security = resolve_validation_sequence(
            "E1_RECOVERABLE_PROJECT_LOCAL",
            focused_validation_relevant=True,
            full_validation_required=False,
            security_or_certification_required=True,
        )
        self.assertIn("FULL_VALIDATION", security["steps"])
        self.assertTrue(security["full_validation_required"])


    def test_focused_preflight_blocks_heavy_ci_until_candidate_passes(self):
        effect = "E1_RECOVERABLE_PROJECT_LOCAL"
        pending = resolve_e1_validation_preflight(
            effect, candidate_revision="working-tree-b"
        )
        self.assertEqual(FOCUSED_VALIDATION, pending["route"])

        stale = resolve_e1_validation_preflight(
            effect,
            candidate_revision="working-tree-b",
            focused_revision="working-tree-a",
            focused_status="PASS",
        )
        self.assertEqual(FOCUSED_VALIDATION, stale["route"])

        failed = resolve_e1_validation_preflight(
            effect,
            candidate_revision="working-tree-b",
            focused_revision="working-tree-b",
            focused_status="FAIL",
        )
        self.assertEqual("RECOVERY_DIRECT_REPAIR", failed["route"])

        passed = resolve_e1_validation_preflight(
            effect,
            candidate_revision="working-tree-b",
            focused_revision="working-tree-b",
            focused_status="PASS",
        )
        self.assertEqual(FULL_VALIDATION, passed["route"])

    def test_focused_preflight_falls_back_when_checks_are_unavailable(self):
        effect = "E1_RECOVERABLE_PROJECT_LOCAL"
        unavailable = resolve_e1_validation_preflight(
            effect, candidate_revision="candidate", focused_validation_available=False
        )
        self.assertEqual(FULL_VALIDATION, unavailable["route"])
        self.assertEqual("FOCUSED_UNAVAILABLE", unavailable["reason"])

        irrelevant = resolve_e1_validation_preflight(
            effect, candidate_revision="candidate", focused_validation_relevant=False
        )
        self.assertEqual(FULL_VALIDATION, irrelevant["route"])

        required = resolve_validation_sequence(
            effect, focused_validation_relevant=False,
            full_validation_required=True, security_or_certification_required=True,
        )
        self.assertIn("FULL_VALIDATION", required["steps"])
        self.assertIn("FINAL_EXACT_STATE_CERTIFICATION", required["steps"])

    def test_focused_preflight_preserves_e2_e3_and_rejects_invalid_evidence(self):
        for effect in ("E2_CONSEQUENTIAL_TRANSITION", "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED"):
            decision = resolve_e1_validation_preflight(
                effect, candidate_revision="candidate"
            )
            self.assertEqual(MATERIAL_VALIDATION_UNCHANGED, decision["route"])
        with self.assertRaises(ValueError):
            resolve_e1_validation_preflight(
                "E1_RECOVERABLE_PROJECT_LOCAL",
                candidate_revision="candidate",
                focused_status="UNKNOWN",
            )
        with self.assertRaises(ValueError):
            resolve_e1_validation_preflight(
                "E1_RECOVERABLE_PROJECT_LOCAL",
                candidate_revision="candidate",
                focused_validation_available="false",
            )

    def test_focused_preflight_keeps_supervisor_and_compact_e1_invariants(self):
        skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(
            encoding="utf-8"
        )
        recovery = (ROOT / "plugins/recovery-guardian/skills/recovery-guardian/SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("resolve_e1_validation_preflight", skill)
        self.assertIn("independent Supervisor audit", skill)
        self.assertIn("no new administrative artifacts", skill)
        self.assertIn("focused-check failure", recovery)

    def test_superseded_heavy_work_auto_cancels_only_when_safe_and_irrelevant(self):
        decision = classify_superseded_work(
            "E1_RECOVERABLE_PROJECT_LOCAL",
            work_revision="a" * 40,
            current_revision="b" * 40,
            heavy_work=True,
            can_certify_current_state=False,
            exclusive_diagnostic_evidence_needed=False,
            cancellation_safe=True,
        )
        self.assertEqual(SUPERSEDED, decision["state"])
        self.assertEqual(CANCEL_AND_HYGIENIZE, decision["action"])

    def test_superseded_work_keeps_running_when_it_can_change_technical_decision(self):
        decision = classify_superseded_work(
            "E1_RECOVERABLE_PROJECT_LOCAL",
            work_revision="a" * 40,
            current_revision="b" * 40,
            heavy_work=True,
            can_certify_current_state=False,
            can_change_technical_decision=True,
            exclusive_diagnostic_evidence_needed=False,
            cancellation_safe=True,
        )
        self.assertEqual(KEEP_RUNNING, decision["action"])
        self.assertEqual(
            "TECHNICAL_DECISION_STILL_RELEVANT",
            decision["reason"],
        )

    def test_superseded_work_keeps_running_for_exclusive_diagnostic_evidence(self):
        decision = classify_superseded_work(
            "E1_RECOVERABLE_PROJECT_LOCAL",
            work_revision="a" * 40,
            current_revision="b" * 40,
            heavy_work=True,
            can_certify_current_state=False,
            exclusive_diagnostic_evidence_needed=True,
            cancellation_safe=True,
        )
        self.assertEqual(KEEP_RUNNING, decision["action"])
        self.assertEqual(
            "EXCLUSIVE_DIAGNOSTIC_EVIDENCE_REQUIRED",
            decision["reason"],
        )

    def test_first_sufficient_safe_pass_stops_optional_adjacent_work(self):
        decision = resolve_terminal_action(
            objective_met=True,
            acceptance_criteria_met=True,
            mandatory_regressions_green=True,
            mandatory_full_validation_passed=True,
            exact_state_certified=True,
            hygiene_complete=True,
            no_known_regression=True,
            no_remaining_required_work=True,
        )
        self.assertEqual(FIRST_SUFFICIENT_SAFE_PASS_STOP, decision["decision"])
        self.assertFalse(decision["execute_optional_work"])

    def test_failed_acceptance_criterion_forces_correction_and_revalidation(self):
        decision = resolve_terminal_action(
            objective_met=True,
            acceptance_criteria_met=False,
            mandatory_regressions_green=True,
            mandatory_full_validation_passed=True,
            exact_state_certified=True,
            hygiene_complete=True,
            no_known_regression=True,
            no_remaining_required_work=True,
        )
        self.assertEqual(CONTINUE_REQUIRED, decision["decision"])
        self.assertIn("acceptance_criteria_met", decision["missing"])

    def test_efficiency_rules_leave_material_e2_e3_controls_unchanged(self):
        for effect_class in (
            "E2_CONSEQUENTIAL_TRANSITION",
            "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED",
        ):
            with self.subTest(effect_class=effect_class):
                control = resolve_control_mode(effect_class)
                self.assertEqual(CONTROL_MODE_DURABLE, control["mode"])

                validation = resolve_validation_sequence(
                    effect_class,
                    focused_validation_relevant=True,
                    full_validation_required=True,
                )
                self.assertEqual(
                    MATERIAL_VALIDATION_UNCHANGED,
                    validation["route"],
                )
                self.assertNotIn("FOCUSED_VALIDATION", validation["steps"])
                self.assertIn("FULL_VALIDATION", validation["steps"])

                work = classify_superseded_work(
                    effect_class,
                    work_revision="a" * 40,
                    current_revision="b" * 40,
                    heavy_work=True,
                    can_certify_current_state=False,
                    exclusive_diagnostic_evidence_needed=False,
                    cancellation_safe=True,
                )
                self.assertEqual(KEEP_RUNNING, work["action"])

    def test_fast_gate_accepts_e1_and_rejects_material_or_control_only_paths(self):
        policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        self.assertTrue(
            verify_fast_path_against_base_policy(
                policy, [{"filename": "tests/example_regression.py"}]
            )
        )
        with self.assertRaisesRegex(ValueError, "material/protected"):
            verify_fast_path_against_base_policy(
                policy, [{"filename": "control/managed_project_contract.py"}]
            )
        with self.assertRaisesRegex(ValueError, "control-only"):
            verify_fast_path_against_base_policy(
                policy,
                [{"filename": ".project-leader/tasks/SHOULD-NOT-EXIST.json"}],
            )

    def test_stale_base_workflow_invalidates_previous_green_head(self):
        trusted = (ROOT / ".github/workflows/trusted-pr-gate.yml").read_text(
            encoding="utf-8"
        )
        stale = (ROOT / ".github/workflows/stale-base-invalidation.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("pull_request_target:", trusted)
        self.assertNotIn("\n  push:\n", trusted)
        self.assertNotIn("invalidate-stale-base:", trusted)
        self.assertIn("live_base_sha", trusted)
        self.assertIn("trusted-authorization", trusted)

        self.assertIn("\n  push:\n", stale)
        self.assertNotIn("pull_request_target:", stale)
        self.assertNotIn("github.event.pull_request", stale)
        self.assertIn("statuses: write", stale)
        self.assertIn("/statuses/$head_sha", stale)
        self.assertIn("context='trusted-authorization'", stale)
        self.assertNotIn("/check-runs", stale)
        self.assertIn("Base advanced; recertification required", stale)

    def test_skill_is_execution_first_and_progressively_loaded(self):
        skill = (
            ROOT / "plugins/project-leader/skills/project-leader/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("EXECUTION_FIRST_WITHIN_BOUNDS", skill)
        self.assertIn("PROGRESS_OVER_PROCESS", skill)
        self.assertIn("FUNCTIONAL_CONVERGENCE_FIRST", skill)
        self.assertIn("DIAGNOSIS_MUST_BUY_A_DECISION", skill)
        self.assertIn("REGRESSION_FIRST", skill)
        self.assertIn("CONTINUOUS_HYGIENE_ACTIVE", skill)
        self.assertIn("FIRST_SUFFICIENT_SAFE_PATH_WINS", skill)
        self.assertIn("Progressive loading", skill)
        self.assertNotIn(
            "persist the authorization-only task commit before implementation", skill
        )

    def test_e3_keeps_merge_and_ruleset_as_separate_consequential_transitions(self):
        policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        e3 = policy["effect_policies"]["E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED"]
        self.assertIn("merge_to_main", e3["required_prohibited_actions"])
        self.assertIn(
            "branch_protection_or_ruleset_change",
            e3["required_prohibited_actions"],
        )
        self.assertIn("merge_to_main", e3["required_transition_controls"])
        self.assertIn("trust_root_mutation", e3["required_transition_controls"])

    def test_version_identity_is_coherent(self):
        leader = json.loads(
            (ROOT / "plugins/project-leader/plugin.json").read_text(encoding="utf-8")
        )
        guardian = json.loads(
            (ROOT / "plugins/recovery-guardian/plugin.json").read_text(encoding="utf-8")
        )
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual("0.7.0", leader["version"])
        self.assertEqual("0.6.0", guardian["version"])
        self.assertIn("0.7.0 / Recovery Guardian 0.6.0", changelog)


if __name__ == "__main__":
    unittest.main()
