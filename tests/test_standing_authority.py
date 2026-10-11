import json
import unittest
from pathlib import Path

from control.standing_authority import (
    CONTINUE_AUTONOMOUSLY,
    CONTINUE_REMEDIATION,
    COMPACT_RECOVERY,
    DERIVED_COMPLETION_AUTHORITY,
    EXCLUSIVE_HUMAN_INTERVENTION,
    HUMAN_GATE,
    NEW_UNCOVERED_MATERIAL_DECISION,
    NORMAL_AUTHORITY_RESOLUTION,
    RECOVERY_REPLAN_REQUIRED,
    RECOVERY_DIRECT_REPAIR,
    RECOVERY_DIRECT_REPLAN,
    CONTINUOUS_HYGIENE_ACTIVE,
    HYGIENE_REPORT_ONLY,
    STANDING_OWNER_GRANT,
    resolve_hygiene_action,
    resolve_next_action,
    resolve_recovery_action,
)
from control.validate_records import validate_standing_authority
from control.managed_project_contract import (
    ACCESS_DISCOVERY_REQUIRED_SURFACES,
    NONINTERACTIVE_DIAGNOSTIC_REQUIRED_SURFACES,
)

ROOT = Path(__file__).resolve().parents[1]


def missing_system(**evidence):
    return resolve_next_action(
        "diagnose_runtime", canonical_effect_covered=True,
        system_can_execute=False, controls_satisfied=True, **evidence,
    )


def complete_access(channels=None):
    return {"searched_surfaces": list(ACCESS_DISCOVERY_REQUIRED_SURFACES),
            "candidate_channels": channels or []}


def complete_fallback(channels=None, bridges=None):
    return {"checked_surfaces": list(NONINTERACTIVE_DIAGNOSTIC_REQUIRED_SURFACES),
            "candidate_channels": channels or [], "self_provisioning_checked": True,
            "self_provision_candidates": bridges or []}


