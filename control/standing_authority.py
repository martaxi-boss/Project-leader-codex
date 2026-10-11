"""Deterministic standing-authority resolution for Project Leader.

This module does not grant project scope. It resolves whether a next action
already covered by canonical project state may continue autonomously under the
durable Owner standing grant, requires remediation first, or requires the Owner
because the next irreducible step is genuinely human/manual or a new material
decision.
"""

from control.managed_project_contract import (
    ACCESS_DISCOVERY_INCOMPLETE,
    ACCESS_PATH_UNAVAILABLE,
    NONINTERACTIVE_FALLBACK_EXHAUSTED,
    NONINTERACTIVE_FALLBACK_INCOMPLETE,
    PLATFORM_CONSENT_REQUIRED,
    reconcile_noninteractive_tool_fallback,
    reconcile_operational_access_discovery,
)

CONTINUE_AUTONOMOUSLY = "CONTINUE_AUTONOMOUSLY"
CONTINUE_REMEDIATION = "CONTINUE_REMEDIATION"
HUMAN_GATE = "HUMAN_GATE"

EXCLUSIVE_HUMAN_INTERVENTION = "EXCLUSIVE_HUMAN_INTERVENTION"
NEW_UNCOVERED_MATERIAL_DECISION = "NEW_UNCOVERED_MATERIAL_DECISION"
STANDING_OWNER_GRANT = "STANDING_OWNER_GRANT"
DERIVED_COMPLETION_AUTHORITY = "DERIVED_COMPLETION_AUTHORITY"
COMPACT_RECOVERY = "COMPACT_RECOVERY"
RECOVERY_REPLAN_REQUIRED = "RECOVERY_REPLAN_REQUIRED"
NORMAL_AUTHORITY_RESOLUTION = "NORMAL_AUTHORITY_RESOLUTION"
RECOVERY_DIRECT_REPAIR = "RECOVERY_DIRECT_REPAIR"
RECOVERY_DIRECT_REPLAN = "RECOVERY_DIRECT_REPLAN"

CONTINUOUS_HYGIENE_ACTIVE = "CONTINUOUS_HYGIENE_ACTIVE"
HYGIENE_REPORT_ONLY = "HYGIENE_REPORT_ONLY"
HYGIENE_DEFER_UNCOVERED = "HYGIENE_DEFER_UNCOVERED"
HYGIENE_NOT_REQUIRED = "HYGIENE_NOT_REQUIRED"

RETRY_BASES = frozenset({
    "MATERIAL_CHANGE",
    "NEW_EVIDENCE",
    "NEW_HYPOTHESIS",
    "STRATEGY_CHANGE",
    "OBSERVER_FIX",
    "TRANSIENT_FAILURE",
})

DIRECT_MANUAL_KINDS = frozenset({
    "PHYSICAL_DEVICE_TEST", "HARDWARE_INTERACTION", "OWNER_HELD_INPUT",
})
ACCESS_MANUAL_KINDS = frozenset({ACCESS_PATH_UNAVAILABLE, PLATFORM_CONSENT_REQUIRED})


def _human_intervention(record):
    if record is None:
        return None
    if not isinstance(record, dict) or set(record) != {"kind", "evidence"}:
        raise ValueError("human_intervention must contain only kind and evidence")
    if not isinstance(record["kind"], str) or record["kind"] not in DIRECT_MANUAL_KINDS | ACCESS_MANUAL_KINDS:
        raise ValueError("human_intervention kind must identify a genuine manual action")
    if not isinstance(record["evidence"], str) or not record["evidence"].strip():
        raise ValueError("human_intervention evidence must explain the exact irreducible human step")
    return dict(record)


def _observations(record, defaults):
    if record is None:
        return dict(defaults)
    if not isinstance(record, dict) or set(record) - set(defaults):
        raise ValueError("preflight input must contain raw observations, not a claimed state/route")
    return {**defaults, **record}



