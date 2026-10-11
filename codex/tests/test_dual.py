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
        self.assertEqual(dual.effort(task("one", "docs", "Diagnose race condition", reasoning_effort="low")), "low")

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
workspace = Path(args[args.index('-C')+1])
owned = prompt.split('Owned paths: ', 1)[-1].split('\\n', 1)[0].split(',')[0]
if 'CHECK-PRIOR' in prompt and not (workspace / 'docs/channels/created.txt').exists():
    sys.exit(13)
if 'FAIL-ONE' in prompt:
    sys.exit(12)
if 'NO-CHANGE' in prompt:
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

    def _run(self, plan):
        return dual.run(dual.parse_order(plan), self.repo, self.runs, timeout=30)

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
