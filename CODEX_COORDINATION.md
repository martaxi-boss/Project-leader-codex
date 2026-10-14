# Codex coordination extension (specialized repository only)

## Contract

Project Leader remains the superior universal operating policy. This file
adds executor-specific mechanics for **one or two** Codex workers when the
specialized environment is selected. It does not modify universal rules.

- **One Owner order**: accept natural language or speech-transcribed text;
  do not ask the Owner to choose providers, agent count, file paths, mode
  or reasoning effort just to begin planning.
- **Inspect before routing**: the host coordinator reads enough of the actual
  target project to identify work areas, dependencies, acceptance criteria,
  regression coverage and material boundaries. Never invent ownership paths.
  In a local checkout, `codex.scope_discovery` is a conservative heuristic;
  anything ambiguous remains `needs_scoping` for further real inspection.
- **Automatic mode by default**: pass bounded work items to
  `codex.agent_policy.plan` (via `codex.smart`) with `preference: auto`
  or omitted. It selects `single`, `serial` or `parallel` according to
  scoped independence, dependencies and task cost. A *safe explicit* Owner
  choice of mode takes precedence; never start two merely because configured.
- **One or two workers**: use one when sufficient. Parallel is justified only
  for substantial non-overlapping work; otherwise combine related work into
  one. Serial two-worker execution is for justified sequential phases.
  The existing `codex.dual` legacy CLI deliberately requires exactly two
  explicit jobs; it is not the automatic one-order router.
- **Parallel**: at most two workers on disjoint, verified ownership surfaces;
  each gets an isolated context/worktree/branch. Conflicting paths prohibit
  parallel writes.
- **Serial**: worker 2 starts only if worker 1 has a successful, inspected
  result and sees worker 1's accepted changes. A failed first phase does not
  silently start its dependent successor.
- **Provider and intelligence**: choose only an available, authenticated,
  attested provider/model with sufficient declared capability. At present the
  Codex CLI is the implemented executor; entries for other providers are not
  connections. Choose `low`, `medium` or `high` once per bounded worker task,
  based on actual difficulty/evidence; re-evaluate at the next task boundary.
  Block if no verified profile meets the quality floor rather than silently
  downgrading. A reasoning choice cannot change mid-turn invisibly.
- **Token prudence**: reserve a private, joint *soft* budget before covered
  executions and account for observed usage or conservative reservations
  afterwards. This is not real account quota or a mid-generation hard cap.
  Avoid duplicate reads, unnecessary workers and blind retries.
- **Safety and recovery**: preserve separate scopes, trust boundaries,
  Project Leader authorization, focused and mandatory full tests, CI and
  independent PR review. Never bypass controls or silently merge/deploy.
  Use Project Leader recovery when evidence justifies a correction.
- **Transport truth**: instructions typed or dictated in an ordinary ChatGPT
  chat do not automatically launch Codex merely because this GitHub repository
  is connected. An authenticated host coordinator/runner must explicitly
  deliver a validated task and prove the resulting worker run IDs.

## Supported execution routes

1. **Codex Cloud direct Owner chat**: `AGENTS.md` now selects the separate
   `codex.owner_coordinator_ingress` authenticated relay *before* any worker
   planning. With an Owner-authenticated GitHub CLI, it creates a bounded
   `[coordinator run]` Issue in `martaxi-boss/VPS`; the existing independent
   Coordinator alone audits, selects workers and dispatches them. Codex Cloud
   must not execute the task directly if this identity or transport is missing.
   A successful Issue creation proves only ingress submission, not execution.
   `.codex/config.toml` still caps separate worker threads at two.
2. **Signed-in Codex CLI**: `python -m codex.smart plan --order ORDER.json
   --repo-dir /real/target` may derive real scopes and chooses one/two workers.
   `python -m codex.smart run --order ORDER.json --repo-dir /real/target
   --execute` launches covered jobs only when authenticated, validated and
   authorized. The legacy `python -m codex.dual` route is an explicit
   exactly-two-worker route, not the default auto selector. Neither runner
   automatically pushes, merges or deploys.
3. **VPS**: `martaxi-boss/VPS` is the one authenticated independent
   Coordinator and worker gateway. Selecting this specialized repository alone
   does not inherit VPS credentials, token ledger, or live processes; a direct
   Codex Owner chat must successfully use the signed-in GitHub relay. A Codex
   worker dispatched by the VPS must never relay its own task back as a new
   Owner order.

## Audit requirements

For every actual run report the target repository and base SHA, mode selected
and reason, **one or two** actual worker IDs, provider/model and reasoning
effort, changed-path/worktree evidence, tests/CI, token observations versus
reservations, integration status and remaining blockers. Mark simulations as
simulations; mark unavailable executors as not started.
