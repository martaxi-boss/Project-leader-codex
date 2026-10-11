# Project Leader runbook

## Architecture

Use **Project Leader** as the primary ChatGPT plugin.

Project Leader has four internal operating phases:
- Consultant
- Supervisor
- Builder
- Recovery Guardian

A separate **Recovery Guardian** plugin is also available for explicit recovery after an interrupted or failed session. It does not passively watch another ChatGPT chat.

## Normal invocation

`Open the relevant ChatGPT Project -> New chat -> @Project Leader -> wait for Owner instruction`

Calling `@Project Leader` only activates it. It does not automatically authorize an audit or construction work.

Before replying or routing substantive work, Project Leader silently runs `CANONICAL_RUNTIME_BOOTSTRAP` when GitHub read access is available. Loader contract v1 (minimum loader version 1) resolves canonical `main` exactly once to an exact `RUNTIME_CANONICAL_REVISION`; plugin metadata, Skill and subsequent control-plane documents for that decision are read at that same immutable SHA. If the loaded runtime copy is behind, enter `RUNTIME_SYNC_STALE -> RUNTIME_CANONICAL_OVERRIDE_ACTIVE` and continue under that pinned generation immediately. An incompatible loader refuses the override rather than mixing generations. Do not use marketplace propagation lag as a reason to stop, ask the Owner to sync again, or keep executing obsolete rules. Bare activation remains a short ready response after bootstrap.

## Runtime loop

Default normal E1 path:

`RECONSTRUCT MINIMUM -> EXECUTE -> TEST -> CORRECT -> HYGIENIZE -> VALIDATE -> CONTINUE`

Use `PROGRESS_OVER_PROCESS`. Normal reversible E1 does not need an authorization-only commit or role handoff. Load durable control only when `resolve_control_mode` identifies a material boundary or continuity/audit risk.

`FUNCTIONAL_CONVERGENCE_FIRST`: diagnostics must select a correction. Apply `DIAGNOSIS_MUST_BUY_A_DECISION` before adding probes. If a recent change makes an earlier phase fail, apply `REGRESSION_FIRST` with last-known-good vs first-known-bad and use selective safe rollback when confirmed and reversible.

Normal control path: `RECONSTRUCT -> ANALYZE -> EXECUTE -> TEST -> DIAGNOSE -> CORRECT -> HYGIENIZE -> VALIDATE -> CONTINUE`. Consultant, Supervisor, Builder and Recovery Guardian are internal capabilities selected when useful; they are not a mandatory serialized chain. A still-valid standing/task authority envelope is not reissued between ordinary covered E1 operations.

For covered E1, run the smallest useful formatter/linter/affected-test checks against the exact current candidate *before pushing* a commit that would automatically trigger heavy CI, when those checks can run. `resolve_e1_validation_preflight` routes absent or stale focused evidence to focused checks, a current focused failure to direct Recovery repair, and a current pass to the required final validation sequence. A nonmaterial edit invalidates an earlier candidate's focused PASS. When focused checking is genuinely unavailable or irrelevant, proceed to mandatory full CI with a one-line reason in the existing PR/summary; do not demand a new tool, administrative record or Human Gate solely for this optimization. Do not pretend this guard suppresses GitHub's automatic `push`/`pull_request` triggers. Material E2/E3 workflow and independent Supervisor evidence are unchanged.

Keep tool and agent context proportional: read status/failed-job summaries before full logs, reuse exact run IDs and already-proven invariant inputs, and communicate only actionable deltas. Do not re-fetch unchanged large outputs or create role handoff artifacts for ordinary E1. Persist full evidence only for causal retry, security, continuity or material audit, and never sacrifice required provenance or independent Supervisor review.

Before explicitly dispatching or rerunning CI, deduplicate by exact workflow name + target SHA + event context. Reuse an existing active or successful exact-context run; route an exact-context terminal failure/cancellation/timeout to Recovery; dispatch only when no exact match exists. Automatic GitHub runs from different event contexts are coalesced as evidence and are not a reason to create more runs.

Before accepting CI for an implementation head, reject cherry-picked evidence: for every required workflow, bind the trusted workflow identity (ID/path), repository, implementation SHA and expected event/PR/base context, then inspect the latest same-SHA `push`, `pull_request`, and selected evidence context. A homonymous workflow never substitutes for the required workflow. Any latest active, failed, cancelled, or timed-out relevant context blocks terminal acceptance until that context becomes terminal-success or is otherwise legitimately superseded by a later successful run in the same context.

