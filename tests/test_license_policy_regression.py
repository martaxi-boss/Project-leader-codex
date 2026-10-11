import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LicensePolicyRegressionTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(
                encoding="utf-8"
            )
        )

    def test_e1_cannot_mutate_or_select_license(self):
        e1 = self.policy["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"]
        self.assertNotIn("LICENSE", e1["allowed_scope_patterns"])
        self.assertNotIn("license_selection", e1["allowed_actions"])
        self.assertIn("license_selection", e1["required_prohibited_actions"])
        self.assertIn("license_selection", e1["required_transition_controls"])

    def test_e3_allows_exact_license_path_under_transition_control(self):
        e3 = self.policy["effect_policies"]["E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED"]
        self.assertIn("LICENSE", e3["allowed_scope_patterns"])
        self.assertNotIn("*.md", e3["allowed_scope_patterns"])
        self.assertNotIn("**/*.md", e3["allowed_scope_patterns"])
        self.assertIn("license_selection", e3["allowed_actions"])
        self.assertNotIn("license_selection", e3["required_prohibited_actions"])
        self.assertIn("license_selection", e3["required_transition_controls"])

    def test_license_is_sensitive_and_protected(self):
        self.assertIn("LICENSE", self.policy["sensitive_paths"])
        self.assertIn("LICENSE", self.policy["protected_paths"])


if __name__ == "__main__":
    unittest.main()
