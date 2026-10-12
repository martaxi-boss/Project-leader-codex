"""Live contract tests for explicit two-worker serial routing."""
import unittest

from codex.agent_policy import plan


def _order(*, movies_depends_on_channels=False):
    movies = {
        "id": "movies",
        "task": "Implement movie navigation and tests",
        "paths": ["app/movies"],
    }
    if movies_depends_on_channels:
        movies["depends_on"] = ["channels"]

    return {
        "request": "Implement channel and movie navigation with required integration tests",
        "target_repository": "martaxi-boss/pink-iptv",
        "preference": "serial",
        "work_items": [
            {
                "id": "channels",
                "task": "Implement channel navigation and tests",
                "paths": ["app/channels"],
            },
            movies,
        ],
    }


class LiveSerialPolicyContractTests(unittest.TestCase):
    def test_explicit_serial_preference_assigns_two_workers(self):
        result = plan(_order())

        self.assertEqual(result["mode"], "serial")
        self.assertEqual(result["agent_count"], 2)
        self.assertEqual(
            [worker["id"] for worker in result["tasks"]],
            ["channels", "movies"],
        )

    def test_dependency_preserves_channels_before_movies(self):
        result = plan(_order(movies_depends_on_channels=True))

        self.assertEqual(result["mode"], "serial")
        self.assertEqual(result["agent_count"], 2)
        self.assertEqual(
            [worker["id"] for worker in result["tasks"]],
            ["channels", "movies"],
        )


if __name__ == "__main__":
    unittest.main()
