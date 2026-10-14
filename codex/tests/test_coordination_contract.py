"""Regression: specialized agent instructions match the implemented auto router."""
from pathlib import Path
import unittest

from codex.agent_policy import plan

ROOT = Path(__file__).resolve().parents[2]


def _item(identifier: str, path: str, *, depends_on=None):
    return {
        "id": identifier,
        "task": "Implement the isolated module, integrate with its tests, and validate the full regression behavior",
        "paths": [path],
        **({"depends_on": depends_on} if depends_on is not None else {}),
    }


class AgentCoordinationContractTests(unittest.TestCase):
    def test_specialized_docs_default_to_auto_without_claiming_chat_bridge(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        rules = (ROOT / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
        guide = (ROOT / "README_CODEX.md").read_text(encoding="utf-8")
        for document in (agents, rules):
            self.assertIn("codex.agent_policy.plan", document)
            self.assertIn("single", document)
            self.assertIn("serial", document)
            self.assertIn("parallel", document)
            self.assertIn("Owner", document)
            self.assertNotIn("Owner chooses mode", document)
        self.assertIn("Automatic mode by default", rules)
        self.assertIn("ChatGPT", agents)
        self.assertIn("ChatGPT", rules)
        # The Telegram gateway is implemented, but a green offline contract
        # must never be presented as a real authenticated end-to-end run.
        self.assertIn("**ChatGPT:**", guide)
        self.assertIn("Não existe garantia de despacho", guide)
        self.assertIn("**Codex direto:**", guide)
        self.assertIn("não está certificada", guide)
        self.assertIn("**Telegram:**", guide)
        self.assertIn("ainda falta observar uma", guide)
        self.assertIn("PHASE_STAGED_AWAITING_TARGET_CERTIFICATION", guide)

    def test_router_chooses_one_or_two_and_honors_safe_override(self):
        req = {
            "request": "Implement channel and movie navigation safely with required integration tests",
            "target_repository": "martaxi-boss/pink-iptv",
        }
        first = _item("channels", "app/channels")
        second = _item("movies", "app/movies")
        auto = plan({**req, "work_items": [first, second]})
        self.assertEqual((auto["mode"], auto["agent_count"]), ("parallel", 2))
        single = plan({**req, "work_items": [first, second], "preference": "single"})
        self.assertEqual((single["mode"], single["agent_count"]), ("single", 1))
        serial = plan({**req, "work_items": [first, _item("movies", "app/movies", depends_on=["channels"])]})
        self.assertEqual((serial["mode"], serial["agent_count"]), ("serial", 2))


if __name__ == "__main__":
    unittest.main()
