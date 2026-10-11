"""Single-order smart orchestration with provider-neutral planning.

Live execution is supported only for the Codex CLI adapter; cloud providers
require separately authenticated and verified host integrations. Never infer
that a provider is connected from its name appearing in a registry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from codex import dual
from codex.agent_policy import RoutingError, plan
from codex import resource_budget as budget


def _private_runs(path: Path, repo: Path) -> Path:
    root = path.expanduser().resolve()
    target = repo.resolve(strict=True)
    if root == target or root.is_relative_to(target):
        raise RoutingError("Private run directory must be outside the target checkout")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if root.is_symlink() or root.stat().st_mode & 0o077:
        raise RoutingError("Unsafe run directory permissions")
    return root


def _execute_solo(planned: dict, repo: Path, root: Path, timeout: int, run_id: str) -> dict:
    task = planned["tasks"][0]
    head = dual._preflight(repo, planned["target_repository"])
    work_root = root / ("run-" + run_id)
    work_root.mkdir(mode=0o700)
    workspace = work_root / "worker-1"
    try:
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(workspace), head],
                       capture_output=True, check=True)
        item = {"id": task["id"], "task": task["task"], "paths": task["paths"],
                "selected_effort": task["selection"]["reasoning_effort"]}
        result = dual._worker(item, workspace, work_root, timeout)
        outcome = {"target_repository": planned["target_repository"], "mode": "single",
                   "base_head": head, "run_directory": str(work_root), "workers": [result],
                   "integration": "NOT_AUTOMATED: review changes, validate and open PR"}
        dual._private_file(work_root / "result.json", json.dumps(outcome, indent=2) + "\n")
        return outcome
    except (OSError, subprocess.CalledProcessError, dual.PlanError) as exc:
        raise RoutingError("Solo executor stopped; worktree preserved in " + str(work_root)) from exc


def execute(planned: dict, repo_dir: Path, runs_dir: Path | None = None, *, timeout: int = 1200,
            soft_limit: int = budget.SOFT_LIMIT_DEFAULT) -> dict:
    if planned.get("status") != "planned" or planned.get("capability") != "code_edit":
        raise RoutingError("Plan is not executable for code edits; no agent started")
    if not 30 <= timeout <= 7200:
        raise RoutingError("Timeout must be between 30 and 7200 seconds")
    if "material_boundary_requires_project_leader_controls" in planned.get("warnings", []):
        raise RoutingError("Material operation requires verified Project Leader authorization; no agent started")
    # Deliberately no unsafe generic command templates or silent cross-vendor substitution.
    for task in planned["tasks"]:
        profile = task["selection"]
        if (profile["status"] != "selected" or profile["provider"] != "codex"
                or profile["adapter"] != "codex-cli" or profile["model"] != "runtime-default"):
            raise RoutingError("Provider/model lacks a verified executor adapter; no agent started")
    if shutil.which("codex") is None:
        raise RoutingError("Codex CLI absent; no agent started")
    repo = repo_dir.expanduser().resolve(strict=True)
    dual._preflight(repo, planned["target_repository"])
    root = _private_runs(runs_dir or Path.home() / ".local/share/project-leader-codex/runs", repo)
    run_id = uuid4().hex
    selected = [{"id": t["id"], "effort": t["selection"]["reasoning_effort"]} for t in planned["tasks"]]
    budget_root = root / ".shared-budget"
    reservation = budget.reserve_batch(budget_root, run_id, selected, limit=soft_limit)
    result = None
    try:
        if planned["mode"] == "single":
            result = _execute_solo(planned, repo, root, timeout, run_id)
        else:
            order = {"target_repository": planned["target_repository"], "mode": planned["mode"],
                     "tasks": [{"id": x["id"], "task": x["task"], "paths": x["paths"],
                                "reasoning_effort": x["selection"]["reasoning_effort"]}
                               for x in planned["tasks"]]}
            parsed = dual.parse_order(order)
            result = dual.run(parsed, repo, root, timeout)
    finally:
        usage = {}
        for entry in selected:
            if result is not None:
                logdir = Path(result["run_directory"])
                usage[entry["id"]] = budget.codex_usage_file(logdir / (entry["id"] + ".jsonl"))
            else:
                usage[entry["id"]] = None
        settled = budget.settle_batch(budget_root, run_id, usage)
    result["accounting"] = {**reservation, **settled,
                            "note": "Private local soft budget, not live account/provider quota"}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smart provider-neutral agent planner and guarded Codex CLI runner")
    parser.add_argument("action", choices=("plan", "run"))
    parser.add_argument("--order", type=Path, required=True, help="One Owner request with optional internally scoped work items")
    parser.add_argument("--repo-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--soft-limit", type=int, default=budget.SOFT_LIMIT_DEFAULT)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.order.is_file() or args.order.stat().st_size > 16_000:
            raise RoutingError("Order JSON missing or too large")
        order = json.loads(args.order.read_text(encoding="utf-8"))
        planned = plan(order)
        if args.action == "plan":
            print(json.dumps(planned, indent=2, ensure_ascii=False))
            return 0 if planned["status"] == "planned" else 2
        if not args.execute or args.repo_dir is None:
            raise RoutingError("run requires --execute and --repo-dir; no agent started")
        result = execute(planned, args.repo_dir, args.runs_dir, timeout=args.timeout, soft_limit=args.soft_limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if all(x["status"] == "completed" for x in result["workers"]) else 2
    except (RoutingError, dual.PlanError, budget.BudgetError, ValueError, OSError) as exc:
        print("SMART_AGENT_BLOCKED: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
