"""Prelaunch failures release reservations; attempted workers retain a charge."""
import json
from pathlib import Path
import unittest
from unittest import mock

from codex import smart
from codex.agent_policy import RoutingError, plan
from codex.tests import test_dual as fixtures

task = fixtures.task


class PrelaunchAccountingTests(unittest.TestCase):
    setUp = fixtures.RunnerTests.setUp

    def planned(self, mode):
        tasks = [task("first", "docs/channels", "Implement channel navigation and test integration")]
        if mode != "single":
            tasks.append(task("second", "docs/movies", "Implement movie navigation and test integration"))
            if mode == "serial":
                tasks[1]["depends_on"] = ["first"]
        return plan({"request": "Implement bounded modules and validate tests",
                     "target_repository": "martaxi-boss/pink-iptv",
                     "preference": mode, "work_items": tasks})

    def records(self):
        return json.loads((self.runs / ".shared-budget/usage.json").read_text())["records"]

    def test_clone_failure_releases_all_unstarted_workers_in_every_mode(self):
        for mode in ("single", "serial", "parallel"):
            with self.subTest(mode=mode):
                before = len(self.records()) if (self.runs / ".shared-budget/usage.json").exists() else 0
                with mock.patch.object(smart.dual, "_private_clone", side_effect=OSError("clone setup failed")):
                    with mock.patch.object(smart.dual, "_invoke_codex") as invoke:
                        with self.assertRaises((RoutingError, smart.dual.PlanError)):
                            smart.execute(self.planned(mode), self.repo, self.runs, timeout=30,
                                          phase_one_validator=lambda *args: {"passed": True, "evidence": "test"})
                invoke.assert_not_called()
                records = self.records()[before:]
                self.assertEqual(len(records), 1 if mode == "single" else 2)
                self.assertTrue(all(r["actual"] == 0 and r.get("not_started") for r in records))

    def test_invalid_dual_order_after_reservation_releases_all_workers(self):
        planned = self.planned("parallel")
        planned["tasks"][0]["paths"] = ["../outside"]
        with mock.patch.object(smart.dual, "run") as run:
            with self.assertRaises(smart.dual.PlanError):
                smart.execute(planned, self.repo, self.runs, timeout=30)
        run.assert_not_called()
        self.assertTrue(all(r["actual"] == 0 and r.get("not_started") for r in self.records()))

    def test_cancelled_before_launch_is_not_charged(self):
        planned = self.planned("single")
        import threading
        cancelled = threading.Event()
        cancelled.set()
        invoke = smart.dual._invoke_codex

        def before_launch(*args, **kwargs):
            return invoke(*args[:3], cancelled, **kwargs)

        with mock.patch.object(smart.dual, "_invoke_codex", side_effect=before_launch):
            result = smart.execute(planned, self.repo, self.runs, timeout=30)
        self.assertEqual(result["workers"][0]["status"], "cancelled")
        self.assertEqual(result["accounting"]["accounted_tokens"], 0)
        self.assertEqual(result["accounting"]["not_started_jobs"], 1)

    def test_exception_after_attempt_charges_only_attempted_serial_worker(self):
        planned = self.planned("serial")
        def interrupted(*args, on_start=None, **kwargs):
            if on_start is not None:
                on_start()
            raise OSError("runner interrupted")
        with mock.patch.object(smart.dual, "_invoke_codex", side_effect=interrupted):
            with self.assertRaises(smart.dual.PlanError):
                smart.execute(planned, self.repo, self.runs, timeout=30,
                              phase_one_validator=lambda *args: {"passed": True, "evidence": "test"})
        records = {r["job"]: r for r in self.records()}
        self.assertEqual(records["first"]["actual"], records["first"]["reserved"])
        self.assertFalse(records["first"]["observed"])
        self.assertEqual(records["second"]["actual"], 0)
        self.assertTrue(records["second"]["not_started"])


if __name__ == "__main__":
    unittest.main()
