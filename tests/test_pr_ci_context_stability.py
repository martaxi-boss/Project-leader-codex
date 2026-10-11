import unittest

from control.verify_github_evidence import (
    PROJECT_LEADER_TRUSTED_WORKFLOWS,
    verify_live_pr_context,
    verify_run_payload,
)


class StablePrCiContextTests(unittest.TestCase):
    def setUp(self):
        self.repository = "martaxi-boss/Project-leader"
        self.implementation = "a" * 40
        self.current_head = "b" * 40
        self.base = "c" * 40
        self.task = {
            "starting_state": {
                "base_sha": self.base,
                "default_branch": "main",
            }
        }
        self.result = {
            "implementation_head_sha": self.implementation,
            "pr_number": 78,
        }
        self.ci = {
            "name": "Control contract tests",
            "status": "SUCCESS",
            "run_id": 123,
        }
        self.run = {
            "id": 123,
            "name": "Control contract tests",
            "workflow_id": PROJECT_LEADER_TRUSTED_WORKFLOWS[
                "Control contract tests"
            ]["workflow_id"],
            "path": PROJECT_LEADER_TRUSTED_WORKFLOWS[
                "Control contract tests"
            ]["path"],
            "event": "pull_request",
            "head_sha": self.implementation,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": self.repository},
            "pull_requests": [
                {
                    "number": 78,
                    # GitHub rewrites this projection to the current PR head.
                    "head": {"sha": self.current_head},
                    "base": {"sha": self.base},
                }
            ],
        }
        self.live_pr = {
            "number": 78,
            "state": "open",
            "head": {
                "sha": self.current_head,
                "ref": "builder/task",
                "repo": {"full_name": self.repository},
            },
            "base": {
                "sha": self.base,
                "ref": "main",
                "repo": {"full_name": self.repository},
            },
        }

    def test_evidence_descendant_does_not_rewrite_immutable_run_head(self):
        self.assertTrue(
            verify_run_payload(
                self.ci,
                self.result,
                self.run,
                self.repository,
                PROJECT_LEADER_TRUSTED_WORKFLOWS["Control contract tests"],
                self.task,
            )
        )
        self.assertTrue(
            verify_live_pr_context(
                self.result,
                self.task,
                self.live_pr,
                self.repository,
                self.current_head,
            )
        )

    def test_wrong_immutable_run_head_still_fails(self):
        self.run["head_sha"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "workflow SHA mismatch"):
            verify_run_payload(
                self.ci,
                self.result,
                self.run,
                self.repository,
                PROJECT_LEADER_TRUSTED_WORKFLOWS["Control contract tests"],
                self.task,
            )

    def test_wrong_pr_association_still_fails(self):
        self.run["pull_requests"][0]["number"] = 79
        with self.assertRaisesRegex(ValueError, "expected PR"):
            verify_run_payload(
                self.ci,
                self.result,
                self.run,
                self.repository,
                PROJECT_LEADER_TRUSTED_WORKFLOWS["Control contract tests"],
                self.task,
            )

    def test_wrong_live_base_fails(self):
        self.live_pr["base"]["sha"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "base SHA"):
            verify_live_pr_context(
                self.result,
                self.task,
                self.live_pr,
                self.repository,
                self.current_head,
            )

    def test_wrong_live_current_head_fails(self):
        self.live_pr["head"]["sha"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "current trusted-gate head"):
            verify_live_pr_context(
                self.result,
                self.task,
                self.live_pr,
                self.repository,
                self.current_head,
            )

    def test_cross_repository_pr_context_fails(self):
        self.live_pr["head"]["repo"]["full_name"] = "fork/repo"
        with self.assertRaisesRegex(ValueError, "same-repository"):
            verify_live_pr_context(
                self.result,
                self.task,
                self.live_pr,
                self.repository,
                self.current_head,
            )

    def test_closed_pr_context_fails(self):
        self.live_pr["state"] = "closed"
        with self.assertRaisesRegex(ValueError, "open"):
            verify_live_pr_context(
                self.result,
                self.task,
                self.live_pr,
                self.repository,
                self.current_head,
            )


if __name__ == "__main__":
    unittest.main()
