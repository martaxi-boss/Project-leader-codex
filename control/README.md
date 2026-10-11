# Proportional Project Leader control records

Project Leader uses machine-readable durable records when a material boundary, ambiguous replay risk, context-loss duplication risk, consequential transition, or explicit audit requirement justifies persistence. Ordinary covered FAST_E1 does not require control-only records.

These records preserve continuity and auditability when needed. They never invent product scope, architecture, or new authority.

## Task Authorization

Canonical current schema:

`task-authorization.schema.json`

When DURABLE_CONTROL is selected, Supervisor may compile the bounded record from verified target state plus current/canonical authority. The canonical durable path is:

`.project-leader/tasks/<task-id>.json`

Current v2 records use:

- `transition_controls` for consequential effects that require separate authority/evidence resolution;
- `required_validation` for acceptance checks;
- `required_ci` for applicable named workflows; this list may be empty when the target project has no applicable automated CI;
- `IMMUTABLE_AUTHORIZATION_V1` plus exact authorization commit/digest binding;
- `APPEND_ONLY_V1` recovery history.

Historical `human_gates` fields are compatibility-only evidence. The current runtime must not generate them.

A Task Authorization record never widens the project architecture or current Owner instruction. It contains no credentials, secrets, private conversation text, or unrelated project information.

## Worker Result

Canonical schema:

`worker-result.schema.json`

For DURABLE_CONTROL, Builder emits a result when the material contract requires one and, when target policy permits, persists it at:

`.project-leader/results/<task-id>.json`

`implementation_head_sha` identifies the material implementation state being certified. Evidence-only result/recovery/transition commits may follow it without becoming a new implementation head.

Worker Result is an audit index, not proof. Supervisor independently verifies refs, commits, diffs, PR state, CI, artifacts, and material non-effects.

`TERMINAL_SUCCESS` requires positive validation. Every task-required validation must be `PASS`; every task-required CI workflow must be represented by successful live GitHub run evidence. When `required_ci` is empty, positive validation/evidence remains mandatory.

## Consequential transition authorization/result

Canonical schemas:

- `transition-authorization.schema.json`
- `transition-result.schema.json`

A consequential transition such as an exact merge, deploy, release, governance change, infrastructure/secret/data transition, or commercial activation is outside the ordinary Builder implementation step.

Before the effect, Supervisor persists:

`.project-leader/transitions/<transition-id>.authorization.json`

When the standing-authority resolver proves that the canonical project already covers the effect and the system can execute it, the transition authority source may be:

`STANDING_OWNER_GRANT`

After the effect, persist:

`.project-leader/transitions/<transition-id>.result.json`

A `SUCCESS` transition result without matching prior authorization is invalid.

Historical observed effects without durable authorization stay `HISTORICAL_OBSERVED`; never fabricate retroactive approval.

For newly created or modified authorized transition pairs, `created_at` is the declared authorization-record creation time and `observed_at` is the result observation time. Current admission requires `created_at <= observed_at`. Legacy records remain readable under compatibility validation because some historical pairs contain timestamp inversions even though Git ancestry proves the authorization commit structurally precedes implementation. Temporal metadata is therefore a consistency signal, never a substitute for exact-revision/ancestry evidence.

## Human Gate

`HUMAN_GATE` is a runtime decision, not a synonym for a merge/deploy/release action.

It is valid only when the next irreducible step is:

- `EXCLUSIVE_HUMAN_INTERVENTION`; or
- `NEW_UNCOVERED_MATERIAL_DECISION`.

Covered technical failures, incomplete checks, CI failures, retries, recovery, or executable consequential transitions are not Owner-permission events.

`standing_authority.resolve_next_action` enforces this closure. `system_can_execute=False` alone returns discovery/remediation, never `HUMAN_GATE`. Pass raw `access_discovery` and `diagnostic_fallback` observations using the arguments of the existing reconcilers in `managed_project_contract.py`; the resolver recomputes their outcomes. A claimed `state`/`route` is not closure evidence. Existing channels, covered diagnostic bridges and unresolved bridge authority route back to the appropriate autonomous phase.

