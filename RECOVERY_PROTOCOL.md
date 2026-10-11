# Recovery and anti-loop protocol

## Purpose

Make Project Leader resilient to interrupted responses, transient API/tool failures, ambiguous write outcomes, repeated no-progress loops, and later resumption from GitHub durable state.

This protocol is used automatically by Project Leader and is also the operating contract for the standalone Recovery Guardian plugin.

## Failure classes

1. **Transient** — timeout, connection reset, rate limit, temporary server error, service-busy response, retryable workflow/API error.
2. **Ambiguous write** — a mutation may have completed but the client response was lost or errored.
3. **Permanent/configuration** — invalid input, missing permission, missing resource, policy denial, unsupported operation.
4. **Loop/no-progress** — the same intended action and observed result repeat without durable progress.
5. **Authority/manual boundary** — the next irreducible step is either `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`. An action name or effect class alone does not create this boundary.

## Recovery state machine

For a covered recoverable E1 failure:

`FAILURE -> CLASSIFY -> VERIFY DURABLE STATE -> DIAGNOSE -> DIRECT REMEDIATE -> TEST -> VERIFY -> HYGIENIZE -> CONTINUE`

Use Supervisor/authority resolution only when the attempted recovery reaches a material scope, architecture, security/trust, permission/credential, consequential-transition, or genuine Human-Gate boundary. `BLOCKED` is terminal only after bounded replan/access paths are exhausted and no safe continuation remains inside the mandate.

## Transient failures

- Re-read durable state before retrying whenever a mutation may have occurred.
- Default maximum: 3 total attempts for the same action fingerprint.
- Use increasing delay when the runtime supports waiting; otherwise perform a fresh state read between attempts.
- Stop retrying when the error becomes permanent or no progress is being made.

## Ambiguous writes

Never repeat a write until the source of truth proves it did not happen.

Examples:

- branch creation -> search the branch;
- commit -> inspect branch head/history;
- PR creation -> search PRs by head/base/title/task identifier;
- PR update/comment -> fetch the current PR/comments;
- merge -> inspect merged state and main ancestry;
- workflow dispatch/retry -> inspect workflow runs;
- file write -> fetch the exact path/blob/commit.

If the intended side effect is already present, treat the write as completed and continue.

## Loop breaker

Fingerprint repeated work as:

`task + target + intended action + observed result`

A same-action retry is allowed only when at least one material basis exists: `MATERIAL_CHANGE`, `NEW_EVIDENCE`, `NEW_HYPOTHESIS`, `STRATEGY_CHANGE`, `OBSERVER_FIX`, or a genuinely `TRANSIENT_FAILURE`. A blind identical retry is `BLIND_RETRY_BLOCKED` and must route to `RECOVERY_DIRECT_REPLAN`.

