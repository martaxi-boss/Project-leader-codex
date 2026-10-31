"""Two Codex CLI jobs, independent Git clones, explicit serial/parallel modes.

No agent is started by plan. Run requires --execute and a local
signed-in Codex CLI; no credentials, merges or pushes are managed here.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
from concurrent.futures import ThreadPoolExecutor
import signal
import stat
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
from typing import Callable

REPO_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
JOB_NAME = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")
LEVELS = {"auto", "low", "medium", "high"}
HARD = ("race condition", "deadlock", "security", "seguranca", "segurança",
        "seguranca critica", "segurança crítica", "irreversible migration",
        "migração irreversível", "migracao irreversivel", "complex regression",
        "regressão complexa", "regressao complexa", "root cause", "causa raiz",
        "concurrency", "concorrencia", "concorrência", "credential")
EASY = ("typo", "ortografia", "readme", "formatting", "formatar", "renomear")
ROOT = Path(__file__).resolve().parents[1]
# Never resolve the validator sandbox executable from a worker-controlled PATH.
BWRAP_CANDIDATES = (Path("/usr/bin/bwrap"), Path("/bin/bwrap"))


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
    """Apply the task difficulty floor before any explicit effort override."""
    requested = task.get("reasoning_effort", "auto")
    if type(requested) is not str or requested not in LEVELS:
        raise PlanError("reasoning_effort must be auto, low, medium or high")
    prompt = task["task"].casefold()
    if task.get("verified_hard_failure") is True or any(signal in prompt for signal in HARD):
        minimum = "high"
    elif len(prompt) < 240 and any(signal in prompt for signal in EASY):
        minimum = "low"
    else:
        minimum = "medium"
    if requested == "auto":
        return minimum
    rank = {"low": 0, "medium": 1, "high": 2}
    if rank[requested] < rank[minimum]:
        raise PlanError("Unsafe reasoning-effort override: task requires at least " + minimum)
    return requested

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
            "execution": "two independent Git clones" if mode == "parallel" else "one ordered private Git clone",
            "integration": "manual review + tested PR; no automatic merge"}


def _safe_git(repo: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    """Read attacker-writable Git workspaces without executing their helpers.

    Workers may alter .git/config, hooks, fsmonitor and diff drivers. Never
    give post-worker Git inspection the host environment or credential data.
    """
    clean_env = {
        "PATH": os.defpath,
        "HOME": os.devnull,
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
    }
    cmd = [
        shutil.which("git") or "git",
        "-c", "core.fsmonitor=false",
        "-c", "core.hooksPath=" + os.devnull,
        "-c", "diff.external=",
        "-C", str(repo),
        *args,
    ]
    return subprocess.run(cmd, capture_output=True, text=text,
                          check=False, env=clean_env)


def _git(repo: Path, *args: str) -> str:
    result = _safe_git(repo, *args, text=True)
    if result.returncode:
        raise PlanError("Git preflight failed: " + " ".join(args))
    return result.stdout.strip()


def _metadata_config_snapshot(workspace: Path) -> dict[str, str]:
    """Inspect code-bearing .git control surfaces without invoking Git."""
    root = workspace / ".git"
    if root.is_symlink() or not root.is_dir():
        raise PlanError("Worker replaced or removed its private Git directory")
    probes = [root / "config", root / "config.worktree",
              root / "info/attributes"]
    hooks = root / "hooks"
    if hooks.is_symlink():
        raise PlanError("Worker Git hooks directory is a symlink")
    if hooks.exists():
        if not hooks.is_dir():
            raise PlanError("Worker Git hooks directory is invalid")
        probes.extend(hooks.iterdir())
    state = {}
    for path in probes:
        if path.is_symlink():
            raise PlanError("Worker Git control file is a symlink")
        if not path.exists():
            continue
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise PlanError("Worker Git control file is not private")
        if path.stat().st_size > 1048576:
            raise PlanError("Worker Git control file exceeds audit limit")
        state[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return state


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
        raise PlanError("Source checkout is dirty; preserve changes before starting worker clones")
    return _git(repo, "rev-parse", "HEAD")


def _changes(workspace: Path) -> set[str]:
    result = _safe_git(workspace, "status", "--porcelain=1", "--untracked-files=all", "-z")
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
    result = _safe_git(
        workspace, "diff", "--no-ext-diff", "--no-textconv",
        "--no-renames", "--name-only", "-z", before, after,
    )
    if result.returncode:
        raise PlanError("Cannot audit Codex worker commits; fail closed")
    return {os.fsdecode(p) for p in result.stdout.split(b"\x00") if p}


def _refs_snapshot(repo: Path) -> dict[str, str]:
    """Audit all Git ref names and object IDs, not only detached HEAD."""
    proc = _safe_git(
        repo, "for-each-ref", "--format=%(refname)%00%(objectname)",
        text=True,
    )
    if proc.returncode:
        raise PlanError("Cannot audit Git references; fail closed")
    output = {}
    for entry in proc.stdout.splitlines():
        name, separator, value = entry.partition("\x00")
        if not separator or not name.startswith("refs/") or not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise PlanError("Malformed Git reference listing; fail closed")
        output[name] = value
    return output


def _ref_committed_paths(workspace: Path, baseline: str,
                         changed_refs: list[str],
                         refs: dict[str, str]) -> set[str]:
    """Include edits preserved on side refs even if detached HEAD was reset."""
    result = set()
    for name in changed_refs:
        object_id = refs.get(name)
        if object_id is None:
            continue
        commit = _safe_git(
            workspace, "rev-parse", "--verify", object_id + "^{commit}",
            text=True,
        )
        if commit.returncode:
            # Still an unauthorized ref mutation; cannot treat it as success.
            continue
        result.update(_committed_paths(workspace, baseline, commit.stdout.strip()))
    return result


def _private_clone(repo: Path, destination: Path, head: str) -> None:
    """Never give a model a linked worktree pointing at source Git metadata.

    --no-local prevents both Git object hardlinks and shared alternates.
    Remove the temporary local-path origin before the model can execute.
    """
    subprocess.run(
        ["git", "clone", "--no-local", "--no-checkout", "--no-tags",
         "--quiet", str(repo), str(destination)],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(destination), "remote", "remove", "origin"],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "-C", str(destination), "checkout", "--quiet", "--detach", head],
        capture_output=True, check=True,
    )
    git_dir = Path(_git(destination, "rev-parse", "--absolute-git-dir")).resolve()
    if (git_dir != (destination / ".git").resolve()
            or not (destination / ".git").is_dir()
            or (destination / ".git/objects/info/alternates").exists()
            or _git(destination, "remote")
            or _git(destination, "rev-parse", "HEAD") != head):
        raise PlanError("Worker Git directory is not private and self-contained")


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


_CODEX_ENV_NAMES = frozenset({
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG",
    "LC_ALL", "LC_CTYPE", "TERM", "COLORTERM", "TMPDIR", "TZ",
    "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME",
    "XDG_STATE_HOME", "XDG_RUNTIME_DIR",
    "CODEX_HOME", "CODEX_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL",
    "OPENAI_ORG_ID", "OPENAI_PROJECT_ID",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
})


def _child_environment(explicit: dict[str, str] | None) -> dict[str, str]:
    # Avoid forwarding unrelated inherited project and CI variables to Codex.
    # A host-supplied explicit environment remains caller-controlled.
    if explicit is not None:
        return dict(explicit)
    return {name: value for name, value in os.environ.items()
            if name in _CODEX_ENV_NAMES}


def _invoke_codex(cmd: list[str], prompt: str, timeout: int,
                  cancel_event: threading.Event | None = None,
                  *, cwd: Path | None = None,
                  env: dict[str, str] | None = None) -> tuple[int, str, str, str]:
    if cancel_event is not None and cancel_event.is_set():
        return 125, "", "Cancelled before model launch", "cancelled"
    process = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=(os.name == "posix"),
        cwd=str(cwd) if cwd is not None else None, env=_child_environment(env),
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


def _trusted_bwrap() -> Path:
    """Select a preinstalled, non-writable Linux namespace isolation binary."""
    if sys.platform != "linux":
        raise PlanError("Isolated serial validation requires Linux bubblewrap")
    for candidate in BWRAP_CANDIDATES:
        path = Path(candidate)
        if path.is_symlink() or not path.is_file():
            continue
        details = path.stat()
        if (details.st_uid in {0, os.getuid()}
                and not details.st_mode & 0o022
                and os.access(path, os.X_OK)):
            return path.resolve(strict=True)
    raise PlanError(
        "Isolated serial validation requires trusted /usr/bin/bwrap "
        "(bubblewrap); no validator or dependent worker started"
    )


def _validator_sandbox_cmd(bwrap: Path, script: Path, workspace: Path) -> list[str]:
    """Only expose the read-only worker tree, validator and runtime libraries.

    Unshare namespaces (including network); no host HOME, secrets, Git
    credentials or other host paths are mounted. /work is read-only.
    """
    cmd = [str(bwrap), "--die-with-parent", "--unshare-all", "--new-session",
           "--clearenv", "--ro-bind", "/usr", "/usr"]
    for location in (Path("/bin"), Path("/lib"), Path("/lib64")):
        if location.is_symlink():
            cmd.extend(["--symlink", os.readlink(location), str(location)])
        elif location.is_dir():
            cmd.extend(["--ro-bind", str(location), str(location)])
    cmd.extend([
        "--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc",
        "--dir", "/validator", "--ro-bind", str(script), "/validator/check",
        "--ro-bind", str(workspace), "/work", "--chdir", "/work",
        "--setenv", "HOME", "/tmp",
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "PYTHONNOUSERSITE", "1",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--", "/validator/check",
    ])
    return cmd


def trusted_phase_one_validator(script: Path, repo: Path, timeout: int):
    """Run a host-controlled acceptance verifier in a credential-free namespace.

    A verifier may execute worker-authored tests, so checking its own pathname
    is insufficient. If kernel namespace isolation cannot be set up, fail
    closed; never execute test code with the orchestration host's credentials.
    """
    path = Path(script)
    if not path.is_absolute() or path.is_symlink():
        raise PlanError("Phase-one validator must be an absolute, non-symlinked host path")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise PlanError("Configured phase-one validator does not exist") from exc
    if resolved.is_relative_to(Path(repo).resolve(strict=True)):
        raise PlanError("Phase-one validator must be outside the worker's repository")
    st = resolved.stat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid not in {0, os.getuid()}
            or st.st_mode & 0o022 or not os.access(resolved, os.X_OK)):
        raise PlanError("Phase-one validator must be an executable, trusted host file")
    sandbox = _trusted_bwrap()
    # Probe real kernel namespace/mount support before the first worker starts.
    # Merely locating the bwrap executable is insufficient on restricted hosts.
    probe = _validator_sandbox_cmd(sandbox, resolved, Path(repo).resolve(strict=True))
    probe[-1] = "/usr/bin/true"
    status, _, _, termination = _invoke_codex(
        probe, "{}", 8,
        env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8"},
    )
    if status != 0 or termination != "finished":
        raise PlanError(
            "Validator sandbox preflight failed; no model or worker started"
        )

    def check(workspace: Path, task: dict, report: dict) -> dict:
        payload = {
            "workspace": "/work",
            "task_id": task["id"],
            "owned_paths": task["paths"],
            "changed_paths": report["new_paths"],
            "base_head": _git(workspace, "rev-parse", "HEAD"),
        }
        cmd = _validator_sandbox_cmd(sandbox, resolved, workspace.resolve(strict=True))
        code, out, err, state = _invoke_codex(
            cmd, json.dumps(payload, ensure_ascii=False), min(timeout, 900),
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8"},
        )
        if state != "finished" or code != 0:
            return {
                "passed": False,
                "evidence": "Isolated validator did not pass "
                            f"(state={state}, exit={code}); second worker blocked",
            }
        if len(out) > 16000 or len(err) > 16000:
            raise PlanError("Isolated validator returned unbounded output")
        try:
            verdict = json.loads(out)
        except (ValueError, TypeError) as exc:
            raise PlanError("Isolated validator returned invalid JSON") from exc
        if (not isinstance(verdict, dict)
                or type(verdict.get("passed")) is not bool
                or type(verdict.get("evidence")) is not str
                or not 1 <= len(verdict["evidence"].strip()) <= 4000):
            raise PlanError("Isolated validator returned invalid acceptance evidence")
        return {"passed": verdict["passed"], "evidence": verdict["evidence"]}

    return check


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
    previous_refs = _refs_snapshot(workspace)
    previous_state = _snapshot(workspace)
    previous_metadata = _metadata_config_snapshot(workspace)
    code, stdout, stderr, termination = _invoke_codex(
        cmd, _prompt(task), timeout, cancel_event, cwd=workspace,
    )
    _private_file(logdir / (task["id"] + ".jsonl"), stdout)
    _private_file(logdir / (task["id"] + ".stderr"), stderr)
    current_metadata = _metadata_config_snapshot(workspace)
    if current_metadata != previous_metadata:
        if cancel_event is not None:
            cancel_event.set()
        modified = sorted(name for name in set(previous_metadata) | set(current_metadata)
                          if previous_metadata.get(name) != current_metadata.get(name))
        # Do not call Git, status, diff or ref inspection on a potentially
        # hostile .git/config (e.g. core.fsmonitor) after model execution.
        return {"id": task["id"], "status": "git_metadata_violation",
                "exit_code": code, "reasoning_effort": task["selected_effort"],
                "workspace": str(workspace), "changed_paths": [],
                "new_paths": [], "committed_paths": [], "commit_detected": False,
                "ref_changes": [], "out_of_scope": [".git/" + x for x in modified],
                "duration_seconds": round(time.monotonic() - started, 2)}
    current_head = _git(workspace, "rev-parse", "HEAD")
    current_refs = _refs_snapshot(workspace)
    ref_changes = sorted(
        name for name in set(previous_refs) | set(current_refs)
        if previous_refs.get(name) != current_refs.get(name)
    )
    current_state = _snapshot(workspace)
    committed = _committed_paths(workspace, previous_head, current_head)
    side_ref_paths = _ref_committed_paths(workspace, previous_head,
                                          ref_changes, current_refs)
    committed.update(side_ref_paths)
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
              "unauthorized_ref_change" if ref_changes else
              "timeout" if termination == "timeout" else
              "cancelled" if termination == "cancelled" else
              "failed" if code else
              "unauthorized_commit" if committed_by_worker else
              "unverified_result" if not completed_event else
              "no_change" if not mutated else "completed")
    if cancel_event is not None and status in {
        "scope_violation", "unauthorized_ref_change", "timeout", "failed",
        "unauthorized_commit", "unverified_result", "no_change",
    }:
        cancel_event.set()
    return {"id": task["id"], "status": status, "exit_code": code,
            "reasoning_effort": task["selected_effort"], "workspace": str(workspace),
            "changed_paths": changed, "new_paths": newly_changed,
            "committed_paths": sorted(committed), "commit_detected": committed_by_worker,
            "ref_changes": ref_changes,
            "out_of_scope": out_of_scope, "duration_seconds": round(time.monotonic() - started, 2)}

def _private_runs_root(repo: Path, requested: Path | None) -> Path:
    """Choose private writable state without assuming Cloud HOME is writable.

    Explicit paths are authoritative. Automatic selection tries XDG state,
    the normal user state directory, then a configured private runtime dir.
    Never put worker Git clones, usage ledgers or logs inside the source repo.
    """
    target = repo.resolve(strict=True)
    candidates = []
    if requested is not None:
        candidates.append(requested.expanduser())
    else:
        state = os.environ.get("XDG_STATE_HOME", "")
        if state and Path(state).is_absolute():
            candidates.append(Path(state) / "project-leader-codex" / "runs")
        candidates.append(Path.home() / ".local/share/project-leader-codex/runs")
        runtime = os.environ.get("XDG_RUNTIME_DIR", "")
        if runtime and Path(runtime).is_absolute():
            candidates.append(Path(runtime) / "project-leader-codex" / "runs")
    for candidate in candidates:
        if candidate.is_symlink():
            raise PlanError("Runs directory must not be a symlink")
        root = candidate.resolve()
        if root == target or root.is_relative_to(target):
            if requested is not None:
                raise PlanError("Runs directory must be outside the target repository")
            continue
        try:
            root.mkdir(parents=True, exist_ok=True, mode=0o700)
            details = root.stat()
            if details.st_uid != os.getuid() or details.st_mode & 0o077:
                raise PlanError("Runs directory must be owned by this user and private (0700)")
            probe = root / (".write-probe-" + uuid4().hex)
            fd = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
            probe.unlink()
            return root
        except OSError as exc:
            if requested is None and exc.errno in {errno.EACCES, errno.EPERM, errno.EROFS}:
                continue
            raise PlanError(
                "Runs directory is not writable; use --runs-dir with a private "
                "writable directory outside the checkout"
            ) from exc
    raise PlanError(
        "No private writable runs directory in this host; use --runs-dir "
        "with a writable private directory outside the checkout, or use "
        "native Codex Cloud workers if nested Codex CLI is restricted"
    )


def run(order: dict, repo: Path, runs_dir: Path | None = None, timeout: int = 1200,
        phase_one_validator: Callable[[Path, dict, dict], dict] | None = None) -> dict:
    if shutil.which("codex") is None:
        raise PlanError("Codex CLI is not installed or accessible; no model started")
    if not 30 <= timeout <= 7200:
        raise PlanError("timeout must be between 30 and 7200 seconds")
    if order["mode"] == "serial" and not callable(phase_one_validator):
        raise PlanError(
            "Serial phase one requires an independent acceptance validator; no model started"
        )
    repo = repo.resolve(strict=True)
    head = _preflight(repo, order["target_repository"])
    original_refs = _refs_snapshot(repo)
    root = _private_runs_root(repo, runs_dir)
    work_root = root / ("run-" + uuid4().hex)
    work_root.mkdir(mode=0o700)
    workspaces = []
    try:
        for idx in range(2 if order["mode"] == "parallel" else 1):
            workspace = work_root / ("worker-" + str(idx + 1))
            _private_clone(repo, workspace, head)
            workspaces.append(workspace)
    except (OSError, subprocess.CalledProcessError, PlanError) as exc:
        raise PlanError("Could not create independent Git clone; inspect " + str(work_root)) from exc
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
                # A completed Codex turn is not independent project validation.
                # The host's trusted validator inspects real changes and tests;
                # never launch the dependent agent on self-attested success.
                review = phase_one_validator(workspaces[0], tasks[0], first)
                if (not isinstance(review, dict)
                        or type(review.get("passed")) is not bool
                        or type(review.get("evidence")) is not str
                        or not review["evidence"].strip()):
                    raise PlanError("Independent phase-one validator must return a verdict and evidence")
                first["validation"] = {"passed": review["passed"],
                                       "evidence": review["evidence"]}
                if review["passed"]:
                    second = _worker(tasks[1], workspaces[0], work_root, timeout)
                    results.append(second)
                else:
                    results.append({"id": tasks[1]["id"], "status": "not_started",
                                    "reason": "Independent phase-one validation failed"})
            else:
                results.append({"id": tasks[1]["id"], "status": "not_started",
                                "reason": "First task did not complete"})
    except (OSError, PlanError) as exc:
        raise PlanError("Worker error: " + str(exc) + "; preserved workspaces in " + str(work_root)) from exc
    if (_git(repo, "rev-parse", "HEAD") != head
            or _refs_snapshot(repo) != original_refs
            or _changes(repo)):
        raise PlanError("Original Git repository changed during workers; fail closed, "
                        "preserve evidence in " + str(work_root))
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
    parser.add_argument("--phase-one-validator", type=Path,
                        help="Trusted host test/acceptance script; required for serial execution")
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
        validator = (trusted_phase_one_validator(args.phase_one_validator, args.repo_dir,
                                                 args.timeout)
                     if args.phase_one_validator is not None else None)
        result = run(order, args.repo_dir, args.runs_dir, args.timeout,
                     phase_one_validator=validator)
        print(json.dumps(result, indent=2))
        return 0 if all(r["status"] == "completed" for r in result["workers"]) else 2
    except (PlanError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("CODEX_DUAL_BLOCKED: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
