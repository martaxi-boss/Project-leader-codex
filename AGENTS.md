# Project Leader + Codex (specialized runtime)

This repository is **not** the universal Project Leader. It is an independent copy
plus a specialized, provider-neutral agent router with the Codex CLI as the
currently verified executor.

When this repository is the selected Codex environment:

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
   execution trigger. A host coordinator must inspect the project and invoke
   an available authenticated runner (for example `codex.smart run --execute`
   in a signed-in CLI environment). Selecting a Codex Cloud environment alone
   is not proof that a worker ran. Report real run IDs, scope, reasoning,
   validation, usage observations and blockers without fabricating execution.
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
