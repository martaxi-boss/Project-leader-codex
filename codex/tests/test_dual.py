"""Offline, deterministic dual-agent safety and actual two-process tests (fake Codex)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from codex import dual


def task(name, path, text="Implement focused change and validate the result.", **kwargs):
    return {"id": name, "task": text, "paths": [path], **kwargs}


def order(mode="parallel", **kwargs):
    return {"target_repository": "martaxi-boss/pink-iptv", "mode": mode,
            "tasks": [task("first", "docs/channels"), task("second", "docs/movies")], **kwargs}


class PlanTests(unittest.TestCase):
    def test_automatic_effort_and_override(self):
        self.assertEqual(dual.effort(task("one", "docs", "Fix typo in README")), "low")
        self.assertEqual(dual.effort(task("one", "docs", "Implement the viewing module")), "medium")
        self.assertEqual(dual.effort(task("one", "docs", "Diagnose security regression and validate")), "high")
        self.assertEqual(dual.effort(task("one", "docs", "Update docs and tests", verified_hard_failure=True)), "high")
        with self.assertRaisesRegex(dual.PlanError, "Unsafe reasoning-effort override"):
            dual.effort(task("one", "docs", "Diagnose race condition", reasoning_effort="low"))
        self.assertEqual(dual.effort(task("one", "docs", "Run normal regression tests")), "medium")
        self.assertEqual(dual.effort(task("one", "docs", "Diagnose deadlock", reasoning_effort="high")), "high")

    def test_two_jobs_and_ordering(self):
        self.assertEqual(len(dual.parse_order(order())["tasks"]), 2)
        self.assertEqual(dual.parse_order(order("serial"))["execution"], "one ordered worktree")
        with self.assertRaisesRegex(dual.PlanError, "Exactly two"):
            dual.parse_order({**order(), "tasks": order()["tasks"][:1]})
        with self.assertRaisesRegex(dual.PlanError, "Invalid task fields"):
            p = order(); p["tasks"][0]["provider"] = "unexpected"; dual.parse_order(p)

    def test_invalid_or_overlapping_paths_fail_closed(self):
        for bad in ("../other", "/etc/passwd", ".git/config", "../", "foo\\bar", "hello/*"):
            p = order(); p["tasks"][0]["paths"] = [bad]
            with self.subTest(path=bad), self.assertRaises(dual.PlanError):
                dual.parse_order(p)
        p = order(); p["tasks"][0]["paths"] = ["docs"]
        with self.assertRaisesRegex(dual.PlanError, "overlapping"):
            dual.parse_order(p)
        self.assertEqual(dual.parse_order({**p, "mode": "serial"})["mode"], "serial")

    def test_rejects_unsafe_manifest_and_duplicates(self):
        p = order(); p["tasks"][1]["id"] = "first"
        with self.assertRaises(dual.PlanError):
            dual.parse_order(p)
        p = order(); p["target_repository"] = "../../other"
        with self.assertRaises(dual.PlanError):
            dual.parse_order(p)
        p = order(); p["tasks"][0]["reasoning_effort"] = "infinite"
        with self.assertRaises(dual.PlanError):
            dual.parse_order(p)

    def test_safe_hidden_project_scopes_and_accents(self):
        self.assertTrue(dual._is_safe_path(".github/workflows/build.yml"))
        self.assertTrue(dual._is_safe_path(".codex/config.toml"))
        for path in (".git/config", ".env", "foo/.github/config", ".codex/../secret"):
            self.assertFalse(dual._is_safe_path(path))
        for text in ("Diagnostica falha de segurança", "Corrige concorrência nos processos"):
            self.assertEqual(dual.effort(task("one", "docs", text)), "high")
        for bad in ([], {}, 42):
            p = order(); p["tasks"][0]["reasoning_effort"] = bad
            with self.subTest(value=bad), self.assertRaises(dual.PlanError):
                dual.parse_order(p)
        for bad_mode in ([], {}, 5):
            p = order(); p["mode"] = bad_mode
            with self.subTest(mode=bad_mode), self.assertRaises(dual.PlanError):
                dual.parse_order(p)
        for name in ("./..", "martaxi-boss/..", "../repo"):
            p = order(); p["target_repository"] = name
            with self.subTest(repo=name), self.assertRaises(dual.PlanError):
                dual.parse_order(p)

    def test_no_execution_without_explicit_flag(self):
        with tempfile.TemporaryDirectory() as td:
            m = Path(td) / "order.json"; m.write_text(json.dumps(order()))
            self.assertEqual(dual.main(["plan", "--manifest", str(m)]), 0)
            self.assertEqual(dual.main(["run", "--manifest", str(m)]), 3)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repository"; self.repo.mkdir()
        self.runs = self.root / "runs"; self.runs.mkdir(mode=0o700)
        def git(*args):
            subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True)
        git("init", "-q")
        git("config", "user.email", "offline-test@example.test")
        git("config", "user.name", "Offline Test")
        git("remote", "add", "origin", "https://github.com/martaxi-boss/pink-iptv.git")
        (self.repo / "base.txt").write_text("initial\n")
        git("add", ".")
        git("commit", "-qm", "initial")
        self.rules = self.root / "rules"
        (self.rules / "plugins/project-leader/skills/project-leader").mkdir(parents=True)
        (self.rules / "plugins/project-leader/skills/project-leader/SKILL.md").write_text("TEST PROJECT LEADER RULE")
        (self.rules / "CODEX_COORDINATION.md").write_text("TEST CODEX RULE")
        self.bin = self.root / "bin"; self.bin.mkdir()
        executable = self.bin / "codex"
        executable.write_text("""#!/usr/bin/env python3
