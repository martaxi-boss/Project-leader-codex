import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PolicyDocumentationScopeRegressionTests(unittest.TestCase):
    def test_documentation_scope_is_exact_and_security_policy_stays_protected(self):
        policy = json.loads(
            (ROOT / "projects/policies/project-leader.json").read_text(encoding="utf-8")
        )
        e1 = policy["effect_policies"]["E1_RECOVERABLE_PROJECT_LOCAL"][
            "allowed_scope_patterns"
        ]
        e3 = policy["effect_policies"]["E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED"][
            "allowed_scope_patterns"
        ]

        self.assertIn("CHANGELOG.md", e1)
        self.assertIn("SOURCES.md", e1)
        self.assertNotIn("SECURITY.md", e1)

        for path in ("CHANGELOG.md", "SECURITY.md", "SOURCES.md"):
            self.assertIn(path, e3)

        self.assertIn("SECURITY.md", policy["sensitive_paths"])
        self.assertIn("SECURITY.md", policy["protected_paths"])

        self.assertNotIn("*.md", e1)
        self.assertNotIn("*.md", e3)
        self.assertNotIn("**/*.md", e1)
        self.assertNotIn("**/*.md", e3)


if __name__ == "__main__":
    unittest.main()
