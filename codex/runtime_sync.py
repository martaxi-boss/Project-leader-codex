"""Read-only provenance check for Codex Cloud/CLI certification.

A green test is not evidence of the newest coordinator if the checkout
predates main. This checks repository bytes, not the host's loaded model,
effort, installed ChatGPT plugin release or phone delivery.
"""
from __future__ import annotations

import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = (
    "AGENTS.md",
    "CODEX_COORDINATION.md",
    ".codex/config.toml",
    "plugins/project-leader-codex/skills/project-leader-codex/SKILL.md",
)
CANONICAL_ORIGIN = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"martaxi-boss/Project-leader-codex(?:\.git)?/?$",
    re.IGNORECASE,
)
_SHA = re.compile(r"^[0-9a-f]{40}$")


class PreflightError(RuntimeError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def _git(repo: Path, *args: str) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat",
               GIT_ASKPASS="/bin/false")
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args], env=env, text=True,
            capture_output=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError("NOT_VERIFIED", "Git check unavailable") from exc
    if completed.returncode:
        raise PreflightError("NOT_VERIFIED", "Git check failed: " + " ".join(args))
    return completed.stdout.strip()


def check(repo: Path, *, require_origin_identity: bool = True) -> dict:
    """Certify local source against live origin/main or fail without side effects."""
    repo = repo.expanduser().resolve(strict=True)
    if Path(_git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise PreflightError("NOT_VERIFIED", "Expected the project repository root")
    origin = _git(repo, "remote", "get-url", "origin")
    if require_origin_identity and not CANONICAL_ORIGIN.fullmatch(origin):
        raise PreflightError("NOT_VERIFIED", "Origin is not the project-owned repository")
    head = _git(repo, "rev-parse", "HEAD")
    if not _SHA.fullmatch(head):
        raise PreflightError("NOT_VERIFIED", "Cannot establish exact local HEAD")
    fingerprints = {}
    for relative in SOURCE_FILES:
        path = repo / relative
        if path.is_symlink() or not path.is_file():
            raise PreflightError("NOT_VERIFIED", "Required source missing or symlinked: " + relative)
        _git(repo, "ls-files", "--error-unmatch", "--", relative)
        if _git(repo, "status", "--porcelain", "--untracked-files=no", "--", relative):
            raise PreflightError("NOT_VERIFIED", "Uncommitted runtime instructions: " + relative)
        fingerprints[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    config = configparser.ConfigParser(interpolation=None)
    config.read_string((repo / ".codex/config.toml").read_text(encoding="utf-8"))
    if (not config.getboolean("agents", "enabled", fallback=False)
            or config.getint("agents", "max_concurrent_threads_per_session", fallback=0) != 2):
        raise PreflightError("NOT_VERIFIED", "Unexpected Codex agent configuration")
    remote = _git(repo, "ls-remote", "--refs", "origin", "refs/heads/main").split()
    if len(remote) != 2 or not _SHA.fullmatch(remote[0]) or remote[1] != "refs/heads/main":
        raise PreflightError("NOT_VERIFIED", "Cannot verify current origin/main")
    main_sha = remote[0]
    # Never fetch or modify the checkout during a certification preflight.
    # If the current main commit is absent, this checkout is stale for testing.
    try:
        _git(repo, "cat-file", "-e", main_sha + "^{commit}")
    except PreflightError as exc:
        raise PreflightError("STALE", "Current origin/main commit is absent from this checkout") from exc
    ancestry = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", main_sha, head],
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_PAGER="cat"),
        capture_output=True, text=True, check=False, timeout=20,
    )
    if ancestry.returncode == 1:
        raise PreflightError("STALE", "Current origin/main is not an ancestor of the tested HEAD")
    if ancestry.returncode != 0:
        raise PreflightError("NOT_VERIFIED", "Cannot prove relation to current origin/main")
    return {
        "status": "PASS",
        "head_sha": head,
        "origin_main_sha": main_sha,
        "source_sha256": fingerprints,
        "host_loaded_skill_release": "NOT_VERIFIED",
        "host_model_effort": "NOT_VERIFIED",
        "note": "Only repository source was proven; host-loaded Skill/model and real worker still require independent evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Read-only exact-revision preflight before Codex certification")
    p.add_argument("--repo", type=Path, default=ROOT)
    args = p.parse_args(argv)
    try:
        result = check(args.repo)
    except (PreflightError, OSError, ValueError, configparser.Error) as exc:
        state = exc.status if isinstance(exc, PreflightError) else "NOT_VERIFIED"
        print(json.dumps({"status": state, "reason": str(exc)}, sort_keys=True))
        return 3 if state == "STALE" else 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
