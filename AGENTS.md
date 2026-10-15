# Project Leader + Codex (specialized runtime)

This repository is **not** the universal Project Leader. It is an independent copy
plus a specialized, provider-neutral agent router with the Codex CLI as the
currently verified executor.

## Two independent Owner entry points — do not disable either

### Codex Cloud: work directly, including private photographs and files

A new Owner instruction in an explicitly selected **Codex Cloud task** is a
**direct Cloud execution request by default**, whether it is dictated, typed,
or accompanied by screenshots, photographs, documents or examples. The Cloud
executor must load the Project Leader Skill and this repository's
`CODEX_COORDINATION.md`, inspect the actual selected target and execute the
covered task **in the Cloud environment**: implement, test, correct and prepare
isolated commits/PRs subject to the target's normal protections. Do not
automatically relay this instruction to the VPS and do not stop at a plan.

The Cloud task must use only attachments actually provided and readable in its
own authorized runtime; inspect the real originals when needed. An attachment
visible in a chat is NOT automatically a file on the VPS, in a GitHub Issue, or
in another Cloud task. Do not claim to have used unseen photographs. If the
files are inaccessible, report the exact dependency rather than fabricate a
visual diagnosis. Never upload private photographs, media, provider links or
credentials to a public repository or Issue. The Owner may choose to stay in
Cloud for the whole job; no MCP, VPS relay or second Coordinator is required
for direct Cloud work.

A new Cloud task may target a repository other than this specialized
`Project-leader-codex` repository only when its actual GitHub checkout and
authorized target access are verified. Preserve existing branches, PRs and
running jobs; check the current target state before work to prevent duplicate
or conflicting edits. If the selected Cloud runtime cannot execute or
publish, report the specific blocking capability; do not claim completion
based on selecting an environment, or keep repeating a stalled operation.

### VPS: the existing independent Coordinator remains available

The VPS entry point, its independent Codex Coordinator, one/two workers,
Project Leader enforcement and passive Telegram Supervisor are **unchanged**.
An Owner order issued in an ordinary **ChatGPT chat** (outside Codex Cloud)
goes to the **existing VPS Codex Coordinator** through the authenticated
ChatGPT/GitHub route; a message alone is not proof of delivery or dispatch.
Do not attempt direct Codex Cloud execution on behalf of this ChatGPT route.
Owner orders issued to the VPS continue using their existing authenticated
path. A Codex Cloud Owner task may explicitly request **VPS delegation**,
but delegation is optional, not the default.

Only when the Owner explicitly requests the VPS route, relay the bounded
**text-only** Owner objective through the existing authenticated ingress:

`python -m codex.owner_coordinator_ingress --target martaxi-boss/<project> --task '<original Owner request>'`

The authenticated GitHub CLI must identify as `martaxi-boss`. Verify the
current Cloud checkout and successful Owner Issue creation as the existing
ingress code requires. The resulting Owner Issue proves handoff, not worker
execution. Never retry an ambiguous write or create another Coordinator.
An explicit VPS delegation containing indispensable private attachments
must NOT silently become a text-only order: use only an already authenticated,
verified private media path and confirm private receipt first; if it is
unavailable, report the limitation and preserve the attachments in Cloud.
Do not publish photographs or image links as a substitute. Do not quietly
switch an expressly delegated job into direct execution after a failed
handoff.

A Codex worker already dispatched by the verified VPS Coordinator is NOT
a fresh Cloud Owner instruction: **skip this** Owner-entry routing, execute
only its verified bounded worker job, and never relay its own task back.

### Exactly one passive Supervisor

The only Supervisor is the **existing VPS Supervisor**. Do not create a
Cloud Supervisor, issue commands on the Supervisor's behalf or confuse it
with a Coordinator. Cloud work should leave factual, privacy-safe PR,
commit and CI evidence for that same Supervisor to observe through an
existing authorized reporting path. This does not imply that the Supervisor
can already see private Cloud attachments, private model chats, or every
Cloud task automatically: if live Cloud-to-Supervisor delivery is not
verified, say so rather than inventing a notification.

## Continuous execution of one Coordinator decision — both supported entrances

A Coordinator decision consists of the Owner objective, the verified target and
its entire bounded phase DAG. **One Owner order starts the whole authorized
operation, not one chat turn per phase.** Do not hand the Owner a new prompt,
request a new command, or stop merely to send a phase report. Publish factual
progress evidence without relinquishing the current operation.