class StandingAuthorityTests(unittest.TestCase):
    def test_canonical_standing_authority_is_machine_valid(self):
        record = json.loads(
            (ROOT / "projects/standing-authority.json").read_text(encoding="utf-8")
        )
        self.assertTrue(validate_standing_authority(record))
        self.assertEqual(record["runtime_scope"], "PROJECT_LEADER_SKILL_RUNTIME")
        self.assertEqual(
            record["autonomy_rule"],
            "ALL_CANONICALLY_COVERED_EXECUTABLE_ACTIONS",
        )
        self.assertEqual(
            set(record["human_gate_conditions"]),
            {
                EXCLUSIVE_HUMAN_INTERVENTION,
                NEW_UNCOVERED_MATERIAL_DECISION,
            },
        )
        self.assertEqual(
            record["project_isolation"],
            "ONE_MUTABLE_TARGET_REPOSITORY_PER_TASK",
        )


    def compact_recovery(self, **overrides):
        args = {
            "objective_authorized": True,
            "standing_delegation_valid": True,
            "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
            "same_project_workstream": True,
        }
        args.update(overrides)
        return resolve_recovery_action(**args)

    def test_recovery_compaction_a_simple_ci_failure(self):
        decision = self.compact_recovery()
        self.assertEqual(decision["decision"], COMPACT_RECOVERY)
        self.assertEqual(decision["authority_kind"], DERIVED_COMPLETION_AUTHORITY)
        self.assertEqual(decision["route"], RECOVERY_DIRECT_REPAIR)
        self.assertEqual(decision["executor"], "RECOVERY_GUARDIAN")
        self.assertFalse(decision["durable_recovery_required"])

    def test_recovery_compaction_b_architecture_change_requires_normal_authority(self):
        decision = self.compact_recovery(architecture_change=True)
        self.assertEqual(decision["decision"], NORMAL_AUTHORITY_RESOLUTION)
        self.assertIsNone(decision["executor"])

    def test_recovery_compaction_c_evident_e1_fix_uses_derived_completion_authority(self):
        decision = self.compact_recovery()
        self.assertEqual(decision["authority_kind"], DERIVED_COMPLETION_AUTHORITY)
        self.assertEqual(decision["authority_source"], STANDING_OWNER_GRANT)
        self.assertEqual(decision["route"], RECOVERY_DIRECT_REPAIR)

    def test_recovery_compaction_d_new_permission_keeps_existing_gate_rules(self):
        self.assertEqual(self.compact_recovery(new_permission_required=True)["decision"], NORMAL_AUTHORITY_RESOLUTION)

    def test_recovery_compaction_e_repeated_no_progress_forces_replan(self):
        decision = self.compact_recovery(no_progress_iterations=3)
        self.assertEqual(decision["decision"], RECOVERY_REPLAN_REQUIRED)
        self.assertEqual(decision["route"], RECOVERY_DIRECT_REPLAN)
        self.assertEqual(decision["executor"], "RECOVERY_GUARDIAN")
        self.assertTrue(decision["durable_recovery_required"])

    def test_blind_same_action_retry_is_blocked_and_replanned(self):
        decision = self.compact_recovery(same_action_retry=True)
        self.assertEqual(decision["decision"], RECOVERY_REPLAN_REQUIRED)
        self.assertEqual(decision["reason"], "BLIND_RETRY_BLOCKED")
        self.assertEqual(decision["route"], RECOVERY_DIRECT_REPLAN)

    def test_same_action_retry_with_material_basis_keeps_durable_causal_journal(self):
        decision = self.compact_recovery(same_action_retry=True, retry_basis="NEW_EVIDENCE")
        self.assertEqual(decision["decision"], COMPACT_RECOVERY)
        self.assertEqual(decision["route"], RECOVERY_DIRECT_REPAIR)
        self.assertTrue(decision["durable_recovery_required"])

    def test_continuous_hygiene_runs_in_same_mutation_cycle(self):
        decision = resolve_hygiene_action(
            mutation_capable=True,
            explicit_read_only=False,
            cleanup_needed=True,
        )
        self.assertEqual(decision["mode"], CONTINUOUS_HYGIENE_ACTIVE)
        self.assertTrue(decision["write_allowed"])
        self.assertTrue(decision["same_cycle"])

    def test_explicit_read_only_hygiene_reports_without_writing(self):
        decision = resolve_hygiene_action(
            mutation_capable=True,
            explicit_read_only=True,
            cleanup_needed=True,
        )
        self.assertEqual(decision["mode"], HYGIENE_REPORT_ONLY)
        self.assertFalse(decision["write_allowed"])
        self.assertFalse(decision["same_cycle"])

    def test_merge_to_main_is_not_a_human_gate_by_action_name(self):
        decision = resolve_next_action(
            "merge_to_main",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=True,
        )
        self.assertEqual(decision["decision"], CONTINUE_AUTONOMOUSLY)
        self.assertEqual(decision["authority_source"], STANDING_OWNER_GRANT)

    def test_unsatisfied_controls_route_to_remediation_not_owner(self):
        decision = resolve_next_action(
            "merge_to_main",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=False,
        )
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["authority_source"], STANDING_OWNER_GRANT)

    def test_missing_tool_alone_cannot_interrupt_owner(self):
        decision = missing_system(convergence_complete=True)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["reason"], "ACCESS_DISCOVERY_INCOMPLETE")
        self.assertEqual(decision["route"], "CONTINUE_DISCOVERY")

    def test_physical_device_test_is_a_gate_after_automated_work_converges(self):
        decision = missing_system(
            convergence_complete=True,
            human_intervention={"kind": "PHYSICAL_DEVICE_TEST",
                                "evidence": "Acceptance requires observation on the Owner's physical device."},
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], EXCLUSIVE_HUMAN_INTERVENTION)

    def test_new_material_decision_requires_owner(self):
        decision = resolve_next_action(
            "change_architecture",
            canonical_effect_covered=True,
            system_can_execute=True,
            controls_satisfied=True,
            new_material_decision=True,
            convergence_complete=True,
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], NEW_UNCOVERED_MATERIAL_DECISION)

    def test_uncovered_effect_requires_new_material_decision(self):
        decision = resolve_next_action(
            "unknown_effect",
            canonical_effect_covered=False,
            system_can_execute=True,
            controls_satisfied=True,
            convergence_complete=True,
        )
        self.assertEqual(decision["decision"], HUMAN_GATE)
        self.assertEqual(decision["reason"], NEW_UNCOVERED_MATERIAL_DECISION)

    def test_human_gate_waits_for_convergence_including_new_material_decisions(self):
        for args in (
            {"canonical_effect_covered": True, "system_can_execute": False,
             "human_intervention": {"kind": "PHYSICAL_DEVICE_TEST", "evidence": "Physical device observation required."}},
            {"canonical_effect_covered": False, "system_can_execute": True},
            {"canonical_effect_covered": True, "system_can_execute": True, "new_material_decision": True},
        ):
            with self.subTest(args=args):
                decision = resolve_next_action("next_step", controls_satisfied=True, **args)
                self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
                self.assertEqual(decision["reason"], "CONVERGENCE_PREFLIGHT_REQUIRED")
                if not args["canonical_effect_covered"] or args.get("new_material_decision"):
                    self.assertIsNone(decision["authority_source"])

    def test_red_ci_is_remediation_even_if_a_later_device_test_requires_owner(self):
        decision = resolve_next_action(
            "physical_device_test", canonical_effect_covered=True,
            system_can_execute=False, controls_satisfied=False, convergence_complete=True,
            human_intervention={"kind": "PHYSICAL_DEVICE_TEST", "evidence": "Physical camera proof required."},
        )
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["reason"], "COVERED_CONTROLS_NOT_YET_SATISFIED")

    def test_missing_ssh_uses_existing_actions_bridge(self):
        decision = missing_system(
            access_discovery=complete_access([{
                "name": "actions-ssh", "usable": True, "requires_mutation": False,
            }]), convergence_complete=True,
        )
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["route"], "CONTINUE")
        self.assertEqual(decision["access_discovery"]["selected_channel"], "actions-ssh")

    def test_operations_bridge_authority_is_resolved_without_owner_prompt(self):
        for covered, expected in ((True, "BOUND_OPERATIONS_TASK"), (False, "SUPERVISOR_AUTHORITY_RESOLUTION")):
            with self.subTest(covered=covered):
                decision = missing_system(access_discovery=complete_access([{
                    "name": "operations-repository", "usable": True,
                    "requires_mutation": True, "authority_covered": covered,
                }]), convergence_complete=True)
                self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
                self.assertEqual(decision["route"], expected)

    def test_one_missing_connector_method_uses_native_diagnostics(self):
        decision = missing_system(diagnostic_fallback={
            "candidate_channels": [{"name": "job-logs", "usable": True}],
        }, convergence_complete=True)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["reason"], "NONINTERACTIVE_PATH_FOUND")

    def test_access_exhaustion_still_requires_diagnostics_and_self_provisioning(self):
        decision = missing_system(access_discovery=complete_access(), convergence_complete=True)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["reason"], "NONINTERACTIVE_FALLBACK_INCOMPLETE")
        fallback = complete_fallback()
        fallback["self_provisioning_checked"] = False
        decision = missing_system(access_discovery=complete_access(), diagnostic_fallback=fallback)
        self.assertEqual(decision["diagnostic_fallback"]["missing_surfaces"], ["self_provisioned_diagnostic_bridge"])

    def test_provisionable_diagnostic_bridge_defeats_platform_consent_gate(self):
        for covered, expected in ((True, "BOUND_DIAGNOSTIC_BRIDGE_TASK"), (False, "SUPERVISOR_AUTHORITY_RESOLUTION")):
            with self.subTest(covered=covered):
                decision = missing_system(
                    access_discovery=complete_access(), convergence_complete=True,
                    diagnostic_fallback=complete_fallback(
                        [{"name": "interactive-consent", "usable": True, "requires_user_consent": True}],
                        [{"name": "temporary-diagnostic-workflow", "provisionable": True, "authority_covered": covered}],
                    ),
                    human_intervention={"kind": "PLATFORM_CONSENT_REQUIRED", "evidence": "Platform offers an interactive prompt."},
                )
                self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
                self.assertEqual(decision["route"], expected)

    def test_exhausted_preflights_need_an_exact_human_action_and_convergence(self):
        evidence = dict(access_discovery=complete_access(), diagnostic_fallback=complete_fallback(),
                        post_fallback_access_discovery=complete_access())
        decision = missing_system(convergence_complete=True, **evidence)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["reason"], "HUMAN_INTERVENTION_EVIDENCE_REQUIRED")
        evidence["human_intervention"] = {"kind": "ACCESS_PATH_UNAVAILABLE", "evidence": "Only Owner can grant the missing account capability."}
        self.assertEqual(missing_system(**evidence)["reason"], "CONVERGENCE_PREFLIGHT_REQUIRED")
        self.assertEqual(missing_system(convergence_complete=True, **evidence)["decision"], HUMAN_GATE)

    def test_mfa_is_a_gate_only_after_both_preflights_close(self):
        evidence = dict(
            convergence_complete=True,
            human_intervention={"kind": "PLATFORM_CONSENT_REQUIRED", "evidence": "Provider requires Owner account MFA confirmation."},
            diagnostic_fallback=complete_fallback([{
                "name": "provider-mfa", "usable": True, "requires_user_consent": True,
            }]),
        )
        self.assertEqual(missing_system(**evidence)["decision"], CONTINUE_REMEDIATION)
        decision = missing_system(access_discovery=complete_access(), **evidence)
        self.assertEqual(decision["decision"], HUMAN_GATE)

    def test_claimed_preflight_state_is_not_closure_evidence(self):
        for field in ("access_discovery", "diagnostic_fallback", "post_fallback_access_discovery"):
            evidence = {"access_discovery": complete_access(), "diagnostic_fallback": complete_fallback(),
                        field: {"state": "EXHAUSTED"}}
            with self.subTest(field=field), self.assertRaises(ValueError):
                missing_system(**evidence)

    def test_diagnostic_exhaustion_requires_fresh_access_reentry_before_any_gate(self):
        evidence = dict(
            access_discovery=complete_access(), diagnostic_fallback=complete_fallback(),
            convergence_complete=True,
            human_intervention={"kind": "ACCESS_PATH_UNAVAILABLE", "evidence": "Owner account capability is required."},
        )
        decision = missing_system(**evidence)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["route"], "REENTER_ACCESS_DISCOVERY")
        decision = missing_system(post_fallback_access_discovery={}, **evidence)
        self.assertEqual(decision["reason"], "ACCESS_DISCOVERY_INCOMPLETE")
        decision = missing_system(post_fallback_access_discovery=complete_access([{
            "name": "newly-discovered-operations-path", "usable": True,
        }]), **evidence)
        self.assertEqual(decision["decision"], CONTINUE_REMEDIATION)
        self.assertEqual(decision["route"], "CONTINUE")
        decision = missing_system(post_fallback_access_discovery=complete_access(), **evidence)
        self.assertEqual(decision["decision"], HUMAN_GATE)

    def test_technical_failures_cannot_masquerade_as_manual_intervention(self):
        for record in (
            {"kind": "CI_FAILURE", "evidence": "CI is red."},
            {"kind": "PHYSICAL_DEVICE_TEST", "evidence": " "},
            {"kind": [], "evidence": "invalid"},
            {"kind": "HARDWARE_INTERACTION", "evidence": "Press a physical button.", "trusted": True},
        ):
            with self.subTest(record=record), self.assertRaises(ValueError):
                missing_system(human_intervention=record)

    def test_preflight_boolean_flags_are_strict(self):
        with self.assertRaises(ValueError):
            missing_system(access_discovery={"direct_access_available": "false"})
        with self.assertRaises(ValueError):
            missing_system(convergence_complete="true")


if __name__ == "__main__":
    unittest.main()
