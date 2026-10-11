# Project Leader + Codex (specialized runtime)

This repository is **not** the universal Project Leader. It is an independent copy
plus a separately maintained two-Codex execution policy.

When this repository is the selected Codex environment:

1. Load `plugins/project-leader/skills/project-leader/SKILL.md` and honor its
   superior rule `EXECUTION_FIRST_WITHIN_BOUNDS`. If live GitHub access exists,
   bootstrap the canonical Project Leader policy from `martaxi-boss/Project-leader`
   at one pinned `main` revision, following the Skill's canonical rules.
2. Also load `CODEX_COORDINATION.md` for every specialized Codex task. This
   overlay is additive; it cannot weaken Project Leader safety or governance.
3. Follow the Owner's requested execution mode. In `parallel`, delegate to
   **exactly two** Codex workers only for genuinely independent work with
   non-overlapping changes. In `serial`, run worker 2 after worker 1 succeeds.
4. For each bounded new task choose `low`, `medium`, or `high` reasoning effort
   using scope, evidence, and difficulty; accept explicit Owner choice. Review
   again at the next task boundary; never claim to change a running turn's
   reasoning level invisibly.
5. Isolate concurrent edits in separate worktrees / branches. Never let two
   workers concurrently modify the same files. Require validation and independent
   integration review, with no automatic merge or production deployment.
6. Before claiming two workers ran, supply run IDs / worker evidence. If the
   current Codex host does not support multi-agent delegation or a second
   authenticated CLI process, report the limitation without pretending success.
7. Do not change the source repository `martaxi-boss/Project-leader` as part of
   this specialization. Keep universal original files byte-for-byte in their
   original paths, except for the fork-specific policy
   `projects/policies/project-leader.json`, whose repository binding and
   exact Codex scope are specialized only in this new repository.
   Specialized files belong in `codex/`, `.codex/`, this `AGENTS.md`,
   and `CODEX_COORDINATION.md`.

A non-Codex chat or agent using the original `martaxi-boss/Project-leader` is
not subject to these Codex-specific instructions.
