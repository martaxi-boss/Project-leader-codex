"""One-Owner-order, bounded phase continuation for the Project Leader Codex host.

The host supplies the independently authenticated executor, exact Git HEAD
observer, Project Leader certifier and passive notifier. This module NEVER
silently accepts a staged PR, skipped CI or model report as certification.
Its purpose is to keep all preplanned phases in one host operation, not to
create another coordinator or request Owner prompts between phases.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any

from codex.agent_policy import RoutingError, _validate_item, _has_overlap, MAX_ITEMS

SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_PHASES = 8


class PhaseCycleError(RoutingError):
    """Unverified continuation; no dependent work may start."""


@dataclass(frozen=True)
class Phase:
    number: int
    task_ids: tuple[str, ...]
    work_items: tuple[dict, ...]
    mode: str
    reasoning_by_task: tuple[tuple[str, str], ...]


# Immutable status vocabulary used by independent host adapters.
CERTIFIED = "PHASE_VALIDATED_PENDING_NEXT_PHASE"
TERMINAL = "TERMINAL_SUCCESS"
GATE = "HUMAN_GATE"
RECOVERY = "RECOVERY_REQUIRED"
QUOTA = "QUOTA_PAUSED"
PENDING = "PHASE_STAGED_AWAITING_TARGET_CERTIFICATION"


def validated_phases(work_items: Any, phase_plan: Any) -> tuple[Phase, ...]:
    """Preserve the Coordinator's phase/mode/effort decisions, without replanning.

    Reject invalid dependencies or parallel conflicts *before* any model turn.
    Never guess phases, choose a worker count, or adjust reasoning here.
    """
    if type(work_items) is not list or not 1 <= len(work_items) <= MAX_ITEMS:
        raise PhaseCycleError("Unbounded Coordinator work items")
    if type(phase_plan) is not list or not 1 <= len(phase_plan) <= MAX_PHASES:
        raise PhaseCycleError("No valid Coordinator phase plan")
    rows = [_validate_item(i) for i in work_items]
    by_id = {item["id"]: item for item in rows}
    if len(by_id) != len(rows):
        raise PhaseCycleError("Duplicate work-item identity")
    if any(item["id"] in item["depends_on"] or
           not set(item["depends_on"]) <= set(by_id) for item in rows):
        raise PhaseCycleError("Unknown or self dependency")
    done: set[str] = set()
    phases: list[Phase] = []
    for idx, raw in enumerate(phase_plan, 1):
        if (type(raw) is not dict or
                set(raw) != {"task_ids", "mode", "reasoning_by_task"}):
            raise PhaseCycleError("Malformed Coordinator phase identity")
        ids = raw["task_ids"]
        mode = raw["mode"]
        efforts = raw["reasoning_by_task"]
        if (type(ids) is not list or not 1 <= len(ids) <= 2 or
                any(type(x) is not str or x not in by_id or x in done for x in ids) or
                len(set(ids)) != len(ids) or
                mode not in ({"single"} if len(ids) == 1 else {"serial", "parallel"}) or
                type(efforts) is not dict or set(efforts) != set(ids) or
                any(level not in ("low", "medium", "high") for level in efforts.values())):
            raise PhaseCycleError("Unsafe Coordinator phase mode, task or reasoning")
        current = [by_id[x] for x in ids]
        if mode == "parallel" and (
                any(set(item["depends_on"]).intersection(ids) for item in current) or
                _has_overlap(current[0], current[1])):
            raise PhaseCycleError("Overlapping or dependent parallel workers")
        within = set(done)
        for item in current:
            if not set(item["depends_on"]) <= within:
                raise PhaseCycleError("A predecessor phase has not been certified")
            if mode == "serial":
                within.add(item["id"])
        phases.append(Phase(idx, tuple(ids),
                            tuple({**item, "depends_on": []} for item in current),
                            mode, tuple((identifier, efforts[identifier]) for identifier in ids)))
        done.update(ids)
    if done != set(by_id):
        raise PhaseCycleError("Coordinator omitted preplanned work")
    return tuple(phases)


def phases_from_planner(planned: Mapping[str, Any]) -> list[dict]:
    """Translate the scoped Coordinator plan to the existing host runtime.

    Preserve each original task and its per-task reasoning. The existing
    validated_phases() enforces scope, dependencies and disjointness before
    any worker may start. Nothing here invokes a model or grants approval.
    """
    if (not isinstance(planned, Mapping) or
            planned.get("status") != "planned" or
            planned.get("continuation_policy") !=
            "CONTINUE_ALL_AUTHORIZED_PHASES_AFTER_VALIDATION"):
        raise PhaseCycleError("The original scoped Coordinator plan is required")
    flat = planned.get("phase_plan")
    mode = planned.get("mode")
    if (type(flat) is not list or not 1 <= len(flat) <= MAX_PHASES
            or mode not in ("single", "serial", "parallel")):
        raise PhaseCycleError("Missing bounded phase/mode information")
    if any(
        type(item) is not dict or
        set(item) != {"sequence", "id", "depends_on", "paths", "reasoning_effort"} or
        item.get("sequence") != i + 1 or
        type(item.get("id")) is not str or
        item.get("reasoning_effort") not in ("low", "medium", "high")
        for i, item in enumerate(flat)
    ):
        raise PhaseCycleError("Malformed or reordered Coordinator phases")
    result: list[dict] = []
    step = 2 if mode == "parallel" else 1
    for start in range(0, len(flat), step):
        batch = flat[start:start + step]
        ids = [item["id"] for item in batch]
        result.append({
            "task_ids": ids,
            "mode": "parallel" if len(ids) == 2 else "single",
            "reasoning_by_task": {
                item["id"]: item["reasoning_effort"] for item in batch
            },
        })
    return result


def phase_plan_digest(phases: tuple[Phase, ...]) -> str:
    """Bind a resumed checkpoint to exact original phase identities and scopes."""
    raw = json.dumps([asdict(phase) for phase in phases], sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def execute_until_terminal(
    phases: tuple[Phase, ...], *,
    checked_head: Callable[[], str],
    run_phase: Callable[[Phase, str], Mapping[str, Any]],
    certify_phase: Callable[[Phase, Mapping[str, Any], str], Mapping[str, Any]],
    notify: Callable[[Mapping[str, Any]], None] | None = None,
    resume_checkpoint: Mapping[str, Any] | None = None,
    verify_resume: Callable[[tuple[Phase, ...], Mapping[str, Any], str], bool] | None = None,
) -> dict:
    """Continue without another Owner prompt only after independent certification.

    Any error, partial result, material gate, skipped/pending CI, quota pause or
    unverifiable outcome stops the ENTIRE operation, never just one worker.
    The host may later resume from a separately validated durable checkpoint;
    replaying a phase on an ambiguous write is not allowed here. A resume
    requires the original plan digest, current certified target HEAD and a
    trusted host verifier that independently checks ALL preceding phases.
    """
    if (type(phases) is not tuple or not 1 <= len(phases) <= MAX_PHASES or
            not all(isinstance(p, Phase) and p.number == index + 1
                    for index, p in enumerate(phases)) or
            not callable(checked_head) or not callable(run_phase) or
            not callable(certify_phase) or
            (notify is not None and not callable(notify))):
        raise PhaseCycleError("No authorized, bounded host phase operation")
    before = checked_head()
    if type(before) is not str or not SHA.fullmatch(before):
        raise PhaseCycleError("Unverified initial target revision")
    # A former CI wait never authorizes rerunning an already-published phase.
    # The host must derive this checkpoint from its original authenticated
    # order and externally certified integration record, not a worker report.
    start_index = 0
    if resume_checkpoint is not None:
        checkpoint = resume_checkpoint
        if (not isinstance(checkpoint, Mapping) or
                set(checkpoint) != {"completed_phase", "accepted_sha",
                                    "plan_digest", "status", "exact_ci",
                                    "independent_review", "material_gate"} or
                type(checkpoint["completed_phase"]) is not int or
                not 1 <= checkpoint["completed_phase"] < len(phases) or
                checkpoint["status"] != "PHASE_CERTIFIED" or
                checkpoint["accepted_sha"] != before or
                checkpoint["plan_digest"] != phase_plan_digest(phases) or
                checkpoint["exact_ci"] is not True or
                checkpoint["independent_review"] is not True or
                checkpoint["material_gate"] is not False or
                not callable(verify_resume)):
            raise PhaseCycleError("Resume lacks exact independently certified checkpoint")
        try:
            externally_verified = verify_resume(phases, checkpoint, before)
        except Exception as exc:
            raise PhaseCycleError("External checkpoint verification failed") from exc
        if externally_verified is not True or checked_head() != before:
            raise PhaseCycleError("External checkpoint not certified at current HEAD")
        start_index = checkpoint["completed_phase"]
    elif verify_resume is not None:
        raise PhaseCycleError("Unused resume verifier without original checkpoint")

    records: list[dict] = []
    observer_failures = 0

    def emit(record: dict) -> None:
        records.append(record)
        # The observer reports only; it cannot authorize work or dispatch.
        nonlocal observer_failures
        if notify is not None:
            try:
                notify({k: v for k, v in record.items() if k in
                        {"phase", "status", "target_sha", "reason", "task_ids"}})
            except Exception:
                # Passive Supervisor delivery failures are observable, but
                # cannot issue commands or grant/withdraw execution authority.
                observer_failures += 1

    for phase in phases[start_index:]:
        if checked_head() != before:
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": RECOVERY, "reason": "BASE_REVISION_DRIFT"})
            return {"status": RECOVERY, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        try:
            outcome = run_phase(phase, before)
        except Exception:
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": RECOVERY, "reason": "EXECUTOR_FAILED"})
            return {"status": RECOVERY, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        if (not isinstance(outcome, Mapping) or
                outcome.get("status") != "WORKERS_COMPLETED" or
                not isinstance(outcome.get("worker_ids"), (list, tuple)) or
                not 1 <= len(outcome["worker_ids"]) <= 2 or
                any(type(w) is not str or not w for w in outcome["worker_ids"])):
            status = (outcome.get("status") if isinstance(outcome, Mapping) else None)
            reason = "QUOTA_PAUSED" if status == QUOTA else "WORKER_NOT_CERTIFIED"
            state = QUOTA if status == QUOTA else RECOVERY
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": state, "reason": reason})
            return {"status": state, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        try:
            certification = certify_phase(phase, outcome, before)
        except Exception:
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": RECOVERY, "reason": "CERTIFIER_FAILED"})
            return {"status": RECOVERY, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        if not isinstance(certification, Mapping):
            certification = {}
        status = certification.get("status")
        if status in (GATE, QUOTA, PENDING, RECOVERY):
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": status, "reason": "INDEPENDENT_PHASE_HOLD"})
            return {"status": status, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        new_head = certification.get("accepted_sha")
        if (status != "PHASE_CERTIFIED" or type(new_head) is not str or
                not SHA.fullmatch(new_head) or
                new_head != checked_head() or
                certification.get("exact_ci") is not True or
                certification.get("independent_review") is not True or
                certification.get("material_gate") is not False):
            emit({"phase": phase.number, "task_ids": phase.task_ids,
                  "status": RECOVERY, "reason": "EXACT_CI_OR_REVIEW_NOT_VERIFIED"})
            return {"status": RECOVERY, "phases": records, "next_phase": phase.number,
                    "observer_failures": observer_failures}
        before = new_head
        emit({"phase": phase.number, "task_ids": phase.task_ids,
              "target_sha": before,
              "status": CERTIFIED if phase.number < len(phases) else TERMINAL})
    return {"status": TERMINAL, "phases": records, "next_phase": None,
            "target_sha": before, "observer_failures": observer_failures}