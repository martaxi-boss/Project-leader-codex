# Codex coordination extension (specialized repository only)

## Contract

Project Leader remains the superior, universal operating policy. This document
adds execution mechanics for *two Codex workers* when the Owner selects this
specialized environment. It never modifies or overrides universal safety.

- **Owner chooses mode** for each order: `serial` or `parallel`. Do not infer
  parallel work from the mere presence of this configuration.
- **Exactly two workers** when the Owner requests dual mode. An unsupported
  host must fail honestly; one worker is not evidence of two workers.
- **Parallel**: split into genuinely independent, bounded, non-overlapping
  ownership surfaces; each worker uses its own context and isolated worktree
  or branch. Start only after verifying that the surfaces are disjoint.
- **Serial**: worker 2 starts only after worker 1 has a successful, inspected
  result. Worker 2 must see worker 1's accepted changes.
- **Effort**: use `auto` per new bounded task (simple=`low`, normal=`medium`,
  validated complex regression/concurrency/security=`high`), or explicitly
  requested `low|medium|high`. Reevaluate after new material diagnostics or
  failure evidence at the *next* task/turn boundary, never silently mid-turn.
- **Token prudence**: avoid duplicate context, redundant tests and blind
  retries. Account and provider quotas are not exposed by this repository;
  never invent quota percentages or assert account-wide token savings.
- **Safety**: stop on conflicting edits, unsafe permissions, ambiguous writes,
  missing Codex CLI/authentication, CI failure, unsupported provider or any
  material boundary not covered by authority. Apply Project Leader recovery.
- **No silent integration**: collect workspace and diff evidence, run focused
  validation, then required full regression/security/CI and exact SHA review.
  Changes must be integrated only via authorized repository PR flow.

## Supported execution routes

1. **Codex Cloud**: `AGENTS.md` and `.codex/config.toml` express the intended
   subagent policy. Actual availability and launch of two subagents must be
   verified inside the selected Codex Cloud environment. Selecting the
   environment alone does not prove two jobs started.
2. **Signed-in Codex CLI**: `python -m codex.dual plan ...` generates an offline
   bounded dispatch. `python -m codex.dual run ... --execute` launches two
   independent `codex exec` calls using one authenticated CLI installation.
   It never pushes or merges code, and requires a clean target checkout.
3. **VPS**: the separately deployed `martaxi-boss/VPS` dual-Codex mechanism
   remains distinct; this repository does not inherit VPS credentials,
   schedules, token ledger or running services automatically.

## Audit requirements

When reporting completion provide: selected repository and SHA; selected mode;
exactly two worker IDs and their reasoning effort; isolation/workspace proof;
change scope and test results; explicit state of integration. If jobs were
simulated, say simulated. If a provider was unavailable, say not started.
