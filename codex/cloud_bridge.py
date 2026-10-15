"""Capability-checked cloud agent transport for authenticated host integrations.

No built-in vendor credentials or network calls. The embedding CloudHost must
implement capability attestation and return verifiable execution evidence.
External calls here are injected by the trusted host, never shell templates.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from typing import Protocol
from uuid import uuid4

from codex.agent_policy import RoutingError
from codex import dual
from codex import resource_budget as budget

RUN_ID = re.compile(r"[A-Za-z0-9._-]{8,128}\Z")


class CloudHost(Protocol):
    def supports(self, provider: str, model: str, capability: str) -> bool: ...
    def execute(self, task: dict, *, target_repository: str) -> dict: ...


def _validate_evidence(task: dict, capability: str, payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("id") != task["id"]:
        raise RoutingError("Cloud provider returned mismatched or unstructured worker evidence")
    if payload.get("status") not in ("completed", "failed", "blocked", "quota_blocked"):
        raise RoutingError("Cloud provider omitted terminal worker status")
    run_id = payload.get("run_id")
    if type(run_id) is not str or not RUN_ID.fullmatch(run_id):
        raise RoutingError("Cloud provider omitted valid immutable run identifier")
    changed = payload.get("changed_paths", [])
    if not isinstance(changed, list) or any(type(p) is not str or not dual._is_safe_path(p) for p in changed):
        raise RoutingError("Invalid cloud change scope evidence")
    out_of_scope = [p for p in changed if not dual._scope(p, task["paths"])]
    status = "scope_violation" if out_of_scope else payload["status"]
    # For code-edit results, an empty diff cannot certify implementation done.
    if status == "completed" and capability == "code_edit" and not changed:
        status = "no_change"
    if status in ("completed", "quota_blocked") and payload.get("verified") is not True:
        status = "unverified_result"
    raw_usage = payload.get("usage")
    measured = None
    if isinstance(raw_usage, dict) and all(type(raw_usage.get(k)) is int and raw_usage[k] >= 0
                                            for k in ("input_tokens", "output_tokens", "cached_input_tokens")):
        if raw_usage["cached_input_tokens"] <= raw_usage["input_tokens"]:
            measured = {k: raw_usage[k] for k in ("input_tokens", "output_tokens", "cached_input_tokens")}
    return {"id": task["id"], "status": status, "run_id": run_id,
            "provider": task["selection"]["provider"], "model": task["selection"]["model"],
            "reasoning_effort": task["selection"]["reasoning_effort"],
            "changed_paths": changed, "out_of_scope": out_of_scope,
            "usage": measured, "usage_status": "measured" if measured is not None else "unknown"}


def execute_cloud(planned: dict, host: CloudHost, budget_directory: Path, *, soft_limit: int | None = budget.SOFT_LIMIT_DEFAULT) -> dict:
    """Launch 1 or 2 attested provider jobs, with dependencies and private usage ledger.

    The adapter boundary is explicit. No credential is copied to the repo, no
    unverified cloud vendor is silently enabled, no commits/PRs are merged.
    """
    if planned.get("status") not in ("planned", "planned_needs_adapter") or planned.get("mode") not in ("single", "serial", "parallel"):
        raise RoutingError("No executable cloud plan; no agent started")
    if "material_boundary_requires_project_leader_controls" in planned.get("warnings", []):
        raise RoutingError("Protected effect needs Project Leader durable authorization")
    tasks = planned.get("tasks", [])
    if len(tasks) not in (1, 2) or (len(tasks) == 1 and planned["mode"] != "single"):
        raise RoutingError("Unsupported cloud task cardinality")
    for t in tasks:
        selection = t["selection"]
        if selection.get("status") != "selected" or not host.supports(selection["provider"], selection["model"], planned["capability"]):
            raise RoutingError("Cloud host has no independently verified capability for provider/model")
    session = uuid4().hex
    reserved = budget.reserve_batch(budget_directory, session,
                                    [{"id": t["id"], "effort": t["selection"]["reasoning_effort"]} for t in tasks],
                                    soft_limit)
    results = []
    attempted: set[str] = set()
    try:
        def launch(task: dict) -> dict:
            # Mark before invoking an external provider. A raised call is
            # ambiguous; only never-invoked stages can be refunded.
            attempted.add(task["id"])
            response = host.execute(task, target_repository=planned["target_repository"])
            return _validate_evidence(task, planned["capability"], response)
        if planned["mode"] == "parallel":
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(launch, t) for t in tasks]
                for fut in futures:
                    results.append(fut.result())
        else:
            for t in tasks:
                if results and results[-1]["status"] != "completed":
                    results.append({"id": t["id"], "status": "not_started", "reason": "Preceding task did not verify"})
                    break
                results.append(launch(t))
    finally:
        # Never charge the conservative reservation for a verified stage that
        # was not even launched after a quota rejection in the prior stage.
        usage_by_id = {}
        for t in tasks:
            worker = next((w for w in results if w["id"] == t["id"]), None)
            usage_by_id[t["id"]] = (
                {"not_started": True}
                if t["id"] not in attempted or
                   (worker is not None and worker["status"] == "not_started")
                else worker.get("usage") if worker is not None else None
            )
        accounted = budget.settle_batch(budget_directory, session, usage_by_id)
    return {"session": session, "target_repository": planned["target_repository"],
            "mode": planned["mode"], "workers": results, "accounting": {**reserved, **accounted},
            "integration": "REQUIRES_INDEPENDENT_REVIEW: no automatic merge, deployment or provider substitution"}


def execute_cloud_coordinator_phases(
    order: dict,
    host: CloudHost,
    budget_directory: Path,
    *,
    checked_head,
    trusted_certifier,
    registry: dict | None = None,
    soft_limit: int | None = budget.SOFT_LIMIT_DEFAULT,
    passive_notify=None,
) -> dict:
    """Bind a real CloudHost to the *existing* shared phase cycle.

    The host must have independently authenticated access to the selected
    target and its original private attachments (if any). Neither attachments
    nor provider credentials are copied to GitHub or to the VPS. The host
    owns exact-head observation and independent CI/review certification;
    a cloud worker report or staged PR cannot certify itself.
    """
    from codex.agent_policy import plan
    from codex import phase_cycle

    if not callable(checked_head) or not callable(trusted_certifier):
        raise RoutingError("Cloud phases need an exact-head observer and independent certifier")
    if (type(order) is not dict or
            not {"request", "target_repository", "work_items"} <= set(order) or
            set(order) - {"request", "target_repository", "work_items",
                          "phases", "preference"}):
        raise RoutingError("Original bounded Cloud Coordinator order is required")

    if "phases" in order:
        phase_rows = order["phases"]
    else:
        original = plan({
            "request": order["request"],
            "target_repository": order["target_repository"],
            "work_items": order["work_items"],
            **({"preference": order["preference"]} if "preference" in order else {}),
        }, registry)
        if original.get("status") != "planned":
            raise RoutingError("Cloud phase planning lacks an attested provider")
        phase_rows = phase_cycle.phases_from_planner(original)

    phases = phase_cycle.validated_phases(order["work_items"], phase_rows)

    def run_phase(phase, base_sha):
        # Preserve Coordinator-chosen scopes, mode and per-task effort. A
        # selected provider must still independently pass host capability
        # attestation before any external model call or budget reservation.
        effort = dict(phase.reasoning_by_task)
        planned = plan({
            "request": order["request"],
            "target_repository": order["target_repository"],
            "work_items": [
                {**item, "reasoning_effort": effort[item["id"]]}
                for item in phase.work_items
            ],
            "preference": phase.mode,
        }, registry)
        if planned.get("status") != "planned" or planned.get("mode") != phase.mode:
            raise RoutingError("Cloud phase mode or capability changed after coordination")

        execution = execute_cloud(planned, host, budget_directory,
                                  soft_limit=soft_limit)
        workers = execution.get("workers", [])
        if (len(workers) != planned["agent_count"] or
                any(worker.get("status") != "completed" for worker in workers)):
            status = (phase_cycle.QUOTA
                      if any(worker.get("status") == "quota_blocked"
                             for worker in workers)
                      else phase_cycle.RECOVERY)
            return {"status": status}
        return {
            "status": "WORKERS_COMPLETED",
            "worker_ids": [worker["run_id"] for worker in workers],
            "worker_evidence": execution,
            "target_base_sha": base_sha,
        }

    return phase_cycle.execute_until_terminal(
        phases, checked_head=checked_head, run_phase=run_phase,
        certify_phase=trusted_certifier, notify=passive_notify)
