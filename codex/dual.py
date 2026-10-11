"""Two Codex CLI jobs, independent worktrees, explicit serial/parallel modes.

No agent is started by plan. Run requires --execute and a local
signed-in Codex CLI; no credentials, merges or pushes are managed here.
"""
from __future__ import annotations

import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
import signal
import threading
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from uuid import uuid4

REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
JOB_NAME = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")
LEVELS = {"auto", "low", "medium", "high"}
HARD = ("race condition", "deadlock", "security", "seguranca", "segurança",
        "seguranca critica", "segurança crítica", "migration", "migracao", "migração",
        "regression", "regressao", "regressão", "root cause", "causa raiz",
        "complex", "complexo", "concurrency", "concorrencia", "concorrência", "credential")
EASY = ("typo", "ortografia", "readme", "formatting", "formatar", "renomear")
ROOT = Path(__file__).resolve().parents[1]


class PlanError(ValueError):
    pass


def _is_safe_path(value: object) -> bool:
    if type(value) is not str or not value or len(value) > 160 or "\\" in value:
        return False
    parts = value.split("/")
    # Only the two known repository metadata areas may start with a dot.
    # .git, .env, nested hidden directories and traversal remain forbidden.
    return (not PurePosixPath(value).is_absolute()
            and all(part not in {"", ".", "..", ".git"}
                    and (not part.startswith(".") or (i == 0 and part in {".codex", ".github"}))
                    for i, part in enumerate(parts))
            and not any(c in value for c in "*?[]\n\r\x00")
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))

def effort(task: dict) -> str:
    requested = task.get("reasoning_effort", "auto")
    if type(requested) is not str or requested not in LEVELS:
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
    if type(mode) is not str or mode not in {"serial", "parallel"}:
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


def _snapshot(workspace: Path) -> dict[str, str]:
    """Record each changed path separately, so serial workers cannot alter inherited files."""
    states = {}
    for name in sorted(_changes(workspace)):
        path = workspace / name
        digest = hashlib.sha256()
        if path.is_symlink():
            digest.update(b"symlink:" + os.readlink(path).encode("utf-8", errors="replace"))
        elif path.is_file():
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(65536), b""):
                    digest.update(block)
        else:
            digest.update(b"absent-or-directory")
        states[name] = digest.hexdigest()
    return states


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
         "Only change the explicitly owned paths. Never commit, push, merge, deploy, or reveal credentials. "
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


def _committed_paths(workspace: Path, before: str, after: str) -> set[str]:
    """Audit committed edits as well as working-tree edits (including renames)."""
    if before == after:
        return set()
    result = subprocess.run(
        ["git", "-C", str(workspace), "diff", "--no-renames", "--name-only", "-z", before, after],
        capture_output=True, check=False,
    )
    if result.returncode:
        raise PlanError("Cannot audit Codex worker commits; fail closed")
    return {os.fsdecode(p) for p in result.stdout.split(b"\x00") if p}


def _stop_process_group(process: subprocess.Popen) -> tuple[str, str]:
    """Terminate the entire spawned Codex process group, not only its parent."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.terminate()
    try:
        return process.communicate(timeout=0.6)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            process.kill()
        try:
            return process.communicate(timeout=2)
        except subprocess.TimeoutExpired as exc:
            raise PlanError("Worker process group did not stop; inspect retained workspace") from exc


def _invoke_codex(cmd: list[str], prompt: str, timeout: int,
                  cancel_event: threading.Event | None = None) -> tuple[int, str, str, str]:
    if cancel_event is not None and cancel_event.is_set():
        return 125, "", "Cancelled before model launch", "cancelled"
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=(os.name == "posix"),
    )
    started = time.monotonic()
    first_input = True
    while True:
        if cancel_event is not None and cancel_event.is_set():
            stdout, stderr = _stop_process_group(process)
            return 125, stdout, stderr, "cancelled"
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            stdout, stderr = _stop_process_group(process)
            return 124, stdout, stderr, "timeout"
        try:
            stdout, stderr = process.communicate(
                input=prompt if first_input else None,
                timeout=min(0.2, remaining),
            )
            return process.returncode, stdout, stderr, "finished"
        except subprocess.TimeoutExpired:
            # Python preserves buffered input/output across communicate retries.
            first_input = False


def _worker(task: dict, workspace: Path, logdir: Path, timeout: int,
            cancel_event: threading.Event | None = None) -> dict:
    # --ask-for-approval is a ROOT option on Codex 0.159.x, not an exec option.
    # Retain workspace-write sandbox and explicit never-approval policy.
    cmd = [shutil.which("codex") or "codex", "--ask-for-approval", "never", "exec",
           "--sandbox", "workspace-write",
           "-c", "model_reasoning_effort=" + task["selected_effort"],
           "-C", str(workspace), "--json", "-"]
    started = time.monotonic()
    previous_head = _git(workspace, "rev-parse", "HEAD")
    previous_state = _snapshot(workspace)
    code, stdout, stderr, termination = _invoke_codex(
        cmd, _prompt(task), timeout, cancel_event,
    )
    _private_file(logdir / (task["id"] + ".jsonl"), stdout)
    _private_file(logdir / (task["id"] + ".stderr"), stderr)
    current_head = _git(workspace, "rev-parse", "HEAD")
    current_state = _snapshot(workspace)
    committed = _committed_paths(workspace, previous_head, current_head)
    changed = sorted(set(current_state) | committed)
    newly_changed = sorted(
        {p for p in (set(previous_state) | set(current_state))
         if previous_state.get(p) != current_state.get(p)} | committed
    )
    mutated = bool(newly_changed)
    out_of_scope = [p for p in newly_changed if not _scope(p, task["paths"])]
    completed_event = any(
        line.strip().startswith("{") and _completed_event(line)
        for line in stdout.splitlines()
    )
    committed_by_worker = previous_head != current_head
    status = ("scope_violation" if out_of_scope else
              "timeout" if termination == "timeout" else
              "cancelled" if termination == "cancelled" else
              "failed" if code else
              "unauthorized_commit" if committed_by_worker else
              "unverified_result" if not completed_event else
              "no_change" if not mutated else "completed")
    if cancel_event is not None and status in {
        "scope_violation", "timeout", "failed", "unauthorized_commit", "unverified_result",
    }:
        cancel_event.set()
    return {"id": task["id"], "status": status, "exit_code": code,
            "reasoning_effort": task["selected_effort"], "workspace": str(workspace),
            "changed_paths": changed, "new_paths": newly_changed,
            "committed_paths": sorted(committed), "commit_detected": committed_by_worker,
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
            cancel_event = threading.Event()

            def guarded_worker(task: dict, workspace: Path) -> dict:
                try:
                    return _worker(task, workspace, work_root, timeout, cancel_event)
                except Exception:
                    # A runner/setup error must not leave its sibling running unattended.
                    cancel_event.set()
                    raise

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(guarded_worker, t, workspaces[i])
                           for i, t in enumerate(tasks)]
                results = [f.result() for f in futures]
        else:
            first = _worker(tasks[0], workspaces[0], work_root, timeout)
            results = [first]
            if first["status"] == "completed":
                # The second agent sees the first agent's changes, in the same worktree.
                # Per-file before/after hashes distinguish inherited diffs from new edits.
                second = _worker(tasks[1], workspaces[0], work_root, timeout)
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