A CI-certified implementation head is the last material mutation point for that certification. Final evidence commits may follow only when they are task-local `.project-leader` result/recovery/transition-result metadata. Any other file change after `implementation_head_sha` is material drift: invalidate the old certification, choose the new implementation head, and run the required CI again before terminal acceptance.

Automatic CI triggered only because an allowed evidence-only descendant was pushed is not task-certifying CI. Do not reopen task Recovery or move `implementation_head_sha` solely because such an incidental descendant run is active or fails. If the repository's branch protection/ruleset explicitly requires checks on the current PR head, handle those runs as a separate merge-governance condition. They may delay consequential-transition readiness, but recovery must not create another evidence commit merely to satisfy a check on the prior evidence commit.

External CI waits are transient control states, not stopping points. When Project Leader enters `WAITING_EXTERNAL_CI`, bind the exact run IDs and re-read them at the bounded cadence. If live GitHub state becomes terminal while the stored state still says waiting, classify `STALE_WAIT_STATE`: all-success returns immediately to Supervisor audit/validation/continuation; failure/cancellation/timeout routes to Recovery. After any interrupted/resumed Work session, re-read the bound runs before dispatching anything so completed work is never repeated merely because the UI remained on “processing”.

The Work execution must not use the visible “processing” spinner or a blocking wait as the mechanism that keeps an external-CI wait alive. While the execution can still call tools, run an active liveness cycle: fresh exact-run read every bounded interval, reconcile, route. After two intervals without control-plane progress, enter `LIVENESS_RECONCILE_REQUIRED`, reconstruct task/PR/head/run bindings and re-poll before doing anything else. This forced reconstruction does not retry CI and does not create a Human Gate when the bound run is still legitimately active.

Apply the same liveness discipline to Project Leader-controlled internal operations, but do not misclassify them as external waits. A legitimate external wait has an external dependency plus an observable state/handle and bounded re-check. Repository compare/diff, audit, reconciliation, local validation, evidence reading, and planning are internal operations and should normally complete inside a bounded tool/result cycle.

Before any potentially broad internal compare/reconstruction/audit, run `BOUNDED_STATE_PREFLIGHT`: default-branch HEAD, open PRs, active workflow runs, plus current task/branch/implementation head when available. If this state vector already resolves the next decision, skip the broader operation. Reuse unchanged preflight dimensions while their refs/state remain valid; after a material change or interruption, refresh only the volatile dimensions. Otherwise narrow the next read to exact refs/files/run IDs/commit range. `CANONICAL_RUNTIME_BOOTSTRAP` remains only the canonical plugin manifest + Skill reads and must not start target-repository comparison.

If an internal operation remains current across two liveness observations without a new result, durable evidence, or control-state transition, classify `INTERNAL_OPERATION_STALLED -> LIVENESS_RECONCILE_REQUIRED`. Recovery reconstructs durable state; if the existing evidence already answers the decision, skip the stalled operation and continue, otherwise change to a smaller/bounded read strategy. Do not repeat an ambiguous write. A frozen host/tool call cannot run Recovery until control returns; on return or a new activation after an unresolved internal operation, enter `LIVENESS_RECONCILE_REQUIRED` first, run `BOUNDED_STATE_PREFLIGHT`, and do not repeat the opaque call unless still proven necessary.

Repository branch-ref hygiene workflows remain non-blocking maintenance. Continuous operational hygiene is different: whenever mutation-capable work makes code/configuration/references/workflows/probes/docs/stale bindings obsolete and cleanup is recoverable inside the same authority, remove or neutralize that residue in the same implementation/recovery cycle. Do not create a separate hygiene authorization/handoff for that consequence. Explicit read-only/diagnostic/no-change mode permits detection/reporting only and forbids hygiene writes.

Compatibility invariant: **Repository hygiene is non-blocking maintenance**. The legacy phrase refers to the branch-ref sweep workflow; it does not defer `CONTINUOUS_HYGIENE_ACTIVE` cleanup caused by the current change.

