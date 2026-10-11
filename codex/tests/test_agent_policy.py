"""Routing acceptance tests: balanced intelligence, reasoning, and agent count."""
import copy
import unittest

from codex.agent_policy import RoutingError, load_registry, plan


def item(name, path, prompt="Implement the navigation and validate it with focused integration tests.", **kwargs):
    return {"id": name, "task": prompt, "paths": [path], **kwargs}


def request(items, **kwargs):
    return {"request": "Improve channels and movies while keeping existing features working",
            "target_repository": "martaxi-boss/pink-iptv", "work_items": items, **kwargs}


class RoutingTests(unittest.TestCase):
    def test_unknown_user_scope_never_invents_files_or_spends_tokens(self):
        result = plan({"request": "Corrige os menus dos filmes e dos canais da minha aplicação",
                       "target_repository": "martaxi-boss/pink-iptv"})
        self.assertEqual(result["status"], "needs_scoping")
        self.assertEqual(result["agent_count"], 0)
        self.assertNotIn("tasks", result)

    def test_malformed_json_effort_dependencies_and_registry_fail_closed(self):
        base = request([item("one", "src/x")])
        for bad in ([], {}, 9):
            broken = {**base, "work_items": [{**base["work_items"][0], "reasoning_effort": bad}]}
            with self.subTest(effort=bad), self.assertRaises(RoutingError):
                plan(broken)
        bad_dep = {**base, "work_items": [{**base["work_items"][0], "depends_on": [{}]}]}
        with self.assertRaises(RoutingError):
            plan(bad_dep)
        reg = load_registry()
        reg["providers"][0]["models"][0]["efforts"] = [{}]
        with self.assertRaises(RoutingError):
            plan(base, reg)

    def test_accented_security_and_concurrency_require_high_capability(self):
        for request_text in ("Corrige a segurança e valida os testes",
                             "Diagnostica concorrência de threads e aplica testes"):
            p = plan({"request": request_text,
                      "target_repository": "martaxi-boss/pink-iptv",
                      "work_items": [item("one", "src/core", request_text)]})
            self.assertEqual(p["tasks"][0]["selection"]["reasoning_effort"], "high")
            self.assertEqual(p["status"], "blocked_no_provider")

    def test_short_simple_tasks_use_single_agent_to_avoid_duplicate_cost(self):
        p = plan(request([item("first", "docs/a", "Corrige um typo no README da secção A"),
                          item("second", "docs/b", "Corrige um typo no README da secção B")]))
        self.assertEqual(p["mode"], "single")
        self.assertEqual(p["agent_count"], 1)
        self.assertEqual(p["tasks"][0]["selection"]["reasoning_effort"], "medium")

    def test_two_independent_significant_work_items_parallel(self):
        p = plan(request([item("channels", "app/channels", "Implement the channel interface, validate the player integration, and run regression tests"),
                          item("movies", "app/movies", "Implement the movie catalogue, integrate search and run regression tests")]))
        self.assertEqual(p["mode"], "parallel")
        self.assertEqual(p["agent_count"], 2)
        self.assertEqual([x["selection"]["provider"] for x in p["tasks"]], ["codex", "codex"])

    def test_parallel_does_not_follow_large_number_of_dependent_phases(self):
        p = plan(request([item("build", "app/core", "Implement complex playback interface, integrate feature and run regression tests"),
                          item("verify", "tests/core", "Test new playback integration, implement fixes and run full regression tests", depends_on=["build"])]))
        self.assertEqual(p["mode"], "serial")
        p2 = plan(request([item("build", "app/core", "Implement it"),
                           item("verify", "tests/core", "Verify it after first", depends_on=["build"])]))
        self.assertEqual(p2["mode"], "single")

    def test_worktree_overlap_falls_back_single_not_unsafe_parallel(self):
        p = plan(request([item("one", "app", "Implement channel browsing and test the playback controller"),
                          item("two", "app/movies", "Implement movie browsing and test the playback controller")]))
        self.assertEqual(p["mode"], "single")
        with self.assertRaises(RoutingError):
            plan(request([item("one", "app", "Implement channel browsing and test player"),
                          item("two", "app/movies", "Implement movie browsing and test player")], preference="parallel"))

    def test_invalid_duplicate_cyclic_and_secret_orders_block(self):
        with self.assertRaises(RoutingError):
            plan(request([item("first", "src/a"), item("first", "src/b")]))
        with self.assertRaises(RoutingError):
            plan(request([item("first", "src/a", depends_on=["second"]),
                          item("second", "src/b", depends_on=["first"])]))
        with self.assertRaises(RoutingError):
            plan(request([item("first", "../src", "Implement safe change for a module")]))
        with self.assertRaises(RoutingError):
            plan(request([item("first", "src/core", "api_key = supersecretvalue")]))
        with self.assertRaises(RoutingError):
            plan({**request([item("first", "src/a")]), "target_repository": "martaxi-boss/Project-leader"})

    def test_planned_material_boundaries_carry_unchanged_human_authority(self):
        p = plan({**request([item("deploy", "app/core", "Deploy to production after validating regression tests")]),
                  "request": "Deploy new version to production after tests"})
        self.assertIn("material_boundary_requires_project_leader_controls", p["warnings"])

    def test_requires_available_attested_provider_not_fake_cloud_support(self):
        reg = load_registry()
        blocked = plan(request([item("job", "src")], providers=["gemini"]), reg)
        self.assertEqual(blocked["status"], "blocked_no_provider")
        self.assertEqual(blocked["tasks"][0]["selection"]["status"], "no_attested_provider")
        unknown = copy.deepcopy(reg)
        unknown["providers"][0]["enabled"] = False
        self.assertEqual(plan(request([item("job", "src")]), unknown)["status"], "blocked_no_provider")

    def test_multi_vendor_model_selection_uses_attested_capabilities_and_cost_floor(self):
        reg = load_registry()
        reg["providers"].append({"id": "sample-cloud", "adapter": "host-unconfigured", "enabled": True,
                                 "models": [
                                     {"id": "cheap-insufficient", "quality_tier": 1, "relative_cost": 1,
                                      "capabilities": ["code_edit"], "efforts": ["low", "medium", "high"], "attested": True},
                                     {"id": "balanced", "quality_tier": 3, "relative_cost": 3,
                                      "capabilities": ["code_edit"], "efforts": ["low", "medium", "high"], "attested": True},
                                     {"id": "expensive", "quality_tier": 5, "relative_cost": 9,
                                      "capabilities": ["code_edit"], "efforts": ["low", "medium", "high"], "attested": True}]})
        p = plan(request([item("job", "src")], providers=["sample-cloud"]), reg)
        self.assertEqual(p["tasks"][0]["selection"]["model"], "balanced")
        p2 = plan(request([item("hard", "src", "Diagnose deadlock and make a safe fix")], providers=["sample-cloud"]), reg)
        self.assertEqual(p2["tasks"][0]["selection"]["model"], "expensive")
        self.assertEqual(p2["tasks"][0]["selection"]["reasoning_effort"], "high")

    def test_reasoning_low_only_bounded_simple_not_general_task(self):
        p = plan(request([item("spell", "docs", "Corrige um typo no README da interface")]))
        self.assertEqual(p["tasks"][0]["selection"]["reasoning_effort"], "low")
        p = plan(request([item("fix", "docs", "Improve architecture and make sure critical security is protected")]))
        self.assertEqual(p["status"], "blocked_no_provider")
        self.assertEqual(p["tasks"][0]["selection"]["status"], "no_adequate_provider")

    def test_protected_actions_inside_subtasks_require_material_control(self):
        p = plan(request([item("job", "src", "Deploy to production and publish new credentials safely")]))
        self.assertIn("material_boundary_requires_project_leader_controls", p["warnings"])

    def test_not_enough_model_capacity_does_not_silently_use_cheapest(self):
        reg = load_registry()
        p = plan(request([item("hard", "src", "Diagnose deadlock in the account recovery flow")]), reg)
        self.assertEqual(p["status"], "blocked_no_provider")
        self.assertEqual(p["tasks"][0]["selection"]["status"], "no_adequate_provider")


