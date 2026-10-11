"""Guarded executor tests using fake local Codex, never live model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from codex import smart
from codex.agent_policy import RoutingError, plan
from codex.tests.test_dual import RunnerTests, order, task


class SmartRunTests(unittest.TestCase):
    setUp = RunnerTests.setUp
    def test_single_codex_is_actually_one_worker_with_bounded_scope_and_budget(self):
        p = plan({"request": "Implement a small channel detail view and verify the tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("one", "docs/channels", "Implement channel navigation and run tests for playback") ]})
        result = smart.execute(p, self.repo, self.runs, timeout=30)
        self.assertEqual(result["mode"], "single")
        self.assertEqual([x["status"] for x in result["workers"]], ["completed"])
        self.assertEqual(result["accounting"]["observed_jobs"], 1)
        self.assertEqual(result["accounting"]["accounted_tokens"], 21)
        self.assertEqual((self.repo / "base.txt").read_text(), "initial\n")

    def test_parallel_codex_two_workers_observed_usage_and_private_ledger(self):
        p = plan({"request": "Implement channels and movies independently with integration and regression tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("channels", "docs/channels", "Implement channel navigation and integration tests for playback"),
                                 task("movies", "docs/movies", "Implement movie navigation and integration tests for playback") ]})
        self.assertEqual(p["mode"], "parallel")
        r = smart.execute(p, self.repo, self.runs, timeout=30)
        self.assertEqual([x["status"] for x in r["workers"]], ["completed", "completed"])
        self.assertEqual(r["accounting"]["observed_jobs"], 2)
        self.assertEqual(r["accounting"]["accounted_tokens"], 42)
        self.assertEqual(len(list((self.runs / ".shared-budget").iterdir())), 2)

    def test_missing_other_cloud_adapter_never_runs_codex_by_substitution(self):
        p = plan({"request": "Build new detailed cloud feature with tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("first", "docs/a", "Implement detailed feature and run tests")],
                  "providers": ["gemini"]})
        with self.assertRaises(RoutingError):
            smart.execute(p, self.repo, self.runs, timeout=30)
        self.assertEqual(list(self.runs.iterdir()), [])

    def test_soft_budget_blocks_before_models_and_no_side_effects(self):
        p = plan({"request": "Build two independent modules and validate tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("a", "docs/a", "Implement new module and test integration"),
                                 task("b", "docs/b", "Implement another module and test integration")],
                  "preference": "parallel"})
        smart.execute(p, self.repo, self.runs, timeout=30, soft_limit=100000)
        worktrees = len([x for x in self.runs.iterdir() if x.name.startswith("run-")])
        from codex import resource_budget
        resource_budget.reserve_batch(self.runs / ".shared-budget", "a" * 32, [{"id": "hold", "effort": "high"}], 100000)
        with self.assertRaisesRegex(Exception, "soft token budget exceeded"):
            smart.execute(p, self.repo, self.runs, timeout=30, soft_limit=100000)
        self.assertEqual(worktrees, len([x for x in self.runs.iterdir() if x.name.startswith("run-")]))

    def test_material_boundaries_require_project_leader_gate(self):
        p = plan({"request": "Deploy to production after tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("prod", "docs/deploy", "Implement production release and validate tests") ]})
        with self.assertRaises(RoutingError):
            smart.execute(p, self.repo, self.runs, timeout=30)


if __name__ == "__main__":
    unittest.main()