- After 2 identical failures, reconstruct and materially change the hypothesis/strategy rather than repeat the same action.
- After 3 no-progress iterations overall, stop that strategy and persist replan state when continuity requires it.
- Recovery Guardian owns that technical replan while the task remains covered E1; do not bounce between Builder/Consultant/Supervisor merely to restate the same fault.
- Escalate to Supervisor only when the new plan crosses a real authority/architecture/security/consequential boundary. Use `HUMAN_GATE` only after the standing-authority resolver proves `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.

## Durable recovery checkpoint (legacy v1)

For legacy v1 tasks only, when retry state, loop counters, or strategy changes must survive a chat/session interruption, persist:

`.project-leader/checkpoints/<task-id>.json`

using `control/recovery-checkpoint.schema.json`.

The checkpoint records the last durable step, current action fingerprint, attempt count, identical-failure count, no-progress iterations, strategy generation, last error, and next step. It must not contain secrets or private conversation text and never grants authority.

Legacy checkpoint liveness must be reconstructed, not trusted from the stored `status` field. `ACTIVE` is actionable only when current GitHub state independently corroborates a live workstream (for example a live branch, open PR, or active CI). If a terminal result exists, or no such live workstream exists, classify `STALE_LEGACY_CHECKPOINT`, preserve the historical checkpoint unchanged, and do not use its old `next_step` or counters to resume work.

Update the checkpoint after a material failure/replan and before relying on a retry counter that must survive interruption. On resume, read and validate it before deciding whether another attempt is allowed.

## Resume after interruption

On a new turn after an interrupted response:

1. Identify the active project and last bounded task from current Project context plus GitHub evidence.
2. Look for `.project-leader/tasks/<task-id>.json` in the target repository and validate it against `control/task-authorization.schema.json` when present.
3. For v2 tasks, read and validate `.project-leader/recovery-events/<task-id>/` and restore retry/no-progress state from the append-only journal. For legacy v1 tasks, read a checkpoint when present.
4. Re-read default branch, task branch, open PRs, task-related commits, and CI/workflow state.
5. Determine the last durable completed step.
6. Verify whether any write that lacked a response already occurred.
7. Compare durable authorization evidence with any current Owner instruction. A task record may preserve authority but can never widen or override a newer instruction.
8. Re-read and validate `projects/standing-authority.json` when the next step is consequential.
9. Continue from the first incomplete step when the bounded task authority remains valid. If the next step is a consequential transition, return it to Supervisor for standing-authority resolution rather than asking the Owner by action name.

GitHub history without a compatible task authorization record can prove effects, but not the full original authorization envelope. If the current conversation also does not establish mutation authority, recover read-only and identify the exact authorization gap instead of guessing.

Do not require the Owner to remember exact SHAs or re-copy old role prompts when GitHub can safely reconstruct the state.

## Dictation ambiguity

Minor transcription errors may be resolved from context for read-only or easily reversible actions when intent is unambiguous.

Never infer a materially expanded scope, architecture/strategy change, trust/environment change, irreversible-risk choice, or other new material decision from ambiguous dictation. For a consequential action already resolved by canonical project state, use the standing-authority resolver and exact Supervisor evidence instead of asking again merely because of the action name.

## Standing authority during recovery

Recovery Guardian never creates authority, but it must preserve and reuse authority that already exists.

When a failure occurs inside a covered task:
- technical errors, failed CI, unsatisfied controls, stale evidence, ambiguous writes, and bounded justified retries are recovery/remediation work, not Owner authorization requests;
- if `resolve_recovery_action` returns `RECOVERY_DIRECT_REPAIR`, Recovery Guardian itself diagnoses, performs the minimum in-scope E1 correction, tests, applies related recoverable hygiene, verifies, and continues;
- if a blind retry or no-progress condition returns `RECOVERY_DIRECT_REPLAN`, Recovery Guardian changes hypothesis/strategy instead of repeating or handing the same fault around;
- Supervisor is required when recovery encounters a consequential next action, material boundary change, or independent acceptance checkpoint. It is not a mandatory handoff after every technical correction;
- if canonical project state covers a consequential effect and the system can execute it, Supervisor may issue an exact `STANDING_OWNER_GRANT` transition authorization and the flow continues autonomously;
- use `HUMAN_GATE` only when the next irreducible step is `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.

Recovery must not widen project scope or cross into another mutable repository. One mutable target repository per task remains mandatory.

For mutation-capable recovery, `CONTINUOUS_HYGIENE_ACTIVE` is implicit. Remove or neutralize stale project-local operational residue made obsolete by the correction when that cleanup is recoverable and covered. Preserve inert history, ADRs, immutable evidence and required audit trails. An explicit read-only/diagnostic/no-change instruction makes hygiene report-only.

Before returning an Owner interruption, apply `control/standing_authority.py::resolve_next_action` and the closure inputs in `control/README.md`. A missing-capability boolean or a claimed exhausted preflight state is insufficient. Recompute access and diagnostic outcomes from raw observations, including self-provisioned bridges and authority resolution. Require convergence of currently executable covered work independent of the human step plus evidence of the exact irreducible action. Physical/device tests, hardware interaction or Owner-held input may bypass operational discovery only when independently evidenced and automated prerequisites pass. Do not require the future manual-test result before asking for that test. New uncovered material decisions require convergence without authorizing their implementation. Unobtainable evidence follows the existing bounded anti-loop path; never fabricate a manual gate to terminate a technical failure.

After `NONINTERACTIVE_FALLBACK_EXHAUSTED`, perform the required `REENTER_ACCESS_DISCOVERY` with fresh operational observations and supply `post_fallback_access_discovery` to the closure resolver. An earlier access snapshot does not prove post-fallback reconciliation. A new path continues automatically; repeated exhaustion remains subject to the same anti-loop limits.

## Platform outage limitation

A ChatGPT agent cannot observe, control, or repair another ChatGPT conversation while the ChatGPT service itself is unavailable. It also cannot press UI retry buttons in a dead session.

Durable work therefore lives in GitHub. When ChatGPT becomes available again, Project Leader or Recovery Guardian reconstructs from GitHub and resumes from the last verified step.

## V2 Recovery Compaction and append-only recovery journal

For Task Authorization v2, `APPEND_ONLY_V1` remains the durable anti-loop and audit mechanism. It is **not** a requirement to create a separate control commit for every ordinary technical failure.

