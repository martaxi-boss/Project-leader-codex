#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
PLUGINS = ("project-leader", "recovery-guardian")
SOURCE_REPOSITORY = "martaxi-boss/Project-leader"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PACKAGE_WORKFLOW_PATH = ".github/workflows/package-plugins.yml"


def sha256_bytes(payload):
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_plugin_files(name):
    skill = name
    return {
        ".app.json",
        "plugin.json",
        f"skills/{skill}/SKILL.md",
        f"skills/{skill}/agents/openai.yaml",
        f"skills/{skill}/references/recovery-protocol.md",
    }


def validate_plugin_tree(plugin_dir, expected_name):
    plugin_dir = Path(plugin_dir)
    if plugin_dir.is_symlink():
        raise ValueError(f"plugin root must not be a symlink: {plugin_dir}")

    observed = set()
    for path in plugin_dir.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"plugin package contains a symlink: {path}")
        if path.is_file():
            observed.add(path.relative_to(plugin_dir).as_posix())

    expected = expected_plugin_files(expected_name)
    unexpected = sorted(observed - expected)
    missing = sorted(expected - observed)
    if unexpected:
        raise ValueError(
            f"{expected_name}: unexpected package files: {', '.join(unexpected)}"
        )
    if missing:
        raise ValueError(
            f"{expected_name}: required package files missing: {', '.join(missing)}"
        )

    metadata = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    app = json.loads((plugin_dir / ".app.json").read_text(encoding="utf-8"))

    if metadata.get("name") != expected_name:
        raise ValueError(
            f"{expected_name}: plugin.json name does not match package directory"
        )
    version = metadata.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        raise ValueError(
            f"{expected_name}: plugin.json version must be valid SemVer"
        )
    if metadata.get("skills") != "./skills/":
        raise ValueError(f"{expected_name}: plugin.json skills path must be ./skills/")
    openai = ((metadata.get("extensions") or {}).get("com.openai") or {})
    if openai.get("apps") != "./.app.json":
        raise ValueError(f"{expected_name}: plugin.json apps path must be ./.app.json")

    github = ((app.get("apps") or {}).get("github") or {})
    connector_id = github.get("id")
    if github.get("required") is not True or not isinstance(connector_id, str) or not connector_id:
        raise ValueError(f"{expected_name}: required GitHub connector metadata is invalid")

    contents = []
    for relative in sorted(observed):
        payload = (plugin_dir / relative).read_bytes()
        contents.append(
            {
                "path": relative,
                "sha256": sha256_bytes(payload),
                "size": len(payload),
            }
        )
    return metadata, connector_id, contents


def package_plugin(plugin_dir, output_zip, expected_name):
    plugin_dir = Path(plugin_dir)
    output_zip = Path(output_zip)
    metadata, connector_id, contents = validate_plugin_tree(
        plugin_dir, expected_name
    )
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        output_zip,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for item in contents:
            relative = item["path"]
            payload = (plugin_dir / relative).read_bytes()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(
                info,
                payload,
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return output_zip, metadata, connector_id, contents


def build(
    root,
    output_dir,
    source_revision=None,
    build_revision=None,
    build_run_id=None,
):
    root = Path(root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if source_revision is not None and SHA_RE.fullmatch(source_revision) is None:
        raise ValueError("source_revision must be an exact 40-hex Git commit SHA")
    if build_revision is not None and SHA_RE.fullmatch(build_revision) is None:
        raise ValueError("build_revision must be an exact 40-hex Git commit SHA")
    if build_run_id is not None and not str(build_run_id).strip():
        raise ValueError("build_run_id must be non-empty when supplied")

    entries = []
    connector_ids = set()

    for name in PLUGINS:
        plugin_dir = root / "plugins" / name
        archive, metadata, connector_id, contents = package_plugin(
            plugin_dir,
            output_dir / f"{name}.zip",
            name,
        )
        connector_ids.add(connector_id)
        entries.append(
            {
                "name": name,
                "version": metadata["version"],
                "file": archive.name,
                "sha256": sha256_file(archive),
                "size": archive.stat().st_size,
                "github_connector_id": connector_id,
                "contents": contents,
            }
        )

    if len(connector_ids) != 1:
        raise ValueError("Project Leader and Recovery Guardian must use one GitHub connector")

    manifest = {
        "schema_version": "2.0",
        "provenance": {
            "repository": SOURCE_REPOSITORY,
            "source_revision": source_revision or "UNBOUND_LOCAL_BUILD",
            "build_revision": build_revision or source_revision or "UNBOUND_LOCAL_BUILD",
            "workflow_path": PACKAGE_WORKFLOW_PATH,
            "build_run_id": str(build_run_id) if build_run_id is not None else "LOCAL",
        },
        "plugins": entries,
    }
    (output_dir / "plugin-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "SHA256SUMS").write_text(
        "".join(f"{entry['sha256']}  {entry['file']}\n" for entry in entries),
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-revision", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--build-revision", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--build-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    args = parser.parse_args()
    build(
        args.root,
        args.output_dir,
        source_revision=args.source_revision,
        build_revision=args.build_revision,
        build_run_id=args.build_run_id,
    )


if __name__ == "__main__":
    main()
