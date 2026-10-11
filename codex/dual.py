"""Two Codex CLI jobs, independent worktrees, explicit serial/parallel modes.

No agent is started by plan. Run requires --execute and a local
signed-in Codex CLI; no credentials, merges or pushes are managed here.
"""
from __future__ import annotations

import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from uuid import uuid4

REPO_NAME = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
JOB_NAME = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")
LEVELS = {"auto", "low", "medium", "high"}
HARD = ("race condition", "deadlock", "security", "seguranca", "seguranca critica",
        "migration", "migracao", "regression", "regressao", "root cause", "causa raiz",
        "complex", "complexo", "concurrency", "concorrencia", "credential")
EASY = ("typo", "ortografia", "readme", "formatting", "formatar", "renomear")
ROOT = Path(__file__).resolve().parents[1]


class PlanError(ValueError):
    pass


def _is_safe_path(value: object) -> bool:
    if type(value) is not str or not value or len(value) > 160 or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(
        part not in {"", ".", "..", ".git"} and not part.startswith(".")
        for part in value.split("/")
    ) and not any(c in value for c in "*?[]\n\r\x00")


def effort(task: dict) -> str:
    requested = task.get("reasoning_effort", "auto")
    if requested not in LEVELS:
        raise PlanError("reasoning_effort must be auto, low, medium or high")
    if requested != "auto":
        return requested
    if task.get("verified_hard_failure") is True:
        return "high"
    prompt = task["task"].casefold()
    if any(s in prompt for s in HARD):
        return "high"
    if len(prompt) < 240 and any(s in prompt for s in EASY):
        return "low"
    return "medium"