Before creating recovery-only persistence, evaluate `control/standing_authority.py::resolve_recovery_action`. Compact Recovery is allowed only while the objective is already authorized, the standing delegation remains valid, work stays in the same project/workstream, the effect is `E1_RECOVERABLE_PROJECT_LOCAL`, and there is no material architecture change, security/trust-boundary change, new permission/credential, genuine Human Gate, or new uncovered material decision.

When the closure passes, use `DERIVED_COMPLETION_AUTHORITY` and execute:

`FAIL -> DIAGNOSE -> DIRECT REMEDIATE -> TEST -> VERIFY -> HYGIENIZE -> CONTINUE`

Do not create a separate commit merely to record failure discovery, repeat authority already covered by standing delegation, announce retry/replan intent, mirror transient CI/log state, or re-state validation that can be bound to the next technical checkpoint. Keep those observations in live execution, CI/logs/PR evidence, and the eventual Worker Result or one consolidated durable checkpoint after a meaningful technical transition.

Durable Recovery persistence is required when it materially protects continuity or governance, including:
- a true same-action GitHub rerun where `run_attempt > 1`, or another retry whose causal authorization must precede the effect;
- Recovery state/counters must survive interruption before the next technical checkpoint;
- repeated no-progress reaches a strategy replan or anti-loop boundary;
- an ambiguous write requires durable causal proof before repeating a mutation;
- an explicit immutable-audit requirement, Human Gate, BLOCKED outcome, authority change, security/trust boundary, or scope transition must survive context;
- the control artifact itself is required for execution or certification.

When durable persistence is required, use `.project-leader/recovery-events/<task-id>/<sequence>.json`. Each event remains schema-validated, hash-chained, contiguous and monotonic. For a durability-required retry, commit `FAILURE_OBSERVED` and `RETRY_AUTHORIZED` before the causally journaled retry, `REPLAN` before a durability-required strategy-generation change, and `RECOVERED` after successful certification.

The journal is causal evidence, not a retrospective narrative. A `RETRY_AUTHORIZED` record persisted after the retry started is invalid. Recovery-event files are append-only and must never be rewritten.

Terminal certification must fail when a durability-required Recovery journal is absent or causally invalid. A retroactive event is invalid. A journal containing `RETRY_AUTHORIZED` triggers structural verification even when the replacement CI run has `run_attempt=1`: required pre-retry events must be ancestors of `implementation_head_sha`, and terminal `RECOVERED` must follow that SHA.

An old-SHA GitHub rerun cannot be terminal Recovery proof when later journal authority exists. Before treating later CI failure as task Recovery, classify its SHA against `implementation_head_sha`; an evidence-only descendant is non-certifying and must not reopen Recovery. A normal bounded E1 remediation followed by a fresh technical commit and fresh CI is not, by itself, a reason to create recovery-only commits. A same-action retry without one of the material retry bases from the loop breaker is not authorized by compaction; replan instead.

Compatibility shorthand `FAIL -> DIAGNOSE -> REMEDIATE -> TEST -> VERIFY -> CONTINUE` remains the historical Recovery Compaction summary under `DERIVED_COMPLETION_AUTHORITY`; current REMEDIATE means direct Recovery Guardian repair and same-cycle hygiene.


## Waiting on external CI

An existing GitHub Actions run in `queued`, `waiting`, `pending`, `requested`, or `in_progress` state is not itself a failure.

During recovery of any external target project:

1. bind the wait to the exact GitHub Actions run IDs that satisfy the task's required CI;
2. before any explicit dispatch/rerun, deduplicate by exact workflow name + target SHA + event context: reuse an active/successful exact match, route a terminal non-success to Recovery, and dispatch only if no exact match exists;
3. classify the state as `WAITING_EXTERNAL_CI` only while at least one bound run is still active;
4. do not dispatch or retry the same workflow while any bound run is active;
5. re-read those exact run IDs from GitHub no more frequently than the canonical bounded polling cadence unless new evidence arrives;
6. if an active run has not updated beyond the profile's stale threshold, classify it as `INVESTIGATE_STALE_CI` and inspect the existing run/jobs first;
7. if every bound run is terminal but the stored/control state still says `WAITING_EXTERNAL_CI`, classify `STALE_WAIT_STATE`; all-success routes immediately to Supervisor audit/validate/continue, while any failure/cancellation/timeout routes to Recovery;
8. on session resume after interruption, re-read the bound run IDs before any new dispatch. Never use a stale chat/UI spinner as proof that CI is still active.
9. if the session ended before the exact wait binding was durably captured, reconstruct the candidate run set from the live task, current certifying SHA, required workflow names, PR/head state, and GitHub run contexts; bind the existing runs before any dispatch. Missing chat state is never permission to create replacement CI.
10. when recovering an interrupted or stale wait, reconstruct the existing run set from the live task, certifying SHA, required workflow names and PR/head before dispatching anything; candidate reconstruction and exact-run binding must converge on the already-existing GitHub runs rather than manufacturing replacement CI.

