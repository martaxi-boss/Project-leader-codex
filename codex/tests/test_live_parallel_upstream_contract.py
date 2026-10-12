"""Offline regression for canonical Project Leader provenance."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class UpstreamProjectLeaderContractTests(unittest.TestCase):
    def test_canonical_rules_are_from_a_distinct_repository(self):
        provenance = json.loads(
            (ROOT / "UPSTREAM_PROJECT_LEADER.json").read_text(encoding="utf-8")
        )
        self.assertEqual(provenance["upstream_repository"], "martaxi-boss/Project-leader")
        self.assertNotEqual(
            provenance["upstream_repository"], "martaxi-boss/Project-leader-codex"
        )
        self.assertEqual(provenance["universal_plugin_version"], "0.7.0")
        self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{40}", provenance["upstream_commit"]))


if __name__ == "__main__":
    unittest.main()
