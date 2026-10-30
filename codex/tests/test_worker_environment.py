"""Real subprocess regression for Codex host-environment isolation."""
import os
import sys
import unittest
from unittest.mock import patch

from codex.dual import _invoke_codex


class WorkerEnvironmentTests(unittest.TestCase):
    def test_implicit_host_environment_is_filtered(self):
        values = {
            "PL_OTHER_PROJECT_CANARY": "dont-share",
            "GITHUB_TOKEN": "unrelated",
            "CODEX_HOME": "/tmp/rea-codex-home",
        }
        source = ("import os; "
                  "print(os.getenv('PL_OTHER_PROJECT_CANARY', 'ABSENT')); "
                  "print(os.getenv('GITHUB_TOKEN', 'ABSENT')); "
                  "print(os.getenv('CODEX_HOME', 'ABSENT'))")
        with patch.dict(os.environ, values):
            code, output, error, status = _invoke_codex(
                [sys.executable, "-c", source], "", timeout=10
            )
        self.assertEqual((code, status), (0, "finished"), error)
        self.assertEqual(output.strip().splitlines(),
                         ["ABSENT", "ABSENT", "/tmp/rea-codex-home"])

    def test_explicit_host_environment_stays_explicit(self):
        source = "import os; print(os.getenv('PL_EXPLICIT_CANARY', 'ABSENT'))"
        code, output, error, status = _invoke_codex(
            [sys.executable, "-c", source], "", timeout=10,
            env={"PATH": "/usr/bin:/bin", "PL_EXPLICIT_CANARY": "HOST_SET"}
        )
        self.assertEqual((code, status), (0, "finished"), error)
        self.assertEqual(output.strip(), "HOST_SET")


if __name__ == "__main__":
    unittest.main()
