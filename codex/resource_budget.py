"""Atomic, local, provider-neutral soft token ledger for dispatched jobs only.

Never an OpenAI/provider account quota API or hard in-flight spend cap. Unknown
usage is charged against a conservative reservation rather than called zero.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import stat
import time

SOFT_LIMIT_DEFAULT = 300_000
WINDOW = 24 * 3600
RESERVATIONS = {"low": 12_000, "medium": 35_000, "high": 75_000}
SAFE_RUN = re.compile(r"[a-f0-9]{32}\Z")
SAFE_JOB = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")


class BudgetError(ValueError):
    pass


def _directory(root: Path) -> None:
    if root.is_symlink():
        raise BudgetError("Symlinked budget directory is forbidden")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise BudgetError("Budget directory must have private permissions 0700")


def _with_ledger(root: Path, fn):
    _directory(root)
    fd = os.open(root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if stat.S_IMODE(os.fstat(fd).st_mode) & 0o077:
            raise BudgetError("Budget lock file must be private")
        fcntl.flock(fd, fcntl.LOCK_EX)
        path = root / "usage.json"
        if path.is_symlink():
            raise BudgetError("Unsafe budget ledger symlink")
        if path.exists():
            if path.stat().st_size > 256_000 or stat.S_IMODE(path.stat().st_mode) & 0o077:
                raise BudgetError("Invalid budget ledger size/permissions")
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = {"version": 1, "records": []}
        if data.get("version") != 1 or not isinstance(data.get("records"), list):
            raise BudgetError("Invalid budget ledger")
        now = time.time()
        data["records"] = [r for r in data["records"]
                           if isinstance(r, dict) and isinstance(r.get("at"), (int, float))
                           and now - WINDOW <= r["at"] <= now + 60]
        if len(data["records"]) > 5000:
            raise BudgetError("Unbounded token records")
        result = fn(data, now)
        temporary = root / (".usage." + str(os.getpid()) + ".tmp")
        file_fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(file_fd, "w", encoding="utf-8") as stream:
                json.dump(data, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()
        return result
    finally:
        os.close(fd)


def reserve_batch(root: Path, run_id: str, tasks: list[dict], limit: int = SOFT_LIMIT_DEFAULT) -> dict:
    if type(limit) is not int or not 100_000 <= limit <= 2_000_000:
        raise BudgetError("Soft budget must be between 100000 and 2000000")
    if not SAFE_RUN.fullmatch(run_id) or not 1 <= len(tasks) <= 2:
        raise BudgetError("Invalid run identity or task count")
    if any(not SAFE_JOB.fullmatch(t.get("id", "")) or t.get("effort") not in RESERVATIONS for t in tasks):
        raise BudgetError("Invalid task identity or effort")
    if len({t["id"] for t in tasks}) != len(tasks):
        raise BudgetError("Duplicate task identity")

    def op(data, now):
        if any(r["run"] == run_id for r in data["records"]):
            raise BudgetError("Ambiguous reservation replay blocked")
        used = sum(r.get("actual") if r.get("actual") is not None else r["reserved"]
                   for r in data["records"])
        required = sum(RESERVATIONS[t["effort"]] for t in tasks)
        if used + required > limit:
            raise BudgetError("Local 24-hour soft token budget exceeded; no agent started")
        for t in tasks:
            data["records"].append({"run": run_id, "job": t["id"], "at": now,
                                    "reserved": RESERVATIONS[t["effort"]], "actual": None,
                                    "observed": False})
        return {"allowed": True, "reserved_tokens": required,
                "soft_limit": limit, "remaining_estimate": limit - used - required,
                "quota_source": "local_soft_budget_not_account_quota"}
    return _with_ledger(root, op)


def settle_batch(root: Path, run_id: str, usage: dict[str, dict | None]) -> dict:
    if not SAFE_RUN.fullmatch(run_id):
        raise BudgetError("Invalid run identity")

    def op(data, now):
        records = [r for r in data["records"] if r.get("run") == run_id]
        if not records or set(usage) != {r["job"] for r in records}:
            raise BudgetError("Cannot settle unknown or incomplete reservation")
        for r in records:
            if r["actual"] is not None:
                raise BudgetError("Already settled; ambiguous accounting replay")
            observed = usage[r["job"]]
            if observed is None:
                r["actual"] = r["reserved"]
                r["observed"] = False
            else:
                if not isinstance(observed, dict) or any(type(observed.get(k)) is not int or observed[k] < 0 for k in
                                                        ("input_tokens", "output_tokens", "cached_input_tokens")):
                    raise BudgetError("Invalid observed usage")
                if observed["cached_input_tokens"] > observed["input_tokens"]:
                    raise BudgetError("Cached tokens cannot exceed input tokens")
                r["actual"] = observed["input_tokens"] + observed["output_tokens"]
                r["observed"] = True
        return {"settled": True, "observed_jobs": sum(r["observed"] for r in records),
                "conservative_jobs": sum(not r["observed"] for r in records),
                "accounted_tokens": sum(r["actual"] for r in records)}
    return _with_ledger(root, op)


def codex_usage_file(path: Path) -> dict | None:
    """Count per-turn completed usage once. Unknown layout => unknown, not zero."""
    if not path.is_file() or path.stat().st_size > 2_000_000:
        return None
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0}
    count = 0
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            if event.get("type") != "turn.completed":
                continue
            usage = event.get("usage")
            if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in totals):
                return None
            if usage["cached_input_tokens"] > usage["input_tokens"]:
                return None
            for name in totals:
                totals[name] += usage[name]
            count += 1
    except (ValueError, TypeError, OSError):
        return None
    return totals if count else None
