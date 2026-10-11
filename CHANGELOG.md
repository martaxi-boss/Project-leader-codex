# Changelog

This file records consumer-visible Project Leader control/runtime changes. Exact implementation and CI evidence remain in Git history, pull requests, Task Authorization records, Worker Results and transition records.

## 0.7.0 / Recovery Guardian 0.6.0 — 2026-10-07

### Compatible operational/Marketplace maintenance — 2026-10-09

- Enforce a per-candidate fast E1 validation preflight before avoidable heavy-CI-triggering pushes. Reject stale focused test evidence, route focused failures to direct Recovery Guardian repair, and retain all mandatory full/security/exact-commit checks and independent Supervisor material audits.
- Compact ordinary E1 cross-role context and Recovery Guardian reporting. This update changed both Skill instruction files, without changing the plugin manifest compatibility versions (0.7.0 / 0.6.0).
- Bind the existing Project Leader workspace plugin to GitHub Marketplace synchronization by its verified `pluginId` instead of creating a second plugin. Regression coverage preserves the Recovery Guardian marketplace entry and canonical-bootstrap rules.
- Reconcile setup documentation with the actual synced Marketplace and retain historical schema/evidence files needed for recovery. Old superseded builder refs may be removed only by exact-revision authorization and lease-safe repository hygiene; canonical records and unique evidence remain.


### Incremental operational-efficiency refinement

- Add `FAST_VALIDATION_BEFORE_FULL_VALIDATION`: normal E1 rejects incoherent candidates with the smallest relevant validation before any already-required heavy/full validation, while final security/regression/certification and exact-state proof remain mandatory.
- Add `SUPERSEDED_WORK_AUTO_CANCEL`: old heavy E1 work may be classified `SUPERSEDED` and cancelled/hygienized only when it cannot certify the current state, has no exclusive diagnostic evidence still needed, and cancellation is safe.
- Add `FIRST_SUFFICIENT_SAFE_PASS_STOP`: once objective, acceptance criteria, mandatory regressions/full validation, exact-state certification, hygiene and no-required-work conditions are all satisfied, optional adjacent improvement stops.
- Preserve the existing 0.7.0 architecture and protections unchanged: FAST_E1/DURABLE_CONTROL, direct Recovery, anti-loop, REGRESSION_FIRST/SAFE_ROLLBACK, stale-base protection, secrets/scope discipline, progressive loading and material E2/E3 governance remain intact.

- Make `EXECUTION_FIRST_WITHIN_BOUNDS` and FAST_E1 the normal path for reversible covered work; remove authorization-only/task-result/handoff ceremony from ordinary E1.
- Add `PROGRESS_OVER_PROCESS`, `FUNCTIONAL_CONVERGENCE_FIRST`, `DIAGNOSIS_MUST_BUY_A_DECISION`, `REGRESSION_FIRST`, selective safe rollback, evidence reuse and progressive loading.
- Keep Consultant, Supervisor, Builder and Recovery Guardian as internal capabilities rather than a mandatory serialized chain; Recovery Guardian directly repairs covered faults.
- Preserve proportional durable controls for destructive/privileged/material architecture, release/deploy/production, permission/secrets/trust/governance, irreversible, ambiguous-write and continuity/audit-sensitive work.
- Add executable FAST_E1 vs DURABLE_CONTROL selection and tests for decision-buying diagnosis/regression handling.
- Close the stale-base gap even with GitHub ruleset strict-update disabled: isolate PR admission and push invalidation into separate event-specific workflows; a push to `main` invalidates prior `trusted-authorization` certification on every open PR head through the GitHub Actions commit-status context, forcing recertification without cross-event job-graph coupling or Checks API write permission.
- Finalize coherent version identity as Project Leader 0.7.0 / Recovery Guardian 0.6.0 after the execution-first implementation reached required CI validation; retain continuous same-cycle hygiene.

### Included audit hardening carried forward from the prior unreleased state

- Tighten JSON/schema semantics so booleans cannot masquerade as numbers, anchored identifiers reject trailing data, and date-time fields use RFC3339 extended form.
- Reject partial/mixed fixed-vs-`ACTIVE_TARGET` project policy declarations.
- Protect root-level `secrets*` and nested `.env*` paths under the generic managed-project policy.
- Require the canonical standing-authority control set and distinct schema IDs for legacy versions.
- Reject malformed external-CI observations and helper booleans before using them as execution evidence.
- Add `control/runtime_execution.py` plus behavioral acceptance for bounded preflight, internal-stall detection, ambiguous-write reconciliation, restart deduplication, timeout handling and external-CI routing.
- Remove obsolete Recovery wording and tautological phrase-only assertions while retaining behavior-level tests.
- Add explicit source/provenance links, distribution-verification instructions and GitHub Actions event-policy readiness documentation.
- Record an observed ChatGPT host invocation of the Project Leader skill, including stale-loaded-copy reconciliation via canonical runtime override and the absence of a public global release identity in the available plugin-management surface.
- The repository Owner selected a proprietary / All Rights Reserved license; `LICENSE` now records that no general open-source reuse permission is granted and preserves third-party license obligations.

## 0.6.8 / Recovery Guardian 0.5.6 — 2026-10-06

- Simplified Project Leader execution around direct covered work, compact Recovery Guardian repair and continuous same-cycle hygiene.
- Added bounded state preflight and stale/live Work liveness reconciliation.
- Added pinned canonical runtime generation and stronger package provenance/confinement.
- Hardened trusted CI evidence, immutable authorization history, Recovery journal continuity and transition-failure evidence.

## Historical versions

Older durable records and legacy schemas remain in the repository for audit compatibility. Git history is authoritative for exact pre-0.6.8 changes.