import os
from pathlib import Path
import sys
import time
prompt = sys.stdin.read()
args = sys.argv
if '--ask-for-approval' not in args or args.index('--ask-for-approval') > args.index('exec'):
    sys.stderr.write('error: unrecognized post-exec approval option')
    sys.exit(2)
workspace = Path(args[args.index('-C')+1])
owned = prompt.split('Owned paths: ', 1)[-1].split('\\n', 1)[0].split(',')[0]
if 'CHECK-PRIOR' in prompt and not (workspace / 'docs/channels/created.txt').exists():
    sys.exit(13)
if 'FAIL-ONE' in prompt:
    time.sleep(0.4)
    sys.exit(12)
if 'SLOW-LONG' in prompt:
    time.sleep(12)
if 'SLOW-GROUP' in prompt:
    import subprocess
    subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(12)'])
    time.sleep(12)
if 'NO-CHANGE' in prompt:
    time.sleep(0.3)
    print('{"type":"turn.completed"}')
    sys.exit(0)
if 'BREAK-SCOPE' in prompt:
    owned = 'unowned'
if 'BREAK-INHERITED' in prompt:
    prior = workspace / 'docs/channels/created.txt'
    if not prior.exists():
        sys.exit(14)
    prior.write_text('unauthorized second-worker edit')
time.sleep(0.15)
target = workspace / owned / 'created.txt'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text('fake codex result refined' if 'CHECK-PRIOR' in prompt else 'fake codex result')
if 'COMMIT-OUTSIDE' in prompt or 'COMMIT-OWNED' in prompt:
    import subprocess
    if 'COMMIT-OUTSIDE' in prompt:
        rogue = workspace / 'unowned/rogue.txt'
        rogue.parent.mkdir(parents=True, exist_ok=True)
        rogue.write_text('unauthorized committed file')
    subprocess.run(['git', '-C', str(workspace), 'add', '-A'], check=True)
    subprocess.run(['git', '-C', str(workspace), 'commit', '-qm', 'bad worker commit'], check=True)
