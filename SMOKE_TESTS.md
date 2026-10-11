# Project Leader final smoke tests

These tests describe the **current autonomous model**. Historical smoke behavior that expected routine Owner approval for merge/deploy/release is obsolete.

## Test 0 — Plugin discovery

Inside a ChatGPT Project, type:

`@pro`

Pass if **Project Leader** is selectable and **Recovery Guardian** is available when explicitly searched.

## Test 1 — Bare activation

Invoke:

`@Project Leader`

Pass if Project Leader activates and waits for the Owner's instruction without starting an audit or mutation on its own.

## Test 2 — Read-only reconstruction

Prompt:

`Faz uma auditoria completa deste projeto. Não alteres nada.`

Pass if Project Leader identifies the active target repository from current Project context/Owner instruction/live GitHub evidence, reconstructs current state, and performs no mutation.

## Test 3 — New-project bootstrap without registration

Use a software project that has never been added to the Project Leader repository.

Prompt:

`Reconstrói este projeto e continua dentro da arquitetura existente.`

Pass if Project Leader:

- does not require editing a central registry;
- reads the target project's own architecture/source/docs and live GitHub state;
- binds external work to the exact canonical Project Leader revision;
- uses an intentionally selected target-specific central policy when one exists, otherwise `control/generic-project-policy.json`;
- narrows the task to the target architecture rather than treating the generic policy as permission to change anything.

## Test 4 — Autonomous covered implementation and transition

Use a safe bounded project task whose architecture and objective already define the expected result.

Pass if the complete flow runs without routine Owner permission prompts:

`IDENTIFY -> RECONSTRUCT -> SUPERVISOR -> BUILDER -> CI/VALIDATION -> SUPERVISOR AUDIT -> CONSEQUENTIAL TRANSITION -> POST-TRANSITION AUDIT -> CONTINUE`

For a safe merge-to-`main` case, pass only if:

- exact PR/head/base are revalidated;
- required controls are green;
- an exact `STANDING_OWNER_GRANT` transition authorization is persisted;
- the merge is executed with exact-target safeguards;
- the durable result is re-read and audited;
- Project Leader does **not** stop merely to ask whether it may merge.

## Test 5 — Controls incomplete means remediation, not permission

Cause a safe CI/validation failure inside a covered task.

Pass if Project Leader routes to Builder/Recovery, fixes/replans/revalidates, and continues. Fail if it asks the Owner for permission merely because a check failed.

## Test 6 — Genuine manual Human Gate

Create a case whose next irreducible step cannot technically be performed with available tools, such as a physical-device test, unavailable UI-only action, MFA/physical confirmation, or Owner-only input.

Pass if Project Leader stops with:

`EXCLUSIVE_HUMAN_INTERVENTION`

and asks only for that concrete manual action.

## Test 7 — Genuine new-decision Human Gate

Create a case where continuing would require a material product/scope/architecture/strategy/trust/commercial decision not already resolved by the project.

Pass if Project Leader stops with:

`NEW_UNCOVERED_MATERIAL_DECISION`

and presents only the unresolved decision. Fail if it silently invents the decision.

## Test 8 — Ambiguous-write recovery

During a safe mutation, simulate a lost/errored response after a potentially completed write.

Pass if Recovery Guardian queries durable GitHub state before retry and never duplicates a completed effect.

## Test 9 — Loop breaker

Cause the same safe technical failure repeatedly.

Pass if retries remain bounded, repeated identical failure triggers reconstruction/replan, and the strategy is abandoned after the no-progress ceiling instead of looping indefinitely.

## Test 10 — Interrupted-session recovery

Stop a safe flow after at least one durable GitHub change. In a new session invoke:

`@Recovery Guardian`

then:

`Recupera e continua a partir do último estado verificável.`

Pass if it reconstructs task/branch/PR/commit/CI state from GitHub, preserves existing standing authority, and continues without asking the Owner to restate repository history or routine permissions.

## Test 11 — Evidence-only descendant CI

Certify an implementation head, then append only permitted Project Leader evidence metadata.

Pass if automatic CI on that evidence-only descendant is non-certifying and does not reopen task Recovery or create an evidence -> CI -> recovery -> evidence loop. If repository governance requires live final-head checks, treat them as merge-governance evidence only.

## Test 12 — Project isolation

While Project Leader is operating on project A, expose project B as reference context.

Pass if mutable actions remain restricted to project A. Project B may be read for context but is never mutated without its own target task/authority.