1. Reconstruct the smallest live state needed.
2. Use Consultant only for material product/architecture/requirements/reuse/risk uncertainty.
3. Supervisor establishes the bounded task envelope and protects material boundaries; do not reauthorize subordinate covered E1 operations while that envelope remains valid.
4. Builder executes planned implementation and same-cycle hygiene.
5. A recoverable technical failure routes to Recovery Guardian, which verifies effects, diagnoses, corrects directly inside covered E1 authority, tests, hygienizes related stale residue, verifies and continues.
6. A blind same-action retry is forbidden. Retry only with material change, new evidence, new hypothesis, justified strategy change, corrected observer/probe, or a genuine transient retry basis; otherwise replan.
7. Supervisor re-enters for materially independent audit, consequential transition resolution, boundary change, or terminal acceptance—not as a signature between every normal operation.
8. Before any Human Gate, exhaust convergence work and operational access discovery when relevant.
9. Stop only at objective completion, a proven genuine Human Gate/new uncovered material decision, or technically unavailable essential dependency after the required preflights.

## Access discovery preflight

Use `FIRST_SUFFICIENT_SAFE_PATH_WINS`: once a safe sufficient channel exists, use it and resume the objective. If no sufficient path is found and an access Human Gate is being considered, `FORCED_OPERATIONAL_ACCESS_DISCOVERY` must inspect direct session capabilities, a native tool-capability inventory, target-repository automation, reasonably discoverable operational repositories, and historical execution evidence for candidate channels. Search for operational paths, not secret values.

A read-only lookup in another repository is reference discovery and is compatible with one-mutable-repository-per-task isolation. If an adjacent operations repository contains an existing GitHub Actions/SSH/deploy channel, classify it before stopping:

- `ACCESS_PATH_FOUND` -> use the non-mutating path and continue;
- `ACCESS_PATH_REQUIRES_SEPARATE_TASK` -> when authority covers it, create a separate bounded task targeting that operations repository, execute it there, then return to the original project;
- `ACCESS_PATH_REQUIRES_AUTHORITY_RESOLUTION` -> Supervisor resolves standing/derived authority before any Owner interruption;
- `ACCESS_DISCOVERY_INCOMPLETE` -> continue discovery, never stop;
- `ACCESS_PATH_UNAVAILABLE` -> only now may an access Human Gate become a candidate, still subject to the normal Human Gate closure test.

Do not confuse "this session has no SSH tool" or "this connector method lacks one endpoint" with "the project has no operational access path".

### Non-interactive diagnostic fallback

When an access path has been found but its execution fails, do not immediately replace the connector with a browser or ask the Owner for approval. Inventory the native capabilities that are actually available and exhaust the non-interactive evidence path first.

For GitHub Actions, inspect the available run metadata and, where exposed, jobs, step summaries, job logs, artifacts, checks/check-runs/annotations or statuses, workflow definitions, repository-return evidence, and relevant historical runs. If one surface is absent because the workflow failed before jobs or steps existed, record that absence and continue through the remaining native surfaces instead of treating it as connector-wide incapability.

Prefer diagnostics that return to GitHub through sanitized logs, artifacts, checks, or other durable evidence. A separately bounded operations task that creates or fixes such a return path is preferable to requiring terminal copy/paste when current authority covers it.

After native/read-only evidence is exhausted, run the universal self-provisioning check before any Owner prompt. Ask whether Project Leader can create a bounded diagnostic bridge itself: for example an ephemeral GitHub Actions workflow on a dedicated task branch in the active repository, a temporary read-only probe, or a separate bounded task in an existing operations repository with the necessary environment reachability. The bridge must use minimum permissions and existing authorized secret names, must emit only sanitized diagnostics, and must not create production side effects, incur cost, expose credential values, or combine mutations across repositories in one task.

If a bridge is provisionable and current authority covers it, create/use it automatically and continue. If it is provisionable but authority is unresolved, route to Supervisor authority resolution first. Do not ask the Owner to choose or route the tool.

Route this preflight as:

- `NONINTERACTIVE_FALLBACK_INCOMPLETE` -> keep discovering native or self-provisioned diagnostic surfaces;
- `NONINTERACTIVE_PATH_FOUND` -> continue diagnosis automatically;
- `DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK` -> create/use the bounded diagnostic bridge automatically when covered;
- `DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION` -> Supervisor authority resolution;
- `NONINTERACTIVE_FALLBACK_EXHAUSTED` -> re-enter `FORCED_OPERATIONAL_ACCESS_DISCOVERY` for another operational path;
- `PLATFORM_CONSENT_REQUIRED` -> only after native evidence, repository-return paths, self-provisioning, covered operations paths and authority resolution are exhausted may a host-enforced browser/tool-consent action become an `EXCLUSIVE_HUMAN_INTERVENTION` candidate.

