#!/usr/bin/env python3
import hashlib
import re
from datetime import datetime, timezone
from fnmatch import fnmatchcase

from control.validate_records import validate_checkpoint, validate_pair, validate_project_policy, validate_result, validate_scope, validate_task
from control.scope_policy import scope_pattern_is_bounded, scope_pattern_is_within

RUNTIME_CONTRACT_VERSION = 1
MIN_LOADER_VERSION = 1
PINNED_RUNTIME_STATE = "RUNTIME_CANONICAL_PINNED"
RUNTIME_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

NEW_TASK_SCHEMA_VERSION = "2.0"
WORKER_RESULT_SCHEMA_VERSION = "2.0"
RECOVERY_MODE = "APPEND_ONLY_V1"
CI_WAIT_STATE = "WAITING_EXTERNAL_CI"
CI_STALE_WAIT_STATE = "STALE_WAIT_STATE"
CI_LIVENESS_RECONCILE_REQUIRED = "LIVENESS_RECONCILE_REQUIRED"
CI_ROUTE_WAIT = "WAIT"
CI_ROUTE_CONTINUE = "AUDIT_CONTINUE"
CI_ROUTE_RECOVERY = "RECOVERY"
CI_ROUTE_INVESTIGATE = "INVESTIGATE"
POLICY_BINDING_MODE = "CENTRAL_CONTROL_V1"
GENERIC_POLICY_PATH = "control/generic-project-policy.json"
INTEGRITY_MODE = "IMMUTABLE_AUTHORIZATION_V1"
CONTROL_MODE_FAST_E1 = "FAST_E1"
CONTROL_MODE_DURABLE = "DURABLE_CONTROL"
E1_EFFECT_CLASS = "E1_RECOVERABLE_PROJECT_LOCAL"
FAST_E1_ROUTE = "EXECUTE_TEST_CORRECT_HYGIENIZE_VALIDATE_CONTINUE"
MATERIAL_CONTROL_ROUTE = "MATERIAL_CONTROL"
DIAGNOSIS_BUYS_DECISION = "DIAGNOSIS_BUYS_DECISION"
PROBE_NO_DECISION_VALUE = "PROBE_NO_DECISION_VALUE"
REGRESSION_FIRST = "REGRESSION_FIRST"
DIRECT_ROOT_CAUSE = "DIRECT_ROOT_CAUSE"
SAFE_ROLLBACK = "SAFE_ROLLBACK"
FAST_VALIDATION_BEFORE_FULL_VALIDATION = "FAST_VALIDATION_BEFORE_FULL_VALIDATION"
FOCUSED_VALIDATION = "FOCUSED_VALIDATION"
FULL_VALIDATION = "FULL_VALIDATION"
FINAL_EXACT_STATE_CERTIFICATION = "FINAL_EXACT_STATE_CERTIFICATION"
MATERIAL_VALIDATION_UNCHANGED = "MATERIAL_VALIDATION_UNCHANGED"
SUPERSEDED_WORK_AUTO_CANCEL = "SUPERSEDED_WORK_AUTO_CANCEL"
SUPERSEDED = "SUPERSEDED"
KEEP_RUNNING = "KEEP_RUNNING"
CANCEL_AND_HYGIENIZE = "CANCEL_AND_HYGIENIZE"
FIRST_SUFFICIENT_SAFE_PASS_STOP = "FIRST_SUFFICIENT_SAFE_PASS_STOP"
CONTINUE_REQUIRED = "CONTINUE_REQUIRED"
DEFAULT_POLL_INTERVAL_MINUTES = 5
DEFAULT_STALE_AFTER_MINUTES = 60
DEFAULT_LIVENESS_NO_PROGRESS_POLLS = 2
ACCESS_DISCOVERY_REQUIRED_SURFACES = (
    "direct_session_capabilities",
    "native_tool_capability_inventory",
    "target_repository_automation",
    "operational_repository_discovery",
    "existing_access_history",
)
ACCESS_DISCOVERY_INCOMPLETE = "ACCESS_DISCOVERY_INCOMPLETE"
ACCESS_PATH_FOUND = "ACCESS_PATH_FOUND"
ACCESS_PATH_REQUIRES_SEPARATE_TASK = "ACCESS_PATH_REQUIRES_SEPARATE_TASK"
ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION = "ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION"
ACCESS_PATH_UNAVAILABLE = "ACCESS_PATH_UNAVAILABLE"
ACCESS_ROUTE_CONTINUE = "CONTINUE"
ACCESS_ROUTE_DISCOVER = "CONTINUE_DISCOVERY"
ACCESS_ROUTE_BOUND_TASK = "BOUND_OPERATIONS_TASK"
ACCESS_ROUTE_AUTHORITY = "SUPERVISOR_AUTHORITY_RESOLUTION"
ACCESS_ROUTE_HUMAN_GATE_CANDIDATE = "HUMAN_GATE_CANDIDATE"
NONINTERACTIVE_DIAGNOSTIC_REQUIRED_SURFACES = (
    "native_tool_capability_inventory",
    "workflow_run_metadata",
    "workflow_jobs_steps_logs",
    "workflow_artifacts_checks_annotations",
    "repository_return_path",
    "historical_diagnostic_evidence",
)
SELF_PROVISION_DIAGNOSTIC_SURFACE = "self_provisioned_diagnostic_bridge"
NONINTERACTIVE_FALLBACK_INCOMPLETE = "NONINTERACTIVE_FALLBACK_INCOMPLETE"
NONINTERACTIVE_PATH_FOUND = "NONINTERACTIVE_PATH_FOUND"
DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK = "DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK"
DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION = "DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION"
NONINTERACTIVE_FALLBACK_EXHAUSTED = "NONINTERACTIVE_FALLBACK_EXHAUSTED"
PLATFORM_CONSENT_REQUIRED = "PLATFORM_CONSENT_REQUIRED"
NONINTERACTIVE_ROUTE_DISCOVER = "CONTINUE_DIAGNOSTIC_DISCOVERY"
NONINTERACTIVE_ROUTE_CONTINUE = "CONTINUE_DIAGNOSTIC"
NONINTERACTIVE_ROUTE_BOUND_BRIDGE = "BOUND_DIAGNOSTIC_BRIDGE_TASK"
NONINTERACTIVE_ROUTE_AUTHORITY = "SUPERVISOR_AUTHORITY_RESOLUTION"
NONINTERACTIVE_ROUTE_REENTER_ACCESS = "REENTER_ACCESS_DISCOVERY"
LEGACY_ACTIVE_CORROBORATED = "LEGACY_ACTIVE_CORROBORATED"
STALE_LEGACY_CHECKPOINT = "STALE_LEGACY_CHECKPOINT"
LEGACY_CHECKPOINT_TERMINAL = "LEGACY_CHECKPOINT_TERMINAL"
CI_DISPATCH_REQUIRED = "DISPATCH_REQUIRED"
CI_REUSE_ACTIVE = "REUSE_ACTIVE_RUN"
CI_REUSE_SUCCESS = "REUSE_SUCCESSFUL_RUN"
CI_DISPATCH_ROUTE_RECOVERY = "ROUTE_RECOVERY"
POST_CI_DESCENDANT_EVIDENCE_ONLY = "EVIDENCE_ONLY_DESCENDANT"
POST_CI_DESCENDANT_MATERIAL = "MATERIAL_DESCENDANT"
POST_CI_ROUTE_CERTIFICATION_UNCHANGED = "CERTIFICATION_UNCHANGED"
POST_CI_ROUTE_FINAL_HEAD_GOVERNANCE = "FINAL_HEAD_GOVERNANCE_CHECK"
POST_CI_ROUTE_FRESH_IMPLEMENTATION = "FRESH_IMPLEMENTATION_CI"