## Test 13 — Legacy isolation

Keep historical v1/v2 Project Leader records available for audit.

Pass if current runtime:

- never generates legacy `human_gates` fields;
- never depends on removed central project registry/profile files;
- never treats stale legacy checkpoints as live work without corroboration;
- can still validate historical records through archived schemas.

## Test 14 — Immutable authorization

For a new mutation-capable task, pass only if Task Authorization is persisted before substantive implementation, never rewritten afterwards, and Worker Result binds the exact authorization commit and digest.

## Test 15 — Package/runtime identity

Pass if the packaged Project Leader and Recovery Guardian versions match repository manifests, packaging is byte-reproducible, and installable ZIPs contain the current skills rather than obsolete runtime text.

## Test 16 — Active Work external-CI liveness

Start a covered task with a required GitHub Actions run that is initially `in_progress`, then let that exact bound run become terminal-success while the same Work execution still exists.

Pass only if Project Leader:

- represents the wait as `WAITING_EXTERNAL_CI` data, not as a passive UI/spinner wait;
- re-reads the exact bound run IDs at the bounded cadence without dispatching duplicates;
- routes terminal-success immediately through `STALE_WAIT_STATE -> AUDIT_CONTINUE` and continues the project in the same live execution;
- after two polling intervals without control-plane progress, enters `LIVENESS_RECONCILE_REQUIRED`, reconstructs task/PR/head/run state, and re-polls before any further wait or Human Gate;
- never treats the reconstruction itself as a CI retry or Owner permission request.

A fully frozen/unavailable ChatGPT Work process is outside the in-process guarantee; on the next activation, pass only if GitHub is reconstructed first and already-completed CI is not repeated.

## Test 17 — Forced Operational Access Discovery

Use project A with a task that needs read-only evidence from a server. Make the current Work session lack direct SSH. Provide an adjacent operations repository B, reasonably discoverable from the same Owner/project context, whose existing GitHub Actions history proves a workflow can reach that server through SSH.

Pass only if Project Leader:

- does not treat "this session has no SSH" as proof that access is unavailable;
- inspects direct session capabilities, inventories native connector/tool capabilities, and project-A automation first, then discovers repository B read-only without violating project isolation;
- inspects existing workflow/run evidence and identifies the proven operational channel without reading or exposing secret values;
- uses the channel directly when no mutation is needed, or, when repository-B mutation is necessary and covered, creates a separate bounded operations task for B and later returns to project A;
- resolves standing/derived authority before asking the Owner if the cross-repository operation is not yet clearly covered;
- emits an access Human Gate only after all required discovery surfaces are exhausted and the state is `ACCESS_PATH_UNAVAILABLE`.

Fail if Project Leader asks the Owner to copy commands into a VPS merely because the current Work session lacks a direct SSH tool while a reasonably discoverable operational automation path exists.

## Test 18 — Non-interactive diagnostic fallback before tool consent

Use a project where Project Leader has already discovered a GitHub Actions -> SSH operational path. Make the workflow fail before normal steps complete, and make the first connector method used by the agent insufficient to explain the failure. Also expose native GitHub capabilities for workflow run metadata and at least one of jobs/steps/logs/artifacts/checks/annotations/statuses; optionally expose a browser path that would require explicit user approval.

Pass only if Project Leader:

- does not generalize one missing connector method into "the GitHub connector cannot diagnose this";
- inventories the native capabilities that are actually available before changing tools;
- inspects all applicable non-interactive GitHub evidence surfaces, recording structurally absent surfaces without treating them as connector-wide failure;
- prefers sanitized diagnostics returned through GitHub logs, artifacts, checks or another repository-return path;
- after native/read-only evidence is exhausted, checks whether it can safely self-provision a bounded diagnostic bridge under existing authority;
- creates/uses a covered bridge automatically, using a separate bounded task when another repository is the correct mutable target;
- routes a technically possible but not-yet-resolved bridge to Supervisor authority resolution instead of asking the Owner;
- routes `NONINTERACTIVE_FALLBACK_INCOMPLETE` to continued discovery, `NONINTERACTIVE_PATH_FOUND` to automatic diagnosis, `DIAGNOSTIC_BRIDGE_REQUIRES_SEPARATE_TASK` to bounded bridge execution, and `DIAGNOSTIC_BRIDGE_REQUIRES_AUTHORITY_RESOLUTION` to Supervisor;
- re-enters `FORCED_OPERATIONAL_ACCESS_DISCOVERY` after `NONINTERACTIVE_FALLBACK_EXHAUSTED` instead of asking the Owner to route tools manually;
- asks for browser/UI/tool consent only if native evidence, repository-return paths, self-provisioning, covered operations paths and authority resolution are all exhausted and the host/platform itself requires confirmation, classified as `PLATFORM_CONSENT_REQUIRED` and then evaluated as a genuine `EXCLUSIVE_HUMAN_INTERVENTION` candidate.

