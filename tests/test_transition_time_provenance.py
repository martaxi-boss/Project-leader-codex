import copy
import unittest

from control.validate_records import (
    validate_current_transition_pair,
    validate_transition_pair,
)


def valid_authorization():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-TRANSITION-TIME-001",
        "task_id": "TEST-TRANSITION-TIME-001",
        "repository": "owner/repo",
        "created_at": "2026-10-07T10:00:00Z",
        "action": "merge_to_main",
        "effect_class": "E2_CONSEQUENTIAL_TRANSITION",
        "authority": {
            "source": "STANDING_OWNER_GRANT",
            "summary": "test",
            "binding_mode": "EXACT_REVISION_BOUND",
        },
        "target": {
            "kind": "pull_request",
            "identifier": "https://example.test/pr/1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
    }


def valid_result():
    return {
        "schema_version": "1.0",
        "transition_id": "TEST-TRANSITION-TIME-001",
        "task_id": "TEST-TRANSITION-TIME-001",
        "repository": "owner/repo",
        "terminal_status": "SUCCESS",
        "authorization_record": (
            ".project-leader/transitions/"
            "TEST-TRANSITION-TIME-001.authorization.json"
        ),
        "action": "merge_to_main",
        "target": {
            "kind": "pull_request",
            "identifier": "https://example.test/pr/1",
            "revision": "b" * 40,
            "base_revision": "a" * 40,
            "environment": None,
        },
        "observed_at": "2026-10-07T10:00:30Z",
        "final_state": {"status": "MERGED", "revision": "c" * 40},
        "evidence": ["merged"],
        "residual_blockers": [],
    }


class TransitionTimeProvenanceTests(unittest.TestCase):
    def test_current_pair_accepts_authorization_before_observation(self):
        self.assertTrue(
            validate_current_transition_pair(
                valid_authorization(),
                valid_result(),
            )
        )

    def test_current_pair_rejects_temporal_inversion(self):
        authorization = valid_authorization()
        authorization["created_at"] = "2026-10-07T10:01:00Z"
        result = valid_result()
        with self.assertRaisesRegex(
            ValueError, "created_at cannot be later than"
        ):
            validate_current_transition_pair(authorization, result)

    def test_legacy_pair_remains_readable_when_structurally_consistent(self):
        authorization = valid_authorization()
        authorization["created_at"] = "2026-10-07T10:01:00Z"
        result = valid_result()
        self.assertTrue(validate_transition_pair(authorization, result))

    def test_current_pair_keeps_structural_identity_checks(self):
        authorization = valid_authorization()
        result = copy.deepcopy(valid_result())
        result["target"]["revision"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "mismatch for target"):
            validate_current_transition_pair(authorization, result)


if __name__ == "__main__":
    unittest.main()
