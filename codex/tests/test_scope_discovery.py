"""Offline, fail-closed discovery tests using a real temporary Git checkout."""
import io
import json
from contextlib import redirect_stdout
import subprocess
import tempfile
from pathlib import Path
import unittest

from codex.agent_policy import plan
from codex.scope_discovery import discover_work_items
from codex.smart import main


class ScopeDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        def git(*args):
            return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, check=True)
        git("init", "-q")
        git("config", "user.email", "test@example.test")
        git("config", "user.name", "Offline Test")
        git("remote", "add", "origin", "https://github.com/martaxi-boss/pink-iptv.git")
        for name in ("src/channels/main.py", "src/movies/main.py", "src/shared/helpers.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample\n")
        git("add", ".")
        git("commit", "-qm", "initial")
        self.order = {"request": "Implementar o menu dos canais e filmes com testes e integração segura",
                      "target_repository": "martaxi-boss/pink-iptv"}

    def _add_tracked_codex_files(self):
        for name in ("codex/smart.py", "codex/tests/test_smart.py"):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("sample\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "add-codex-code"], check=True)

    def test_explicit_existing_file_takes_priority_over_generic_tests(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Corrige a falha em codex/smart.py e verifica os testes relacionados")
        scoped = discover_work_items(order, self.repo)
        self.assertEqual(scoped["work_items"][0]["paths"], ["codex/smart.py"])
        self.assertEqual(len(scoped["work_items"]), 1)
        self.assertEqual(plan(scoped)["mode"], "single")

    def test_natural_language_cli_preserves_explicit_target(self):
        self._add_tracked_codex_files()
        request = "Corrige o problema em codex/smart.py e executa os testes de regressao"
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["plan", "--task", request, "--repo-dir", str(self.repo)])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["tasks"][0]["paths"], ["codex/smart.py"])
        self.assertEqual(result["agent_count"], 1)

    def test_ambiguous_two_exact_files_need_host_scoping(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Corrige codex/smart.py e codex/tests/test_smart.py e testa ambos")
        self.assertNotIn("work_items", discover_work_items(order, self.repo))
        self.assertEqual(plan(order)["status"], "needs_scoping")

    def test_existing_and_missing_explicit_paths_need_scoping(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Corrige codex/smart.py e codex/missing.py e executa os testes")
        self.assertNotIn("work_items", discover_work_items(order, self.repo))
        self.assertEqual(plan(order)["status"], "needs_scoping")

    def test_untracked_explicit_filename_cannot_fall_back_to_tests(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Corrige codex/untracked_module.py e verifica os testes")
        self.assertNotIn("work_items", discover_work_items(order, self.repo))
        self.assertEqual(plan(order)["status"], "needs_scoping")

    def test_partial_filename_does_not_authorize_tracked_file(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Corrige codex/smart.py.backup e confirma os testes")
        self.assertNotIn("work_items", discover_work_items(order, self.repo))

    def test_negation_never_grants_explicit_file_scope(self):
        self._add_tracked_codex_files()
        order = dict(self.order,
                     request="Melhora o canal sem mexer no codex/smart.py")
        self.assertNotIn("work_items", discover_work_items(order, self.repo))

    def test_one_voice_order_generates_only_existing_paths_and_selects_parallel(self):
        scoped = discover_work_items(self.order, self.repo)
        self.assertEqual({x["id"] for x in scoped["work_items"]}, {"channels", "movies"})
        self.assertEqual({tuple(x["paths"]) for x in scoped["work_items"]},
                         {("src/channels",), ("src/movies",)})
        planned = plan(scoped)
        self.assertEqual(planned["mode"], "parallel")
        self.assertEqual(planned["agent_count"], 2)

    def test_tiny_two_area_edit_stays_with_one_agent(self):
        order = dict(self.order, request="Corrige um typo nos canais e filmes")
        scoped = discover_work_items(order, self.repo)
        self.assertEqual(plan(scoped)["mode"], "single")

    def test_smart_cli_accepts_one_order_without_manually_specified_workers(self):
        manifest = self.repo.parent / "owner-order.json"
        manifest.write_text(json.dumps(self.order), encoding="utf-8")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = main(["plan", "--order", str(manifest), "--repo-dir", str(self.repo)])
        self.assertEqual(rc, 0)
        result = json.loads(out.getvalue())
        self.assertEqual(result["agent_count"], 2)
        self.assertEqual(result["mode"], "parallel")

    def test_single_topic_starts_one_worker(self):
        o = dict(self.order, request="Corrige um typo na lista de filmes e verifica o resultado")
        scoped = discover_work_items(o, self.repo)
        self.assertEqual(scoped["work_items"][0]["paths"], ["src/movies"])
        self.assertEqual(plan(scoped)["agent_count"], 1)

    def test_ambiguous_request_stays_unscoped(self):
        o = dict(self.order, request="Refaz o sistema inteiro sem tocar no login")
        self.assertNotIn("work_items", discover_work_items(o, self.repo))
        self.assertEqual(plan(o)["status"], "needs_scoping")

    def test_validation_terms_are_not_split_as_separate_agents(self):
        p = self.repo / "tests/test_channels.py"; p.parent.mkdir(exist_ok=True)
        p.write_text("sample\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "add-tests"], check=True)
        scoped = discover_work_items(self.order, self.repo)
        self.assertEqual({x["id"] for x in scoped["work_items"]}, {"channels", "movies"})

    def test_negative_constraint_requires_host_scoping(self):
        p = dict(self.order, request="Corrige os canais sem mexer nos filmes")
        self.assertNotIn("work_items", discover_work_items(p, self.repo))

    def test_missing_real_paths_never_invented(self):
        o = dict(self.order, request="Implementa o módulo de meteorologia e instala todos os testes")
        self.assertNotIn("work_items", discover_work_items(o, self.repo))

    def test_dirty_checkout_blocks_scope_inspection(self):
        (self.repo / "untracked.txt").write_text("dirty")
        with self.assertRaisesRegex(Exception, "dirty"):
            discover_work_items(self.order, self.repo)

    def test_wrong_origin_blocks_scope_inspection(self):
        with self.assertRaisesRegex(Exception, "origin does not match"):
            discover_work_items({**self.order, "target_repository": "example/other"}, self.repo)

    def test_overlapping_areas_never_falsely_parallelized(self):
        # The same path matches two concepts; discovery may decline to split.
        p = self.repo / "src/channels/movies.py"; p.write_text("sample\n")
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "nested"], check=True)
        scoped = discover_work_items(self.order, self.repo)
        if "work_items" in scoped:
            planned = plan(scoped)
            self.assertNotEqual(planned["mode"], "parallel")


if __name__ == "__main__":
    unittest.main()