Honor the returned `route` when present. `CONTINUE_REMEDIATION` describes the original action's incomplete executability; a `CONTINUE` or `CONTINUE_DIAGNOSTIC` route means use the selected channel, then re-resolve the original action. It does not request code changes or Owner permission by itself. Bridge and authority-resolution routes select their respective Supervisor/Builder phase.

When diagnostic fallback is exhausted, follow `REENTER_ACCESS_DISCOVERY` and obtain fresh operational observations after that fallback. Supply them as `post_fallback_access_discovery`; the resolver recomputes them before considering an access gate. An absent post-fallback snapshot returns the re-entry route, an incomplete one continues discovery, and a newly found path continues automatically. Supervisor verifies the observation order against real evidence; do not relabel the earlier snapshot as fresh. This bounded re-entry is part of closure, not permission to loop indefinitely.

Before a human interruption, set `convergence_complete=True` only after Supervisor verifies that currently executable covered work which does not depend on that human step is complete. This also applies to new uncovered material decisions; it never authorizes implementing the uncovered decision. Keep `controls_satisfied` scoped to the prerequisites of the exact next action: a manual test's future result is not a prerequisite for asking the person to perform it, but failing automated checks must be remediated first.

For an actual manual action, supply `human_intervention={"kind": ..., "evidence": ...}`. Evidence must identify the exact step, its canonical acceptance requirement or observed platform constraint, and why the available automation cannot perform it. Supervisor verifies it independently; the object is an audit index, not proof by itself.

- `PHYSICAL_DEVICE_TEST`, `HARDWARE_INTERACTION`, `OWNER_HELD_INPUT`: evidenced physical interaction or information only the Owner possesses may bypass operational access discovery.
- `PLATFORM_CONSENT_REQUIRED`: account MFA/consent may become a gate only after complete operational discovery and native/self-provisioned diagnostic closure.
- `ACCESS_PATH_UNAVAILABLE`: complete discovery and diagnostic exhaustion still require an identified action only the Owner can perform.

Missing evidence remains Supervisor remediation/authority resolution. A technical failure cannot be relabelled as a manual intervention. Apply the existing anti-loop protocol if further evidence cannot be obtained; do not fabricate a gate or repeat exhausted discovery.

## External target-project policy

Project Leader does not require a central registry of projects.

For external target repositories in DURABLE_CONTROL, use `CENTRAL_CONTROL_V1` bound to the exact canonical Project Leader revision. Normal FAST_E1 remains bounded by the Owner objective, target architecture, live state, and safety ceiling without requiring a durable Task Authorization.

If an intentionally maintained target-specific central policy is explicitly selected, bind it. Otherwise use:

`generic-project-policy.json`

The generic policy is only a safety ceiling. Supervisor must still reconstruct the target project's architecture and narrow every task's mutation scope and actions accordingly.

## Mutation-scope enforcement

Use:

`python control/validate_records.py scope <task-path> <changed-file> [<changed-file> ...]`

Every changed file must match the Task Authorization `mutation_scope`.

## Recovery

Run `control.standing_authority.resolve_recovery_action` before creating Recovery-only persistence for an already-authorized technical failure. If the objective and standing delegation remain valid, the work stays in the same workstream, the effect is bounded `E1_RECOVERABLE_PROJECT_LOCAL`, and no architecture/security/permission/Human-Gate boundary changes, the resolver returns `COMPACT_RECOVERY` with authority kind `DERIVED_COMPLETION_AUTHORITY`.

Compact Recovery follows `FAIL -> DIAGNOSE -> REMEDIATE -> TEST -> VERIFY -> CONTINUE`. Do not create separate control-only commits for failure observation, repeated standing authority, retry intent, planning, or transient validation state when CI/logs/PR evidence plus the next technical checkpoint preserve sufficient traceability.

