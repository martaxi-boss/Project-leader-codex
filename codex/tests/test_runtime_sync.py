"""Real local-Git tests for the read-only Codex revision coherence gate."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from codex import runtime_sync


class RuntimeSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="codex-sync-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.remote = base / "upstream.git"
        self.source = base / "source"
        self.source.mkdir()
        self.git(base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(base, "init", "-q", "-b", "main", str(self.source))
        self.identity(self.source)
        for name in runtime_sync.SOURCE_FILES:
            destination = self.source / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(runtime_sync.ROOT / name, destination)
        self.git(self.source, "add", "--", *runtime_sync.SOURCE_FILES)
        self.git(self.source, "commit", "-qm", "snapshot")
        self.git(self.source, "remote", "add", "origin", str(self.remote))
        self.git(self.source, "push", "-q", "-u", "origin", "main")

    @staticmethod
    def git(cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True,
                              text=True, check=True, timeout=20).stdout.strip()

    @classmethod
    def identity(cls, repo):
        cls.git(repo, "config", "user.name", "Test")
        cls.git(repo, "config", "user.email", "test@example.invalid")

    def test_exact_current_main_source_passes(self):
        result = runtime_sync.check(self.source, require_origin_identity=False)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["head_sha"], result["origin_main_sha"])
        self.assertEqual(len(result["source_sha256"]), len(runtime_sync.SOURCE_FILES))
        self.assertEqual(result["host_loaded_skill_release"], "NOT_VERIFIED")

    def test_new_main_rejects_stale_cloud_checkout(self):
        updater = Path(self.tmp.name) / "updater"
        self.git(Path(self.tmp.name), "clone", "-q", str(self.remote), str(updater))
        self.identity(updater)
        (updater / "NEW_MAIN.txt").write_text("newer code\n")
        self.git(updater, "add", "NEW_MAIN.txt")
        self.git(updater, "commit", "-qm", "new main")
        self.git(updater, "push", "-q", "origin", "main")
        with self.assertRaises(runtime_sync.PreflightError) as raised:
            runtime_sync.check(self.source, require_origin_identity=False)
        self.assertEqual(raised.exception.status, "STALE")

    def test_dirty_codex_instructions_never_certify(self):
        with (self.source / ".codex/config.toml").open("a") as output:
            output.write("\n# pending local change\n")
        with self.assertRaises(runtime_sync.PreflightError) as raised:
            runtime_sync.check(self.source, require_origin_identity=False)
        self.assertEqual(raised.exception.status, "NOT_VERIFIED")

    def test_unverified_origin_is_not_treated_as_project_repo(self):
        with self.assertRaises(runtime_sync.PreflightError) as raised:
            runtime_sync.check(self.source)
        self.assertEqual(raised.exception.status, "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