For direct **Codex Cloud**, once the Coordinator has scoped real work and
selected phases, preserve its exact phase identities, modes, reasoning and
worker allocation. The host runtime has
`codex.phase_cycle.validated_phases` and
`codex.smart.execute_coordinator_phases` for this contract. The latter
requires an **independent trusted Project Leader certification adapter**;
a raw worker report, draft PR, or merely queued CI is not that adapter. When
that adapter is present, execute and certify all phases within the SAME
operation, with no new Owner prompt between them. Never fabricate an adapter,
completion evidence, permissions, or an external Coordinator.

The **VPS** remains its existing separate Coordinator and its own GitHub
Actions phase-cycle implementation; do not replace or configure VPS routing
from Cloud. In both paths, subsequent phases become eligible only after
exact-head CI, independent integration/review and all mandatory target gates
are satisfied. An E1 recoverable failure is Recovery Guardian work within
the original operation; do not blindly replay ambiguous writes. A genuine
material/Human Gate, unverified certification, unresolved error or quota pause
blocks the ENTIRE dependent phase sequence. Preserve the validated original
plan and resume only from verified reconciliation. The passive VPS Supervisor
may observe and notify, but NEVER starts phases, corrects code or grants a
gate. If the host lacks an independent certifier, state the precise missing
capability rather than asking the Owner to re-prompt each phase.

## Project Leader + Codex execution for Cloud and verified VPS workers

When the Owner requests direct Codex Cloud execution, or a **verified VPS
Coordinator-dispatched worker** runs here, apply the following shared rules.
Direct Cloud tasks have their own Owner scope; VPS workers have only their
already verified delegated scope:

1. Load `plugins/project-leader/skills/project-leader/SKILL.md` and honor its
   superior rule `EXECUTION_FIRST_WITHIN_BOUNDS`. If live GitHub access exists,
   bootstrap the canonical Project Leader policy from `martaxi-boss/Project-leader`
   at one pinned `main` revision, following the Skill's canonical rules.
2. Also load `CODEX_COORDINATION.md` for every specialized Codex task. This
   overlay is additive; it cannot weaken Project Leader safety or governance.

3. Accept a **single spoken or written Owner instruction** without requiring
   the Owner to specify worker count, mode, exact paths, model or effort.
   Inspect the selected target's real repository and derive bounded ownership
   scopes and dependencies before planning. Use `codex.smart` /
   `codex.agent_policy.plan` to choose `single`, `serial` or `parallel`
   automatically. Honor any explicit Owner preference only when safe.
   Ambiguous/unverified paths must stay `needs_scoping`, never be invented.
4. Default to **one** sufficient worker for small, tightly coupled or overlapping
   tasks. Choose two only for substantial, independently scoped parallel work
   or justified serial dependencies. In parallel use two isolated worktrees
   with disjoint ownership. In serial, worker 2 starts after worker 1 succeeds
   and can inspect worker 1's accepted changes. The two-thread Codex config
   is a ceiling, **not** an instruction to always launch two workers.
5. For each new bounded worker task choose `low`, `medium` or `high`
   reasoning using scope, evidence and difficulty; honor explicit safe Owner
   choices. Enforce verified provider/model capability floors: block an
   unqualified model rather than silently downgrading difficult work. Reassess
   effort at the next task boundary, never invisibly in a running turn.
6. Route only through a verified, authenticated host adapter. Today the local
   `codex-cli` executor is implemented; names in the provider registry are
   not active cloud connections. Keep a private shared **soft** token ledger
   for covered runs, settle observed usage conservatively and never claim
   visibility into the real account quota or a hard in-flight token limit.
7. Isolate edits, verify changed paths, run focused then mandatory full
   regressions/CI, and require independent authorized integration review.
   Never silently merge, deploy, relax tests/security or mutate production.
8. Receiving an order in an ordinary ChatGPT chat is **not itself** a Codex
   execution trigger. An Owner-selected Codex Cloud task can execute there;
   a VPS job must be dispatched by the already authenticated VPS gateway.
   Selecting a Cloud environment alone is not proof that a worker ran.
   Report real job/PR IDs, scope, reasoning, validation, usage observations
   and blockers without fabricating execution.
9. Do not change the source repository `martaxi-boss/Project-leader` as part of
   this specialization. Keep universal original files byte-for-byte in their
   original paths, except the explicitly audited fork adaptations:
   `projects/policies/project-leader.json` (repository binding and scoped
   authorizations), `.github/workflows/contract-tests.yml` (FAST_E1 CI),
   and `tests/test_trusted_gate.py` (fork-specific trusted test fixtures).
   Specialized files belong in `codex/`, `.codex/`, this `AGENTS.md`,
   and `CODEX_COORDINATION.md`. Never propagate specialized changes to
   the universal upstream.

A non-Codex chat or agent using the original `martaxi-boss/Project-leader` is
not subject to these Codex-specific instructions.
