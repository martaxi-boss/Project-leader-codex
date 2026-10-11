# Smart agent routing: one Owner instruction, bounded execution

This is an **optional specialization of Project Leader**, never a change to the universal
\`martaxi-boss/Project-leader\`. The directory name \`codex/\` is historical: the
planner and cloud bridge are **provider-neutral**.

## How the coordinating AI must work

1. Receive the Owner's natural-language or dictated instruction. Do **not** demand
   provider names, effort levels, agent count, branch names or a JSON manifest.
2. Inspect the chosen target project just enough to identify real work areas,
   acceptance criteria, prerequisites and trust boundaries.
3. Internally decompose into 1–8 bounded work items with IDs, complete task text,
   real relative owned paths, and explicit \`depends_on\` edges. Do not invent paths.
   If the task concerns non-repository cloud work, use the host's real accessible
   resources and enforce equivalent scopes. This repository's CLI path uses Git.
4. Apply \`codex.agent_policy.plan\` to that internal order. A single agent is
   normal for small or overlapping tasks. Two agents are justified for substantial
   independent work; serial grouping handles dependencies. Never split just to
   consume two workers. Honor any *explicit* Owner choice when safe.
5. Assign each job an **available, attested provider/model**, capability and
   reasoning effort, considering adequacy before cost. The configured quality
   tiers and relative costs are **operator estimates**, not verified model
   benchmarks or current price data. A narrow typo may use Low; broad work should
   not be downgraded solely because one keyword looks easy.
6. Execute only through an authenticated and **verified host adapter**. The
   included signed-in Codex CLI supports one or two code-edit jobs with private
   worktrees. For other cloud agents the trusted host must implement
   \`CloudHost.supports/execute\` and substantiate worker IDs, results and usage.
   Provider names in \`providers.json\` DO NOT provision vendor accounts.
7. Before starting, reserve the shared local soft budget; after running, settle
   with observed usage where provided, or conservatively keep the reservation
   when telemetry is unknown. This is **not** the provider's account-wide quota
   and cannot stop tokens mid-generation.
8. Keep independent diffs isolated. On failure, use Project Leader recovery,
   not blind retries. Integrate only through authorized, tested PRs, never
   automatic merges or production deploys.
9. Report decisions and **real proof**: exact target SHA, provider/models,
   1/2 worker run IDs, observed vs estimated usage, validation results and
   remaining blockers. Never claim simulated jobs were real cloud executions.

## Local CLI (explicit runner authorization)

The CLI accepts one request envelope. The *coordinator*, not the Owner,
builds \`work_items\` after inspecting the repository:

\`\`\`bash
python -m codex.smart plan --order codex/example-smart-order.json
python -m codex.smart run --order codex/example-smart-order.json \
  --repo-dir /actual/target/checkout --execute
\`\`\`

\`plan\` never runs a model. The \`run\` operation requires actual Git, a signed-in
Codex CLI and a clean checkout whose \`origin\` matches the requested repository.
It is limited to the single implemented \`codex-cli\` adapter. For other cloud
providers, an authenticated host must call \`codex.cloud_bridge.execute_cloud\`
with a verified adapter; the repository contains neither credentials nor
provider-specific magic login code.

### Fail-closed behavior

- If no scoped files can be established internally, return \`needs_scoping\`
  and inspect the repository; do not fabricate filenames or spend tokens.
- If the configured provider is disabled or unverified, return
  \`blocked_no_provider\`; never silently substitute another provider.
- If tasks touch the same files, avoid unsafe parallel writes.
- Production, credential and governance changes require an applicable
  Project Leader material-control authorization.
- Missing telemetry is marked **unknown**, not free or zero cost.
- Owner account quota percentages remain **unknown** unless obtained from
  an authenticated, reliable provider source. Local estimates are not billing.

## Integration limits

Only the Codex CLI executor is implemented end-to-end (tested against a fake
CLI locally). The generic cloud bridge is a tested integration **interface**;
it does not independently connect Gemini, Claude, Copilot, Antigravity, or
other providers. Those services require explicit provider adapter support,
host permissions, capability and billing validation, and a real end-to-end test.
