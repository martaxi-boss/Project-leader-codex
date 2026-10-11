# Project Leader

GitHub-backed software-project coordination, packaged as two ChatGPT plugins:

- **Project Leader** — the single entry point for project work.
- **Recovery Guardian** — recovery after interrupted or failing execution.

Project Leader is an independent control project. External projects keep their architecture, implementation, credentials, CI and durable state in their own repositories. Every mutable task targets one repository.

## Use

`Open the relevant ChatGPT Project -> New chat -> @Project Leader`

Invocation activates the controller. The Owner then gives the concrete instruction to audit, build, fix, recover or continue.

Project Leader reconstructs live GitHub state and coordinates Consultant, Supervisor, Builder and Recovery Guardian as internal capabilities rather than a mandatory handoff chain. Builder handles planned implementation; Recovery Guardian directly fixes covered recoverable E1 failures and only returns to Supervisor for material boundaries, consequential transitions or independent acceptance checkpoints.

Every invocation now performs a silent canonical runtime bootstrap against the live Project Leader `main` contract when GitHub is readable. If the locally loaded Skill copy is stale, execution switches immediately to the canonical contract for that invocation instead of waiting for marketplace propagation.

Before broad repository compare/reconstruction work, Project Leader checks a bounded durable state vector first, reuses still-valid preflight dimensions, and expands only to exact refs/files/run IDs when necessary. Background repository branch hygiene remains non-blocking, while `CONTINUOUS_HYGIENE_ACTIVE` makes recoverable cleanup caused by the current mutation part of the same work cycle. Explicit read-only remains strictly non-mutating.

Covered work is execution-first: `RECONSTRUCT MINIMUM -> EXECUTE -> TEST -> CORRECT -> HYGIENIZE -> VALIDATE -> CONTINUE`. Normal reversible E1 uses FAST_E1 without authorization-only commits or role handoff ceremony. Material effects use proportional durable control. A failed check routes to direct bounded recovery when covered.

## Authority and transitions

`projects/standing-authority.json` defines the standing Owner autonomy rule. Consequential effects require exact-target Supervisor audit, successful required validation and CI, and durable transition authorization and result records.

A covered, executable and validated transition uses `STANDING_OWNER_GRANT` and continues automatically. Human interruption is reserved for `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`. Recovery preserves existing authority and never expands it.

The executable standing-authority resolver recomputes access/diagnostic closure before operational Human Gates and requires convergence plus an exact evidenced manual action. Missing tooling alone remains discovery/remediation. Physical tests remain valid manual steps after automated prerequisites and independent covered work are complete.

External targets bootstrap from their own architecture and live repository state. Use an explicitly selected target policy when applicable; otherwise bind `control/generic-project-policy.json` and narrow each task to the authorized objective.

## Canonical contracts

- `PROJECT_LEADER.md` — operational contract.
- `RUNBOOK.md` — execution and validation flow.
- `RECOVERY_PROTOCOL.md` — bounded recovery and CI waiting.
- `roles/` — Consultant, Supervisor, Builder and Recovery Guardian responsibilities.
- `projects/standing-authority.json` — standing Owner authority.
- `projects/policies/project-leader.json` — this repository's policy ceiling.
- `control/generic-project-policy.json` — architecture-first external-target policy.
- `control/` — executable authorization, scope, integrity and evidence checks.
- `SMOKE_TESTS.md` — acceptance scenarios.

Durable material tasks use current v2 records, exact policy binding and concrete CI evidence when required. Normal covered E1 does not create those records by default. Recovery Compaction keeps diagnose/fix/test cycles free of control-only commit spam; archived schemas remain available for historical/material audit validation.

Behavioral acceptance now also uses `control/runtime_execution.py`, an injected observable adapter for bounded preflight, internal-liveness observations, external-CI reconciliation, and verify-before/after handling of ambiguous writes. It is deliberately small: it makes the existing protocol testable without turning Project Leader into a separate long-running service.

## Installation and packaging

See `PLUGIN_SETUP.md` for installation. `.github/workflows/package-plugins.yml` builds deterministic installable ZIPs and a supply-chain manifest.

- Project Leader: **0.7.0**.
- Recovery Guardian: **0.6.0**.
- Marketplace: `.agents/plugins/marketplace.json`.
- Plugin source: `plugins/project-leader/` and `plugins/recovery-guardian/`.

Both plugins use the OpenAI GitHub connector, limited to the repositories and actions authorized for the signed-in account.

## Continuity and repository hygiene

GitHub stores task authority, commits, PRs, CI, results and transition evidence. Verify a potentially completed write before repeating it. Reconstruct from the last verified durable state after an interruption.

Continuous hygiene removes or neutralizes stale operational code/configuration/references/probes created or exposed by the current authorized change when cleanup is recoverable and in scope. Background repository hygiene separately removes audited obsolete refs. Preserve useful audit evidence, ADRs and inert history; explicit read-only requests only report hygiene debt and never mutate.

A ChatGPT-wide outage prevents execution while the service is unavailable. Resume by reconstructing GitHub state after service returns.

## License

Project Leader is proprietary software. Copyright (c) 2026 martaxi-boss. **All rights reserved.** No general permission is granted to copy, modify, redistribute, sublicense, sell, host, publish, commercialize, or create derivative works. See `LICENSE` for the full terms. Third-party components remain subject to their own licenses.