def parse_order(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != {"target_repository", "mode", "tasks"}:
        raise PlanError("Required fields: target_repository, mode, tasks")
    repo = data["target_repository"]
    if type(repo) is not str or not REPO_NAME.fullmatch(repo):
        raise PlanError("Invalid GitHub target repository")
    if repo.casefold() == "martaxi-boss/project-leader":
        raise PlanError("The universal Project Leader upstream is read-only for this executor")
    mode = data["mode"]
    if mode not in {"serial", "parallel"}:
        raise PlanError("mode must be serial or parallel")
    raw = data["tasks"]
    if not isinstance(raw, list) or len(raw) != 2:
        raise PlanError("Exactly two Codex tasks are required")
    tasks = []
    for task in raw:
        if not isinstance(task, dict) or not {"id", "task", "paths"} <= set(task) or set(task) - {"id", "task", "paths", "reasoning_effort", "verified_hard_failure"}:
            raise PlanError("Invalid task fields")
        job_id = task["id"]
        if type(job_id) is not str or not JOB_NAME.fullmatch(job_id) or any(t["id"] == job_id for t in tasks):
            raise PlanError("Duplicate or invalid task id")
        prompt = task["task"]
        if type(prompt) is not str or not 12 <= len(prompt) <= 3000 or any(c in prompt for c in "\x00\x1b"):
            raise PlanError("Invalid task text")
        paths = task["paths"]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 20 or len(set(map(str, paths))) != len(paths) or not all(_is_safe_path(p) for p in paths):
            raise PlanError("Each task needs unique, safe, bounded paths")
        hard = task.get("verified_hard_failure", False)
        if type(hard) is not bool:
            raise PlanError("verified_hard_failure must be a boolean")
        t = dict(task)
        t["selected_effort"] = effort(t)
        tasks.append(t)
    if mode == "parallel":
        for a in tasks[0]["paths"]:
            for b in tasks[1]["paths"]:
                if a == b or a.startswith(b + "/") or b.startswith(a + "/"):
                    raise PlanError("Parallel workers have overlapping owned paths")
    return {"target_repository": repo, "mode": mode, "tasks": tasks,
            "execution": "two isolated worktrees" if mode == "parallel" else "one ordered worktree",
            "integration": "manual review + tested PR; no automatic merge"}


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise PlanError("Git preflight failed: " + " ".join(args))
    return result.stdout.strip()


def _remote_repo(origin: str) -> str:
    candidates = (
        re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?/?", origin),
        re.fullmatch(r"git@github\.com:([\w.-]+/[\w.-]+?)(?:\.git)?", origin),
        re.fullmatch(r"ssh://git@github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?", origin),
    )
    return next((m.group(1) for m in candidates if m), "")


def _preflight(repo: Path, expected: str) -> str:
    repo = repo.resolve(strict=True)
    if Path(_git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise PlanError("Use the top-level checkout of the selected target repository")
    if _remote_repo(_git(repo, "remote", "get-url", "origin")).casefold() != expected.casefold():
        raise PlanError("Git origin does not match target_repository")
    if _git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise PlanError("Source checkout is dirty; preserve changes before starting worktrees")
    return _git(repo, "rev-parse", "HEAD")


def _changes(workspace: Path) -> set[str]:
    result = subprocess.run(["git", "-C", str(workspace), "status", "--porcelain=1", "--untracked-files=all", "-z"], capture_output=True, check=False)
    if result.returncode:
        raise PlanError("Cannot read worker Git status")
    pieces = result.stdout.decode("utf-8", errors="replace").split("\x00")
    paths = set()
    idx = 0
    while idx < len(pieces) and pieces[idx]:
        entry = pieces[idx]
        status = entry[:2]
        paths.add(entry[3:])
        idx += 1
        if "R" in status or "C" in status:
            if idx < len(pieces) and pieces[idx]:
                paths.add(pieces[idx])
                idx += 1
    return paths


def _fingerprint(workspace: Path) -> str:
    """Fingerprint both changed path names and working-tree content."""
    digest = hashlib.sha256()
    for name in sorted(_changes(workspace)):
        path = workspace / name
        digest.update(name.encode("utf-8", errors="replace") + b"\0")
        if path.is_symlink():
            digest.update(b"link:" + os.readlink(path).encode("utf-8", errors="replace"))
        elif path.is_file():
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(65536), b""):
                    digest.update(block)
        else:
            digest.update(b"absent-or-directory")
    return digest.hexdigest()


def _scope(path: str, owned: list[str]) -> bool:
    return any(path == item or path.startswith(item + "/") for item in owned)


def _private_file(path: Path, content: str) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(content)


def _prompt(task: dict) -> str:
    skill = (ROOT / "plugins/project-leader/skills/project-leader/SKILL.md").read_text(encoding="utf-8")
    rules = (ROOT / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
    return (
        "Apply the following Project Leader rules and this repository's Codex specialization. "
        "Only change the explicitly owned paths. Never push, merge, deploy, or reveal credentials. "
        "Do not claim validation without running it.\n\n"
        "=== PROJECT LEADER RULES ===\n" + skill + "\n=== CODEX SPECIALIZATION ===\n" + rules +
        "\n=== THIS WORKER ===\nOwned paths: " + ", ".join(task["paths"]) +
        "\nRequested task:\n" + task["task"]
    )


def _completed_event(line: str) -> bool:
    try:
        return json.loads(line).get("type") == "turn.completed"
    except (ValueError, AttributeError):
        return False


def _worker(task: dict, workspace: Path, logdir: Path, timeout: int, previous: set[str]) -> dict:
    cmd = [shutil.which("codex") or "codex", "exec", "--sandbox", "workspace-write",
           "--ask-for-approval", "never", "-c", "model_reasoning_effort=" + task["selected_effort"],
           "-C", str(workspace), "--json", "-"]
    started = time.monotonic()
    previous_state = _fingerprint(workspace)
    try:
        result = subprocess.run(cmd, input=_prompt(task), text=True, capture_output=True, timeout=timeout, check=False)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        code = 124
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        timed_out = True
    _private_file(logdir / (task["id"] + ".jsonl"), stdout)
    _private_file(logdir / (task["id"] + ".stderr"), stderr)
    changed = sorted(_changes(workspace))
    newly_changed = sorted(set(changed) - previous)
    mutated = _fingerprint(workspace) != previous_state
    out_of_scope = [p for p in changed if not _scope(p, task["paths"])]
    completed_event = any(
        line.strip().startswith("{") and _completed_event(line)
        for line in stdout.splitlines()
    )
    status = ("scope_violation" if out_of_scope else "timeout" if timed_out else
              "failed" if code else "unverified_result" if not completed_event else
              "no_change" if not mutated else "completed")
    return {"id": task["id"], "status": status, "exit_code": code,
            "reasoning_effort": task["selected_effort"], "workspace": str(workspace),
            "changed_paths": changed, "new_paths": newly_changed,
            "out_of_scope": out_of_scope, "duration_seconds": round(time.monotonic() - started, 2)}


def run(order: dict, repo: Path, runs_dir: Path | None = None, timeout: int = 1200) -> dict:
    if shutil.which("codex") is None:
        raise PlanError("Codex CLI is not installed or accessible; no model started")
    if not 30 <= timeout <= 7200:
        raise PlanError("timeout must be between 30 and 7200 seconds")
    repo = repo.resolve(strict=True)
    head = _preflight(repo, order["target_repository"])
    root = (runs_dir or Path.home() / ".local/share/project-leader-codex/runs").expanduser().resolve()
    if root == repo or root.is_relative_to(repo):
        raise PlanError("Runs directory must be outside target repository")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_mode & 0o077:
        raise PlanError("Runs directory permissions must be private (0700)")
    work_root = root / ("run-" + uuid4().hex)
    work_root.mkdir(mode=0o700)
    workspaces = []
    try:
        for idx in range(2 if order["mode"] == "parallel" else 1):
            workspace = work_root / ("worker-" + str(idx + 1))
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(workspace), head],
                           capture_output=True, check=True)
            workspaces.append(workspace)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PlanError("Could not create isolated Git worktree; inspect " + str(work_root)) from exc
    tasks = order["tasks"]
    try:
        if order["mode"] == "parallel":
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(_worker, t, workspaces[i], work_root, timeout, set())
                           for i, t in enumerate(tasks)]
                results = [f.result() for f in futures]
        else:
            first = _worker(tasks[0], workspaces[0], work_root, timeout, set())
            results = [first]
            if first["status"] == "completed":
                # The second agent sees the first agent's changes, in the same worktree.
                second = _worker(tasks[1], workspaces[0], work_root, timeout,
                                 set(first["changed_paths"]))
                # Serial workers may legitimately inherit the first agent's changed paths.
                second["out_of_scope"] = [p for p in second["new_paths"] if not _scope(p, tasks[1]["paths"])]
                if second["status"] == "scope_violation" and not second["out_of_scope"]:
                    second["status"] = "completed"
                results.append(second)
            else:
                results.append({"id": tasks[1]["id"], "status": "not_started", "reason": "First task did not complete"})
    except (OSError, PlanError) as exc:
        raise PlanError("Worker error; preserved workspaces in " + str(work_root)) from exc
    result = {"target_repository": order["target_repository"], "mode": order["mode"],
              "base_head": head, "run_directory": str(work_root), "workers": results,
              "integration": "NOT_AUTOMATED: inspect changes, validate, open and review PR"}
    _private_file(work_root / "result.json", json.dumps(result, indent=2) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Codex dual-agent executor")
    parser.add_argument("action", choices=("plan", "run"))
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.manifest.stat().st_size > 16000:
            raise PlanError("Manifest exceeds 16 KB")
        order = parse_order(json.loads(args.manifest.read_text(encoding="utf-8")))
        if args.action == "plan":
            print(json.dumps(order, indent=2))
            return 0
        if not args.execute or args.repo_dir is None:
            raise PlanError("run requires both --execute and --repo-dir; no model started")
        result = run(order, args.repo_dir, args.runs_dir, args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if all(r["status"] == "completed" for r in result["workers"]) else 2
    except (PlanError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("CODEX_DUAL_BLOCKED: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