CI_ACTIVE_STATUSES = {"queued", "waiting", "pending", "requested", "in_progress"}
CI_TERMINAL_CONCLUSIONS = {
    "success", "failure", "cancelled", "timed_out", "action_required",
    "neutral", "skipped", "stale", "startup_failure",
}


def _require_strict_bool(value, label):
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be boolean")
    return value


def _require_positive_int(value, label):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _validate_ci_run_payload(run, *, require_timestamp=False):
    if not isinstance(run, dict):
        raise ValueError("CI run payload must be an object")
    _require_positive_int(run.get("id"), "CI run id")
    status = run.get("status")
    if status not in CI_ACTIVE_STATUSES | {"completed"}:
        raise ValueError(f"CI run has unsupported status: {status!r}")
    if status == "completed":
        conclusion = run.get("conclusion")
        if not isinstance(conclusion, str) or conclusion not in CI_TERMINAL_CONCLUSIONS:
            raise ValueError("completed CI run requires a recognized conclusion")
    timestamps = [
        run.get("created_at"),
        run.get("run_started_at"),
        run.get("updated_at"),
    ]
    present = [value for value in timestamps if value is not None]
    if require_timestamp and not present:
        raise ValueError("CI run requires at least one progress timestamp")
    for value in present:
        if not isinstance(value, str) or not value:
            raise ValueError("CI run timestamps must be non-empty strings")
        parsed = _parse_time(value)
        if parsed is None or parsed.tzinfo is None:
            raise ValueError("CI run timestamps must be offset-aware ISO timestamps")
    return True


def resolve_control_mode(
    effect_class,
    *,
    destructive=False,
    privileged=False,
    architecture_change=False,
    product_decision=False,
    permission_change=False,
    external_effect=False,
    irreversible=False,
    ambiguous_write_replay_risk=False,
    context_loss_duplication_risk=False,
    durable_audit_required=False,
):
    """Choose the lightest control mode that still protects a material boundary."""
    if not isinstance(effect_class, str) or not effect_class:
        raise ValueError("effect_class must be a non-empty string")
    flags = {
        "destructive": destructive,
        "privileged": privileged,
        "architecture_change": architecture_change,
        "product_decision": product_decision,
        "permission_change": permission_change,
        "external_effect": external_effect,
        "irreversible": irreversible,
        "ambiguous_write_replay_risk": ambiguous_write_replay_risk,
        "context_loss_duplication_risk": context_loss_duplication_risk,
        "durable_audit_required": durable_audit_required,
    }
    for label, value in flags.items():
        _require_strict_bool(value, label)

    material_boundary = any(flags.values())
    if effect_class == E1_EFFECT_CLASS and not material_boundary:
        return {
            "mode": CONTROL_MODE_FAST_E1,
            "durable_records_required": False,
            "route": FAST_E1_ROUTE,
        }
    return {
        "mode": CONTROL_MODE_DURABLE,
        "durable_records_required": True,
        "route": MATERIAL_CONTROL_ROUTE,
    }


def resolve_validation_sequence(
    effect_class,
    *,
    focused_validation_relevant=True,
    full_validation_required=True,
    security_or_certification_required=False,
):
    """Run the smallest useful E1 validation first without weakening final certification."""
    if not isinstance(effect_class, str) or not effect_class:
        raise ValueError("effect_class must be a non-empty string")
    for label, value in {
        "focused_validation_relevant": focused_validation_relevant,
        "full_validation_required": full_validation_required,
        "security_or_certification_required": security_or_certification_required,
    }.items():
        _require_strict_bool(value, label)

    effective_full_validation = (
        full_validation_required or security_or_certification_required
    )
    steps = []
    if effect_class == E1_EFFECT_CLASS and focused_validation_relevant:
        steps.append(FOCUSED_VALIDATION)
    if effective_full_validation:
        steps.append(FULL_VALIDATION)
    steps.append(FINAL_EXACT_STATE_CERTIFICATION)

    return {
        "rule": FAST_VALIDATION_BEFORE_FULL_VALIDATION,
        "route": (
            FAST_VALIDATION_BEFORE_FULL_VALIDATION
            if effect_class == E1_EFFECT_CLASS
            else MATERIAL_VALIDATION_UNCHANGED
        ),
        "steps": steps,
        "full_validation_required": effective_full_validation,
        "final_exact_state_required": True,
    }



