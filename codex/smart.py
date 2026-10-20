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
from codex.scope_discovery import discover_work_items
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
    original_refs = dual._refs_snapshot(repo)
    work_root = root / ("run-" + run_id)
    work_root.mkdir(mode=0o700)
    workspace = work_root / "worker-1"
    try:
        dual._private_clone(repo, workspace, head)
        item = {"id": task["id"], "task": task["task"], "paths": task["paths"],
                "selected_effort": task["selection"]["reasoning_effort"]}
        result = dual._worker(item, workspace, work_root, timeout)
        if (dual._git(repo, "rev-parse", "HEAD") != head
                or dual._refs_snapshot(repo) != original_refs
                or dual._changes(repo)):
            raise RoutingError("Original source Git repository changed during solo worker")
        outcome = {"target_repository": planned["target_repository"], "mode": "single",
                   "base_head": head, "run_directory": str(work_root), "workers": [result],
                   "integration": "NOT_AUTOMATED: review changes, validate and open PR"}
        dual._private_file(work_root / "result.json", json.dumps(outcome, indent=2) + "\n")
        return outcome
    except (OSError, subprocess.CalledProcessError, dual.PlanError) as exc:
        raise RoutingError("Solo executor stopped; independent clone preserved in " + str(work_root)) from exc


def execute(planned: dict, repo_dir: Path, runs_dir: Path | None = None, *, timeout: int = 1200,
            soft_limit: int | None = budget.SOFT_LIMIT_DEFAULT, phase_one_validator=None) -> dict:
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
    if planned["mode"] == "serial" and not callable(phase_one_validator):
        raise RoutingError(
            "Serial execution requires an independent project validator; "
            "no worker or budget reserved"
        )
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
            result = dual.run(parsed, repo, root, timeout,
                              phase_one_validator=phase_one_validator)
    finally:
        usage = {}
        for entry in selected:
            if result is not None:
                worker = next((w for w in result["workers"] if w["id"] == entry["id"]), None)
                if worker is not None and worker.get("status") == "not_started":
                    # A prior serial stage stopped; this stage consumed nothing.
                    usage[entry["id"]] = {"not_started": True}
                else:
                    logdir = Path(result["run_directory"])
                    usage[entry["id"]] = budget.codex_usage_file(
                        logdir / (entry["id"] + ".jsonl"))
            else:
                # An interrupted/ambiguous runner is charged conservatively.
                usage[entry["id"]] = None
        settled = budget.settle_batch(budget_root, run_id, usage)
    result["accounting"] = {**reservation, **settled,
                            "note": "Private usage ledger; only an explicitly selected soft limit can deny a turn; provider quota remains unknown"}
    return result