`APPEND_ONLY_V1` is the durable Recovery mechanism, not a mandate to persist every failure. Use `.project-leader/recovery-events/<task-id>/` when a true same-action rerun, interruption-safe counters, replan/no-progress state, ambiguous-write causality, an explicit immutable-audit requirement, a boundary/Human-Gate outcome, or another certification requirement must survive context. A GitHub workflow `run_attempt > 1` still requires the causal journal; a fresh run on a new technical remediation SHA does not require one merely because an earlier implementation failed.

Validate a required/present journal with:

`python control/validate_records.py recovery-journal <event-1> <event-2> ...`

The journal remains hash chained and monotonic. Validation derives attempt, identical-failure and no-progress budgets across the whole task/strategy history, so interleaving fingerprints cannot reset a budget. Generic journal validity is separate from retry certification: a legitimate replan or Human Gate does not invent a retry, while a true retry still requires its causal authorization. External evidence verification also inspects task-local Git history and rejects deletion or rename of previously persisted append-only events, including the case where the final directory is absent. Mutable checkpoints remain only for historical/legacy continuity.

## Trust model

`control/trusted_gate.py` evaluates untrusted task data against policy loaded from trusted base/control-plane state.

The `pull_request_target` trusted workflow never executes PR-head control code. Before promotion it rejects incomplete PR-file evidence (including the GitHub 3000-file API ceiling), re-reads the live base ref, and requires the event base to remain current.

For Project Leader-local certification, required CI is bound to the trusted workflow identity as well as its display name: workflow ID/path, event context, repository, implementation SHA and expected PR/base context must agree. A homonymous workflow cannot substitute for the required workflow. In DURABLE_CONTROL, immutable authorization proof also verifies that the base-to-authorization history contains only the canonical Task Authorization file; material implementation starts after that authorization-only commit.

For external targets, target base SHA and canonical control-policy revision are independent states.

Required CI claims are verified against live GitHub data by exact workflow/run/SHA evidence.

## Historical compatibility

Archived v1 schemas remain because historical records are part of the audit trail:

- `task-authorization.v1.schema.json`
- `worker-result.v1.schema.json`

They are not templates for new work.

Historical v2 records that used old `human_gates` terminology remain readable for audit, while current runtime records use `transition_controls`. Historical transition results remain readable under their original record contract; newly created/modified transition results use the current state semantics, so `SUCCESS` cannot retain blockers and `FAILURE`/`NOT_EXECUTED` remain authorized, auditable, non-promotable outcomes.

## Validation commands

Examples:

`python control/validate_records.py task <task-path>`

`python control/validate_records.py result <result-path>`

`python control/validate_records.py pair <task-path> <result-path>`

`python control/validate_records.py recovery-journal <event-1> <event-2> ...`

`python control/validate_records.py transition-auth <authorization-path>`

`python control/validate_records.py transition-result <result-path>`

`python control/validate_records.py transition-pair <authorization-path> <result-path>`

GitHub Actions execute positive and negative contract tests on pull requests and pushes to `main`.

## Runtime generation and package provenance

Runtime loader contract v1 requires loader version >= 1. Resolve canonical Project Leader `main` once to an exact `RUNTIME_CANONICAL_REVISION` and read the runtime contract bundle from that one immutable SHA. `control/managed_project_contract.py::pin_runtime_bundle` is the executable invariant used by tests; an incompatible loader refuses an override rather than mixing generations.

Plugin ZIPs are built from an exact allowlist. Symlinks, unexpected files, missing assets, identity mismatch, invalid SemVer and invalid GitHub connector metadata fail packaging. `plugin-manifest.json` schema v2 records repository, source revision, packaging workflow, run ID, plugin ZIP hash/size and hashes/sizes for every packaged file. This provenance is an audit binding; it is not a cryptographic signature or a claim that every external ChatGPT host has been exercised.
