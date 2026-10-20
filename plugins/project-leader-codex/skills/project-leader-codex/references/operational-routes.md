# Project Leader + Codex: bounded operational reference

This reference belongs to the specialized `martaxi-boss/Project-leader-codex` project only, not `martaxi-boss/Project-leader`.

## Current implementation boundary

- Specialized contract: `martaxi-boss/Project-leader-codex` / `AGENTS.md`, `CODEX_COORDINATION.md`, `README_CODEX.md`.
- Universal upstream: `martaxi-boss/Project-leader` is independently maintained. Specialized work never publishes back into upstream implicitly.
- ChatGPT owner order: GitHub connector authenticated as the actual Owner creates **one** `[coordinator run]` Issue in `martaxi-boss/VPS`; body first line `TARGET_REPOSITORY=...`. Existing `Coordinator to existing Codex router (Owner order)` Actions workflow plans once and dispatches Codex. Do not edit the Coordinator architecture or supervise it with an additional model.
- Cloud Owner instruction: owner selects the existing `Project-leader-codex` Codex Cloud environment and runs independently. The ChatGPT route does not imply an ability to launch Cloud tasks.
- Existing passive Supervisor: `martaxi-boss/VPS` / `ops/supervisor_live.py`. It reports existing VPS worker events and published Cloud PR/CI evidence through GitHub Actions, never runs workers and never sends commands back into Codex. Cloud observation via `.github/workflows/cloud-supervisor-observation.yml` is based on public fixed-repo GitHub evidence.
- Optional GitHub connector is already installed on the Owner's ChatGPT account when verified by the connected tools. The skill's presence does not itself grant further write access.

## Real evidence, not assumptions

For any dispatched ChatGPT/VPS order record authenticated Issue number, run URL/ID, worker count, `single`/`serial`/`parallel`, reasoning effort, true execution interval (when parallel proof requested), exact PR commits, changed paths, tests and CI bound to exact HEAD, target-specific integration status. A PR staged awaiting certification is **not** merged.

For Cloud direct orders record Cloud task output (from user or authorized connected source), related PR head, exact CI checks and files. A public PR proves published changes, not private session execution timing unless timing data is independently corroborated.

Telegram statuses:
- `SENT_TO_PRIVATE_TELEGRAM`: authenticated runtime reports accepted sending, not a proof the owner viewed the message.
- `SUPERVISOR_CLOUD=FORWARDED; COUNT=N`: existing Cloud observer reports N Telegram messages sent; actual phone receipt can be confirmed by user screenshot.
- `NO_CHANGE`: polling completed and nothing eligible was sent.
- `OBSERVATION_FAILED`: diagnose the exact GitHub Actions job; do not claim success or silently create new Supervisors.

## Safety examples

- User says `@Project Leader` without Codex: leave it to the independent universal Project Leader skill.
- User says `@Project Leader + Codex` alone: acknowledge readiness only.
- User says `@Project Leader + Codex Faz uma auditoria read-only de martaxi-boss/VPS`: inspect current live evidence, do not dispatch.
- User says `@Project Leader + Codex Continua a tarefa X no repositorio Y`: verify current state and authority, then create exactly one bounded VPS Owner Issue if needed; follow through with existing GitHub Actions evidence.
- User says `Arranca no Codex Cloud`: instruct how to run in the Cloud environment unless actual authenticated Cloud task launch tool is available. Do not claim to have started a Cloud task merely by writing a prompt.
