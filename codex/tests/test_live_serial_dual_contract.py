import unittest

from codex import dual


class LiveSerialDualContractTests(unittest.TestCase):
    def test_serial_accepts_overlapping_paths_but_parallel_rejects_them(self):
        manifest = {
            "target_repository": "martaxi-boss/Project-leader-codex",
            "mode": "serial",
            "tasks": [
                {
                    "id": "first",
                    "task": "Fix typo in channel docs",
                    "paths": ["src/channels"],
                },
                {
                    "id": "second",
                    "task": "Fix typo in movie docs",
                    "paths": ["src/channels/notes"],
                },
            ],
        }

        parsed = dual.parse_order(manifest)

        self.assertEqual(parsed["mode"], "serial")
        self.assertEqual(len(parsed["tasks"]), 2)
        self.assertEqual(parsed["execution"], "one ordered private Git clone")

        parallel_manifest = {**manifest, "mode": "parallel"}
        with self.assertRaises(dual.PlanError):
            dual.parse_order(parallel_manifest)


if __name__ == "__main__":
    unittest.main()