if __name__ == "__main__":
    unittest.main()

class MultiStageRoutingTests(unittest.TestCase):
    def test_six_disjoint_phases_are_balanced_into_two_workers(self):
        phases = [item(f"part-{i}", f"src/area-{i}",
                       f"Implement feature {i}, integrate with existing functionality, and test regression behavior")
                  for i in range(6)]
        p = plan(request(phases))
        self.assertEqual(p["agent_count"], 2)
        self.assertEqual(p["mode"], "parallel")
        paths0 = set(p["tasks"][0]["paths"])
        paths1 = set(p["tasks"][1]["paths"])
        self.assertEqual(len(paths0 | paths1), 6)
        self.assertFalse(paths0 & paths1)

    def test_four_dependent_phases_use_serial_two_workers(self):
        steps = []
        for i in range(4):
            dependency = [f"part-{i-1}"] if i else []
            steps.append(item(f"part-{i}", f"src/step-{i}",
                              f"Implement stage {i}, integrate it and run tests for the full subsystem",
                              depends_on=dependency))
        p = plan(request(steps))
        self.assertEqual(p["mode"], "serial")
        self.assertEqual(p["agent_count"], 2)
        self.assertEqual(p["tasks"][1]["depends_on"], ["phase-one"])

    def test_three_phase_cycle_rejected(self):
        phases = [item("first", "src/a", depends_on=["third"]),
                  item("second", "src/b", depends_on=["first"]),
                  item("third", "src/c", depends_on=["second"])]
        with self.assertRaises(RoutingError):
            plan(request(phases))