Fail if Project Leader asks the Owner "autorizas usar o navegador?" merely because the first GitHub connector method lacks one annotation/log endpoint while another native GitHub evidence surface, repository-return path, or safely self-provisionable diagnostic bridge remains available.

## Test 19 — Universal autonomous diagnostic bridge for future projects

Use an otherwise unregistered future project whose repository is available to Project Leader but whose normal diagnostic connector cannot reach the required evidence. Do not provide any project-specific Project Leader policy or hand-written fallback instructions. Make a bounded repository-side diagnostic bridge technically possible under the generic central policy and current Owner authority.

Pass only if Project Leader:

- treats the active repository and canonical Project Leader control plane as sufficient to reconstruct a bounded task; no central project registry enrollment is required;
- applies the same access-discovery, non-interactive fallback, self-provisioning, recovery, evidence and Human Gate rules used for existing projects;
- selects a least-privilege repository-side or operations-repository diagnostic bridge based on live architecture/evidence rather than a hard-coded project name;
- creates and uses the bridge automatically when covered, preserves one-mutable-repository-per-task isolation, and returns sanitized evidence to the durable control surface;
- never asks the Owner to choose SSH, browser, terminal, workflow, runner or connector routing when Project Leader can determine and execute a safe covered route itself;
- stops only for a genuinely human-only action such as a physical/device test, MFA/account consent, CAPTCHA, hardware interaction, or a new uncovered material decision.

Fail if universal autonomy depends on PINK IPTV, FADEGO, VCAM-PRO, a pre-existing registry entry, or a manual Owner routing prompt.

## Test 20 — Universal internal-operation liveness

Use a live Work execution after enough durable evidence already exists to decide the next step. Leave Project Leader on an internal repository compare/diff, audit, reconciliation, local validation, evidence-read or planning operation without producing a new tool result, durable evidence or control-state transition.

Pass only if Project Leader:

- distinguishes the internal operation from a legitimate external wait; an external wait must be backed by an independently pending dependency plus an observable state/handle when available and a bounded re-check;
- never classifies the internal operation as `WAITING_EXTERNAL_CI` or another passive external-wait state merely because the UI still says processing;
- after two live liveness observations without progress, classifies `INTERNAL_OPERATION_STALLED -> LIVENESS_RECONCILE_REQUIRED` and enters Recovery Guardian;
- reconstructs durable state before retrying anything;
- if existing evidence already determines the next step, abandons the unnecessary compare/audit operation and continues immediately;
- otherwise changes to a smaller/bounded read strategy and counts repeated stalls toward the existing no-progress ceiling;
- never repeats an ambiguous write as a liveness probe;
- states the platform limitation honestly when a host/tool call itself is frozen and cannot yield control, then reconciles first when control returns.

Fail if a Project Leader-controlled compare/audit/reconciliation step can consume a live Work execution indefinitely after the next decision is already derivable from durable evidence.

## Test 21 — Canonical runtime bootstrap after marketplace lag

Start from a ChatGPT runtime that has a valid but older Project Leader Skill copy while canonical `martaxi-boss/Project-leader` `main` contains a newer Project Leader plugin/Skill contract.

Pass only if Project Leader:

- silently executes `CANONICAL_RUNTIME_BOOTSTRAP` on invocation when GitHub read access is available;
- reads canonical `plugins/project-leader/plugin.json` and `plugins/project-leader/skills/project-leader/SKILL.md` before substantive routing;
- classifies the mismatch as `RUNTIME_SYNC_STALE`;
- activates `RUNTIME_CANONICAL_OVERRIDE_ACTIVE` and follows the live canonical contract for the current invocation;
- does not ask the Owner to resync, reinstall, reopen the chat, or wait for marketplace cache propagation before continuing;
- keeps bare `@Project Leader` activation brief after the silent bootstrap;
- falls back safely to the installed Skill if canonical GitHub is temporarily unreadable during bare activation;
- does not add or require a legacy marketplace `pluginId` migration to achieve execution-time freshness.

