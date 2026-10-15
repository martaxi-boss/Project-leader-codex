"""Shared Cloud/VPS phase-continuation contract; offline, no models or secrets."""
from pathlib import Path
import unittest

from codex.agent_policy import RoutingError, next_phase_action, plan

ROOT = Path(__file__).resolve().parents[2]
A = "a" * 40
B = "b" * 40
C = "c" * 40


def _planned():
    tasks = [
        {"id": "prepare", "paths": ["docs/start"],
         "task": "Corrige um typo no README"},
        {"id": "catalog", "paths": ["src/catalog"],
         "task": "Implement movie categories and verify integration tests",
         "depends_on": ["prepare"]},
        {"id": "episodes", "paths": ["src/episodes"],
         "task": "Implement series episodes and run full regression tests",
         "depends_on": ["catalog"]},
    ]
    return plan({
        "request": "Complete the full app improvement objective in every phase",
        "target_repository": "martaxi-boss/pink-iptv",
        "work_items": tasks,
    })


def _verified(candidate):
    return {"status": "validated", "candidate": candidate,
            "certified_candidate": candidate, "validator": "independent_host",
            "evidence": "Verified targeted regression against exact candidate"}


class PhaseContinuationTests(unittest.TestCase):
    def test_complete_plan_includes_all_original_phases_and_effort(self):
        result = _planned()
        self.assertEqual(result["status"], "planned")
        self.assertEqual(result["continuation_policy"],
                         "CONTINUE_ALL_AUTHORIZED_PHASES_AFTER_VALIDATION")
        self.assertEqual([x["id"] for x in result["phase_plan"]],
                         ["prepare", "catalog", "episodes"])
        self.assertEqual([x["sequence"] for x in result["phase_plan"]], [1, 2, 3])
        self.assertEqual(result["phase_plan"][0]["reasoning_effort"], "low")
        self.assertEqual(result["phase_plan"][2]["depends_on"], ["catalog"])
        # Worker count is a resource cap and is NOT a limit on completed phases.
        self.assertLessEqual(result["agent_count"], 2)

    def test_automatically_advances_after_exact_independent_evidence(self):
        planned = _planned()
        self.assertEqual(next_phase_action(planned, {})["phase_id"], "prepare")
        received = {"prepare": _verified(A)}
        action = next_phase_action(planned, received)
        self.assertEqual((action["action"], action["phase_id"]),
                         ("DISPATCH_NEXT", "catalog"))
        received["catalog"] = _verified(B)
        action = next_phase_action(planned, received)
        self.assertEqual((action["action"], action["phase_id"]),
                         ("DISPATCH_NEXT", "episodes"))
        received["episodes"] = _verified(C)
        self.assertEqual(next_phase_action(planned, received),
                         {"action": "FINAL_ACCEPTANCE_AND_PR", "phase_count": 3})

    def test_staged_pr_or_worker_completion_never_masquerades_as_certification(self):
        planned = _planned()
        for status in ("pr_staged", "completed", "awaiting_ci", "awaiting_review"):
            with self.subTest(status=status):
                self.assertEqual(
                    next_phase_action(planned, {"prepare": {"status": status}}),
                    {"action": "WAIT_INDEPENDENT_VALIDATION", "phase_id": "prepare"},
                )
        self.assertEqual(
            next_phase_action(planned, {"prepare": {"status": "in_progress"}}),
            {"action": "WAIT_RUNNING", "phase_id": "prepare"})

    def test_stale_or_worker_self_attested_evidence_not_accepted(self):
        planned = _planned()
        for bad in (
            {"status": "validated", "candidate": A,
             "certified_candidate": B, "validator": "independent_host",
             "evidence": "Wrong SHA"},
            {"status": "validated", "candidate": A,
             "certified_candidate": A, "validator": "worker",
             "evidence": "I passed"},
            {"status": "validated", "candidate": A,
             "certified_candidate": A, "validator": "independent_host",
             "evidence": ""},
        ):
            with self.subTest(bad=bad):
                self.assertEqual(
                    next_phase_action(planned, {"prepare": bad})["action"],
                    "WAIT_INDEPENDENT_VALIDATION")

    def test_recoverable_error_and_true_human_gate_are_distinct(self):
        planned = _planned()
        self.assertEqual(
            next_phase_action(planned, {"prepare": {"status": "failed"}}),
            {"action": "RECOVER_PHASE", "phase_id": "prepare"})
        self.assertEqual(
            next_phase_action(planned, {"prepare": {"status": "human_gate"}}),
            {"action": "HUMAN_GATE", "phase_id": "prepare"})

    def test_never_mix_phases_from_another_owner_order(self):
        with self.assertRaisesRegex(RoutingError, "Unknown phase"):
            next_phase_action(_planned(), {"foreign-job": {"status": "validated"}})
        with self.assertRaises(RoutingError):
            next_phase_action({"status": "needs_scoping"}, {})

    def test_cloud_vps_and_supervisor_contracts_are_not_conflated(self):
        agents = (ROOT / "AGENTS.md").read_text()
        policy = (ROOT / "CODEX_COORDINATION.md").read_text()
        self.assertIn("One Owner order must cover the complete phase cycle", agents)
        self.assertIn("The Cloud task executes directly in Cloud", agents)
        self.assertIn("existing VPS workflow is a", agents)
        self.assertIn("The Supervisor cannot dispatch", policy)
        self.assertIn("PHASE_STAGED_AWAITING_TARGET_CERTIFICATION", policy)
        self.assertIn("Codex Cloud direct Owner task", policy)


if __name__ == "__main__":
    unittest.main()