def resolve_recovery_action(
    *,
    objective_authorized,
    standing_delegation_valid,
    effect_class,
    same_project_workstream,
    architecture_change=False,
    security_boundary_change=False,
    new_permission_required=False,
    human_gate_required=False,
    new_material_decision=False,
    same_action_retry=False,
    durable_continuity_required=False,
    immutable_audit_required=False,
    no_progress_iterations=0,
    attempt_count=0,
    identical_failure_count=0,
    retry_basis=None,
):
    """Resolve compact completion authority for already-covered E1 Recovery."""
    for name, value in (
        ("objective_authorized", objective_authorized),
        ("standing_delegation_valid", standing_delegation_valid),
        ("same_project_workstream", same_project_workstream),
        ("architecture_change", architecture_change),
        ("security_boundary_change", security_boundary_change),
        ("new_permission_required", new_permission_required),
        ("human_gate_required", human_gate_required),
        ("new_material_decision", new_material_decision),
        ("same_action_retry", same_action_retry),
        ("durable_continuity_required", durable_continuity_required),
        ("immutable_audit_required", immutable_audit_required),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")
    if not isinstance(effect_class, str) or not effect_class:
        raise ValueError("effect_class must be a non-empty string")
    if not isinstance(no_progress_iterations, int) or isinstance(no_progress_iterations, bool) or no_progress_iterations < 0:
        raise ValueError("no_progress_iterations must be a non-negative integer")
    if not isinstance(attempt_count, int) or isinstance(attempt_count, bool) or attempt_count < 0:
        raise ValueError("attempt_count must be a non-negative integer")
    if not isinstance(identical_failure_count, int) or isinstance(identical_failure_count, bool) or identical_failure_count < 0:
        raise ValueError("identical_failure_count must be a non-negative integer")
    if retry_basis is not None and retry_basis not in RETRY_BASES:
        raise ValueError("retry_basis must be a recognized material retry basis")

    covered_e1 = (
        objective_authorized
        and standing_delegation_valid
        and same_project_workstream
        and effect_class == "E1_RECOVERABLE_PROJECT_LOCAL"
    )
    boundary_changed = any((
        architecture_change,
        security_boundary_change,
        new_permission_required,
        human_gate_required,
        new_material_decision,
    ))
    if not covered_e1 or boundary_changed:
        return {
            "decision": NORMAL_AUTHORITY_RESOLUTION,
            "reason": "RECOVERY_SCOPE_OR_BOUNDARY_CHANGED",
            "authority_kind": None,
            "authority_source": None,
            "durable_recovery_required": True,
            "route": "AUTHORITY_RESOLUTION",
            "executor": None,
        }

    if same_action_retry and retry_basis is None:
        return {
            "decision": RECOVERY_REPLAN_REQUIRED,
            "reason": "BLIND_RETRY_BLOCKED",
            "authority_kind": DERIVED_COMPLETION_AUTHORITY,
            "authority_source": STANDING_OWNER_GRANT,
            "durable_recovery_required": True,
            "route": RECOVERY_DIRECT_REPLAN,
            "executor": "RECOVERY_GUARDIAN",
        }

    if same_action_retry and (
        attempt_count >= 3
        or identical_failure_count >= 2
        or no_progress_iterations >= 3
    ):
        return {
            "decision": RECOVERY_REPLAN_REQUIRED,
            "reason": "RECOVERY_BUDGET_EXHAUSTED",
            "authority_kind": DERIVED_COMPLETION_AUTHORITY,
            "authority_source": STANDING_OWNER_GRANT,
            "durable_recovery_required": True,
            "route": RECOVERY_DIRECT_REPLAN,
            "executor": "RECOVERY_GUARDIAN",
        }

    if no_progress_iterations >= 3:
        return {
            "decision": RECOVERY_REPLAN_REQUIRED,
            "reason": "NO_PROGRESS_LIMIT_REACHED",
            "authority_kind": DERIVED_COMPLETION_AUTHORITY,
            "authority_source": STANDING_OWNER_GRANT,
            "durable_recovery_required": True,
            "route": RECOVERY_DIRECT_REPLAN,
            "executor": "RECOVERY_GUARDIAN",
        }

    return {
        "decision": COMPACT_RECOVERY,
        "reason": "RECOVERY_COMPACTION_CLOSURE_PASSED",
        "authority_kind": DERIVED_COMPLETION_AUTHORITY,
        "authority_source": STANDING_OWNER_GRANT,
        "durable_recovery_required": (
            same_action_retry
            or durable_continuity_required
            or immutable_audit_required
        ),
        "route": RECOVERY_DIRECT_REPAIR,
        "executor": "RECOVERY_GUARDIAN",
    }


def resolve_hygiene_action(
    *,
    mutation_capable,
    explicit_read_only,
    cleanup_needed,
    cleanup_within_scope=True,
    cleanup_recoverable=True,
):
    """Resolve continuous hygiene without widening mutation authority."""
    for name, value in (
        ("mutation_capable", mutation_capable),
        ("explicit_read_only", explicit_read_only),
        ("cleanup_needed", cleanup_needed),
        ("cleanup_within_scope", cleanup_within_scope),
        ("cleanup_recoverable", cleanup_recoverable),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")

    if explicit_read_only:
        return {
            "mode": HYGIENE_REPORT_ONLY,
            "write_allowed": False,
            "same_cycle": False,
            "reason": "EXPLICIT_READ_ONLY",
        }
    if not mutation_capable or not cleanup_needed:
        return {
            "mode": HYGIENE_NOT_REQUIRED,
            "write_allowed": False,
            "same_cycle": False,
            "reason": "NO_MUTATION_HYGIENE_WORK",
        }
    if cleanup_within_scope and cleanup_recoverable:
        return {
            "mode": CONTINUOUS_HYGIENE_ACTIVE,
            "write_allowed": True,
            "same_cycle": True,
            "reason": "COVERED_RECOVERABLE_CLEANUP",
        }
    return {
        "mode": HYGIENE_DEFER_UNCOVERED,
        "write_allowed": False,
        "same_cycle": False,
        "reason": "HYGIENE_OUTSIDE_CURRENT_AUTHORITY",
    }


def resolve_next_action(
    action,
    *,
    canonical_effect_covered,
    system_can_execute,
    controls_satisfied,
    new_material_decision=False,
    convergence_complete=False,
    human_intervention=None,
    access_discovery=None,
    diagnostic_fallback=None,
    post_fallback_access_discovery=None,
):
    """Resolve the next Project Leader action without action-name gates.

    Action names and effect classes do not create a Human Gate by themselves.
    The caller must already have reconstructed canonical project state. A
    missing-capability boolean is an observation, never Human Gate evidence.
    Recompute access/diagnostic closure from raw discovery observations. Only
    evidenced physical/manual steps may bypass operational access discovery.
    controls_satisfied describes prerequisites for the exact next action, not
    the outcome of a manual test that has yet to be performed.

    Returns a compact decision dictionary suitable for Supervisor/Recovery
    routing.
    """
    if not isinstance(action, str) or not action:
        raise ValueError("action must be a non-empty string")
    for name, value in (
        ("canonical_effect_covered", canonical_effect_covered),
        ("system_can_execute", system_can_execute),
        ("controls_satisfied", controls_satisfied),
        ("new_material_decision", new_material_decision),
        ("convergence_complete", convergence_complete),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be boolean")

    manual = _human_intervention(human_intervention)

    def decision(outcome, reason, authority_source=None, **evidence):
        return {
            "decision": outcome,
            "reason": reason,
            "action": action,
            "authority_source": authority_source,
            **evidence,
        }

    def converge():
        return decision(
            CONTINUE_REMEDIATION, "CONVERGENCE_PREFLIGHT_REQUIRED",
            STANDING_OWNER_GRANT if canonical_effect_covered and not new_material_decision else None,
            route="SUPERVISOR_AUDIT",
        )

    if new_material_decision or not canonical_effect_covered:
        if not convergence_complete:
            return converge()
        return decision(HUMAN_GATE, NEW_UNCOVERED_MATERIAL_DECISION)

    if not controls_satisfied:
        return decision(
            CONTINUE_REMEDIATION, "COVERED_CONTROLS_NOT_YET_SATISFIED",
            STANDING_OWNER_GRANT,
        )

    if system_can_execute:
        return decision(
            CONTINUE_AUTONOMOUSLY, "COVERED_EXECUTABLE_ACTION", STANDING_OWNER_GRANT,
        )

    if manual and manual["kind"] in DIRECT_MANUAL_KINDS:
        if not convergence_complete:
            return converge()
        return decision(HUMAN_GATE, EXCLUSIVE_HUMAN_INTERVENTION, human_intervention=manual)

    access_args = _observations(access_discovery, {
        "searched_surfaces": [], "candidate_channels": [], "direct_access_available": False,
    })
    if not isinstance(access_args["direct_access_available"], bool):
        raise ValueError("direct_access_available must be boolean")
    access = reconcile_operational_access_discovery(**access_args)
    if access["state"] not in {ACCESS_DISCOVERY_INCOMPLETE, ACCESS_PATH_UNAVAILABLE}:
        return decision(
            CONTINUE_REMEDIATION, access["state"], STANDING_OWNER_GRANT,
            route=access["route"], access_discovery=access,
        )

    fallback = reconcile_noninteractive_tool_fallback(**_observations(diagnostic_fallback, {
        "checked_surfaces": [], "candidate_channels": [],
        "self_provisioning_checked": False, "self_provision_candidates": [],
    }))
    if fallback["state"] not in {
        NONINTERACTIVE_FALLBACK_INCOMPLETE,
        NONINTERACTIVE_FALLBACK_EXHAUSTED,
        PLATFORM_CONSENT_REQUIRED,
    }:
        return decision(
            CONTINUE_REMEDIATION, fallback["state"], STANDING_OWNER_GRANT,
            route=fallback["route"], diagnostic_fallback=fallback,
        )
    for preflight, incomplete, key in (
        (access, ACCESS_DISCOVERY_INCOMPLETE, "access_discovery"),
        (fallback, NONINTERACTIVE_FALLBACK_INCOMPLETE, "diagnostic_fallback"),
    ):
        if preflight["state"] == incomplete:
            return decision(
                CONTINUE_REMEDIATION, incomplete, STANDING_OWNER_GRANT,
                route=preflight["route"], **{key: preflight},
            )

    if fallback["state"] == NONINTERACTIVE_FALLBACK_EXHAUSTED:
        if post_fallback_access_discovery is None:
            return decision(
                CONTINUE_REMEDIATION, NONINTERACTIVE_FALLBACK_EXHAUSTED,
                STANDING_OWNER_GRANT, route=fallback["route"],
                access_discovery=access, diagnostic_fallback=fallback,
            )
        # Re-enter forced discovery with observations obtained AFTER fallback;
        # the earlier access snapshot cannot silently certify this re-entry.
        post_args = _observations(post_fallback_access_discovery, {
            "searched_surfaces": [], "candidate_channels": [], "direct_access_available": False,
        })
        if not isinstance(post_args["direct_access_available"], bool):
            raise ValueError("direct_access_available must be boolean")
        access = reconcile_operational_access_discovery(**post_args)
        if access["state"] != ACCESS_PATH_UNAVAILABLE:
            return decision(
                CONTINUE_REMEDIATION, access["state"], STANDING_OWNER_GRANT,
                route=access["route"], post_fallback_access_discovery=access,
            )

    # Exhaustion is a candidate, not proof of an action only the Owner can do.
    expected_kind = (
        PLATFORM_CONSENT_REQUIRED
        if fallback["state"] == PLATFORM_CONSENT_REQUIRED
        else ACCESS_PATH_UNAVAILABLE
    )
    if not manual or manual["kind"] != expected_kind:
        return decision(
            CONTINUE_REMEDIATION, "HUMAN_INTERVENTION_EVIDENCE_REQUIRED",
            STANDING_OWNER_GRANT, route="SUPERVISOR_AUTHORITY_RESOLUTION",
            access_discovery=access, diagnostic_fallback=fallback,
        )
    if not convergence_complete:
        return converge()
    return decision(
        HUMAN_GATE, EXCLUSIVE_HUMAN_INTERVENTION, human_intervention=manual,
        access_discovery=access, diagnostic_fallback=fallback,
    )
