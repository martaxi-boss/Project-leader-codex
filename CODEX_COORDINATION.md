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

## Continuous phases under a single standing Owner instruction

The coordinator **plans the whole requested job first**, with 1–8 verifiable
work items and explicit dependency edges. \`codex.agent_policy.plan\` returns
\`phase_plan\` in topological order, retaining an individually classified
\`reasoning_effort\` for every phase even if the one/two-worker planner groups
several small items into one Codex invocation. Actual model effort is fixed
for that bounded invocation; to adjust effort across phases, start a new
bounded worker invocation at the next phase boundary. Do not claim a
mid-invocation model effort change.

The host can use \`codex.agent_policy.next_phase_action\` after each independently
observed result. Missing eligible work -> \`DISPATCH_NEXT\` without new Owner
authorization; a running worker -> \`WAIT_RUNNING\`; worker-produced or staged
work with missing, stale, or untrusted certification ->
\`WAIT_INDEPENDENT_VALIDATION\`; a recoverable error -> \`RECOVER_PHASE\`;
a genuine exclusive human decision -> \`HUMAN_GATE\`. Once every phase has
verified evidence bound to its exact candidate ->
\`FINAL_ACCEPTANCE_AND_PR\`, **not** automatic merge or production release.
The host, not a worker's self-report, must supply validation evidence.
No terminal "finished" result is valid while requested phases remain.

For PR-only targets, the coordinator should make the smallest safe batch that
allows **all dependent in-scope E1 work to be completed on a single isolated
candidate before opening the final PR**. Run focused checks between changes
and full/security/Android checks where required. This avoids turning a
stage-one PR into an artificial pause. If dependent work really needs a
merged predecessor or target-required CI/review, this is a genuine
\`PHASE_STAGED_AWAITING_TARGET_CERTIFICATION\` external wait, never an excuse
to disable tests or merge without authority. Resume only when the exact
CI/integration evidence actually passes. Independent non-conflicting work
can proceed in parallel under the normal two-worker ceiling.

Supervisor updates to the existing VPS/Telegram observer are non-blocking
telemetry. The Supervisor cannot dispatch, approve, retry, merge or hold a
phase. Cloud direct work and VPS work are separate project executions that
share these rules; a changed repository policy **does not, by itself, patch
a separately deployed VPS GitHub Actions workflow or revive a completed run**.

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