Use a default 5-minute polling cadence and a 60-minute stale threshold unless a stricter canonical project rule applies. A long external CI job inside that window remains normal external work, not a loop. A completed external CI run must never leave the control plane parked indefinitely in `WAITING_EXTERNAL_CI`.

### Active Work liveness guard

`WAITING_EXTERNAL_CI` is a persisted/control data state, not permission to block the Work execution on a UI spinner or an opaque wait primitive. While the current Work execution is still capable of making tool calls, it must keep control of the loop and perform a fresh exact-run GitHub read at each bounded polling interval.

If two polling intervals elapse without a control-plane state transition while the host execution is still live, classify `LIVENESS_RECONCILE_REQUIRED`. This is Recovery work, not a Human Gate and not a CI retry. Recovery Guardian must reconstruct the current task, PR/head, certifying SHA, required workflows and exact bound run IDs, then re-read GitHub and call the external-CI reconciliation again. A still-active run remains `WAITING_EXTERNAL_CI`; a terminal run routes immediately to Supervisor continuation or Recovery.

A frozen/unavailable ChatGPT Work process cannot execute this guard while frozen. That platform limitation must be reported honestly. On the next activation, the first action is durable GitHub reconstruction and stale-wait reconciliation; never ask the Owner to recreate CI or repository history merely because the prior Work process stopped running.

### Universal internal-operation liveness guard

Do not extend external-wait semantics to Project Leader's own internal control work. A legitimate external wait must have an independently pending external dependency (for example an active CI run, approval, provider response, or propagation event), an observable state/handle when available, and a bounded re-check. An internal compare/diff, repository read, audit, reconciliation, local validation, planning step, or evidence synthesis has no such external dependency and must not be parked as `WAITING_EXTERNAL_*` or left indefinitely on a UI spinner.

Before starting or restarting any broad internal compare/diff, reconstruction, audit, or history traversal, run `BOUNDED_STATE_PREFLIGHT`. Reconstruct only the minimal durable state vector first: default-branch HEAD, open PRs, active workflow runs, and the current task/branch/implementation head when available. If that evidence is sufficient, abandon the broader operation. Otherwise constrain the next read to the exact refs/files/run IDs/commit range required by the unresolved question. Repository branch-ref hygiene workflows are not part of this critical path unless hygiene itself is the task or an exact governance control requires it. Same-cycle operational cleanup under `CONTINUOUS_HYGIENE_ACTIVE` remains part of the current correction and must not be deferred merely because the background repository-hygiene workflow is separate.

While the Work execution is still tool-capable, internal operations are bounded to a tool/result cycle. If the same internal operation remains current across two liveness observations at the canonical 5-minute cadence with no new tool result, durable evidence, or control-plane state transition, classify `INTERNAL_OPERATION_STALLED`, then route immediately to `LIVENESS_RECONCILE_REQUIRED`. This is Recovery work, not a Human Gate.

Recovery Guardian then:

1. reconstructs the task, current branch/PR/head and relevant durable evidence before doing anything else;
2. if already-available evidence is sufficient for the pending decision, abandons the stalled internal operation and routes directly to Supervisor continuation;
3. otherwise changes to a smaller, bounded or alternate read strategy instead of repeating the same opaque operation;
4. verifies durable side effects before any write retry and never uses an ambiguous write as a liveness probe;
5. counts repeated `INTERNAL_OPERATION_STALLED` observations toward the existing no-progress/strategy ceiling.

If the host runtime or a connector call itself is frozen and does not yield execution control, Recovery cannot execute concurrently inside that frozen call. That platform limitation must be stated honestly. When control returns or a new session resumes after an unresolved internal operation, enter `LIVENESS_RECONCILE_REQUIRED` immediately, run `BOUNDED_STATE_PREFLIGHT`, reconstruct durable state first, and do not restart the same opaque operation unless the bounded evidence proves that exact read is still required.

