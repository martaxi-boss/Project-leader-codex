import hashlib
import json
import unittest
from pathlib import Path

from control.managed_project_contract import (
    GENERIC_POLICY_PATH,
    resolve_project_policy_path,
    verify_managed_task_against_control_policy,
)

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "owner/new-project"
CONTROL_REPOSITORY = "owner/control"


def task(policy_raw):
    return {
        "schema_version": "2.0",
        "task_id": "TASK-001",
        "project": "NEW PROJECT",
        "repository": REPOSITORY,
        "created_at": "2026-10-03T01:00:00Z",
        "integrity_mode": "IMMUTABLE_AUTHORIZATION_V1",
        "authority": {
            "kind": "STANDING_DELEGATION",
            "summary": "bounded generic-project task",
            "source": "STANDING_OWNER_GRANT",
            "binding_mode": "OBJECTIVE_SCOPE_BOUND",
        },
        "starting_state": {
            "default_branch": "main",
            "base_sha": "a" * 40,
            "task_branch": "builder/task-001",
            "pr_number": None,
        },
        "effect_class": "E1_RECOVERABLE_PROJECT_LOCAL",
        "mutation_scope": [
            "src/**",
            ".project-leader/tasks/**",
            ".project-leader/results/**",
        ],
        "allowed_actions": [
            "create_branch",
            "edit_project_files",
            "create_commits",
            "run_ci",
            "open_or_update_pull_request",
        ],
        "prohibited_actions": [
            "merge_to_main",
            "branch_protection_or_ruleset_change",
            "release_or_publish",
            "production_deploy",
            "destructive_data_change",
            "repository_or_history_deletion",
            "production_secret_change",
            "irreversible_infrastructure_change",
            "paid_service_activation",
        ],
        "transition_controls": [
            {"action": name, "requires_authority_resolution": True}
            for name in (
                "merge_to_main",
                "branch_protection_or_ruleset_change",
                "release_or_publish",
                "production_deploy",
                "destructive_data_change",
                "repository_or_history_deletion",
                "production_secret_change",
                "irreversible_infrastructure_change",
                "paid_service_activation",
            )
        ],
        "required_validation": [
            "Project architecture scope audit",
            "Mutation scope audit",
            "GitHub evidence verification",
        ],
        "required_ci": [],
        "policy": {
            "binding_mode": "CENTRAL_CONTROL_V1",
            "profile": "generic-project-v1",
            "path": GENERIC_POLICY_PATH,
            "repository": CONTROL_REPOSITORY,
            "revision": "c" * 40,
            "sha256": hashlib.sha256(policy_raw).hexdigest(),
        },
        "recovery": {"mode": "APPEND_ONLY_V1"},
        "terminal_condition": "validated bounded task; no unverified transition",
        "privacy": {
            "contains_secrets": False,
            "contains_private_conversation_text": False,
        },
    }


class GenericManagedProjectTests(unittest.TestCase):
    def setUp(self):
        self.policy_path = ROOT / GENERIC_POLICY_PATH
        self.raw = self.policy_path.read_bytes()
        self.policy = json.loads(self.raw)
        self.task = task(self.raw)
        self.changed = [
            "src/app.py",
            ".project-leader/tasks/TASK-001.json",
        ]

    def verify(self, task_record=None, policy=None, raw=None, changed=None, path=None):
        return verify_managed_task_against_control_policy(
            task_record or self.task,
            policy or self.policy,
            raw or self.raw,
            "a" * 40,
            changed or self.changed,
            CONTROL_REPOSITORY,
            "c" * 40,
            path if path is not None else GENERIC_POLICY_PATH,
        )

    def test_generic_policy_is_default_without_registry(self):
        self.assertEqual(resolve_project_policy_path(None), GENERIC_POLICY_PATH)
        self.assertEqual(
            resolve_project_policy_path("projects/policies/custom.json"),
            "projects/policies/custom.json",
        )

    def test_generic_policy_accepts_unregistered_active_repository(self):
        self.assertEqual(self.policy["repository_mode"], "ACTIVE_TARGET")
        self.assertTrue(self.verify())

    def test_generic_policy_binds_exact_control_revision_and_bytes(self):
        task_record = json.loads(json.dumps(self.task))
        task_record["policy"]["revision"] = "9" * 40
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

        task_record = json.loads(json.dumps(self.task))
        task_record["policy"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

    def test_generic_task_cannot_claim_whole_repository_scope(self):
        task_record = json.loads(json.dumps(self.task))
        task_record["mutation_scope"] = ["**"]
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

    def test_task_scope_must_narrow_generic_ceiling_without_path_escape(self):
        task_record = json.loads(json.dumps(self.task))
        task_record["mutation_scope"] = ["src/../secrets/**", ".project-leader/tasks/**"]
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

    def test_consequential_action_stays_outside_builder_actions(self):
        task_record = json.loads(json.dumps(self.task))
        task_record["allowed_actions"].append("merge_to_main")
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

        transition_actions = {
            item["action"] for item in self.task["transition_controls"]
        }
        self.assertIn("merge_to_main", transition_actions)

    def test_generic_policy_requires_architecture_scope_audit(self):
        self.assertIn(
            "Project architecture scope audit",
            self.policy["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]["required_validation"],
        )
        task_record = json.loads(json.dumps(self.task))
        task_record["required_validation"].remove("Project architecture scope audit")
        with self.assertRaises(ValueError):
            self.verify(task_record=task_record)

    def test_target_specific_policy_can_override_generic_default_when_explicit(self):
        fixed = json.loads(json.dumps(self.policy))
        fixed.pop("repository_mode")
        fixed.pop("default_branch_mode")
        fixed["repository"] = REPOSITORY
        fixed["default_branch"] = "main"
        fixed["policy_id"] = "specific-v1"
        raw = (json.dumps(fixed, indent=2) + "\n").encode("utf-8")
        task_record = json.loads(json.dumps(self.task))
        task_record["policy"]["profile"] = "specific-v1"
        task_record["policy"]["path"] = "projects/policies/custom.json"
        task_record["policy"]["sha256"] = hashlib.sha256(raw).hexdigest()
        self.assertTrue(
            self.verify(
                task_record=task_record,
                policy=fixed,
                raw=raw,
                path="projects/policies/custom.json",
            )
        )


if __name__ == "__main__":
    unittest.main()