def resolve_e1_validation_preflight(
    effect_class,
    *,
    candidate_revision,
    focused_revision=None,
    focused_status="NOT_RUN",
    focused_validation_relevant=True,
    focused_validation_available=True,
):
    """Route normal E1 through cheap exact-candidate checks before heavy CI.

    This is a scheduling decision, not authorization or a substitute for required
    full/security/regression validation and final exact-state certification.
    Candidate revisions may be commit SHAs or fingerprints of uncommitted changes.
    """
    if not isinstance(effect_class, str) or not effect_class:
        raise ValueError("effect_class must be a non-empty string")
    if not isinstance(candidate_revision, str) or not candidate_revision.strip():
        raise ValueError("candidate_revision must be a non-empty string")
    if focused_revision is not None and (
        not isinstance(focused_revision, str) or not focused_revision.strip()
    ):
        raise ValueError("focused_revision must be non-empty when supplied")
    if focused_status not in ("NOT_RUN", "PASS", "FAIL"):
        raise ValueError("focused_status must be NOT_RUN, PASS, or FAIL")
    _require_strict_bool(focused_validation_relevant, "focused_validation_relevant")
    _require_strict_bool(focused_validation_available, "focused_validation_available")

    if effect_class != E1_EFFECT_CLASS:
        return {
            "route": MATERIAL_VALIDATION_UNCHANGED,
            "reason": "MATERIAL_CONTROLS_UNCHANGED",
        }
    if not focused_validation_relevant:
        return {"route": FULL_VALIDATION, "reason": "FOCUSED_NOT_RELEVANT"}
    if not focused_validation_available:
        return {"route": FULL_VALIDATION, "reason": "FOCUSED_UNAVAILABLE"}
    if focused_revision != candidate_revision or focused_status == "NOT_RUN":
        return {"route": FOCUSED_VALIDATION, "reason": "FOCUSED_EVIDENCE_NOT_CURRENT"}
    if focused_status == "FAIL":
        return {"route": "RECOVERY_DIRECT_REPAIR", "reason": "FOCUSED_FAILURE"}
    return {"route": FULL_VALIDATION, "reason": "FOCUSED_PASSED"}


def classify_superseded_work(
    effect_class,
    *,
    work_revision,
    current_revision,
    heavy_work=True,
    can_certify_current_state=False,
    can_change_technical_decision=False,
    exclusive_diagnostic_evidence_needed=False,
    cancellation_safe=False,
):
    """Cancel only obsolete E1 heavy work that no longer contributes certification, decisions, or diagnosis."""
    if not isinstance(effect_class, str) or not effect_class:
        raise ValueError("effect_class must be a non-empty string")
    for label, value in {
        "work_revision": work_revision,
        "current_revision": current_revision,
    }.items():
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")
    for label, value in {
        "heavy_work": heavy_work,
        "can_certify_current_state": can_certify_current_state,
        "can_change_technical_decision": can_change_technical_decision,
        "exclusive_diagnostic_evidence_needed": exclusive_diagnostic_evidence_needed,
        "cancellation_safe": cancellation_safe,
    }.items():
        _require_strict_bool(value, label)

    if effect_class != E1_EFFECT_CLASS:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "MATERIAL_CONTROL_UNCHANGED",
            "action": KEEP_RUNNING,
            "reason": "MATERIAL_CONTROL_UNCHANGED",
        }
    if work_revision == current_revision:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "CURRENT",
            "action": KEEP_RUNNING,
            "reason": "CURRENT_REVISION",
        }
    if not heavy_work:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "OBSOLETE_BUT_LIGHTWEIGHT",
            "action": KEEP_RUNNING,
            "reason": "NOT_HEAVY_WORK",
        }
    if can_certify_current_state:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "STILL_RELEVANT",
            "action": KEEP_RUNNING,
            "reason": "CAN_STILL_CERTIFY_CURRENT_STATE",
        }
    if can_change_technical_decision:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "STILL_RELEVANT",
            "action": KEEP_RUNNING,
            "reason": "TECHNICAL_DECISION_STILL_RELEVANT",
        }
    if exclusive_diagnostic_evidence_needed:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "STILL_RELEVANT",
            "action": KEEP_RUNNING,
            "reason": "EXCLUSIVE_DIAGNOSTIC_EVIDENCE_REQUIRED",
        }
    if not cancellation_safe:
        return {
            "rule": SUPERSEDED_WORK_AUTO_CANCEL,
            "state": "STALE_BUT_NOT_SAFE_TO_CANCEL",
            "action": KEEP_RUNNING,
            "reason": "CANCELLATION_NOT_SAFE",
        }
    return {
        "rule": SUPERSEDED_WORK_AUTO_CANCEL,
        "state": SUPERSEDED,
        "action": CANCEL_AND_HYGIENIZE,
        "reason": SUPERSEDED_WORK_AUTO_CANCEL,
    }


def resolve_terminal_action(
    *,
    objective_met,
    acceptance_criteria_met,
    mandatory_regressions_green,
    mandatory_full_validation_passed,
    exact_state_certified,
    hygiene_complete,
    no_known_regression,
    no_remaining_required_work,
):
    """Stop at the first sufficient safe pass instead of expanding into optional work."""
    checks = {
        "objective_met": objective_met,
        "acceptance_criteria_met": acceptance_criteria_met,
        "mandatory_regressions_green": mandatory_regressions_green,
        "mandatory_full_validation_passed": mandatory_full_validation_passed,
        "exact_state_certified": exact_state_certified,
        "hygiene_complete": hygiene_complete,
        "no_known_regression": no_known_regression,
        "no_remaining_required_work": no_remaining_required_work,
    }
    for label, value in checks.items():
        _require_strict_bool(value, label)

    missing = [label for label, value in checks.items() if not value]
    if missing:
        return {
            "decision": CONTINUE_REQUIRED,
            "missing": missing,
            "execute_optional_work": False,
        }
    return {
        "decision": FIRST_SUFFICIENT_SAFE_PASS_STOP,
        "missing": [],
        "execute_optional_work": False,
    }


