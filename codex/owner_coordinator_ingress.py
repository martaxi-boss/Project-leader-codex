"""Codex Cloud direct-chat Owner order relay to the independent VPS Coordinator.

This is an ingress transport, not a planning agent or a worker. It must never
run a local substitute for the independent Coordinator, access VPS secrets or
retry an uncertain GitHub Issue write. The Owner session must already be
authenticated via GitHub CLI as the repository Owner.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from typing import Callable

OWNER = "martaxi-boss"
CONTROL = OWNER + "/VPS"
TARGET = re.compile(r"martaxi-boss/[A-Za-z0-9][A-Za-z0-9._-]{0,99}\Z", re.ASCII)
SENSITIVE = re.compile(
    r"(?i)(?:gh[pousr]_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{12,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY|"
    r"(?:password|senha|access[_-]?token|api[_-]?key|secret)"
    r"\s*[:=]\s*\S{8,})"
)
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class IngressBlocked(ValueError):
    """Safe, non-secret reason for not dispatching a paid remote Coordinator."""


def validate_order(target: object, task: object) -> str:
    if type(target) is not str or TARGET.fullmatch(target) is None:
        raise IngressBlocked("TARGET_OWNER_OR_NAME_UNVERIFIED")
    name = target.split("/", 1)[1]
    if name.startswith("-") or ".." in name or name.endswith((".git", ".")):
        raise IngressBlocked("TARGET_OWNER_OR_NAME_UNVERIFIED")
    if type(task) is not str or not 12 <= len(task) <= 3700:
        raise IngressBlocked("ORDER_TEXT_UNVERIFIED")
    if CONTROL_CHARS.search(task) or SENSITIVE.search(task):
        raise IngressBlocked("PRIVATE_OR_INVALID_ORDER_REFUSED")
    order = "TARGET_REPOSITORY=" + target + "\n\n" + task.strip()
    if not 50 <= len(order.encode("utf-8")) <= 8000:
        raise IngressBlocked("ORDER_ENVELOPE_UNVERIFIED")
    return order


def _gh(method: str, path: str, *, body: dict | None = None,
        runner: Callable = subprocess.run) -> object:
    argv = ["gh", "api", "--method", method, path]
    payload = None
    if body is not None:
        argv += ["--input", "-"]
        payload = json.dumps(body, ensure_ascii=True, separators=(",", ":"))
    try:
        done = runner(argv, input=payload, text=True, capture_output=True,
                      timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise IngressBlocked("GITHUB_CLI_UNAVAILABLE_OR_TIMEOUT") from None
    if (done.returncode != 0 or not isinstance(done.stdout, str)
            or len(done.stdout) > 500_000):
        raise IngressBlocked("GITHUB_AUTH_OR_WRITE_NOT_VERIFIED")
    try:
        return json.loads(done.stdout)
    except (ValueError, UnicodeError):
        raise IngressBlocked("GITHUB_RESPONSE_UNVERIFIED") from None


def submit_owner_order(target: str, task: str, *,
                       runner: Callable = subprocess.run,
                       unique_id: str | None = None) -> int:
    """Return verified Owner Issue number; no retry on ambiguous writes."""
    body = validate_order(target, task)
    principal = _gh("GET", "user", runner=runner)
    if type(principal) is not dict or principal.get("login") != OWNER:
        raise IngressBlocked("CODEX_CLOUD_IS_NOT_AUTHENTICATED_AS_OWNER")
    repo = _gh("GET", "repos/" + target, runner=runner)
    if (type(repo) is not dict or repo.get("full_name") != target or
            repo.get("owner", {}).get("login") != OWNER or
            repo.get("private") is not False or
            repo.get("archived") is not False or
            repo.get("default_branch") != "main"):
        raise IngressBlocked("TARGET_PUBLIC_MAIN_NOT_VERIFIED")
    nonce = unique_id if unique_id is not None else uuid.uuid4().hex[:16]
    if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{16}", nonce) is None:
        raise IngressBlocked("INVALID_IDEMPOTENCY_REFERENCE")
    title = "[coordinator run] Codex Cloud " + nonce
    # One Owner-created Issue is the *only* trigger into the independent VPS
    # Coordinator. If the write is ambiguous, do not replay it blindly.
    created = _gh("POST", "repos/" + CONTROL + "/issues",
                  body={"title": title, "body": body}, runner=runner)
    if (type(created) is not dict or type(created.get("number")) is not int or
            created["number"] <= 0 or created.get("title") != title or
            created.get("body") != body or
            created.get("user", {}).get("login") != OWNER):
        raise IngressBlocked("OWNER_ISSUE_CREATION_UNVERIFIED")
    return created["number"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Relay one authenticated Owner instruction to the independent Coordinator")
    parser.add_argument("--target", required=True, help="Owner/project repository")
    parser.add_argument("--task", required=True, help="Natural-language Owner instruction")
    args = parser.parse_args(argv)
    try:
        issue = submit_owner_order(args.target, args.task)
    except IngressBlocked as exc:
        print("CODEX_CLOUD_COORDINATOR_NOT_STARTED=" + str(exc), file=sys.stderr)
        return 2
    print("CODEX_CLOUD_COORDINATOR_SUBMITTED_PENDING_WORKFLOW=" +
          "https://github.com/" + CONTROL + "/issues/" + str(issue))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
