"""Regression coverage for live dual-worker owned-path gating."""

import unittest

from codex import dual


class LiveParallelOwnedPathGateTests(unittest.TestCase):
    def test_parallel_requires_independent_owned_paths(self):
        parallel_manifest = {
            "target_repository": "martaxi-boss/Project-leader-codex",
            "mode": "parallel",
            "tasks": [
                {
                    "id": "one",
                    "task": "Fix typo in channel docs",
                    "paths": ["src/channels"],
                },
                {
                    "id": "two",
                    "task": "Fix typo in movie docs",
                    "paths": ["src/movies"],
                },
            ],
        }

        plan = dual.parse_order(parallel_manifest)

        self.assertEqual(plan["mode"], "parallel")
        self.assertEqual(len(plan["tasks"]), 2)
        self.assertEqual(plan["execution"], "two independent Git clones")

        overlapping_parallel_manifest = {
            "target_repository": "martaxi-boss/Project-leader-codex",
            "mode": "parallel",
            "tasks": [
                {
                    "id": "one",
                    "task": "Fix typo in channel docs",
                    "paths": ["src/channels"],
                },
                {
                    "id": "two",
                    "task": "Fix typo in movie docs",
                    "paths": ["src/channels/notes"],
                },
            ],
        }

        with self.assertRaises(dual.PlanError):
            dual.parse_order(overlapping_parallel_manifest)

        overlapping_serial_manifest = {
            "target_repository": "martaxi-boss/Project-leader-codex",
            "mode": "serial",
            "tasks": [
                {
                    "id": "one",
                    "task": "Fix typo in channel docs",
                    "paths": ["src/channels"],
                },
                {
                    "id": "two",
                    "task": "Fix typo in movie docs",
                    "paths": ["src/channels/notes"],
                },
            ],
        }

        serial_plan = dual.parse_order(overlapping_serial_manifest)

        self.assertEqual(serial_plan["mode"], "serial")
        self.assertEqual(len(serial_plan["tasks"]), 2)


if __name__ == "__main__":
    unittest.main()
