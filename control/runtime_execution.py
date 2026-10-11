"""Observable execution helpers for Project Leader behavioral acceptance.

This module does not replace the host agent or GitHub connector. It supplies a
small adapter contract around the failure-sensitive parts that must be testable:
bounded reconstruction, internal liveness, CI reconciliation, and verification
before/after an ambiguous external write.
"""

from dataclasses import dataclass, field

from control.managed_project_contract import reconcile_external_ci_liveness

INTERNAL_OPERATION_ACTIVE = "INTERNAL_OPERATION_ACTIVE"
INTERNAL_OPERATION_STALLED = "INTERNAL_OPERATION_STALLED"
LIVENESS_RECONCILE_REQUIRED = "LIVENESS_RECONCILE_REQUIRED"

EFFECT_APPLIED = "EFFECT_APPLIED"
EFFECT_ALREADY_APPLIED = "EFFECT_ALREADY_APPLIED"
AMBIGUOUS_WRITE_RECONCILED = "AMBIGUOUS_WRITE_RECONCILED"


@dataclass
class ExecutionTrace:
    events: list = field(default_factory=list)

    def record(self, event, **detail):
        entry = {"event": event, **detail}
        self.events.append(entry)
        return entry


def bounded_state_preflight(
    read_default_head,
    read_open_prs,
    read_active_runs,
    read_task_head=None,
    *,
    trace=None,
):
    """Read only the minimum durable state vector used before broad discovery."""
    trace = trace or ExecutionTrace()
    state = {}

    trace.record("READ_DEFAULT_HEAD")
    state["default_head"] = read_default_head()

    trace.record("READ_OPEN_PRS")
    state["open_prs"] = read_open_prs()

    trace.record("READ_ACTIVE_RUNS")
    state["active_runs"] = read_active_runs()

    if read_task_head is not None:
        trace.record("READ_TASK_HEAD")
        state["task_head"] = read_task_head()

    trace.record("BOUNDED_STATE_PREFLIGHT_COMPLETE")
    return state, trace


def reconcile_internal_operation(
    *,
    prior_progress_token,
    current_progress_token,
    prior_stall_observations,
    stall_limit=2,
    trace=None,
):
    """Turn repeated no-progress observations into an explicit Recovery route."""
    if not isinstance(prior_stall_observations, int) or isinstance(
        prior_stall_observations, bool
    ):
        raise ValueError("prior_stall_observations must be an integer")
    if prior_stall_observations < 0:
        raise ValueError("prior_stall_observations must be non-negative")
    if not isinstance(stall_limit, int) or isinstance(stall_limit, bool) or stall_limit < 1:
        raise ValueError("stall_limit must be a positive integer")

    trace = trace or ExecutionTrace()
    if current_progress_token != prior_progress_token:
        trace.record("INTERNAL_PROGRESS_OBSERVED")
        return {
            "state": INTERNAL_OPERATION_ACTIVE,
            "route": "CONTINUE",
            "stall_observations": 0,
            "trace": trace.events,
        }

    observations = prior_stall_observations + 1
    if observations >= stall_limit:
        trace.record(
            INTERNAL_OPERATION_STALLED,
            stall_observations=observations,
        )
        trace.record(LIVENESS_RECONCILE_REQUIRED)
        return {
            "state": INTERNAL_OPERATION_STALLED,
            "route": LIVENESS_RECONCILE_REQUIRED,
            "stall_observations": observations,
            "trace": trace.events,
        }

    trace.record("INTERNAL_NO_PROGRESS_OBSERVED", stall_observations=observations)
    return {
        "state": INTERNAL_OPERATION_ACTIVE,
        "route": "OBSERVE_AGAIN",
        "stall_observations": observations,
        "trace": trace.events,
    }


def execute_verified_effect(
    operation_key,
    observe_effect,
    perform_effect,
    *,
    trace=None,
):
    """Execute one effect with observe-before-write and reconcile-on-error semantics.

    observe_effect(operation_key) must return True only when durable external
    state proves that the intended effect already happened. A raised write error
    is ambiguous until the effect is observed again.
    """
    if not isinstance(operation_key, str) or not operation_key:
        raise ValueError("operation_key must be a non-empty string")
    trace = trace or ExecutionTrace()

    trace.record("OBSERVE_EFFECT_BEFORE", operation_key=operation_key)
    before = observe_effect(operation_key)
    if not isinstance(before, bool):
        raise ValueError("observe_effect must return boolean")
    if before:
        trace.record(EFFECT_ALREADY_APPLIED, operation_key=operation_key)
        return {
            "state": EFFECT_ALREADY_APPLIED,
            "performed": False,
            "trace": trace.events,
        }

    trace.record("PERFORM_EFFECT", operation_key=operation_key)
    try:
        perform_effect(operation_key)
    except Exception as exc:
        trace.record(
            "WRITE_RESPONSE_AMBIGUOUS",
            operation_key=operation_key,
            error_type=type(exc).__name__,
        )
        trace.record("OBSERVE_EFFECT_AFTER_ERROR", operation_key=operation_key)
        after_error = observe_effect(operation_key)
        if not isinstance(after_error, bool):
            raise ValueError("observe_effect must return boolean") from exc
        if after_error:
            trace.record(AMBIGUOUS_WRITE_RECONCILED, operation_key=operation_key)
            return {
                "state": AMBIGUOUS_WRITE_RECONCILED,
                "performed": True,
                "trace": trace.events,
            }
        raise

    trace.record("OBSERVE_EFFECT_AFTER_WRITE", operation_key=operation_key)
    after = observe_effect(operation_key)
    if not isinstance(after, bool):
        raise ValueError("observe_effect must return boolean")
    if not after:
        raise RuntimeError("write returned success but durable effect is not observable")

    trace.record(EFFECT_APPLIED, operation_key=operation_key)
    return {
        "state": EFFECT_APPLIED,
        "performed": True,
        "trace": trace.events,
    }


def run_external_ci_cycle(
    bound_run_ids,
    read_live_runs,
    *,
    previous_state="WAITING_EXTERNAL_CI",
    last_progress_at=None,
    now=None,
    trace=None,
):
    """Perform one observable CI liveness cycle without dispatching replacement CI."""
    trace = trace or ExecutionTrace()
    trace.record("READ_BOUND_CI_RUNS", run_ids=list(bound_run_ids))
    live_runs = read_live_runs(list(bound_run_ids))
    if not isinstance(live_runs, list):
        raise ValueError("read_live_runs must return a list")

    state = reconcile_external_ci_liveness(
        list(bound_run_ids),
        live_runs,
        previous_state=previous_state,
        last_progress_at=last_progress_at,
        now=now,
    )
    trace.record("CI_RECONCILED", state=state["state"], route=state["route"])
    state = dict(state)
    state["trace"] = trace.events
    return state
