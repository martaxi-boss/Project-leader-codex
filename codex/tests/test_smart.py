"""Guarded executor tests using fake local Codex, never live model calls."""
import json
import errno
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
    def test_cloud_readonly_home_uses_private_xdg_state_for_real_fake_cli(self):
        p = plan({"request": "Implement channel navigation and validate tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("one", "docs/channels",
                                      "Implement channels and validate tests")]})
        state = self.root / "xdg-state"
        with mock.patch.dict(os.environ, {
                "HOME": str(self.root / "readonly-home"),
                "XDG_STATE_HOME": str(state), "XDG_RUNTIME_DIR": ""}):
            result = smart.execute(p, self.repo, timeout=30)
        self.assertEqual([x["status"] for x in result["workers"]], ["completed"])
        self.assertEqual(Path(result["run_directory"]).parent,
                         state / "project-leader-codex" / "runs")
        self.assertEqual(smart.dual._git(self.repo, "status", "--porcelain"), "")

    def test_default_readonly_home_falls_back_to_private_runtime_directory(self):
        locked = self.root / "locked-home"
        runtime = self.root / "xdg-runtime"
        real_open = os.open

        def readonly_home_probe(path, *args, **kwargs):
            if str(path).startswith(str(locked)):
                raise OSError(errno.EROFS, "Read-only file system")
            return real_open(path, *args, **kwargs)

        with mock.patch.dict(os.environ, {
                "HOME": str(locked), "XDG_STATE_HOME": "",
                "XDG_RUNTIME_DIR": str(runtime)}):
            with mock.patch("codex.dual.os.open", side_effect=readonly_home_probe):
                root = smart.dual._private_runs_root(self.repo, None)
        self.assertEqual(root, runtime / "project-leader-codex" / "runs")
        self.assertEqual(root.stat().st_mode & 0o077, 0)

    def test_explicit_readonly_runs_dir_fails_closed_before_worker_and_budget(self):
        p = plan({"request": "Implement channel navigation and validate tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("one", "docs/channels",
                                      "Implement channels and validate tests")]})
        readonly = self.root / "readonly-explicit"
        with mock.patch("codex.dual.os.open",
                        side_effect=OSError(errno.EROFS, "Read-only file system")):
            with self.assertRaisesRegex(RoutingError, "--runs-dir"):
                smart.execute(p, self.repo, readonly, timeout=30)
        self.assertFalse(any(x.name.startswith("run-") for x in readonly.iterdir()))
        self.assertEqual(smart.dual._git(self.repo, "status", "--porcelain"), "")

    def test_runs_directory_symlink_does_not_bypass_private_root_checks(self):
        link = self.root / "symlink-runs"
        link.symlink_to(self.runs, target_is_directory=True)
        with self.assertRaisesRegex(smart.dual.PlanError, "symlink"):
            smart.dual._private_runs_root(self.repo, link)

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

    def test_serial_validator_failure_does_not_charge_unstarted_codex(self):
        planned = plan({
            "request": "Build two dependent modules and validate them",
            "target_repository": "martaxi-boss/pink-iptv",
            "work_items": [
                {"id": "first", "paths": ["docs/channels"],
                 "task": "Implement channel integration and run tests"},
                {"id": "second", "paths": ["docs/movies"], "depends_on": ["first"],
                 "task": "Implement movie integration and run tests"},
            ],
        })
        self.assertEqual(planned["mode"], "serial")
        outcome = {
            "run_directory": str(self.runs / "run-failed-synthetic"),
            "workers": [
                {"id": planned["tasks"][0]["id"], "status": "failed"},
                {"id": planned["tasks"][1]["id"], "status": "not_started"},
            ],
        }
        with mock.patch.object(smart.dual, "run", return_value=outcome):
            result = smart.execute(planned, self.repo, self.runs, timeout=30,
                                   phase_one_validator=lambda path: True)
        self.assertEqual(result["accounting"]["not_started_jobs"], 1)
        self.assertEqual(result["accounting"]["conservative_jobs"], 1)
        self.assertEqual(result["accounting"]["observed_jobs"], 0)

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

    def test_portable_natural_language_cli_runs_existing_one_worker_without_vps(self):
        request = "Implement a safe channel navigation fix and validate tests"
        def scoped(order, repo):
            self.assertEqual(order["target_repository"], "martaxi-boss/pink-iptv")
            self.assertEqual(order["request"], request)
            self.assertEqual(repo, self.repo)
            return {**order, "work_items": [
                {"id": "channels", "paths": ["docs/channels"],
                 "task": "Implement channel navigation and validate tests safely"}]}
        printed = io.StringIO()
        with mock.patch.object(smart, "discover_work_items", side_effect=scoped):
            with redirect_stdout(printed):
                code = smart.main([
                    "run", "--task", request, "--repo-dir", str(self.repo),
                    "--runs-dir", str(self.runs), "--execute", "--timeout", "30"])
        self.assertEqual(code, 0)
        result = json.loads(printed.getvalue())
        self.assertEqual(result["mode"], "single")
        self.assertEqual(result["target_repository"], "martaxi-boss/pink-iptv")
        self.assertEqual([w["status"] for w in result["workers"]], ["completed"])
        self.assertEqual(result["accounting"]["observed_jobs"], 1)

    def test_portable_cli_refuses_unverified_or_foreign_checkout_before_dispatch(self):
        from contextlib import redirect_stderr
        blocked = io.StringIO()
        with mock.patch.object(smart.dual, "_remote_repo", return_value="other-owner/unrelated"):
            with redirect_stderr(blocked):
                code = smart.main([
                    "run", "--task", "Implement channel navigation and test",
                    "--repo-dir", str(self.repo), "--runs-dir", str(self.runs),
                    "--execute"])
        self.assertEqual(code, 3)
        self.assertIn("outside the authorized Owner", blocked.getvalue())
        self.assertFalse(any(x.name.startswith("run-") for x in self.runs.iterdir()))

    def test_portable_cli_requires_selected_checkout_and_never_assumes_vps(self):
        from contextlib import redirect_stderr
        blocked = io.StringIO()
        with redirect_stderr(blocked):
            code = smart.main(["run", "--task", "Implement safe channel navigation",
                               "--execute"])
        self.assertEqual(code, 3)
        self.assertIn("real checkout", blocked.getvalue())

    def test_material_boundaries_require_project_leader_gate(self):
        p = plan({"request": "Deploy to production after tests",
                  "target_repository": "martaxi-boss/pink-iptv",
                  "work_items": [task("prod", "docs/deploy", "Implement production release and validate tests") ]})
        with self.assertRaises(RoutingError):
            smart.execute(p, self.repo, self.runs, timeout=30)


if __name__ == "__main__":
    unittest.main()