print('{"type":"something_else"}' if 'INVALID-EVENT' in prompt else '{"type":"turn.completed","usage":{"input_tokens":15,"output_tokens":6,"cached_input_tokens":2}}')
""")
        executable.chmod(0o755)
        self.env_path = str(self.bin) + os.pathsep + os.environ["PATH"]
        self.env_patch = mock.patch.dict(os.environ, {"PATH": self.env_path})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.root_patch = mock.patch.object(dual, "ROOT", self.rules)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    @staticmethod
    def _validated_fake_phase(workspace, task, report):
        # An independent offline fixture validates the first phase's output,
        # rather than trusting a Codex turn.completed event as code acceptance.
        paths = report["new_paths"]
        allowed = task["paths"]
        good = bool(paths) and all(dual._scope(p, allowed) for p in paths)
        git_check = subprocess.run(
            ["git", "-C", str(workspace), "diff", "--check"],
            capture_output=True, check=False,
        )
        good = good and git_check.returncode == 0
        return {"passed": good,
                "evidence": "Offline independent fixture inspected changed paths and diff"}

    def _run(self, plan, validator=None):
        if plan["mode"] == "serial" and validator is None:
            validator = self._validated_fake_phase
        return dual.run(dual.parse_order(plan), self.repo, self.runs,
                        timeout=30, phase_one_validator=validator)

    def test_parallel_real_processes_isolated_no_integration(self):
        result = self._run(order())
        self.assertEqual([w["status"] for w in result["workers"]], ["completed", "completed"])
        self.assertNotEqual(result["workers"][0]["workspace"], result["workers"][1]["workspace"])
        self.assertEqual(dual._git(self.repo, "status", "--porcelain"), "")
        self.assertEqual((self.repo / "base.txt").read_text(), "initial\n")
        self.assertTrue((Path(result["workers"][0]["workspace"]) / "docs/channels/created.txt").exists())
        self.assertFalse((Path(result["workers"][0]["workspace"]) / "docs/movies/created.txt").exists())
        self.assertEqual((Path(result["run_directory"]) / "result.json").stat().st_mode & 0o077, 0)

    def test_serial_second_sees_first_changes(self):
        p = order("serial")
        p["tasks"][1]["task"] = "CHECK-PRIOR and implement movie changes after first job"
        result = self._run(p)
        self.assertEqual([w["status"] for w in result["workers"]], ["completed", "completed"])
        self.assertEqual(result["workers"][0]["workspace"], result["workers"][1]["workspace"])

    def test_serial_requires_independent_validation_before_any_model_launch(self):
        p = dual.parse_order(order("serial"))
        with self.assertRaisesRegex(dual.PlanError, "independent acceptance validator"):
            dual.run(p, self.repo, self.runs, timeout=30)
        self.assertEqual(list(self.runs.iterdir()), [])

    def test_failed_independent_validation_stops_phase_two(self):
        result = self._run(order("serial"),
                           validator=lambda workspace, task, report: {
                               "passed": False, "evidence": "Simulated regression failed"
                           })
        self.assertEqual(result["workers"][0]["status"], "completed")
        self.assertEqual(result["workers"][0]["validation"]["passed"], False)
        self.assertEqual(result["workers"][1]["status"], "not_started")

    def test_malformed_independent_validation_never_starts_phase_two(self):
        p = dual.parse_order(order("serial"))
        with self.assertRaisesRegex(dual.PlanError, "verdict and evidence"):
            dual.run(p, self.repo, self.runs, timeout=30,
                     phase_one_validator=lambda w, t, r: {"passed": True})

    def test_failed_first_does_not_start_second(self):
        p = order("serial")
        p["tasks"][0]["task"] = "FAIL-ONE first and make no changes; do not retry blindly"
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "failed")
        self.assertEqual(r["workers"][1]["status"], "not_started")

    def test_no_changes_or_missing_codex_terminal_event_are_not_success(self):
        p = order(); p["tasks"][0]["task"] = "NO-CHANGE: perform implementation without changing code"
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "no_change")
        p = order(); p["tasks"][0]["task"] = "INVALID-EVENT: do not emit completed terminal event"
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "unverified_result")

    def test_serial_second_can_revise_first_task_existing_file(self):
        p = order("serial")
        p["tasks"][1]["paths"] = ["docs/channels"]
        p["tasks"][1]["task"] = "CHECK-PRIOR: refine the existing channels file after first task"
        r = self._run(p)
        self.assertEqual(r["workers"][1]["status"], "completed")

    def test_serial_worker_cannot_modify_inherited_out_of_scope_file(self):
        p = order("serial")
        p["tasks"][1]["task"] = "BREAK-INHERITED: edit previous agent's channel file illegally"
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "completed")
        self.assertEqual(r["workers"][1]["status"], "scope_violation")
        self.assertIn("docs/channels/created.txt", r["workers"][1]["out_of_scope"])

    def test_scope_violation_is_not_success(self):
        p = order(); p["tasks"][1]["task"] = "BREAK-SCOPE: attempt to edit something outside assigned paths"
        r = self._run(p)
        self.assertEqual(r["workers"][1]["status"], "scope_violation")
        self.assertEqual(r["workers"][1]["out_of_scope"], ["unowned/created.txt"])

    def test_committed_out_of_scope_cannot_hide_behind_clean_git_status(self):
        p = order("serial")
        p["tasks"][0]["task"] = "COMMIT-OUTSIDE: add a rogue file and commit every change"
        r = self._run(p)
        first = r["workers"][0]
        self.assertEqual(first["status"], "scope_violation")
        self.assertTrue(first["commit_detected"])
        self.assertIn("unowned/rogue.txt", first["committed_paths"])
        self.assertIn("unowned/rogue.txt", first["out_of_scope"])
        self.assertEqual(dual._changes(Path(first["workspace"])), set())
        self.assertEqual(r["workers"][1]["status"], "not_started")

    def test_in_scope_worker_commit_never_counts_as_safe_completion(self):
        p = order("serial")
        p["tasks"][0]["task"] = "COMMIT-OWNED: commit a file within approved paths"
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "unauthorized_commit")
        self.assertTrue(r["workers"][0]["commit_detected"])
        self.assertEqual(r["workers"][0]["out_of_scope"], [])
        self.assertEqual(r["workers"][1]["status"], "not_started")

    def test_parallel_failure_cancels_running_sibling(self):
        p = order()
        p["tasks"][0]["task"] = "FAIL-ONE: fail first worker deliberately and do not modify anything"
        p["tasks"][1]["task"] = "SLOW-LONG: this second worker would hang without cancellation"
        started = __import__("time").monotonic()
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "failed")
        self.assertEqual(r["workers"][1]["status"], "cancelled")
        self.assertLess(__import__("time").monotonic() - started, 5)

    def test_parallel_no_change_cancels_sibling(self):
        p = order()
        p["tasks"][0]["task"] = "NO-CHANGE: return completion with no material edit"
        p["tasks"][1]["task"] = "SLOW-LONG: continue until sibling stops"
        started = __import__("time").monotonic()
        r = self._run(p)
        self.assertEqual(r["workers"][0]["status"], "no_change")
        self.assertEqual(r["workers"][1]["status"], "cancelled")
        self.assertLess(__import__("time").monotonic() - started, 5)

    def test_codex_timeout_terminates_worker_process(self):
        p = dual.parse_order(order())
        workspace = self.repo
        result = dual._worker(p["tasks"][0] | {"task": "SLOW-LONG: exceed a tiny timeout"},
                              workspace, self.runs, timeout=0.5)
        self.assertEqual(result["status"], "timeout")

    def test_timeout_kills_child_process_group_and_releases_pipes(self):
        p = dual.parse_order(order())
        task = p["tasks"][0] | {"task": "SLOW-GROUP: spawn a child that inherits stdout"}
        started = __import__("time").monotonic()
        r = dual._worker(task, self.repo, self.runs, timeout=0.5)
        self.assertEqual(r["status"], "timeout")
        self.assertLess(__import__("time").monotonic() - started, 3)

    def test_remote_mismatch_and_dirty_checkout_block(self):
        p = dual.parse_order(order())
        with self.assertRaisesRegex(dual.PlanError, "origin does not match"):
            dual.run({**p, "target_repository": "someone/else"}, self.repo, self.runs)
        (self.repo / "untracked.txt").write_text("dirty")
        with self.assertRaisesRegex(dual.PlanError, "dirty"):
            dual.run(p, self.repo, self.runs)
        self.assertEqual(list(self.runs.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
