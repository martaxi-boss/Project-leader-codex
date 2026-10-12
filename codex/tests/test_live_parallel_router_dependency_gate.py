"""Regression tests for the live parallel router dependency gate."""
import unittest

from codex.agent_policy import plan, RoutingError


class LiveParallelRouterDependencyGateTests(unittest.TestCase):
    def setUp(self):
        self.order = {
            "request": "Implement channel and movie navigation with required integration tests",
            "target_repository": "martaxi-boss/pink-iptv",
            "preference": "parallel",
            "work_items": [
                {
                    "id": "channels",
                    "paths": ["app/channels"],
                    "task": "Implement channel navigation and tests",
                },
                {
                    "id": "movies",
                    "paths": ["app/movies"],
                    "task": "Implement movie navigation and tests",
                },
            ],
        }

    def test_independent_scopes_route_to_two_parallel_agents(self):
        result = plan(self.order)

        self.assertEqual(result["mode"], "parallel")
        self.assertEqual(result["agent_count"], 2)

    def test_dependency_rejects_parallel_routing(self):
        self.order["work_items"][1]["depends_on"] = ["channels"]

        with self.assertRaises(RoutingError):
            plan(self.order)

    def test_nested_path_rejects_parallel_routing(self):
        self.order["work_items"][1]["paths"] = ["app/channels/subdir"]

        with self.assertRaises(RoutingError):
            plan(self.order)


if __name__ == "__main__":
    unittest.main()
