# Project Leader + Codex — one portable Coordinator

Source of truth: `martaxi-boss/Project-leader-codex` (`AGENTS.md`, `CODEX_COORDINATION.md`, `codex/smart.py`, `codex/agent_policy.py`). Universal `martaxi-boss/Project-leader` remains unchanged.

## Revision and loaded-environment proof

Start every post-change certification with `python -m codex.runtime_sync`
in the actual Project-leader-codex checkout. A PASS binds the current
`origin/main` to the code and fingerprints of `AGENTS.md`,
`CODEX_COORDINATION.md`, `.codex/config.toml` and this specialized Skill
source. If it returns STALE or NOT_VERIFIED, do not certify the new revision
from that checkout; use a fresh authorized environment and repeat the affected
tests. This is a read-only check, not a new process manager.

The **installed** ChatGPT Skill release and effective Codex Cloud model,
effort and worker sessions need independent host evidence; repository source
alone is not proof of those loaded runtime facts. No automatic remote Cloud
refresh or plugin publishing is implied by a merge or a new ZIP.

## One engine, different entries

**Codex Cloud**: owner selects this project's Cloud environment; direct task uses project instructions, real target checkout and available private attachments. It executes there. No VPS required; no Remote Desktop Commander.

**Codex CLI on a compatible signed-in host**:
```bash
python -m codex.smart plan --task 'Owner instruction' --repo-dir /real/checkout
python -m codex.smart run --task 'Owner instruction' --repo-dir /real/checkout --execute
```
The existing `--order` JSON route still works. Never report workers before actual process/log/worktree evidence; serial work needs an independent verifier. Host permissions, authentication and private model quotas remain real boundaries.

**ChatGPT via Skill**: applies the same Coordinator policy and operates using authenticated host-exposed GitHub tools. It does NOT dispatch through `martaxi-boss/VPS` by default. A ChatGPT Skill does not automatically get a Codex Cloud session or CLI subprocess. If no verified executor tool is accessible, state `CODEX_EXECUTOR_UNAVAILABLE` for autonomous Codex workers and provide a direct Cloud continuation; ordinary GitHub reads/authorized edits may still be executed. Never fabricate a background runner or present a newly created Issue as running workers.

**VPS**: historic Owner Issues / AI planning workflow may still be present pending a controlled retirement. Do not invoke it as default, add another planning agent, or disable without certifying alternate execution. The **single passive Supervisor** can read authenticated published GitHub evidence and send Telegram, but does not perform authorization or execution. Project remains portable if Supervisor/VPS is unavailable; notifications may cease.

## Migration and proof boundaries

- Migration from old VPS-hosted planning must maintain active orders, branch protections and historic PR evidence. A candidate PR is not a cutover or live runtime certification.
- Before any removal of old VPS triggers, independently prove Cloud/CLI project execution without VPS and ensure the ChatGPT route's intended available host action really works. Do not activate new services or paid API billing just to satisfy a test.
- Source permission and exact commit/CI checks must pass on protected files, using an immutable E3 authorization record. No bypass, no forced merging.
- Maintain exact target scope, no duplicated PR/work, no public private media, no changes to the universal Project Leader.

Evidence: actual GitHub PR/commit/head and CI, actual Codex worker IDs if run, real overlap for parallel certification, explicit `NOT_VERIFIED` for missing external signals. `SUPERVISOR_CLOUD=FORWARDED` means API forwarding reported, not automatic proof that the phone displayed a notification.
