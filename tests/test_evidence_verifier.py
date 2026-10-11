import base64
import hashlib
import unittest
from unittest.mock import patch

from control.verify_github_evidence import (
    ci_run_requires_recovery_journal,
    list_same_sha_workflow_runs,
    verify_authorization_payloads,
    verify_compare_payload,
    verify_recovery_journal_records,
    verify_same_sha_ci_consistency,
    verify_recovery_retry_causality,
    verify_recovery_structural_causality,
    verify_run_payload,
)


class EvidenceVerifierTests(unittest.TestCase):
    def setUp(self):
        self.repository = "martaxi-boss/Project-leader"
        self.result = {
            "implementation_head_sha": "a" * 40,
        }
        self.ci = {"name": "Control contract tests", "status": "SUCCESS", "run_id": 123}
        self.run = {
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": self.repository},
        }

    def test_matching_run_is_accepted(self):
        self.assertTrue(verify_run_payload(self.ci, self.result, self.run, self.repository))

    def test_wrong_sha_is_rejected(self):
        self.run["head_sha"] = "b" * 40
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_failed_run_is_rejected(self):
        self.run["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_wrong_workflow_name_is_rejected(self):
        self.run["name"] = "Other"
        with self.assertRaises(ValueError):
            verify_run_payload(self.ci, self.result, self.run, self.repository)

    def test_same_sha_push_green_and_pr_red_is_rejected(self):
        selected = {
            "id": 10,
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }
        runs = [
            selected,
            {
                "id": 11,
                "name": "Control contract tests",
                "head_sha": "a" * 40,
                "event": "pull_request",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-03T01:01:00Z",
            },
        ]
        with self.assertRaises(ValueError):
            verify_same_sha_ci_consistency(self.ci, self.result, selected, runs)

    def test_later_success_supersedes_older_failure_in_same_context(self):
        selected = {
            "id": 12,
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "event": "pull_request",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:02:00Z",
        }
        runs = [
            {
                "id": 11,
                "name": "Control contract tests",
                "head_sha": "a" * 40,
                "event": "pull_request",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-03T01:01:00Z",
            },
            selected,
        ]
        self.assertTrue(
            verify_same_sha_ci_consistency(self.ci, self.result, selected, runs)
        )

    def test_latest_active_same_sha_context_is_rejected(self):
        selected = {
            "id": 10,
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }
        runs = [
            selected,
            {
                "id": 13,
                "name": "Control contract tests",
                "head_sha": "a" * 40,
                "event": "pull_request",
                "status": "in_progress",
                "conclusion": None,
                "created_at": "2026-10-03T01:03:00Z",
            },
        ]
        with self.assertRaises(ValueError):
            verify_same_sha_ci_consistency(self.ci, self.result, selected, runs)

    def test_unrelated_workflow_failure_does_not_block_required_workflow(self):
        selected = {
            "id": 10,
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }
        runs = [
            selected,
            {
                "id": 20,
                "name": "Unrelated workflow",
                "head_sha": "a" * 40,
                "event": "pull_request",
                "status": "completed",
                "conclusion": "failure",
                "created_at": "2026-10-03T01:04:00Z",
            },
        ]
        self.assertTrue(
            verify_same_sha_ci_consistency(self.ci, self.result, selected, runs)
        )

    def test_selected_run_must_exist_in_same_sha_listing(self):
        selected = {
            "id": 10,
            "name": "Control contract tests",
            "head_sha": "a" * 40,
            "event": "push",
            "status": "completed",
            "conclusion": "success",
            "created_at": "2026-10-03T01:00:00Z",
        }
        with self.assertRaises(ValueError):
            verify_same_sha_ci_consistency(self.ci, self.result, selected, [])

    @patch("control.verify_github_evidence.api_get")
    def test_same_sha_workflow_listing_paginates_beyond_first_100(self, mocked_get):
        mocked_get.side_effect = [
            {
                "total_count": 101,
                "workflow_runs": [{"id": index} for index in range(1, 101)],
            },
            {
                "total_count": 101,
                "workflow_runs": [{"id": 101}],
            },
        ]
        runs = list_same_sha_workflow_runs(
            self.repository,
            "a" * 40,
            "token",
            "https://api.github.com",
        )
        self.assertEqual(101, len(runs))
        self.assertEqual(2, mocked_get.call_count)
        self.assertIn("page=1", mocked_get.call_args_list[0].args[0])
        self.assertIn("page=2", mocked_get.call_args_list[1].args[0])

    @patch("control.verify_github_evidence.api_get")
    def test_same_sha_workflow_listing_fails_closed_at_search_limit(self, mocked_get):
        mocked_get.return_value = {
            "total_count": 1000,
            "workflow_runs": [{"id": index} for index in range(1, 101)],
        }
        with self.assertRaisesRegex(ValueError, "1000-result search limit"):
            list_same_sha_workflow_runs(
                self.repository,
                "a" * 40,
                "token",
                "https://api.github.com",
            )

    @patch("control.verify_github_evidence.api_get")
    def test_same_sha_workflow_listing_rejects_unstable_pagination(self, mocked_get):
        mocked_get.side_effect = [
            {
                "total_count": 101,
                "workflow_runs": [{"id": index} for index in range(1, 101)],
            },
            {
                "total_count": 102,
                "workflow_runs": [{"id": 101}],
            },
        ]
        with self.assertRaisesRegex(ValueError, "changed during pagination"):
            list_same_sha_workflow_runs(
                self.repository,
                "a" * 40,
                "token",
                "https://api.github.com",
            )

    def test_ancestor_compare_with_task_local_result_only_is_accepted(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [{"filename": ".project-leader/results/TASK-001.json"}],
        }
        self.assertTrue(
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")
        )

    def test_post_ci_material_change_is_rejected(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {"filename": ".project-leader/results/TASK-001.json"},
                {"filename": "src/app.py"},
            ],
        }
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

    def test_other_task_metadata_after_ci_is_rejected(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [{"filename": ".project-leader/results/OTHER-TASK.json"}],
        }
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

    def test_task_local_recovery_and_transition_result_after_ci_are_accepted(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {"filename": ".project-leader/recovery-events/TASK-001/0003.json"},
                {"filename": ".project-leader/transitions/TASK-001-TRUST-ROOT.result.json"},
                {"filename": ".project-leader/results/TASK-001.json"},
            ],
        }
        self.assertTrue(
            verify_compare_payload(
                payload,
                "a" * 40,
                "b" * 40,
                "TASK-001",
                task_local_transition_paths={
                    ".project-leader/transitions/TASK-001-TRUST-ROOT.result.json"
                },
            )
        )

    def test_post_ci_compare_without_file_evidence_is_rejected(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
        }
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

    def test_post_ci_compare_below_github_file_limit_is_accepted(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {
                    "filename": f".project-leader/recovery-events/TASK-001/{index:04d}.json"
                }
                for index in range(299)
            ],
        }
        self.assertTrue(
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")
        )

    def test_post_ci_compare_at_github_file_limit_is_rejected(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {
                    "filename": f".project-leader/recovery-events/TASK-001/{index:04d}.json"
                }
                for index in range(300)
            ],
        }
        with self.assertRaisesRegex(ValueError, "300-file limit"):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

    def test_diverged_compare_is_rejected(self):
        payload = {"status": "diverged", "base_commit": {"sha": "a" * 40}, "commits": []}
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40)

    def recovery_event(self, sequence, kind, previous=None, attempt=1):
        return {
            "schema_version": "1.0",
            "task_id": "TASK-001",
            "repository": self.repository,
            "sequence": sequence,
            "recorded_at": f"2026-10-03T01:0{sequence}:00Z",
            "event": kind,
            "strategy_generation": 1,
            "action_fingerprint": "ci|android|rerun",
            "attempt_count": attempt,
            "identical_failure_count": 1,
            "no_progress_iterations": 1,
            "previous_event_sha256": previous,
            "detail": "test recovery",
        }

    def test_run_attempt_two_requires_recovery_journal(self):
        self.assertFalse(ci_run_requires_recovery_journal({"run_attempt": 1}))
        self.assertTrue(ci_run_requires_recovery_journal({"run_attempt": 2}))

    def test_fresh_technical_remediation_run_stays_compact(self):
        self.assertFalse(ci_run_requires_recovery_journal({"run_attempt": 1, "head_sha": "b" * 40}))

    def test_retry_requires_valid_recovery_journal(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        self.assertTrue(verify_recovery_journal_records(result, [first, second, third]))

    def test_successful_retry_without_recovered_event_fails(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        with self.assertRaises(ValueError):
            verify_recovery_journal_records(result, [first, second])

    def structural_compare(self, base, head, status="ahead"):
        return {
            "status": status,
            "base_commit": {"sha": base},
            "commits": [] if status == "identical" else [{"sha": head}],
            "files": [],
        }

    def test_structural_recovery_causality_accepts_pre_retry_ancestry_and_post_run_recovered(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
            "implementation_head_sha": "d" * 40,
        }
        persistence = [
            {"commit_sha": "a" * 40, "persisted_at": "2026-10-03T01:01:00Z"},
            {"commit_sha": "b" * 40, "persisted_at": "2026-10-03T01:02:00Z"},
            {"commit_sha": "e" * 40, "persisted_at": "2026-10-03T01:04:00Z"},
        ]
        ancestry = {
            0: self.structural_compare("a" * 40, "d" * 40),
            1: self.structural_compare("b" * 40, "d" * 40),
            2: self.structural_compare("d" * 40, "e" * 40),
        }
        self.assertTrue(
            verify_recovery_structural_causality(result, [first, second, third], persistence, ancestry)
        )

    def test_structural_recovery_rejects_retry_authorization_outside_run_ancestry(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
            "implementation_head_sha": "d" * 40,
        }
        persistence = [
            {"commit_sha": "a" * 40, "persisted_at": "2026-10-03T01:01:00Z"},
            {"commit_sha": "b" * 40, "persisted_at": "2026-10-03T01:02:00Z"},
            {"commit_sha": "e" * 40, "persisted_at": "2026-10-03T01:04:00Z"},
        ]
        ancestry = {
            0: self.structural_compare("a" * 40, "d" * 40),
            1: {"status": "diverged", "base_commit": {"sha": "b" * 40}, "commits": []},
            2: self.structural_compare("d" * 40, "e" * 40),
        }
        with self.assertRaises(ValueError):
            verify_recovery_structural_causality(result, [first, second, third], persistence, ancestry)

    def test_structural_recovery_rejects_recovered_inside_implementation_head(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
            "implementation_head_sha": "d" * 40,
        }
        persistence = [
            {"commit_sha": "a" * 40, "persisted_at": "2026-10-03T01:01:00Z"},
            {"commit_sha": "b" * 40, "persisted_at": "2026-10-03T01:02:00Z"},
            {"commit_sha": "d" * 40, "persisted_at": "2026-10-03T01:03:00Z"},
        ]
        ancestry = {
            0: self.structural_compare("a" * 40, "d" * 40),
            1: self.structural_compare("b" * 40, "d" * 40),
            2: self.structural_compare("d" * 40, "d" * 40, status="identical"),
        }
        with self.assertRaises(ValueError):
            verify_recovery_structural_causality(result, [first, second, third], persistence, ancestry)

    def test_structural_recovery_requires_recovered_after_latest_retry(self):
        first = self.recovery_event(1, "RECOVERED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
            "implementation_head_sha": "d" * 40,
        }
        persistence = [
            {"commit_sha": "e" * 40, "persisted_at": "2026-10-03T01:01:00Z"},
            {"commit_sha": "b" * 40, "persisted_at": "2026-10-03T01:02:00Z"},
        ]
        ancestry = {
            0: self.structural_compare("d" * 40, "e" * 40),
            1: self.structural_compare("b" * 40, "d" * 40),
        }
        with self.assertRaises(ValueError):
            verify_recovery_structural_causality(result, [first, second], persistence, ancestry)

    def test_retry_causality_accepts_precommitted_authorization(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        persistence = [
            {"persisted_at": "2026-10-03T01:01:10Z"},
            {"persisted_at": "2026-10-03T01:01:50Z"},
            {"persisted_at": "2026-10-03T01:03:10Z"},
        ]
        runs = [{
            "run_attempt": 2,
            "run_started_at": "2026-10-03T01:02:00Z",
            "updated_at": "2026-10-03T01:03:00Z",
        }]
        self.assertTrue(
            verify_recovery_retry_causality(result, [first, second, third], persistence, runs)
        )

    def test_retroactive_retry_authorization_is_rejected(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        persistence = [
            {"persisted_at": "2026-10-03T01:01:10Z"},
            {"persisted_at": "2026-10-03T01:02:10Z"},
            {"persisted_at": "2026-10-03T01:03:10Z"},
        ]
        runs = [{
            "run_attempt": 2,
            "run_started_at": "2026-10-03T01:02:00Z",
            "updated_at": "2026-10-03T01:03:00Z",
        }]
        with self.assertRaises(ValueError):
            verify_recovery_retry_causality(result, [first, second, third], persistence, runs)

    def test_recovered_event_cannot_predate_success(self):
        from control.validate_records import canonical_sha256

        first = self.recovery_event(1, "FAILURE_OBSERVED", attempt=1)
        second = self.recovery_event(2, "RETRY_AUTHORIZED", canonical_sha256(first), attempt=2)
        third = self.recovery_event(3, "RECOVERED", canonical_sha256(second), attempt=2)
        result = {
            "task_id": "TASK-001",
            "repository": self.repository,
            "terminal_status": "TERMINAL_SUCCESS",
        }
        persistence = [
            {"persisted_at": "2026-10-03T01:01:10Z"},
            {"persisted_at": "2026-10-03T01:01:50Z"},
            {"persisted_at": "2026-10-03T01:02:50Z"},
        ]
        runs = [{
            "run_attempt": 2,
            "run_started_at": "2026-10-03T01:02:00Z",
            "updated_at": "2026-10-03T01:03:00Z",
        }]
        with self.assertRaises(ValueError):
            verify_recovery_retry_causality(result, [first, second, third], persistence, runs)

    def auth_payload(self, raw):
        return {
            "encoding": "base64",
            "content": base64.b64encode(raw).decode("ascii"),
        }

    def test_immutable_authorization_binding_is_accepted(self):
        raw = b'{"task_id":"TASK-001"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "ahead",
            "base_commit": {"sha": "c" * 40},
            "commits": [{"sha": "a" * 40}],
        }
        self.assertTrue(
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(raw),
                ancestry,
            )
        )

    def test_changed_authorization_after_binding_is_rejected(self):
        raw = b'{"task_id":"TASK-001"}\n'
        changed = b'{"task_id":"TASK-001","scope":"wider"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "ahead",
            "base_commit": {"sha": "c" * 40},
            "commits": [{"sha": "a" * 40}],
        }
        with self.assertRaises(ValueError):
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(changed),
                ancestry,
            )

    def test_terminal_success_requires_work_after_authorization_commit(self):
        raw = b'{"task_id":"TASK-001"}\n'
        result = {
            "terminal_status": "TERMINAL_SUCCESS",
            "authorization_commit_sha": "c" * 40,
            "authorization_sha256": hashlib.sha256(raw).hexdigest(),
        }
        ancestry = {
            "status": "identical",
            "base_commit": {"sha": "c" * 40},
            "commits": [],
        }
        with self.assertRaises(ValueError):
            verify_authorization_payloads(
                result,
                self.auth_payload(raw),
                self.auth_payload(raw),
                ancestry,
            )


if __name__ == "__main__":
    unittest.main()