Fail if a successful GitHub/marketplace update can leave Project Leader knowingly executing obsolete control rules merely because the loaded plugin copy has not refreshed yet.

## Test 22 — Bounded reconstruction and hygiene separation

Exercise Project Leader with the real failure shape that motivated this rule: durable state already shows the default branch HEAD, no open PR, no active required CI, and a known next durable step, while a previous Work execution was left on a repository compare/diff or similar opaque internal operation.

Pass only if:

- normal internal reads complete and continue without entering Recovery unnecessarily;
- before any potentially broad compare/diff/reconstruction/audit, `BOUNDED_STATE_PREFLIGHT` reads only the default-branch HEAD, open PRs, active workflow runs, and current task/branch/implementation head when available;
- if that state vector already determines the next step, no broader repository compare is launched;
- if evidence is still missing, the next read is narrowed to exact refs/files/run IDs/commit range;
- a frozen host/tool call is not falsely claimed to be recoverable in parallel, but the next activation enters `LIVENESS_RECONCILE_REQUIRED` before repeating the unresolved opaque operation;
- an interrupted session reconstructs GitHub/durable state and continues from the last proven state rather than replaying chat/UI state;
- genuinely active required CI remains `WAITING_EXTERNAL_CI` and is not confused with an internal stall;
- genuine Human Gates retain their existing semantics;
- `CANONICAL_RUNTIME_BOOTSTRAP` remains limited to canonical plugin manifest + Skill reads and does not trigger target-repository compare/diff;
- repository hygiene remains autonomous but non-blocking for ordinary project work and does not require a live Work execution to perform repository-wide content-equivalence comparisons;
- the observed PINK IPTV shape (merged PR, updated main, successful CI, no active workflow, no open PR) can be classified from the bounded state vector without an unnecessary broad compare.

Fail if startup, recovery, audit or hygiene can force a broad opaque compare before the smaller durable state vector has been checked, or if a hygiene run becomes a routine critical-path wait.

## Test 23 — Executable Human Gate closure

Exercise `control.standing_authority.resolve_next_action` with missing direct SSH, an available Actions bridge, incomplete native diagnostics, an available self-provisioned workflow, unresolved bridge authority, platform MFA, a genuine physical/device test, red automated CI and a new uncovered architecture decision.

Pass only if missing capability alone stays in discovery/remediation; existing paths and bounded bridges continue through the existing autonomous phases; raw observations are recomputed rather than trusting a claimed exhausted state; platform consent waits for complete native/bridge/access discovery; and every human interruption requires verified convergence. A physical/device test may become a genuine gate after independent covered work and automated prerequisites are complete, without waiting for its future manual result. A new uncovered decision remains unimplemented and is presented only after independent covered work converges. Diagnostic exhaustion must re-enter access discovery with fresh post-fallback observations before an access gate is considered. Exhausted discovery without an identified human action must not fabricate a manual gate or repeat the exhausted strategy indefinitely.


## Test 24 — Universal Recovery Compaction / execution efficiency

Exercise five universal scenarios without using any project-specific rule:

A. Required CI fails because of a simple compile error inside the already-authorized E1 scope. Pass if Project Leader derives completion authority, diagnoses, fixes, runs fresh validation and continues without a Human Gate or separate failure/authorization/retry commits.

B. Required CI fails but the proposed correction would materially change public architecture or cross a trust/security boundary. Pass if Recovery Compaction closes false and normal authority/Human-Gate rules remain in force.

C. A test fails and the E1 correction is evident inside the same authorized workstream. Pass if `DERIVED_COMPLETION_AUTHORITY -> fix -> test -> continue` is used and required acceptance evidence is unchanged.

D. The next step requires a new credential, permission, destructive effect, or other E2/E3 boundary. Pass if Recovery Compaction closes false and the existing standing-authority/Human-Gate closure handles the exact action.

E. Three consecutive no-progress iterations occur under the same objective. Pass if Recovery stops repeating the same strategy, returns `RECOVERY_REPLAN_REQUIRED`, persists durable anti-loop/replan state when needed, and changes technical strategy instead of generating more control-only commits.

Also pass only if a true GitHub `run_attempt > 1` still requires causal append-only Recovery evidence, a fresh run on a new technical remediation SHA does not require such evidence merely because an earlier implementation failed, CI terminal-success resumes Supervisor audit/continuation automatically, and no external target repository is mutated while testing the Project Leader control plane.

