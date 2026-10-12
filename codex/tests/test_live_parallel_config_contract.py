"""Offline regression for the two-agent Codex configuration."""
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ParallelCodexConfigContractTests(unittest.TestCase):
    def test_two_agents_enabled_without_extra_workers(self):
        config = tomllib.loads(
            (ROOT / ".codex/config.toml").read_text(encoding="utf-8")
        )
        agents = config["agents"]
        self.assertIs(agents["enabled"], True)
        self.assertEqual(agents["max_concurrent_threads_per_session"], 2)


if __name__ == "__main__":
    unittest.main()
