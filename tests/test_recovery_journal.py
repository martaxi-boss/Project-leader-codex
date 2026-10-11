import copy
import unittest

from control.validate_records import canonical_sha256, validate_recovery_journal


def event(sequence, kind="FAILURE_OBSERVED", strategy=1, attempt=1, identical=1, no_progress=1, previous=None):
    return {
        "schema_version": "1.0",
        "task_id": "TEST-RECOVERY-001",
        "repository": "owner/repo",
        "sequence": sequence,
        "recorded_at": f"2026-10-02T22:3{sequence}:00Z",
        "event": kind,
        "strategy_generation": strategy,
        "action_fingerprint": "task|target|action|result",
        "attempt_count": attempt,
        "identical_failure_count": identical,
        "no_progress_iterations": no_progress,
        "previous_event_sha256": previous,
        "detail": "test",
    }


class RecoveryJournalTests(unittest.TestCase):
    def test_valid_hash_chained_journal(self):
        first = event(1)
        second = event(2, kind="RETRY_AUTHORIZED", attempt=2, identical=1, no_progress=1, previous=canonical_sha256(first))
        third = event(3, kind="COMPLETE", attempt=2, identical=1, no_progress=1, previous=canonical_sha256(second))
        self.assertTrue(validate_recovery_journal([first, second, third]))

    def test_counter_reset_in_same_strategy_fails(self):
        first = event(1, attempt=2, identical=2, no_progress=2)
        second = event(2, attempt=0, identical=0, no_progress=0, previous=canonical_sha256(first))
        with self.assertRaises(ValueError):
            validate_recovery_journal([first, second])

    def test_hash_chain_tamper_fails(self):
        first = event(1)
        second = event(2, previous="0" * 64)
        with self.assertRaises(ValueError):
            validate_recovery_journal([first, second])

    def test_strategy_generation_changes_only_on_replan(self):
        first = event(1)
        second = event(2, strategy=2, attempt=0, identical=0, no_progress=0, previous=canonical_sha256(first))
        with self.assertRaises(ValueError):
            validate_recovery_journal([first, second])
        second["event"] = "REPLAN"
        self.assertTrue(validate_recovery_journal([first, second]))

    def test_terminal_event_cannot_have_followup(self):
        first = event(1, kind="BLOCKED")
        second = event(2, kind="RETRY_AUTHORIZED", previous=canonical_sha256(first))
        with self.assertRaises(ValueError):
            validate_recovery_journal([first, second])


if __name__ == "__main__":
    unittest.main()