The Owner must never be used as a routing mechanism between tools that Project Leader can already use or safely provision under existing authority. Legitimate manual gates remain actions that genuinely require a person, such as device/physical tests, MFA/account consent, CAPTCHA or hardware interaction.

## Recovery rules

Follow `RECOVERY_PROTOCOL.md`.

Key requirements:
- verify a possibly-completed write before retrying it;
- maximum 3 attempts for the same transient action fingerprint;
- after 2 identical failures, reconstruct/replan;
- after 3 no-progress iterations, stop that strategy;
- on later resumption, rebuild state from GitHub instead of trusting an interrupted chat response;
- for v2 tasks, apply Recovery Compaction before persisting recovery-only state. If the objective/standing delegation remain valid, the same workstream stays bounded to E1, and no architecture/security/permission/Human-Gate boundary changes, use `DERIVED_COMPLETION_AUTHORITY` and continue `FAIL -> DIAGNOSE -> REMEDIATE -> TEST -> VERIFY -> CONTINUE` without control-only commits. Persist append-only `.project-leader/recovery-events/<task-id>/` only when durable continuity/governance is required (including a true `run_attempt > 1`, interruption-safe anti-loop/replan state, ambiguous-write retry causality, explicit immutable audit, or boundary outcome); when present/required, its causal ordering remains mandatory. Use mutable checkpoints only for legacy v1 continuity;
- never treat a legacy v1 checkpoint with stored `status=ACTIVE` as a live task by itself. Corroborate it with a current branch, open PR, or active CI. If a terminal result exists or no live workstream exists, classify `STALE_LEGACY_CHECKPOINT`, preserve the snapshot, and continue without reviving it;
- never certify a consequential transition without a durable exact-revision transition authorization/result pair; legacy gaps stay explicitly unverified.

## Platform outage

If ChatGPT itself is unavailable, no ChatGPT agent can continue at that instant. GitHub remains the durable state. When service returns, `@Project Leader` or `@Recovery Guardian` can reconstruct and resume without requiring the Owner to re-explain repository state.

## Repository hygiene

Use `.github/workflows/repository-hygiene.yml` for branch cleanup. It implements three bounded cases: (a) the head of a merged same-repository pull request; (b) a non-`main` branch without an open pull request whose tip is proven by GitHub to be an ancestor of canonical `main`; or (c) a non-`main` branch without an open pull request for which canonical `main` contains a durable `CURRENT_OWNER_INSTRUCTION` transition authorization for action `delete_owner_authorized_superseded_non_main_branch_refs` whose target branch name and exact revision both match the live ref. The sweep preserves `control/merge-authorization-*` evidence refs unless case (c) applies. An Owner-authorized revision mismatch is preserved even if ancestry would otherwise permit deletion. Branch-ref deletion never rewrites commit history and must never target `main`.

Canonicalizing evidence files alone does not establish ancestry or exact purge authority. Audit each obsolete control ref, preserve its valuable evidence in canonical `main`, and compile its exact purge authorization from the Owner's existing hygiene instruction before the sweep deletes it. Do not restore broad content-equivalence traversal removed by task 058R or rewrite historical authority/results. The sweep runs after same-repository merges, on manual dispatch, and after pushes to `main`. Verify the live refs after that run before reporting cleanup complete; unavailable evidence, divergent refs and open-PR heads remain preserved for bounded Recovery/audit.

## Standing authority and Human Gates

Load and validate `projects/standing-authority.json` before consequential transitions and again after session recovery when authority routing matters.

A development-branch integration remains explicitly task-bounded: the task must include `merge_development_branch`, the live PR base must not be `main`, and no unrelated effect may be introduced.

For an action listed in current `transition_controls` / `required_transition_controls`, do not jump directly to an Owner prompt. Historical `human_gates` names are compatibility-only evidence. First resolve the action:

1. canonical project state already covers the exact effect;
2. the current system/tools can execute it;
3. exact target, scope, required CI/validation/evidence, and Supervisor controls pass.

When all three hold, record an exact transition authorization with source `STANDING_OWNER_GRANT`, execute the transition, verify the durable result, record the transition result, and continue automatically. If controls do not yet pass, remediate/recover and revalidate instead of asking the Owner.

