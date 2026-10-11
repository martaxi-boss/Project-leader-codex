"""Guarded executor tests using fake local Codex, never live model calls."""
import json
import io
import os
from contextlib import redirect_stdout
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
        clone = Path(result["workers"][0]["workspace"])
        self.assertTrue((clone / ".git").is_dir())
        self.assertEqual(smart.dual._git(clone, "remote"), "")
        self.assertNotEqual(clone / ".git", self.repo / ".git")
        self.assertFalse((clone / ".git/objects/info/alternates").exists())

    def test_solo_git_config_injection_fails_closed_without_host_exec(self):
        p = plan({"request": "Implement a channel module and validate tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("one", "docs/channels",
                                      "FS-MONITOR-INJECT: implement channels and run tests")]})
        original_refs = smart.dual._refs_snapshot(self.repo)
        with mock.patch.dict(os.environ,
                             {"HOST_SECRET_SENTINEL": "not-for-the-worker"}):
            result = smart.execute(p, self.repo, self.runs, timeout=30)
        first = result["workers"][0]
        self.assertEqual(first["status"], "git_metadata_violation")
        self.assertFalse((Path(first["workspace"]).parent / "host-secret-leak").exists())
        self.assertEqual(smart.dual._git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(smart.dual._refs_snapshot(self.repo), original_refs)

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

    def test_serial_requires_independent_verifier_before_budget_or_launch(self):
        p = plan({"request": "Implement dependent UI features and validate them",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [
                      {"id": "build", "paths": ["docs/channels"],
                       "task": "Implement channel navigation, integrate the player and run tests"},
                      {"id": "finish", "paths": ["docs/movies"], "depends_on": ["build"],
                       "task": "Implement movie navigation, integrate channel links and run tests"},
                  ]})
        self.assertEqual(p["mode"], "serial")
        with self.assertRaisesRegex(RoutingError, "independent project validator"):
            smart.execute(p, self.repo, self.runs, timeout=30)
        self.assertEqual(list(self.runs.iterdir()), [])

        verified = smart.execute(
            p, self.repo, self.runs, timeout=30,
            phase_one_validator=RunnerTests._validated_fake_phase,
        )
        self.assertEqual([w["status"] for w in verified["workers"]], ["completed", "completed"])
        self.assertTrue(verified["workers"][0]["validation"]["passed"])
        self.assertEqual(verified["accounting"]["observed_jobs"], 2)

    def test_smart_cli_executes_serial_with_trusted_host_validator(self):
        order_file = self.root / "smart-order.json"
        order_file.write_text(json.dumps({
            "request": "Implement dependent channel and film components with tests",
            "target_repository": "martaxi-boss/pink-iptv",
            "work_items": [
                {"id": "build", "paths": ["docs/channels"],
                 "task": "Implement channels, integrate player and run interface tests"},
                {"id": "finish", "paths": ["docs/movies"], "depends_on": ["build"],
                 "task": "Implement films, integrate channels and run interface tests"},
            ],
        }))
        printed = io.StringIO()
        with redirect_stdout(printed):
            exit_code = smart.main([
                "run", "--order", str(order_file),
                "--repo-dir", str(self.repo), "--runs-dir", str(self.runs),
                "--execute", "--timeout", "30",
                "--phase-one-validator", str(self.validator),
            ])
        self.assertEqual(exit_code, 0)
        result = json.loads(printed.getvalue())
        self.assertEqual(result["mode"], "serial")
        self.assertEqual([w["status"] for w in result["workers"]],
                         ["completed", "completed"])
        self.assertTrue(result["workers"][0]["validation"]["passed"])
        self.assertEqual(result["accounting"]["observed_jobs"], 2)

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
