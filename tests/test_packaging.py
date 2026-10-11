import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.package_plugins import build, sha256_file

ROOT = Path(__file__).resolve().parents[1]


class ReproduciblePackagingTests(unittest.TestCase):
    def test_packaging_is_byte_reproducible_and_manifest_matches(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            build(ROOT, first)
            build(ROOT, second)

            for name in ("project-leader.zip", "recovery-guardian.zip", "plugin-manifest.json", "SHA256SUMS"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)

            manifest = json.loads((first / "plugin-manifest.json").read_text())
            self.assertEqual(manifest["schema_version"], "2.0")
            self.assertEqual(manifest["provenance"]["repository"], "martaxi-boss/Project-leader")
            self.assertEqual(manifest["provenance"]["source_revision"], "UNBOUND_LOCAL_BUILD")
            self.assertEqual(manifest["provenance"]["build_revision"], "UNBOUND_LOCAL_BUILD")
            self.assertEqual(manifest["provenance"]["build_run_id"], "LOCAL")
            self.assertEqual({item["name"] for item in manifest["plugins"]}, {"project-leader", "recovery-guardian"})
            for item in manifest["plugins"]:
                self.assertEqual(item["sha256"], sha256_file(first / item["file"]))
                self.assertEqual(item["size"], (first / item["file"]).stat().st_size)

    def test_archives_contain_required_plugin_metadata(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            build(ROOT, output)
            for name in ("project-leader", "recovery-guardian"):
                with zipfile.ZipFile(output / f"{name}.zip") as archive:
                    names = set(archive.namelist())
                    self.assertIn("plugin.json", names)
                    self.assertIn(".app.json", names)
                    self.assertTrue(any(path.endswith("/SKILL.md") for path in names))


if __name__ == "__main__":
    unittest.main()
