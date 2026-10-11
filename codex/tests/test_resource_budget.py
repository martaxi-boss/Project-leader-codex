"""Atomic conservation of real and unknown tokens under a private shared cap."""
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest

from codex import resource_budget as ledger


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "private"

    def test_reserve_both_workers_atomically_and_count_cached_once(self):
        r = ledger.reserve_batch(self.root, "a" * 32, [{"id": "one", "effort": "medium"}, {"id": "two", "effort": "high"}], 150000)
        self.assertEqual(r["reserved_tokens"], 110000)
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)
        res = ledger.settle_batch(self.root, "a" * 32, {"one": {"input_tokens": 1000, "output_tokens": 500, "cached_input_tokens": 900}, "two": None})
        self.assertEqual(res["accounted_tokens"], 76500)
        self.assertEqual(res["observed_jobs"], 1)
        self.assertEqual(res["conservative_jobs"], 1)
        self.assertNotIn("prompt", (self.root / "usage.json").read_text())
        self.assertEqual(stat.S_IMODE((self.root / "usage.json").stat().st_mode), 0o600)
        with self.assertRaises(ledger.BudgetError):
            ledger.settle_batch(self.root, "a" * 32, {"one": None, "two": None})

    def test_parallel_local_budget_limit_never_reserves_both_if_insufficient(self):
        barrier = threading.Barrier(2)
        passed, blocked = [], []
        def job(key):
            barrier.wait(timeout=5)
            try:
                ledger.reserve_batch(self.root, key, [{"id": "worker", "effort": "high"}], 100000)
                passed.append(key)
            except ledger.BudgetError:
                blocked.append(key)
        threads = [threading.Thread(target=job, args=("b" * 32,)), threading.Thread(target=job, args=("c" * 32,))]
        for t in threads: t.start()
        for t in threads: t.join(timeout=10)
        self.assertEqual(len(passed), 1)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(len(json.loads((self.root / "usage.json").read_text())["records"]), 1)

    def test_invalid_replay_and_usage_safety(self):
        ledger.reserve_batch(self.root, "d" * 32, [{"id": "one", "effort": "low"}])
        with self.assertRaises(ledger.BudgetError):
            ledger.reserve_batch(self.root, "d" * 32, [{"id": "one", "effort": "low"}])
        with self.assertRaises(ledger.BudgetError):
            ledger.settle_batch(self.root, "d" * 32, {"one": {"input_tokens": 3, "output_tokens": 2, "cached_input_tokens": 4}})

    def test_malformed_json_task_identity_and_effort_are_guarded(self):
        for bad in ([], {}, 5, None):
            with self.subTest(run=bad), self.assertRaises(ledger.BudgetError):
                ledger.reserve_batch(self.root, bad, [{"id": "one", "effort": "low"}])
            with self.subTest(tasks=bad), self.assertRaises(ledger.BudgetError):
                ledger.reserve_batch(self.root, "f" * 32, bad)
            for field in ("id", "effort"):
                task = {"id": "one", "effort": "medium"}
                task[field] = bad
                with self.subTest(field=field, value=bad), self.assertRaises(ledger.BudgetError):
                    ledger.reserve_batch(self.root, "f" * 32, [task])

    def test_cli_jsonl_usage_missing_is_unknown_not_zero(self):
        log = Path(self.tmp.name) / "codex.jsonl"
        log.write_text('\n'.join([
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20, "cached_input_tokens": 40}}),
            json.dumps({"type": "item.completed", "usage": {"input_tokens": 20000}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 50, "output_tokens": 10, "cached_input_tokens": 5}}),
        ]))
        self.assertEqual(ledger.codex_usage_file(log)["input_tokens"], 150)
        log.write_text('{"type":"turn.completed"}')
        self.assertIsNone(ledger.codex_usage_file(log))


if __name__ == "__main__":
    unittest.main()
