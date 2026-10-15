"""No-Codex, no-network checks for automatic phases and all-project stop gates."""
import tempfile
from pathlib import Path
from unittest import mock
import unittest

from codex.agent_policy import RoutingError
from codex.phase_cycle import (
    PhaseCycleError, validated_phases, execute_until_terminal,
    GATE, PENDING, QUOTA, RECOVERY, TERMINAL, CERTIFIED,
)

BASE = "a" * 40
SECOND = "b" * 40
THIRD = "c" * 40
FOURTH = "d" * 40


def item(name, path, depends=None):
    return {"id": name, "task": "Implement module and verify all mandatory regression tests",
            "paths": [path], "depends_on": depends or []}


class PhaseCycleTests(unittest.TestCase):
    def setUp(self):
        self.dependent = validated_phases([
            item("one", "src/one.py"), item("two", "src/two.py", ["one"]),
            item("three", "src/three.py", ["two"]),
        ], [
            {"task_ids": ["one"], "mode": "single", "reasoning_by_task": {"one": "low"}},
            {"task_ids": ["two"], "mode": "single", "reasoning_by_task": {"two": "medium"}},
            {"task_ids": ["three"], "mode": "single", "reasoning_by_task": {"three": "high"}},
        ])
        self.head = BASE
        self.executed = []
        self.notices = []

    def checked_head(self):
        return self.head

    def execute(self, phase, base):
        self.executed.append((phase.number, phase.task_ids, base))
        return {"status": "WORKERS_COMPLETED", "worker_ids": ["codex-1"]}

    def success(self, phase, worker, before):
        self.head = [BASE, SECOND, THIRD, FOURTH][phase.number]
        return {"status": "PHASE_CERTIFIED", "accepted_sha": self.head,
                "exact_ci": True, "independent_review": True,
                "material_gate": False}

    def drive(self, certify=None, executor=None):
        return execute_until_terminal(
            self.dependent, checked_head=self.checked_head,
            run_phase=executor or self.execute,
            certify_phase=certify or self.success,
            notify=self.notices.append)

    def test_preplanned_three_phases_finish_without_new_owner_order(self):
        result = self.drive()
        self.assertEqual(result["status"], TERMINAL)
        self.assertEqual(result["target_sha"], FOURTH)
        self.assertEqual([p[0] for p in self.executed], [1, 2, 3])
        self.assertEqual([p[2] for p in self.executed], [BASE, SECOND, THIRD])
        self.assertEqual([p["status"] for p in self.notices],
                         [CERTIFIED, CERTIFIED, TERMINAL])
        self.assertEqual([p.task_ids for p in self.dependent],
                         [("one",), ("two",), ("three",)])

    def test_two_disjoint_tasks_can_share_a_phase_but_coordinator_chooses_agents(self):
        phases = validated_phases([
            item("a", "src/a.py"), item("b", "src/b.py"),
            item("c", "src/c.py", ["a", "b"]),
        ], [
            {"task_ids": ["a", "b"], "mode": "parallel",
             "reasoning_by_task": {"a": "high", "b": "low"}},
            {"task_ids": ["c"], "mode": "single", "reasoning_by_task": {"c": "medium"}},
        ])
        self.assertEqual([p.task_ids for p in phases], [("a", "b"), ("c",)])
        self.assertEqual(phases[0].work_items[0]["depends_on"], [])
        self.assertEqual(phases[1].work_items[0]["depends_on"], [])
        self.assertEqual(phases[0].reasoning_by_task, (("a", "high"), ("b", "low")))
        self.assertEqual(phases[0].mode, "parallel")

    def test_overlapping_tasks_never_parallelize(self):
        with self.assertRaisesRegex(PhaseCycleError, "Overlapping"):
            validated_phases([item("a", "src/foo"), item("b", "src/foo/bar")], [
                {"task_ids": ["a", "b"], "mode": "parallel",
                 "reasoning_by_task": {"a": "medium", "b": "medium"}},
            ])

    def test_actual_human_gate_stops_entire_project(self):
        def gated(phase, worker, before):
            return {"status": GATE, "reason": "OWNER_PHYSICAL_DEVICE_CONFIRMATION"}
        result = self.drive(certify=gated)
        self.assertEqual(result["status"], GATE)
        self.assertEqual(result["next_phase"], 1)
        self.assertEqual(len(self.executed), 1)
        self.assertEqual(len(self.notices), 1)

    def test_staged_pr_and_skipped_ci_do_not_start_phase_two(self):
        for cert in (
                {"status": PENDING},
                {"status": "PHASE_CERTIFIED", "accepted_sha": SECOND,
                 "exact_ci": False, "independent_review": True,
                 "material_gate": False},
                {"status": "PHASE_CERTIFIED", "accepted_sha": SECOND,
                 "exact_ci": True, "independent_review": False,
                 "material_gate": False}):
            with self.subTest(cert=cert):
                self.executed.clear(); self.notices.clear(); self.head = BASE
                result = self.drive(certify=lambda *_: cert)
                self.assertNotEqual(result["status"], TERMINAL)
                self.assertEqual([n[0] for n in self.executed], [1])
                self.assertEqual(result["next_phase"], 1)

    def test_failed_worker_and_quota_stop_without_starting_dependents(self):
        for reported, required in (("failed", RECOVERY), (QUOTA, QUOTA)):
            with self.subTest(reported=reported):
                self.executed.clear(); self.notices.clear(); self.head = BASE
                def failed(phase, base):
                    self.executed.append(phase.number)
                    return {"status": reported, "worker_ids": []}
                result = self.drive(executor=failed)
                self.assertEqual(result["status"], required)
                self.assertEqual(self.executed, [1])

    def test_external_revision_drift_is_blocking_even_after_success(self):
        def drifting(phase, worker, before):
            self.head = THIRD
            return {"status": "PHASE_CERTIFIED", "accepted_sha": SECOND,
                    "exact_ci": True, "independent_review": True,
                    "material_gate": False}
        result = self.drive(certify=drifting)
        self.assertEqual(result["status"], RECOVERY)
        self.assertEqual([p[0] for p in self.executed], [1])

    def test_no_unauthorized_empty_or_cyclic_phase_plan(self):
        with self.assertRaises(PhaseCycleError):
            validated_phases([], [])
        with self.assertRaises(PhaseCycleError):
            validated_phases([item("a", "src/a.py", ["b"]),
                              item("b", "src/b.py", ["a"])], [
                {"task_ids": ["a"], "mode": "single", "reasoning_by_task": {"a": "low"}},
                {"task_ids": ["b"], "mode": "single", "reasoning_by_task": {"b": "low"}},
            ])
        with self.assertRaises(PhaseCycleError):
            validated_phases([item("a", "src/a.py", ["unknown"])], [
                {"task_ids": ["a"], "mode": "single", "reasoning_by_task": {"a": "low"}},
            ])
        with self.assertRaises(PhaseCycleError):
            validated_phases([item("a", "src/a.py"), item("a", "src/b.py")], [
                {"task_ids": ["a"], "mode": "single", "reasoning_by_task": {"a": "low"}},
            ])

    def test_no_certifier_or_head_observer_never_executes(self):
        with self.assertRaises(PhaseCycleError):
            execute_until_terminal(self.dependent, checked_head=self.checked_head,
                                   run_phase=self.execute, certify_phase=None)
        self.assertEqual(self.executed, [])

    def test_cloud_api_automatically_runs_all_coordinator_phases_when_certified(self):
        from codex import smart
        plan_order = {
            "request": "Implement and test the three dependent modules safely",
            "target_repository": "martaxi-boss/pink-iptv",
            "work_items": [item("one", "src/one.py"),
                           item("two", "src/two.py", ["one"]),
                           item("three", "src/three.py", ["two"])],
            "phases": [
                {"task_ids": [p.task_ids[0]], "mode": p.mode,
                 "reasoning_by_task": {p.task_ids[0]: "medium"}}
                for p in self.dependent],
        }
        heads = iter([BASE, BASE, SECOND, SECOND, THIRD, THIRD, FOURTH])
        selected = []
        accepted = []
        def fake_selector(order):
            selected.append(order)
            return {"status": "planned", "mode": order["preference"]}
        def fake_execute(*args, **kwargs):
            return {"workers": [{"id": "worker-" + str(len(selected)),
                                  "status": "completed"}]}
        def certify(phase, outcome, before):
            accepted.append(phase.number)
            return {"status": "PHASE_CERTIFIED", "accepted_sha":
                    [BASE, SECOND, THIRD, FOURTH][phase.number],
                    "exact_ci": True, "independent_review": True,
                    "material_gate": False}
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(smart.dual, "_preflight", return_value=BASE), \
                    mock.patch.object(smart.dual, "_git", side_effect=lambda *_: next(heads)), \
                    mock.patch.object(smart, "plan", side_effect=fake_selector), \
                    mock.patch.object(smart, "execute", side_effect=fake_execute):
                result = smart.execute_coordinator_phases(
                    plan_order, Path(temporary), trusted_certifier=certify)
        self.assertEqual(result["status"], TERMINAL)
        self.assertEqual(accepted, [1, 2, 3])
        self.assertEqual(len(selected), 3)
        self.assertEqual([z["work_items"][0]["id"] for z in selected],
                         ["one", "two", "three"])
        self.assertTrue(all(z["preference"] == "single" for z in selected))

    def test_cloud_api_without_trusted_certifier_never_starts_workers(self):
        from codex import smart
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(smart, "execute") as executor:
                with self.assertRaisesRegex(RoutingError, "certification|required"):
                    smart.execute_coordinator_phases({}, Path(directory), trusted_certifier=None)
                executor.assert_not_called()


if __name__ == "__main__":
    unittest.main()