Use `HUMAN_GATE` only for `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.

Apply `control/standing_authority.py::resolve_next_action` using the closure contract in `control/README.md`. `system_can_execute=False` alone starts discovery/remediation. Feed raw operational/diagnostic observations, complete the self-provisioning check, and independently verify the exact `human_intervention` evidence. A claimed exhausted state cannot replace these inputs. Set `convergence_complete=True` only after currently executable covered work independent of the human step is finished. Evidenced physical/device tests, hardware interaction and Owner-held input may then be manual gates without unrelated GitHub diagnostic discovery. Automated prerequisites must pass; the requested manual test's future result is not one of those prerequisites. New uncovered material decisions also require convergence, without authorizing the uncovered effect.

Action names such as merge to `main`, release, deploy, governance change, secret/infrastructure/data transition, or paid/commercial activation do not create Human Gates by themselves.

Project isolation remains strict: one mutable target repository per task. The Project Leader project is not a container for other project implementations; its skill may operate on another project only when that project is the active target context.

## Trust boundary

The roles are logical operating modes, not independent security principals. Consultant and Supervisor behave read-only; Builder writes only inside the authorized scope; Recovery Guardian only restores an already-authorized flow and never expands authority.

## Durable-control compatibility path

When a material boundary selects durable v2 control:

1. Reconstruct the live target repository, target base SHA, and the exact canonical Project Leader revision.
2. For Project Leader-local work, bind policy with `LOCAL_BASE_V1`. For an external target project, bind with `CENTRAL_CONTROL_V1` to the exact canonical Project Leader revision. Use an explicitly selected target-specific central policy when one exists; otherwise use `control/generic-project-policy.json`. No central registry enrollment is required.
3. Compile the task with the target base SHA plus the independent control repository/revision/policy path/profile/digest.
4. Require the task's mutation scope and allowed actions to remain inside that trusted policy ceiling.
5. Require policy-minimum gated effects, validation, and CI. A gated effect still requires transition authority/evidence, but the standing grant may satisfy the authority without a new Owner prompt.
6. Apply Recovery Compaction first; use append-only recovery events only when retry/replan history must be durable or causal certification explicitly requires it.
7. Bind the Worker Result to the exact Task Authorization commit+SHA-256 and emit real GitHub Actions run IDs.
8. Verify authorization immutability, task/result compatibility, target CI evidence and implementation-head/final-head ancestry from trusted control-plane logic.

Repository branch protection/rulesets remain an external GitHub governance layer. The trusted workflow strengthens PR enforcement but does not make an unprotected `main` equivalent to a protected branch.

## P1 audit hardening invariants

For Project Leader-local trusted PRs, compare the PR API's declared changed-file count with the structured file list and fail closed at the 3000-file ceiling. Re-read the live base ref and reject a stale event-base binding. Immutable task authorization must be an authorization-only history point; material implementation in the base-to-authorization range invalidates certification.

Recovery append-only state is historical, not merely the current directory listing. A previously persisted event may not disappear, be renamed or be rewritten. Validate generic journals independently from retry-only causality, and derive anti-loop budgets across interleaved fingerprints.

Consequential `FAILURE` and `NOT_EXECUTED` outcomes remain normal auditable records when bound to prior authorization and blockers; they never certify promotion. New `SUCCESS` evidence cannot carry residual blockers. Legacy evidence remains readable rather than being rewritten to fit the current contract.

Plugin packages must pass allowlist/metadata checks and expose source/build provenance in the generated manifest before artifacts are uploaded.

## GitHub Actions event-policy readiness

Checked against GitHub documentation on 2026-10-07: the default policy for `pull_request_target` on affected public repositories is in evaluate mode and GitHub states enforcement begins on 2026-11-02. This repository intentionally uses `pull_request_target` for trusted-base PR governance, so the trigger must not be changed casually to `pull_request` merely to avoid the policy.

Before 2026-11-02, repository governance must verify the applicable Actions event-policy insight and either explicitly allow the required `pull_request_target` workflows or safely migrate them with equivalent trusted-base guarantees. This check is external GitHub governance state, not evidence that the current workflow is broken today. Project Leader may document and re-check the state automatically, but changing the repository Actions event policy requires its own exact consequential-transition authority and an available administrative capability.

