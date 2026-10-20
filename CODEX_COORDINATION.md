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

## Supported execution routes — one Coordinator, multiple hosts

The project Coordinator is the existing `codex.smart` + `codex.agent_policy` in `martaxi-boss/Project-leader-codex`. **Execution location is a host choice, not a second Coordinator.** No permanent VPS, remote desktop, new MCP or additional planning model is required.

1. **Codex Cloud direct Owner task (default for Cloud)**: the selected authenticated Cloud task loads this policy, inspects its real target, scopes work, chooses one or two appropriately isolated workers, implements and tests with actual evidence and proposes reviewed PRs. It may use screenshots, photographs and original private files actually available within that Cloud task. Never silently hand off to VPS, expose private originals on GitHub or claim a worker ran solely because a prompt was entered. Cloud environment permissions still apply.
2. **Signed-in Codex CLI on any supported host**: the same project engine supports `python -m codex.smart plan --task 'Owner request' --repo-dir /real/target` and, when permitted and authenticated, `python -m codex.smart run --task 'Owner request' --repo-dir /real/target --execute`. An existing `--order ORDER.json` remains supported for independently verified complex scopes. The CLI verifies the selected checkout and can discover grounded paths. Ambiguous scopes remain `needs_scoping` for host inspection, never invented. Serial phases still need an independent validator. The engine does not silently publish, merge or deploy.
3. **ChatGPT Skill using available host tools**: an instruction to the specialized `@Project Leader + Codex` Skill activates this project's coordinator policy. Use the GitHub connector for authenticated target reads/allowed writes, and a verified Codex executor action only if the active host really exposes one. A Skill cannot invent a Cloud-run API or turn an Issue into a running Codex worker. If a live executor is unavailable, return the exact limitation and enable continuation directly in Codex Cloud; never silently substitute the old VPS Coordinator.
4. **VPS legacy observation only by default**: existing historic Coordinator assets under `martaxi-boss/VPS` are outside this project's runtime and remain untouched until a separately verified retirement. The **only Supervisor** is the passive existing VPS Supervisor, which observes published GitHub evidence and sends Telegram notifications when available. It never plans, dispatches, approves or blocks integration. If the VPS is absent, the Coordinator and workers remain usable in Codex Cloud or an authenticated CLI host, while Telegram observation may be unavailable.

Original ChatGPT orders no longer default to `codex.owner_coordinator_ingress` or any VPS Issue. That legacy ingress remains historical code, not the portable execution route. No route may silently create a second planning engine.

## Audit requirements

For every actual run report the target repository and base SHA, mode selected
and reason, **one or two** actual worker IDs, provider/model and reasoning
effort, changed-path/worktree evidence, tests/CI, token observations versus
reservations, integration status and remaining blockers. Mark simulations as
simulations; mark unavailable executors as not started.