For external target-project v2 tasks, append-only recovery events are authoritative when the Recovery Compaction closure says durable state is required or when a journal already exists. Ordinary bounded E1 remediation may remain compact with no control-only event commits. New mutable v1 checkpoints must not be used as the source of retry counters; a checkpoint may only summarize legacy state.

## Operational access discovery during recovery

When Recovery or Supervisor encounters missing direct access, do not convert that observation directly into `BLOCKED` or `HUMAN_GATE`. Run `FORCED_OPERATIONAL_ACCESS_DISCOVERY` first. Reconstruct available direct session capabilities, inventory the native capabilities of the connected service/tool, inspect the target repository for existing automation, inspect reasonably discoverable adjacent operational repositories read-only, and inspect historical workflow/run evidence for candidate access paths.

Read-only cross-repository discovery does not widen mutation authority. If an existing channel is usable only by changing another repository, route back to Supervisor for a separate bounded operations task and authority resolution. Recovery must never mutate the second repository under the first repository's task authorization.

If a discovered channel fails or one connector method lacks the needed detail, run the non-interactive diagnostic fallback before asking the Owner to approve a browser/tool switch. For GitHub Actions, dynamically inspect every available native evidence surface: run metadata, jobs, step summaries, job logs, artifacts, checks/check-runs/annotations or statuses, workflow definitions, repository-return evidence, and relevant historical runs. A workflow that fails before creating jobs/steps is evidence about that surface only, not proof that the GitHub connector is exhausted.

Prefer sanitized diagnostics returned through GitHub logs, artifacts, checks, or other durable repository evidence. If current authority covers a separate operations task that can create or repair such a return path, use that bounded task instead of delegating terminal copy/paste to the Owner.

Recovery must then run the universal self-provisioning check before any Owner prompt. This applies to every current or future managed project and does not require prior project registration. Determine whether Project Leader can safely create a bounded diagnostic bridge under existing authority in the active repository or, when necessary, in a separately authorized operations repository. GitHub Actions is one implementation path, not a project-specific assumption. The bridge must be temporary, auditable, least-privilege, read-only with respect to production state, and must return only sanitized evidence. It must not print credentials, mutate customer/runtime data, create paid resources, broaden architecture, or combine mutations across repositories under one task.

If a bridge is provisionable and authority covers it, Recovery returns to Supervisor/Builder to create and use it automatically. If provisionable but authority is unresolved, route to Supervisor authority resolution before any Owner interruption.

Route diagnostic fallback as `NONINTERACTIVE_FALLBACK_INCOMPLETE` while required native or self-provisioned surfaces remain unchecked, `NONINTERACTIVE_PATH_FOUND` when a non-interactive channel can continue, `DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK` when a covered bounded bridge task should be created automatically, `DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION` when Supervisor must resolve authority, `NONINTERACTIVE_FALLBACK_EXHAUSTED` when Recovery must re-enter `FORCED_OPERATIONAL_ACCESS_DISCOVERY`, and `PLATFORM_CONSENT_REQUIRED` only when all native evidence, repository-return paths, self-provisioning, separately taskable covered operations paths and authority resolution are exhausted and the host/platform itself requires user confirmation.

Do not search for replacement credential values or expose secrets. Discover channel metadata and proof of reachability only. An access Human Gate is eligible only after required discovery surfaces are complete and no direct, native non-interactive, repository-return, self-provisioned, separately-taskable, or authority-resolvable channel remains. A browser/UI/MFA/tool-consent prompt may become `EXCLUSIVE_HUMAN_INTERVENTION` only at that irreducible point. Physical/device testing, MFA/account consent, CAPTCHA, hardware interaction, or another action that only a human can actually perform remains a legitimate manual gate.

## Recovery journal continuity and mode separation

Append-only Recovery history is historical state, not merely the set of files visible at the final head. Certification must inspect task-local journal history and reject deletion, rename, or rewrite of an event that was previously persisted. A descendant commit cannot make a journal optional by deleting the directory.

Journal validation is mode-neutral first: sequence, hash chain, task/repository identity, strategy generations and history-derived budgets must be valid for every journal. Retry-specific requirements apply only when a true retry is required or a `RETRY_AUTHORIZED` event exists. A legitimate `REPLAN`, `HUMAN_GATE`, `BLOCKED`, or other durable non-retry journal must not invent a retry merely to pass certification.

Within one strategy generation, counters are derived across the whole journal, not only adjacent entries. Interleaving action fingerprints cannot reset attempt or identical-failure counters, and each `RETRY_AUTHORIZED` must strictly advance the attempt for that action. The bounded retry budget remains two retries (attempts 2 and 3) per action fingerprint before replan.

