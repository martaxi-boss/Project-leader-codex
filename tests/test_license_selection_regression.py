import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProprietaryLicenseSelectionTests(unittest.TestCase):
    def test_license_is_proprietary_and_reserves_rights(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("PROPRIETARY LICENSE", text)
        self.assertIn("ALL RIGHTS RESERVED", text)
        self.assertIn("No General License Grant", text)
        self.assertIn("No open-source or other general license is granted", text)
        self.assertIn("Third-Party Materials", text)
        self.assertIn("All rights not expressly granted in writing are reserved", text)

    def test_docs_consistently_identify_proprietary_status(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        setup = (ROOT / "PLUGIN_SETUP.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("Project Leader is proprietary software", readme)
        self.assertIn("proprietary / All Rights Reserved", setup)
        self.assertIn("proprietary / All Rights Reserved", changelog)
        self.assertNotIn(
            "repository Owner has not chosen a project license",
            changelog,
        )

    def test_license_does_not_relicense_third_party_materials(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(
            "remain subject to their own licenses, terms, and rights",
            normalized,
        )
        self.assertIn(
            "Nothing in this license attempts to relicense or override third-party rights",
            normalized,
        )


if __name__ == "__main__":
    unittest.main()