def execute_coordinator_phases(
    order: dict, repo_dir: Path, *,
    trusted_certifier,
    runs_dir: Path | None = None,
    timeout: int = 1200,
    soft_limit: int | None = budget.SOFT_LIMIT_DEFAULT,
    phase_one_validator=None,
    passive_notify=None,
    resume_checkpoint=None,
    verify_resume=None,
) -> dict:
    """Execute every Coordinator-selected phase in the SAME authorized order.

    The certifier must be an independent Project Leader host adapter that
    integrates/verifies exact-SHA CI and any material gates. Codex alone can
    only stage changes; it never grants itself acceptance/merge authority.
    Without a callable certifier no phase or model is launched.
    """
    from codex import phase_cycle
    if not callable(trusted_certifier):
        raise RoutingError("Independent host certification required for phase continuation")
    if (type(order) is not dict or
            not {"request", "target_repository", "work_items"} <= set(order) or
            set(order) - {"request", "target_repository", "work_items",
                          "phases", "preference"}):
        raise RoutingError("A bounded original Coordinator plan is required")
    if "phases" in order:
        phase_rows = order["phases"]
    else:
        # The host has already verified/scoped every Owner work item.
        # Select one/two workers and preserve an effort choice per phase.
        original = plan({
            "request": order["request"],
            "target_repository": order["target_repository"],
            "work_items": order["work_items"],
            **({"preference": order["preference"]}
               if "preference" in order else {}),
        })
        phase_rows = phase_cycle.phases_from_planner(original)
    phases = phase_cycle.validated_phases(order["work_items"], phase_rows)
    repo = repo_dir.expanduser().resolve(strict=True)
    dual._preflight(repo, order["target_repository"])

    def checked_head() -> str:
        return dual._git(repo, "rev-parse", "HEAD")

    def run_phase(phase, base):
        # Keep the Coordinator's phases, worker choice and effort. The
        # capability selector verifies the quality floor without new prompts.
        scoped = []
        for item in phase.work_items:
            selected_effort = dict(phase.reasoning_by_task)[item["id"]]
            scoped.append({**item, "reasoning_effort": selected_effort})
        planned = plan({
            "request": order["request"],
            "target_repository": order["target_repository"],
            "work_items": scoped,
            "preference": phase.mode,
        })
        if (planned.get("status") != "planned" or
                planned.get("mode") != phase.mode):
            raise RoutingError("Coordinator's selected phase failed bounded planner")
        result = execute(planned, repo, runs_dir, timeout=timeout,
                         soft_limit=soft_limit,
                         phase_one_validator=phase_one_validator)
        workers = result.get("workers", [])
        if (not workers or not all(w.get("status") == "completed" for w in workers)):
            return {"status": phase_cycle.RECOVERY,
                    "worker_ids": [w.get("id", "") for w in workers]}
        return {"status": "WORKERS_COMPLETED",
                "worker_ids": [w["id"] for w in workers],
                "worker_evidence": result}

    return phase_cycle.execute_until_terminal(
        phases, checked_head=checked_head, run_phase=run_phase,
        certify_phase=trusted_certifier, notify=passive_notify,
        resume_checkpoint=resume_checkpoint, verify_resume=verify_resume)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smart provider-neutral agent planner and guarded Codex CLI runner")
    parser.add_argument("action", choices=("plan", "run"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--order", type=Path, help="Existing validated order JSON")
    source.add_argument("--task", help="Natural-language Owner request for this checkout")
    parser.add_argument("--repo-dir", type=Path)
    parser.add_argument("--runs-dir", type=Path)
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--soft-limit", type=int, default=budget.SOFT_LIMIT_DEFAULT)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--phase-one-validator", type=Path,
                        help="Trusted host acceptance verifier needed for serial CLI mode")
    args = parser.parse_args(argv)
    try:
        if args.order is not None:
            if not args.order.is_file() or args.order.stat().st_size > 16_000:
                raise RoutingError("Order JSON missing or too large")
            order = json.loads(args.order.read_text(encoding="utf-8"))
        else:
            if args.repo_dir is None:
                raise RoutingError("Natural-language orders require a real checkout; no agent started")
            # Discover only the actual authenticated target from its Git origin.
            # A malformed or foreign origin is never a grant to another repo.
            repo = args.repo_dir.expanduser().resolve(strict=True)
            target = dual._remote_repo(dual._git(repo, "remote", "get-url", "origin"))
            if not target.startswith("martaxi-boss/"):
                raise RoutingError("Selected checkout is outside the authorized Owner")
            dual._preflight(repo, target)
            order = {"request": args.task, "target_repository": target}
        if "work_items" not in order and args.repo_dir is not None:
            order = discover_work_items(order, args.repo_dir)
        planned = plan(order)
        if args.action == "plan":
            print(json.dumps(planned, indent=2, ensure_ascii=False))
            return 0 if planned["status"] == "planned" else 2
        if not args.execute or args.repo_dir is None:
            raise RoutingError("run requires --execute and --repo-dir; no agent started")
        validator = (dual.trusted_phase_one_validator(
            args.phase_one_validator, args.repo_dir, args.timeout,
        ) if args.phase_one_validator is not None else None)
        result = execute(planned, args.repo_dir, args.runs_dir, timeout=args.timeout,
                         soft_limit=args.soft_limit, phase_one_validator=validator)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if all(x["status"] == "completed" for x in result["workers"]) else 2
    except (RoutingError, dual.PlanError, budget.BudgetError, ValueError, OSError) as exc:
        print("SMART_AGENT_BLOCKED: " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
