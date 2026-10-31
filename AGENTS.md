# Project Leader + Codex (specialized runtime)

This repository is **not** the universal Project Leader. It is an independent copy
plus a specialized, provider-neutral agent router with the Codex CLI as the
currently verified executor.

## One portable, project-owned Coordinator — no VPS dependency

**The sole Coordinator belongs to this repository**, `martaxi-boss/Project-leader-codex`: the existing `codex.smart`, `codex.agent_policy`, host scoping and Codex workers. Its policies and execution engine must travel with this repository. GitHub Actions or a VPS may supply compute/transport, but neither owns another planning AI. Do not create a second Coordinator, another Supervisor or an MCP just to route work.

### Mandatory revision-coherence check before testing or certifying Codex

Before a new or repeated Cloud/CLI certification, execute `python -m codex.runtime_sync`
from the **Project-leader-codex repository root**. It is read-only: it checks
the actual source checkout, the live GitHub `origin/main` ancestry, clean
`AGENTS.md`, `CODEX_COORDINATION.md`, `.codex/config.toml` and the specialized
Skill source, and prints exact SHAs and source fingerprints. Save its output
with the worker and CI evidence. Only `status=PASS` permits claiming that
the repository instructions match the current main revision.

A `STALE` or `NOT_VERIFIED` preflight is **not** a successful test of the
new code. Reconcile a new authorized Cloud checkout/task with current main,
re-read these instructions and the Skill, then rerun affected tests; do not
overwrite an existing dirty worktree or silently weaken this check. A Cloud
runtime's installed ChatGPT plugin release, selected model and effective
reasoning effort are **separate host facts**: Git source fingerprints cannot
prove them. Require actual host evidence or mark each `NOT_VERIFIED`.
Publishing GitHub source or a plugin ZIP does not automatically refresh the
installed ChatGPT Skill or a previously created Codex Cloud environment.

### Codex Cloud: work directly with the project Coordinator

A new Owner instruction in an explicitly selected **Codex Cloud task** is a **direct Cloud execution request by default**, whether dictated, typed, or accompanied by screenshots, photographs, documents or examples. Load the Project Leader Skill and `CODEX_COORDINATION.md`, inspect the actual authorized target and implement, test, correct and prepare scoped commits/PRs there. Use the existing portable coordinator planner/worker capabilities for scoped work; do not automatically relay this instruction to the VPS or start a redundant VPS planning AI.

The Cloud task may use only attachments actually provided and readable in its own authorized environment. **An attachment** in ChatGPT is **NOT automatically a file on the VPS** or another Cloud task. An explicit transfer must NOT silently become a text-only order. A verified private media path would be needed if delegation actually required remote originals; never put private media, credentials or signed links into a public Issue. Report a real blocker rather than invent missing evidence.

An Owner task may target another authorized repository only when its real checkout and rights are verified. Reconcile existing commits/PRs and avoid duplicate implementation, force pushes, or hidden merges. A selected Cloud task is not evidence of worker execution without actual run IDs and results. Cloud can operate with no VPS and no desktop-remote tools.

### ChatGPT: invoke the same project-owned Coordinator through the Skill

A substantive `@Project Leader + Codex` instruction is handled by this project's Skill/Coordinator policy using authenticated, available ChatGPT/GitHub tools. Inspect and scope the exact owner-selected repository, plan via the project policy, and perform only actions the active host really supports. **Never route an ordinary ChatGPT instruction through the VPS AI Coordinator by default.** Do not open `[coordinator run]` Issues in `martaxi-boss/VPS` as an automatic substitute for project execution.

A ChatGPT Skill activation cannot by itself start a separate private Codex Cloud session or a signed-in Codex CLI worker. When a verified host action can dispatch the portable Codex executor, use that established authenticated action; if no such host action exists, explicitly report `CODEX_EXECUTOR_UNAVAILABLE` and supply a concise direct Codex Cloud continuation using the same project policy. Do not pretend GitHub Issue creation is an executable run or claim unattended execution without a persistent authenticated runner.

### VPS: optional execution infrastructure; Supervisor only as a retained service

Historical `martaxi-boss/VPS` Coordinator workflows may still exist until separately retired with a safe, verified cutover. They are **not** the source of truth, are **not** this project's default entry, and must not be invoked just because ChatGPT or Cloud received an instruction. Preserve legacy evidence but do not add another planning agent, perform speculative migrations or silently disable a functioning route. The existing VPS remains optional; code and decisions must not depend on it.

### Exactly one passive Supervisor

The only Supervisor is the **existing VPS Supervisor**. Do not create a
Cloud Supervisor, issue commands on the Supervisor's behalf or confuse it
with a Coordinator. Cloud work should leave factual, privacy-safe PR,
commit and CI evidence for that same Supervisor to observe through an
existing authorized reporting path. This does not imply that the Supervisor
can already see private Cloud attachments, private model chats, or every
Cloud task automatically: if live Cloud-to-Supervisor delivery is not
verified, say so rather than inventing a notification.

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
   an external Codex job requires an authenticated host executor. Historical\n   VPS jobs remain valid evidence but are not the default planning route.
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