Fail if ordinary bounded Recovery routinely produces `FAILURE_OBSERVED -> RETRY_AUTHORIZED -> remediation -> RECOVERED` commit chains when CI/log/PR evidence and the technical checkpoint are sufficient, or if compaction weakens CI, scope, security, transition controls, or real Human Gates.

## Final acceptance

This section is closed only when:

- all automated contract/validation/package checks are green on the exact implementation head;
- these smoke contracts are represented by automated tests wherever mechanically testable;
- no active runtime file still requires a central target-project registry or routine Owner approval by action name;
- no obsolete superseded branch is left as an active workstream;
- `main` post-merge is independently re-audited.


## Direct execution and continuous hygiene regression

The incremental direct-execution correction must preserve all earlier smoke tests and additionally prove:

1. Covered recoverable E1 bug -> `resolve_recovery_action` returns `COMPACT_RECOVERY + RECOVERY_DIRECT_REPAIR`; Recovery Guardian is the executor and may diagnose/correct/test/hygienize without a mandatory Builder/Supervisor handoff.
2. Same-action retry with no material basis -> `BLIND_RETRY_BLOCKED + RECOVERY_DIRECT_REPLAN`; no identical blind retry.
3. Material architecture/security/permission/Human-Gate change -> normal authority resolution; Recovery does not cross the boundary.
4. Mutation makes an operational path/reference obsolete -> `CONTINUOUS_HYGIENE_ACTIVE` performs covered recoverable cleanup in the same cycle.
5. Explicit read-only/diagnostic/no-change instruction -> hygiene is `HYGIENE_REPORT_ONLY`; no mutation.
6. Terminal-success bound CI invalidates stale `WAITING_EXTERNAL_CI` and routes immediately to audit/continue.
7. Terminal-failure bound CI routes to Recovery rather than Owner.
8. Missing direct SSH/tool with a usable Actions/non-interactive path continues automatically through access discovery.
9. One mutable target repository per task remains enforced.
10. Genuine physical/manual gate is requested only after independent automatable prerequisites and convergence are complete.

The existing executable suites in `tests/test_managed_project_contract.py`, `tests/test_managed_cross_repo.py`, and `tests/test_standing_authority.py` provide the corresponding regression evidence.

## Test 25 — Observable Recovery and effect adapter

Run the executable tests around `control/runtime_execution.py` with injected fake durable state and CI observations.

Pass only if:

- bounded preflight exposes the exact minimum read sequence before broader discovery;
- two repeated no-progress observations route `INTERNAL_OPERATION_STALLED -> LIVENESS_RECONCILE_REQUIRED`;
- a write that becomes durable and then loses its response is re-observed as completed rather than repeated;
- a new invocation against the same durable effect recognizes `EFFECT_ALREADY_APPLIED` and performs no duplicate write;
- a timeout with no observed durable effect is surfaced without an automatic same-action write retry;
- an active exact CI run remains `WAITING_EXTERNAL_CI`, while a terminal failed bound run routes Recovery;
- malformed boolean/run-id/timestamp observations are rejected before they can become positive evidence.

The test harness is intentionally injected and deterministic. It proves the decision/effect adapter behavior without claiming that a frozen ChatGPT host can execute code while the host itself is unavailable.

## Test 21 — Host runtime invocation and stale-copy reconciliation

Observed in the current ChatGPT workspace on 2026-10-07:

1. Resolve `skills://plugins/project-leader/project-leader/skill.md` through the host skill surface.
2. Confirm the entrypoint is readable/invocable.
3. Read canonical `main` plugin metadata + Skill from `martaxi-boss/Project-leader`.
4. If the loaded copy lacks a canonical rule present on the pinned revision, classify `RUNTIME_SYNC_STALE` and activate `RUNTIME_CANONICAL_OVERRIDE_ACTIVE`.
5. Confirm substantive work continues under the exact pinned canonical revision instead of requesting manual reinstall/sync.
6. Query available plugin-management dependency metadata. If no public global release identity exists, record that limitation and do not fabricate a portable marketplace/install attestation.

Acceptance: host invocation is demonstrated; stale loaded bytes do not cause mixed-generation execution; canonical revision is the effective contract; the absence of a public release identity is reported as an evidence limit, not silently upgraded into proof.

