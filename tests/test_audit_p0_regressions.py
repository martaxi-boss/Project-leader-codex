import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from control.scope_policy import scope_pattern_is_bounded
from control.trusted_gate import (
    canonical_task_path,
    verify_promotable_result,
    verify_task_against_base_policy,
)
from control.validate_records import (
    validate_persisted_transition_result,
    validate_scope,
    validate_transition_authorization,
)
from control.verify_github_evidence import verify_compare_payload

ROOT = Path(__file__).resolve().parents[1]


class AuditP0RegressionTests(unittest.TestCase):
    def project_policy(self):
        raw = (ROOT / "projects/policies/project-leader.json").read_bytes()
        return json.loads(raw.decode("utf-8")), raw

    def e1_task(self, scope=None):
        policy, raw = self.project_policy()
        effect = policy["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]
        base = "a" * 40
        task_id = "AUDIT-E1-PURGE-001"
        return {
            "schema_version": "2.0",
            "task_id": task_id,
            "project": "PROJECT LEADER",
            "repository": policy["repository"],
            "created_at": "2026-10-07T08:30:00Z",
            "authority": {
                "kind": "STANDING_DELEGATION",
                "summary": "P0 regression fixture",
                "source": "CURRENT_OWNER_INSTRUCTION",
                "binding_mode": "OBJECTIVE_SCOPE_BOUND",
            },
            "starting_state": {
                "default_branch": "main",
                "base_sha": base,
                "task_branch": "builder/audit-e1-purge-001",
                "pr_number": None,
            },
            "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
            "mutation_scope": scope or [
                ".project-leader/transitions/AUDIT-E1-PURGE-001-DELETE.authorization.json"
            ],
            "allowed_actions": list(effect["allowed_actions"]),
            "prohibited_actions": list(effect["required_prohibited_actions"]),
            "transition_controls": [
                {"action": action, "requires_authority_resolution": True}
                for action in effect["required_transition_controls"]
            ],
            "required_validation": list(effect["required_validation"]),
            "required_ci": list(effect["required_ci"]),
            "policy": {
                "binding_mode": "LOCAL_BASE_V1",
                "profile": policy["policy_id"],
                "path": "projects/policies/project-leader.json",
                "base_sha": base,
                "sha256": hashlib.sha256(raw).hexdigest(),
            },
            "recovery": {"mode": "APPEND_ONLY_V1"},
            "terminal_condition": "regression fixture",
            "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        }

    def test_e1_cannot_introduce_executable_transition_authorization(self):
        policy, raw = self.project_policy()
        task = self.e1_task()
        changed = [
            ".project-leader/transitions/AUDIT-E1-PURGE-001-DELETE.authorization.json"
        ]
        with self.assertRaisesRegex(ValueError, "trust-root mutation"):
            verify_task_against_base_policy(
                task,
                policy,
                raw,
                task["starting_state"]["base_sha"],
                changed,
                "projects/policies/project-leader.json",
                actual_task_path=canonical_task_path(task),
            )

    def test_new_or_changed_v2_task_cannot_disable_immutability(self):
        policy, raw = self.project_policy()
        task = self.e1_task(scope=["tests/**"])
        del task["integrity_mode"]
        with self.assertRaisesRegex(ValueError, "immutable"):
            verify_task_against_base_policy(
                task,
                policy,
                raw,
                task["starting_state"]["base_sha"],
                ["tests/fixture.txt"],
                "projects/policies/project-leader.json",
                actual_task_path=canonical_task_path(task),
            )

    def test_task_alias_path_is_rejected(self):
        policy, raw = self.project_policy()
        task = self.e1_task(scope=["tests/**"])
        with self.assertRaisesRegex(ValueError, "canonical"):
            verify_task_against_base_policy(
                task,
                policy,
                raw,
                task["starting_state"]["base_sha"],
                ["tests/fixture.txt"],
                "projects/policies/project-leader.json",
                actual_task_path=".project-leader/tasks/DIFFERENT-FILENAME.json",
            )

    def test_git_paths_keep_exact_identity(self):
        task = self.e1_task(scope=["tests/fixture.txt"])
        for changed in (
            " tests/fixture.txt",
            "tests/fixture.txt ",
            "tests\\fixture.txt",
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    validate_scope(task, [changed])

    def test_generic_scope_aliases_are_not_bounded(self):
        for pattern in ("*", "**", "***", "?*"):
            with self.subTest(pattern=pattern):
                self.assertFalse(scope_pattern_is_bounded(pattern))
        self.assertTrue(scope_pattern_is_bounded("src/**"))
        self.assertTrue(scope_pattern_is_bounded("src/*.py"))
        self.assertTrue(scope_pattern_is_bounded("README.md"))

    def test_exact_revision_bound_requires_git_revisions(self):
        auth = json.loads(
            (
                ROOT
                / ".project-leader/transitions/PROJECT-LEADER-RECOVERY-COMPACTION-065-MERGE-67.authorization.json"
            ).read_text()
        )
        missing_revision = copy.deepcopy(auth)
        missing_revision["target"]["revision"] = None
        with self.assertRaises(ValueError):
            validate_transition_authorization(missing_revision)

        missing_base = copy.deepcopy(auth)
        missing_base["target"]["base_revision"] = None
        with self.assertRaises(ValueError):
            validate_transition_authorization(missing_base)

    def test_success_transition_requires_persisted_matching_authorization(self):
        result = json.loads(
            (
                ROOT
                / ".project-leader/transitions/PROJECT-LEADER-RECOVERY-COMPACTION-065-MERGE-67.result.json"
            ).read_text()
        )
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "durable authorization"):
                validate_persisted_transition_result(result, repository_root=tmp)

    def test_blocked_result_is_not_promotable(self):
        task = json.loads(
            (
                ROOT
                / ".project-leader/tasks/PROJECT-LEADER-RECOVERY-COMPACTION-065.json"
            ).read_text()
        )
        result = json.loads(
            (
                ROOT
                / ".project-leader/results/PROJECT-LEADER-RECOVERY-COMPACTION-065.json"
            ).read_text()
        )
        result["terminal_status"] = "BLOCKED"
        result["residual_blockers"] = ["not ready for promotion"]
        with self.assertRaisesRegex(ValueError, "TERMINAL_SUCCESS"):
            verify_promotable_result(task, result)

    def test_rename_origin_is_material_after_ci(self):
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [
                {
                    "status": "renamed",
                    "filename": ".project-leader/results/TASK-001.json",
                    "previous_filename": "src/material.py",
                }
            ],
        }
        with self.assertRaisesRegex(ValueError, "material changes"):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

    def test_transition_prefix_does_not_define_task_identity(self):
        path = ".project-leader/transitions/TASK-001-FIX-MERGE.result.json"
        payload = {
            "status": "ahead",
            "base_commit": {"sha": "a" * 40},
            "commits": [{"sha": "b" * 40}],
            "files": [{"filename": path}],
        }
        with self.assertRaises(ValueError):
            verify_compare_payload(payload, "a" * 40, "b" * 40, "TASK-001")

        own = ".project-leader/transitions/TASK-001-MERGE.result.json"
        payload["files"] = [{"filename": own}]
        self.assertTrue(
            verify_compare_payload(
                payload,
                "a" * 40,
                "b" * 40,
                "TASK-001",
                task_local_transition_paths={own},
            )
        )

    def test_repository_hygiene_is_lease_safe_and_serialized(self):
        workflow = (ROOT / ".github/workflows/repository-hygiene.yml").read_text()
        self.assertIn("--force-with-lease=refs/heads/", workflow)
        self.assertIn("concurrency:", workflow)
        self.assertNotIn("git.deleteRef", workflow)
        self.assertIn("grants.has(branch.commit.sha)", workflow)
        self.assertIn("branchHasOpenPull", workflow)

    def test_trusted_gate_never_skips_forks(self):
        workflow = (ROOT / ".github/workflows/trusted-pr-gate.yml").read_text()
        self.assertNotIn(
            "if: github.event.pull_request.head.repo.full_name == github.repository",
            workflow,
        )
        self.assertIn("HEAD_REPO:", workflow)
        self.assertIn("previous_filename", workflow)


if __name__ == "__main__":
    unittest.main()
