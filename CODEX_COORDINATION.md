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

## Canonical Owner decision: Coordinator responsibilities and token economy (2026-10-20)

This is the **closed, approved coordination contract** for Project Leader + Codex,
not a new implementation request. Preserve the universal Project Leader Skill
unchanged; do not create a second intelligent manager or Supervisor.

- **Coordinator plans once**: in the authenticated VPS Coordinator route, the
  existing read-only Codex planning call inspects the actual pinned target and
  produces a bounded, validated DAG of findings, work items, dependencies and
  scopes for the **original Owner order**. This is not a continuous AI watcher.
  A separately selected direct Codex Cloud Owner task retains its independent
  entry route and is not forced through the VPS Coordinator.
- **Router minimizes worker cost**: use one worker when sufficient; use at most
  two only when independence, scope and risk justify them. Select
  `low`/`medium`/`high` per bounded task using evidence and existing rules.
  Avoid speculative workers, repeated audits and blind token-consuming retries.
- **Worker owns execution and recovery**: each verified Codex worker loads
  canonical Project Leader and autonomously diagnoses, repairs, validates,
  replans *within its authorized task* and continues. Normal recoverable errors
  and CI regressions are not reasons to invoke the Coordinator again.
- **Later phases are deterministic**: reuse the original authorized DAG and
  exact-state checkpoints. Do not call Coordinator AI again on every phase;
  advance only after the previous phase's required CI, integration and
  authorization checks. Never repeat a completed phase because context was lost.
- **Infrastructure recovery remains technical**: host, publisher, runner or
  transport faults are handled by their existing recovery/control mechanisms,
  or repaired narrowly when diagnosed. A justified job retry is not a new
  Coordinator planning cycle. Do **not** claim universal automatic recovery of
  every possible infrastructure failure has been certified.
- **One passive Supervisor**: observe status, errors, quota events and genuine
  Human Gates and report through the existing private Telegram path. It never
  directs workers, repairs code, replans or starts a new model.

**Explicitly closed, not pending features:**

1. `GENERAL_AUTONOMOUS_FAILURE_RECOVERY_MANAGER`: **NOT REQUIRED**.
   Project Leader already owns worker-side technical recovery; real external
   defects are fixed in the relevant infrastructure, without a new AI manager.
2. `CONTINUOUS_AI_REPLANNING`: **NOT REQUIRED / PROHIBITED AS DEFAULT**.
   It duplicates worker responsibility, burns model quota, and contradicts
   the one-order/one-audit, deterministic-phase architecture.

A genuinely new Owner objective or uncovered material authority decision may
require a new bounded order or a real Human Gate; this is not routine,
per-phase AI supervision. Existing safety, exact-SHA proof and mandatory tests
remain unchanged.

**Verified scope:** the real two-dependent-documentary-phase execution
([VPS Owner Issue #288](https://github.com/martaxi-boss/VPS/issues/288),
[workflow 39450295755](https://github.com/martaxi-boss/VPS/actions/runs/39450295755),
specialized [PR #34](https://github.com/martaxi-boss/Project-leader-codex/pull/34)
and [PR #35](https://github.com/martaxi-boss/Project-leader-codex/pull/35))
proved phase continuation without another Coordinator AI invocation.
The publisher `p2-1` infrastructure defect was fixed separately
([VPS PR #289](https://github.com/martaxi-boss/VPS/pull/289)).
This does not certify every failure class, Cloud attachment route, or physical
Android/VPN flow.

## Supported execution routes

1. **Codex Cloud direct Owner task (default for Cloud)**: the selected
   Cloud environment is an independent execution entry point. Accept Owner
   instructions and authorized original photographs, screenshots and other
   files that are really readable inside that task; apply the Project Leader
   Skill, inspect the real target, scope the work, execute covered fixes and
   produce independently validated GitHub commits/PRs when target access
   permits. Do not automatically run `codex.owner_coordinator_ingress` and
   never mistake a chat attachment for a VPS-side original. Use no public
   GitHub media relay, extra MCP or new Coordinator for direct Cloud work.
   If a selected file cannot be accessed, surface the real evidence gap.
   `.codex/config.toml` caps separately supported threads at two; it does
   not itself prove that agents ran.
   **Optional Owner-explicit VPS delegation**: use the existing authenticated
   `codex.owner_coordinator_ingress` for text-only orders after verifying
   current Cloud checkout and Owner GitHub identity. This ingress continues
   to create just one `[coordinator run]` VPS Issue and can never transmit
   private originals by itself. For media-dependent delegation, use only an
   authenticated private receipt verified before starting the Coordinator;
   otherwise stop and report the missing attachment route instead of sending
   a stripped text order. Explicit VPS delegation does not also start Cloud
   workers.
2. **Signed-in Codex CLI**: `python -m codex.smart plan --order ORDER.json
   --repo-dir /real/target` may derive real scopes and chooses one/two workers.
   `python -m codex.smart run --order ORDER.json --repo-dir /real/target
   --execute` launches covered jobs only when authenticated, validated and
   authorized. The legacy `python -m codex.dual` route is an explicit
   exactly-two-worker route, not the default auto selector. Neither runner
   automatically pushes, merges or deploys.
3. **VPS (unchanged and independent)**: `martaxi-boss/VPS` remains
   the existing authenticated Coordinator/worker gateway with its existing
   passive Telegram Supervisor. Owner instructions from an ordinary ChatGPT
   chat go through the existing authenticated ChatGPT/GitHub path to the VPS;
   successful Issue and worker-run evidence, not a chat message, prove dispatch.
   Codex Cloud does not replace, reconfigure or
   impersonate the VPS. A verified VPS worker must never relay its own task
   back as a new Owner order. The **only Supervisor** is the existing VPS
   Supervisor: Cloud tasks should leave privacy-safe PR/commit/CI evidence
   for its existing authorized observation path, but Cloud private file and
   chat visibility or automatic live Telegram reporting must not be presumed.
   Do not create a second Supervisor or allow the Supervisor to dispatch
   commands or workers.

## Audit requirements

For every actual run report the target repository and base SHA, mode selected
and reason, **one or two** actual worker IDs, provider/model and reasoning
effort, changed-path/worktree evidence, tests/CI, token observations versus
reservations, integration status and remaining blockers. Mark simulations as
simulations; mark unavailable executors as not started.