def evaluate_diagnostic_probe(question, hypotheses, outcome_actions):
    """Only spend diagnostic effort when an observation can change the next action."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("diagnostic question must be a non-empty string")
    if (
        not isinstance(hypotheses, list)
        or len(hypotheses) < 2
        or not all(isinstance(item, str) and item for item in hypotheses)
        or len(set(hypotheses)) != len(hypotheses)
    ):
        raise ValueError("hypotheses must contain at least two unique non-empty strings")
    if not isinstance(outcome_actions, dict) or set(outcome_actions) != set(hypotheses):
        raise ValueError("outcome_actions must map every hypothesis exactly once")
    actions = list(outcome_actions.values())
    if not all(isinstance(item, str) and item for item in actions):
        raise ValueError("diagnostic outcome actions must be non-empty strings")

    buys_decision = len(set(actions)) > 1
    return {
        "execute_probe": buys_decision,
        "reason": DIAGNOSIS_BUYS_DECISION if buys_decision else PROBE_NO_DECISION_VALUE,
        "question": question.strip(),
    }


def resolve_regression_strategy(
    *,
    last_known_good=None,
    first_known_bad=None,
    recent_change=False,
    regression_confirmed=False,
    recoverable_change=True,
    produced_unique_value=False,
    boundary_crossed=False,
):
    """Prioritize causal regression analysis and safe rollback before new theory growth."""
    for label, value in {
        "recent_change": recent_change,
        "regression_confirmed": regression_confirmed,
        "recoverable_change": recoverable_change,
        "produced_unique_value": produced_unique_value,
        "boundary_crossed": boundary_crossed,
    }.items():
        _require_strict_bool(value, label)
    for label, value in {
        "last_known_good": last_known_good,
        "first_known_bad": first_known_bad,
    }.items():
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{label} must be a non-empty string when provided")

    if (
        regression_confirmed
        and recoverable_change
        and not produced_unique_value
        and not boundary_crossed
    ):
        return {
            "decision": SAFE_ROLLBACK,
            "compare": [last_known_good, first_known_bad],
        }
    if recent_change and last_known_good and first_known_bad:
        return {
            "decision": REGRESSION_FIRST,
            "compare": [last_known_good, first_known_bad],
        }
    return {"decision": DIRECT_ROOT_CAUSE, "compare": []}


def validate_loader_version(loader_version):
    if not isinstance(loader_version, int) or isinstance(loader_version, bool):
        raise ValueError("loader_version must be an integer")
    if loader_version < MIN_LOADER_VERSION:
        raise ValueError(
            f"loader version {loader_version} is incompatible; "
            f"minimum is {MIN_LOADER_VERSION}"
        )
    return True


def pin_runtime_bundle(resolve_main_sha, read_at_revision, *, loader_version=1, paths=None):
    """Resolve canonical main once and read one coherent contract generation."""
    validate_loader_version(loader_version)
    revision = resolve_main_sha()
    if not isinstance(revision, str) or RUNTIME_SHA_RE.fullmatch(revision) is None:
        raise ValueError("canonical main resolver must return an exact 40-hex commit SHA")

    selected_paths = tuple(paths or ())
    if not selected_paths:
        raise ValueError("runtime bundle requires at least one contract path")
    if len(selected_paths) != len(set(selected_paths)):
        raise ValueError("runtime bundle paths must be unique")

    files = {}
    for path in selected_paths:
        if not isinstance(path, str) or not path or path.startswith("/"):
            raise ValueError(f"invalid runtime contract path: {path!r}")
        files[path] = read_at_revision(path, revision)

    return {
        "state": PINNED_RUNTIME_STATE,
        "runtime_contract_version": RUNTIME_CONTRACT_VERSION,
        "loader_version": loader_version,
        "revision": revision,
        "files": files,
    }


def verify_pr_evidence_context(
    *,
    declared_changed_count,
    observed_changes,
    event_base_sha,
    live_base_sha,
    api_limit=3000,
):
    """Fail closed on truncated PR-file evidence or a stale trusted base."""
    if not isinstance(declared_changed_count, int) or isinstance(
        declared_changed_count, bool
    ):
        raise ValueError("declared_changed_count must be an integer")
    if declared_changed_count < 0:
        raise ValueError("declared_changed_count must be non-negative")
    if declared_changed_count >= api_limit:
        raise ValueError(
            f"PR changed-file evidence reached GitHub's {api_limit}-file limit "
            "and is not certifiable"
        )
    if declared_changed_count != len(observed_changes):
        raise ValueError(
            "PR changed-file evidence is incomplete: "
            f"declared={declared_changed_count} observed={len(observed_changes)}"
        )
    if event_base_sha != live_base_sha:
        raise ValueError(
            f"trusted gate base is stale: event={event_base_sha} live={live_base_sha}"
        )
    return True


def resolve_project_policy_path(explicit_policy_path=None):
    """Use a target-specific central policy when explicitly selected, otherwise the generic active-project policy."""
    return explicit_policy_path or GENERIC_POLICY_PATH


def validate_managed_task(task, repository, control_repository=None):
    validate_task(task)
    if task.get("schema_version") != NEW_TASK_SCHEMA_VERSION:
        raise ValueError("new managed-project mutation tasks must use Task Authorization v2")
    if task.get("repository") != repository:
        raise ValueError("managed task repository does not match active repository")
    if task.get("integrity_mode") != INTEGRITY_MODE:
        raise ValueError("new managed-project tasks must bind immutable authorization integrity")
    if (task.get("recovery") or {}).get("mode") != RECOVERY_MODE:
        raise ValueError("managed task recovery history must use APPEND_ONLY_V1")

    binding = task.get("policy") or {}
    if binding.get("binding_mode") != POLICY_BINDING_MODE:
        raise ValueError("managed-project tasks must use CENTRAL_CONTROL_V1 policy binding")
    if control_repository and binding.get("repository") != control_repository:
        raise ValueError("managed task policy repository does not match canonical control repository")

    required_ci = task.get("required_ci")
    if not isinstance(required_ci, list) or not all(isinstance(x, str) and x for x in required_ci):
        raise ValueError("managed task required_ci must be a list of non-empty workflow names")
    return True


def validate_managed_result(task, result, repository, control_repository=None):
    validate_managed_task(task, repository, control_repository)
    validate_pair(task, result)
    if result.get("schema_version") != WORKER_RESULT_SCHEMA_VERSION:
        raise ValueError("managed-project Worker Result must use schema v2")
    if result.get("task_id") != task.get("task_id"):
        raise ValueError("managed task/result task_id mismatch")
    if result.get("repository") != repository:
        raise ValueError("managed result repository does not match active repository")
    if not result.get("authorization_commit_sha") or not result.get("authorization_sha256"):
        raise ValueError("managed Worker Result must bind the exact Task Authorization commit and digest")
    if result.get("terminal_status") == "TERMINAL_SUCCESS":
        by_name = {item.get("name"): item for item in result.get("ci", [])}
        for name in task["required_ci"]:
            item = by_name.get(name)
            run_id = None if not item else item.get("run_id")
            if (
                not item
                or item.get("status") != "SUCCESS"
                or not isinstance(run_id, int)
                or isinstance(run_id, bool)
                or run_id <= 0
            ):
                raise ValueError(f"managed terminal success requires live CI run_id evidence for {name}")
    return True


def policy_sha256(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def _task_transition_actions(task):
    items = task.get("transition_controls") or task.get("human_gates") or []
    return {item["action"] for item in items}


def _policy_transition_actions(effect_policy):
    return set(
        effect_policy.get("required_transition_controls")
        or effect_policy.get("required_human_gates")
        or []
    )


def verify_managed_task_against_control_policy(
    task,
    policy,
    policy_raw,
    actual_target_base_sha,
    changed_files,
    control_repository,
    control_revision,
    expected_policy_path,
):
    validate_managed_task(task, task["repository"], control_repository)
    validate_project_policy(policy)

    if policy.get("repository_mode") == "ACTIVE_TARGET":
        pass
    elif task["repository"] != policy.get("repository"):
        raise ValueError("task repository does not match central policy repository")
    if task["starting_state"]["base_sha"] != actual_target_base_sha:
        raise ValueError("task starting_state.base_sha does not match actual target PR base SHA")

    binding = task["policy"]
    if binding["repository"] != control_repository:
        raise ValueError("task policy repository does not match canonical control repository")
    if binding["revision"] != control_revision:
        raise ValueError("task policy revision does not match the exact control-plane revision")
    selected_policy_path = resolve_project_policy_path(expected_policy_path)
    if binding["path"] != selected_policy_path:
        raise ValueError("task policy path does not match selected central policy path")
    if binding["profile"] != policy["policy_id"]:
        raise ValueError("task policy profile does not match central policy_id")
    if binding["sha256"] != policy_sha256(policy_raw):
        raise ValueError("task policy sha256 does not match exact central policy bytes")

    effect = task["effect_class"]
    effect_policy = policy["effect_policies"].get(effect)
    if not effect_policy:
        raise ValueError(f"central policy does not authorize effect class {effect}")

    protected = [
        path for path in changed_files
        if any(fnmatchcase(path, pattern) for pattern in policy["protected_paths"])
    ]
    if protected and effect != "E3_DESTRUCTIVE_EXTERNAL_PRIVILEGED":
        raise ValueError(
            "managed E1 task touches protected paths and requires a separate governance task: "
            + ", ".join(sorted(protected))
        )

    allowed_patterns = effect_policy["allowed_scope_patterns"]
    if policy.get("repository_mode") == "ACTIVE_TARGET":
        unbounded_patterns = sorted(
            pattern
            for pattern in task["mutation_scope"]
            if not scope_pattern_is_bounded(pattern)
        )
        if unbounded_patterns:
            raise ValueError(
                "generic active-target task must use literal-bounded mutation_scope patterns: "
                + ", ".join(unbounded_patterns)
            )

    widened_patterns = sorted(
        pattern
        for pattern in task["mutation_scope"]
        if not any(scope_pattern_is_within(pattern, allowed) for allowed in allowed_patterns)
    )
    if widened_patterns:
        raise ValueError("managed task mutation_scope exceeds central policy ceiling: " + ", ".join(widened_patterns))

    allowed_actions = set(effect_policy["allowed_actions"])
    widened_actions = sorted(set(task["allowed_actions"]) - allowed_actions)
    if widened_actions:
        raise ValueError("managed task allowed_actions exceeds central policy ceiling: " + ", ".join(widened_actions))

    missing_prohibitions = sorted(
        set(effect_policy["required_prohibited_actions"]) - set(task["prohibited_actions"])
    )
    if missing_prohibitions:
        raise ValueError("managed task is missing required prohibitions: " + ", ".join(missing_prohibitions))

    task_gates = _task_transition_actions(task)
    missing_gates = sorted(_policy_transition_actions(effect_policy) - task_gates)
    if missing_gates:
        raise ValueError("managed task is missing required consequential transition controls: " + ", ".join(missing_gates))

    missing_ci = sorted(set(effect_policy["required_ci"]) - set(task["required_ci"]))
    if missing_ci:
        raise ValueError("managed task required_ci is weaker than central policy: " + ", ".join(missing_ci))
    allowed_ci = effect_policy.get("allowed_ci")
    if allowed_ci is not None:
        unknown_ci = sorted(set(task["required_ci"]) - set(allowed_ci))
        if unknown_ci:
            raise ValueError("managed task required_ci contains workflows outside central policy: " + ", ".join(unknown_ci))

    missing_validation = sorted(
        set(effect_policy["required_validation"]) - set(task["required_validation"])
    )
    if missing_validation:
        raise ValueError(
            "managed task required_validation is weaker than central policy: " + ", ".join(missing_validation)
        )

    validate_scope(task, changed_files)
    return True



def reconcile_external_ci_liveness(
    bound_run_ids,
    live_runs,
    previous_state=CI_WAIT_STATE,
    last_progress_at=None,
    now=None,
    poll_interval_minutes=DEFAULT_POLL_INTERVAL_MINUTES,
    no_progress_poll_limit=DEFAULT_LIVENESS_NO_PROGRESS_POLLS,
    stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES,
):
    """Apply an active liveness guard around external-CI reconciliation.

    WAITING_EXTERNAL_CI is a data state, never a passive UI/tool wait. Terminal
    GitHub state always routes immediately. If the Work execution is still live
    but the control plane has made no progress for two polling intervals, force
    a reconstruction/re-poll cycle instead of remaining parked on a spinner.
    """
    now = now or datetime.now(timezone.utc)
    state = reconcile_external_ci_wait(
        bound_run_ids,
        live_runs,
        previous_state=previous_state,
        now=now,
        stale_after_minutes=stale_after_minutes,
    )
    state["poll_interval_minutes"] = poll_interval_minutes

    if state.get("route") != CI_ROUTE_WAIT:
        state["liveness_action"] = "ROUTE_IMMEDIATELY"
        return state

    if poll_interval_minutes <= 0:
        raise ValueError("poll_interval_minutes must be positive")
    if no_progress_poll_limit < 1:
        raise ValueError("no_progress_poll_limit must be at least 1")

    if last_progress_at is None:
        state["state"] = CI_LIVENESS_RECONCILE_REQUIRED
        state["route"] = CI_ROUTE_INVESTIGATE
        state["liveness_action"] = "ESTABLISH_PROGRESS_BASELINE"
        return state

    last_progress = (
        _parse_time(last_progress_at)
        if isinstance(last_progress_at, str)
        else last_progress_at
    )
    if last_progress is None or last_progress.tzinfo is None:
        raise ValueError("last_progress_at must be an offset-aware datetime or ISO timestamp")

    no_progress_minutes = (now - last_progress).total_seconds() / 60
    state["no_progress_minutes"] = no_progress_minutes
    threshold = poll_interval_minutes * no_progress_poll_limit
    if no_progress_minutes >= threshold:
        state["state"] = CI_LIVENESS_RECONCILE_REQUIRED
        state["route"] = CI_ROUTE_INVESTIGATE
        state["liveness_action"] = "RECONSTRUCT_AND_REPOLL"
        return state

    state["liveness_action"] = "POLL_AGAIN"
    return state


def reconcile_operational_access_discovery(
    searched_surfaces,
    candidate_channels,
    direct_access_available=False,
):
    """Reconcile access discovery before any access-related Human Gate.

    Missing direct session SSH/tooling is not proof that operational access is
    unavailable. Read-only discovery may inspect adjacent operational repositories
    and historical automation without violating one-mutable-repository isolation.
    Any mutation of another repository still requires a separate bounded task.
    """
    if not isinstance(searched_surfaces, list):
        raise ValueError("searched_surfaces must be a list")
    if len(set(searched_surfaces)) != len(searched_surfaces):
        raise ValueError("searched_surfaces must be unique")
    if not all(isinstance(item, str) and item for item in searched_surfaces):
        raise ValueError("searched_surfaces entries must be non-empty strings")
    if not isinstance(candidate_channels, list):
        raise ValueError("candidate_channels must be a list")
    _require_strict_bool(direct_access_available, "direct_access_available")

    if direct_access_available:
        return {
            "state": ACCESS_PATH_FOUND,
            "route": ACCESS_ROUTE_CONTINUE,
            "selected_channel": "direct_session_capabilities",
            "missing_surfaces": [],
        }

    normalized = []
    for index, candidate in enumerate(candidate_channels):
        if not isinstance(candidate, dict):
            raise ValueError("candidate channel must be an object")
        name = candidate.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("candidate channel name must be a non-empty string")
        usable = candidate.get("usable")
        requires_mutation = candidate.get("requires_mutation", False)
        authority_covered = candidate.get("authority_covered", False)
        if not isinstance(usable, bool):
            raise ValueError(f"candidate channel usable must be boolean: {name}")
        if not isinstance(requires_mutation, bool):
            raise ValueError(f"candidate channel requires_mutation must be boolean: {name}")
        if not isinstance(authority_covered, bool):
            raise ValueError(f"candidate channel authority_covered must be boolean: {name}")
        normalized.append({
            "index": index,
            "name": name,
            "usable": usable,
            "requires_mutation": requires_mutation,
            "authority_covered": authority_covered,
        })

    for candidate in normalized:
        if candidate["usable"] and not candidate["requires_mutation"]:
            return {
                "state": ACCESS_PATH_FOUND,
                "route": ACCESS_ROUTE_CONTINUE,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    for candidate in normalized:
        if candidate["usable"] and candidate["requires_mutation"] and candidate["authority_covered"]:
            return {
                "state": ACCESS_PATH_REQUIRES_SEPARATE_TASK,
                "route": ACCESS_ROUTE_BOUND_TASK,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    missing = [
        surface
        for surface in ACCESS_DISCOVERY_REQUIRED_SURFACES
        if surface not in searched_surfaces
    ]
    if missing:
        return {
            "state": ACCESS_DISCOVERY_INCOMPLETE,
            "route": ACCESS_ROUTE_DISCOVER,
            "selected_channel": None,
            "missing_surfaces": missing,
        }

    for candidate in normalized:
        if candidate["usable"] and candidate["requires_mutation"]:
            return {
                "state": ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION,
                "route": ACCESS_ROUTE_AUTHORITY,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    return {
        "state": ACCESS_PATH_UNAVAILABLE,
        "route": ACCESS_ROUTE_HUMAN_GATE_CANDIDATE,
        "selected_channel": None,
        "missing_surfaces": [],
    }


def reconcile_noninteractive_tool_fallback(
    checked_surfaces,
    candidate_channels,
    self_provisioning_checked=False,
    self_provision_candidates=None,
):
    """Exhaust non-interactive diagnostics and self-provisioned bridges before consent.

    After native connector evidence is exhausted, Project Leader must still ask:
    can it create a bounded repository-side diagnostic bridge under existing
    authority? Examples include an ephemeral task branch/workflow or an existing
    operations repository path that returns sanitized logs/artifacts/check evidence.

    Platform/browser consent is eligible only after native evidence, repository
    return paths, self-provisioning, and authority-resolvable alternatives are
    all exhausted.
    """
    if not isinstance(checked_surfaces, list):
        raise ValueError("checked_surfaces must be a list")
    if len(set(checked_surfaces)) != len(checked_surfaces):
        raise ValueError("checked_surfaces must be unique")
    if not all(isinstance(item, str) and item for item in checked_surfaces):
        raise ValueError("checked_surfaces entries must be non-empty strings")
    if not isinstance(candidate_channels, list):
        raise ValueError("candidate_channels must be a list")
    if not isinstance(self_provisioning_checked, bool):
        raise ValueError("self_provisioning_checked must be boolean")
    if self_provision_candidates is None:
        self_provision_candidates = []
    if not isinstance(self_provision_candidates, list):
        raise ValueError("self_provision_candidates must be a list")

    normalized = []
    for index, candidate in enumerate(candidate_channels):
        if not isinstance(candidate, dict):
            raise ValueError("diagnostic candidate channel must be an object")
        name = candidate.get("name")
        usable = candidate.get("usable")
        requires_user_consent = candidate.get("requires_user_consent", False)
        if not isinstance(name, str) or not name:
            raise ValueError("diagnostic candidate channel name must be a non-empty string")
        if not isinstance(usable, bool):
            raise ValueError(f"diagnostic candidate channel usable must be boolean: {name}")
        if not isinstance(requires_user_consent, bool):
            raise ValueError(
                f"diagnostic candidate channel requires_user_consent must be boolean: {name}"
            )
        normalized.append(
            {
                "index": index,
                "name": name,
                "usable": usable,
                "requires_user_consent": requires_user_consent,
            }
        )

    normalized_bridges = []
    for index, candidate in enumerate(self_provision_candidates):
        if not isinstance(candidate, dict):
            raise ValueError("self-provision diagnostic candidate must be an object")
        name = candidate.get("name")
        provisionable = candidate.get("provisionable")
        authority_covered = candidate.get("authority_covered")
        if not isinstance(name, str) or not name:
            raise ValueError("self-provision diagnostic candidate name must be a non-empty string")
        if not isinstance(provisionable, bool):
            raise ValueError(
                f"self-provision diagnostic candidate provisionable must be boolean: {name}"
            )
        if not isinstance(authority_covered, bool):
            raise ValueError(
                f"self-provision diagnostic candidate authority_covered must be boolean: {name}"
            )
        normalized_bridges.append(
            {
                "index": index,
                "name": name,
                "provisionable": provisionable,
                "authority_covered": authority_covered,
            }
        )

    for candidate in normalized:
        if candidate["usable"] and not candidate["requires_user_consent"]:
            return {
                "state": NONINTERACTIVE_PATH_FOUND,
                "route": NONINTERACTIVE_ROUTE_CONTINUE,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    missing = [
        surface
        for surface in NONINTERACTIVE_DIAGNOSTIC_REQUIRED_SURFACES
        if surface not in checked_surfaces
    ]
    if missing:
        return {
            "state": NONINTERACTIVE_FALLBACK_INCOMPLETE,
            "route": NONINTERACTIVE_ROUTE_DISCOVER,
            "selected_channel": None,
            "missing_surfaces": missing,
        }

    if not self_provisioning_checked:
        return {
            "state": NONINTERACTIVE_FALLBACK_INCOMPLETE,
            "route": NONINTERACTIVE_ROUTE_DISCOVER,
            "selected_channel": None,
            "missing_surfaces": [SELF_PROVISION_DIAGNOSTIC_SURFACE],
        }

    for candidate in normalized_bridges:
        if candidate["provisionable"] and candidate["authority_covered"]:
            return {
                "state": DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK,
                "route": NONINTERACTIVE_ROUTE_BOUND_BRIDGE,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    for candidate in normalized_bridges:
        if candidate["provisionable"]:
            return {
                "state": DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION,
                "route": NONINTERACTIVE_ROUTE_AUTHORITY,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    for candidate in normalized:
        if candidate["usable"] and candidate["requires_user_consent"]:
            return {
                "state": PLATFORM_CONSENT_REQUIRED,
                "route": ACCESS_ROUTE_HUMAN_GATE_CANDIDATE,
                "selected_channel": candidate["name"],
                "missing_surfaces": [],
            }

    return {
        "state": NONINTERACTIVE_FALLBACK_EXHAUSTED,
        "route": NONINTERACTIVE_ROUTE_REENTER_ACCESS,
        "selected_channel": None,
        "missing_surfaces": [],
    }


def reconcile_legacy_checkpoint_liveness(
    checkpoint,
    has_live_branch=False,
    has_open_pr=False,
    has_active_ci=False,
    has_terminal_result=False,
):
    """Interpret legacy v1 checkpoint state against current durable evidence.

    Legacy checkpoint status is historical evidence. ACTIVE is actionable only
    when current repository state independently corroborates a live workstream.
    """
    validate_checkpoint(checkpoint)
    for label, value in (
        ("has_live_branch", has_live_branch),
        ("has_open_pr", has_open_pr),
        ("has_active_ci", has_active_ci),
        ("has_terminal_result", has_terminal_result),
    ):
        _require_strict_bool(value, label)
    status = checkpoint.get("status")
    task_id = checkpoint.get("task_id")

    if status != "ACTIVE":
        return {
            "task_id": task_id,
            "state": LEGACY_CHECKPOINT_TERMINAL,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "legacy checkpoint already records a terminal/non-active state",
        }

    if has_terminal_result:
        return {
            "task_id": task_id,
            "state": STALE_LEGACY_CHECKPOINT,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "terminal task result supersedes legacy ACTIVE checkpoint snapshot",
        }

    live_evidence = bool(has_live_branch or has_open_pr or has_active_ci)
    if not live_evidence:
        return {
            "task_id": task_id,
            "state": STALE_LEGACY_CHECKPOINT,
            "actionable": False,
            "checkpoint_status": status,
            "reason": "legacy ACTIVE checkpoint has no corroborating live branch, PR, or active CI",
        }

    return {
        "task_id": task_id,
        "state": LEGACY_ACTIVE_CORROBORATED,
        "actionable": True,
        "checkpoint_status": status,
        "reason": "legacy ACTIVE checkpoint is corroborated by current live workstream evidence",
    }



def decide_ci_dispatch(workflow_name, target_sha, event, workflow_runs):
    """Decide whether Project Leader should explicitly create another CI run.

    Deduplication is exact by workflow name, target SHA, and GitHub event
    context. Automatic runs from different contexts remain independent evidence.
    """
    for label, value in (
        ("workflow_name", workflow_name),
        ("target_sha", target_sha),
        ("event", event),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")
    if not isinstance(workflow_runs, list):
        raise ValueError("workflow_runs must be a list")
    if RUNTIME_SHA_RE.fullmatch(target_sha) is None:
        raise ValueError("target_sha must be an exact 40-hex commit SHA")

    matching = [
        run for run in workflow_runs
        if isinstance(run, dict)
        and run.get("name") == workflow_name
        and run.get("head_sha") == target_sha
        and run.get("event") == event
    ]
    if not matching:
        return {
            "decision": CI_DISPATCH_REQUIRED,
            "run_id": None,
            "reason": "no existing exact workflow/SHA/context run",
        }

    for run in matching:
        _validate_ci_run_payload(run, require_timestamp=True)

    def order_key(run):
        timestamp = (
            run.get("created_at")
            or run.get("run_started_at")
            or run.get("updated_at")
        )
        return (_parse_time(timestamp), run["id"])

    latest = max(matching, key=order_key)
    status = latest.get("status")
    conclusion = latest.get("conclusion")
    run_id = latest.get("id")

    if status in CI_ACTIVE_STATUSES:
        return {
            "decision": CI_REUSE_ACTIVE,
            "run_id": run_id,
            "reason": "exact matching CI run is already active",
        }
    if status == "completed" and conclusion == "success":
        return {
            "decision": CI_REUSE_SUCCESS,
            "run_id": run_id,
            "reason": "exact matching CI run already completed successfully",
        }
    if status == "completed":
        return {
            "decision": CI_DISPATCH_ROUTE_RECOVERY,
            "run_id": run_id,
            "reason": f"exact matching CI run is terminal non-success: {conclusion}",
        }
    return {
        "decision": "INVESTIGATE_CI_STATE",
        "run_id": run_id,
        "reason": f"unrecognized exact matching CI state: {status}",
    }


def _is_task_local_post_ci_evidence_path(path, task_id, task_local_transition_paths=None):
    if path == f".project-leader/results/{task_id}.json":
        return True
    if path.startswith(f".project-leader/recovery-events/{task_id}/") and path.endswith(".json"):
        return True
    return path in set(task_local_transition_paths or ())


def classify_post_implementation_descendant(
    changed_files,
    task_id,
    final_head_checks_required=False,
    task_local_transition_paths=None,
):
    """Classify changes after a CI-certified implementation head.

    Required task CI is bound to implementation_head_sha. A newer PR head may
    contain only task-local Project Leader evidence metadata without becoming a
    new implementation head. Automatic CI that happens to run on such an
    evidence-only descendant is non-certifying and must not by itself reopen
    task Recovery. If repository governance explicitly requires checks on the
    current PR head, that CI is a merge-governance condition, not a reason to
    move implementation_head_sha or manufacture another evidence commit.
    """
    if not isinstance(task_id, str) or not task_id:
        raise ValueError("task_id must be a non-empty string")
    if not isinstance(changed_files, list) or not all(
        isinstance(path, str) and path for path in changed_files
    ):
        raise ValueError("changed_files must be a list of non-empty paths")
    if not isinstance(final_head_checks_required, bool):
        raise ValueError("final_head_checks_required must be boolean")

    material = sorted(
        path
        for path in changed_files
        if not _is_task_local_post_ci_evidence_path(
            path, task_id, task_local_transition_paths
        )
    )
    if material:
        return {
            "state": POST_CI_DESCENDANT_MATERIAL,
            "route": POST_CI_ROUTE_FRESH_IMPLEMENTATION,
            "certification_ci_required": True,
            "final_head_checks_required": final_head_checks_required,
            "material_files": material,
        }

    return {
        "state": POST_CI_DESCENDANT_EVIDENCE_ONLY,
        "route": (
            POST_CI_ROUTE_FINAL_HEAD_GOVERNANCE
            if final_head_checks_required
            else POST_CI_ROUTE_CERTIFICATION_UNCHANGED
        ),
        "certification_ci_required": False,
        "final_head_checks_required": final_head_checks_required,
        "evidence_only_files": sorted(changed_files),
    }


def _parse_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_external_ci(run, now=None, stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES):
    _validate_ci_run_payload(
        run,
        require_timestamp=run.get("status") in CI_ACTIVE_STATUSES if isinstance(run, dict) else False,
    )
    status = run.get("status")
    conclusion = run.get("conclusion")
    if status == "completed":
        return "COMPLETED_SUCCESS" if conclusion == "success" else "COMPLETED_FAILURE"

    now = now or datetime.now(timezone.utc)
    updated = (
        _parse_time(run.get("updated_at"))
        or _parse_time(run.get("run_started_at"))
        or _parse_time(run.get("created_at"))
    )
    if updated is not None:
        age_minutes = (now - updated).total_seconds() / 60
        if age_minutes > stale_after_minutes:
            return "INVESTIGATE_STALE_CI"
    return CI_WAIT_STATE


def reconcile_external_ci_wait(bound_run_ids, live_runs, previous_state=CI_WAIT_STATE, now=None, stale_after_minutes=DEFAULT_STALE_AFTER_MINUTES):
    """Reconcile a persisted external-CI wait against fresh live GitHub run state.

    WAITING_EXTERNAL_CI is transient. Exact bound run IDs are re-read from GitHub;
    once every bound run is terminal, an older wait becomes STALE_WAIT_STATE and
    must route immediately to Supervisor audit/continue or Recovery.
    """
    if not isinstance(bound_run_ids, list) or not bound_run_ids:
        raise ValueError("external CI wait must bind at least one exact run_id")
    if len(set(bound_run_ids)) != len(bound_run_ids):
        raise ValueError("external CI wait run_ids must be unique")
    if not all(
        isinstance(run_id, int) and not isinstance(run_id, bool) and run_id > 0
        for run_id in bound_run_ids
    ):
        raise ValueError("external CI wait run_ids must be positive integers")
    if not isinstance(live_runs, list):
        raise ValueError("live_runs must be a list")

    for run in live_runs:
        _validate_ci_run_payload(
            run,
            require_timestamp=run.get("status") in CI_ACTIVE_STATUSES if isinstance(run, dict) else False,
        )
    by_id = {run["id"]: run for run in live_runs}
    missing = [run_id for run_id in bound_run_ids if run_id not in by_id]
    if missing:
        return {
            "state": "INVESTIGATE_CI_STATE",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "missing_run_ids": missing,
        }

    classifications = {
        run_id: classify_external_ci(
            by_id[run_id],
            now=now,
            stale_after_minutes=stale_after_minutes,
        )
        for run_id in bound_run_ids
    }

    if any(value == "INVESTIGATE_STALE_CI" for value in classifications.values()):
        return {
            "state": "INVESTIGATE_STALE_CI",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "classifications": classifications,
        }
    if any(value == "INVESTIGATE_CI_STATE" for value in classifications.values()):
        return {
            "state": "INVESTIGATE_CI_STATE",
            "route": CI_ROUTE_INVESTIGATE,
            "bound_run_ids": list(bound_run_ids),
            "classifications": classifications,
        }

    active = [run_id for run_id, value in classifications.items() if value == CI_WAIT_STATE]
    if active:
        return {
            "state": CI_WAIT_STATE,
            "route": CI_ROUTE_WAIT,
            "bound_run_ids": list(bound_run_ids),
            "active_run_ids": active,
            "classifications": classifications,
        }

    failed = [run_id for run_id, value in classifications.items() if value == "COMPLETED_FAILURE"]
    state = CI_STALE_WAIT_STATE if previous_state == CI_WAIT_STATE else (
        "COMPLETED_FAILURE" if failed else "COMPLETED_SUCCESS"
    )
    return {
        "state": state,
        "route": CI_ROUTE_RECOVERY if failed else CI_ROUTE_CONTINUE,
        "bound_run_ids": list(bound_run_ids),
        "failed_run_ids": failed,
        "classifications": classifications,
    }
