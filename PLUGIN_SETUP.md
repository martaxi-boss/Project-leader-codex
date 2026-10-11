# Project Leader plugin setup

This repository contains two ChatGPT plugins:

- **Project Leader** — primary project controller.
- **Recovery Guardian** — independent recovery controller for interrupted/failed sessions.

Project Leader also uses the Recovery Guardian protocol internally, so normal work does not require manual role switching.

## Current canonical runtime

- Project Leader **0.7.0**.
- Recovery Guardian **0.6.0**.

These are compatibility versions in `plugin.json`, not immutable source/build revisions. The 2026-10-09 maintenance updated Project Leader's E1 preflight and Recovery Guardian's Skill guidance without changing those manifest versions. Use the exact GitHub `main` SHA or package provenance to identify the current bytes rather than assuming a constant version string means unchanged instructions.

Before consequential work, read the live `PROJECT_LEADER.md`, `RUNBOOK.md`, `RECOVERY_PROTOCOL.md`, role contracts and `projects/standing-authority.json` from canonical GitHub state. The active target's architecture and live repository state define its bounded task; external projects do not require central enrollment.

On each `@Project Leader` invocation, the Skill performs `CANONICAL_RUNTIME_BOOTSTRAP` when GitHub read access is available. Loader contract v1 (minimum loader version 1) resolves canonical `main` once to an exact `RUNTIME_CANONICAL_REVISION`; plugin, Skill, control documents and policies for that control decision are then read at that same immutable SHA. If the installed/runtime copy lags, `RUNTIME_SYNC_STALE -> RUNTIME_CANONICAL_OVERRIDE_ACTIVE` uses that pinned generation without requiring manual resync. A loader below the minimum must refuse an incompatible override rather than mixing revisions.

The 0.7.0 runtime preserves `BOUNDED_STATE_PREFLIGHT`, non-blocking repository hygiene, direct covered Recovery, and the execution-first contract. This compatible incremental refinement adds only `FAST_VALIDATION_BEFORE_FULL_VALIDATION`, `SUPERSEDED_WORK_AUTO_CANCEL`, and `FIRST_SUFFICIENT_SAFE_PASS_STOP` to reduce unnecessary validation, obsolete CI tracking, and optional post-PASS work.

It also adds strict JSON/policy input semantics plus observable behavioral acceptance for ambiguous writes, restart deduplication, bounded internal liveness and live CI reconciliation through the testable runtime adapter.

Version 0.7.0 keeps the existing Human Gate closure, authority/effect boundaries, stale-base protection, security checks, anti-loop behavior, and material E2/E3 controls unchanged. Recovery Guardian 0.6.0 was unchanged in the original 2026-10-07 refinement; its Skill guidance was subsequently updated by the compatible 2026-10-09 patch, with mandatory security and control boundaries intact.

Covered executable transitions continue through exact Supervisor authorization and validation under standing Owner authority. Human interruption is reserved for exclusive human intervention or a new uncovered material decision.

## GitHub Marketplace synchronization (verified 2026-10-09)

For the current ChatGPT workspace, the verified normal update path is **Marketplaces -> Project Leader repository -> Sincronizar agora**, with automatic sync enabled where available. The tracked marketplace source is `https://github.com/martaxi-boss/Project-leader` on `main`, manifest `.agents/plugins/marketplace.json`, and source path set to the repository root.

The `project-leader` marketplace entry deliberately contains the exact `pluginId` of the pre-existing plugin in this workspace. That identifier is workspace-installation-specific: do not reuse it for a different ChatGPT workspace without checking the target installation and supported association process. The `recovery-guardian` entry is unchanged. The workspace UI confirmed both plugins imported without errors at the corresponding canonical commit. A successful GitHub package build alone never proves the workspace has actually synchronized.

Prefer this Marketplace path for subsequent updates; the ZIP process below is a fallback for an installation that cannot use Marketplace sync and does **not** provide ongoing GitHub synchronization.

## Proven direct install path

The installation path verified in the current ChatGPT workspace is:

1. Open **Plugins**.
2. Press the **+** button beside plugin search.
3. Choose **Carregar plugin / Upload plugin**.
4. Select the installable ZIP:
   - `project-leader.zip`
   - `recovery-guardian.zip`
5. Wait for **Importação bem-sucedida / Import successful**.
6. Press **Ver plugin / View plugin**.
7. Press **Instalar plugin / Install plugin**.
8. Approve the GitHub dependency if prompted.

After installation, verify availability in a project chat by typing `@pro`. **Project Leader** should appear. **Recovery Guardian** should also be available when explicitly searched or selected.

## GitHub-built ZIP artifacts

The workflow `.github/workflows/package-plugins.yml` produces installable ZIP artifacts for both plugins on pull requests and pushes to `main`.

Each ZIP is built with the plugin manifest at the ZIP root, matching the direct upload format.

For each packaging run, verify `plugin-manifest.json` and `SHA256SUMS` from the same GitHub Actions artifact set. Manifest v2 binds the repository, exact source revision, build workflow/run identity, ZIP digest and per-file content hashes. Treat a ZIP without that matching manifest/checksum set as unverified distribution output.

## Normal use

Inside a ChatGPT Project:

`@Project Leader`

Then give the command, for example:

- `Faz uma auditoria completa deste projeto.`
- `Continua a construção a partir do estado atual.`
- `Vê o PR aberto e corrige o que faltar.`

Project Leader automatically routes through Consultant, Supervisor, Builder, and Recovery Guardian phases as needed.

## Manual recovery

After an interrupted session you may instead invoke:

`@Recovery Guardian`

Then:

`Recupera e continua a partir do último estado verificável.`

Recovery Guardian reconstructs from GitHub before repeating any write.

## Important limitation

Neither plugin can keep running inside ChatGPT while the ChatGPT service itself is unavailable, and Recovery Guardian cannot passively watch another dead chat. The resilience mechanism is durable-state recovery from GitHub after service returns.

## GitHub dependency

Both plugins reference the installed OpenAI GitHub connector. Access remains limited to the repositories and actions authorized for the signed-in account.

## Historical host runtime observation — 2026-10-07

The host observed on 2026-10-07 successfully resolved an installed Project Leader skill entrypoint at `skills://plugins/project-leader/project-leader/skill.md`, which proves that the skill is invocable in this workspace.

The loaded host copy observed on 2026-10-07 still contains the earlier floating-`main` bootstrap wording, while canonical GitHub `main` at `e633144e11b10f1e6e28c778cd42360e1c147985` contains the current single-revision bootstrap contract. This is an observed `RUNTIME_SYNC_STALE` case, not a runtime stop: the canonical contract requires `RUNTIME_CANONICAL_OVERRIDE_ACTIVE` and pins the invocation to the exact live canonical revision.

The available ChatGPT plugin-management dependency lookup does not resolve `project-leader` as a public globally listed plugin with a current release. Therefore this repository does **not** claim a portable public-marketplace release identity from that surface. The verified operational facts are narrower: the skill is invocable in the current host, canonical GitHub is readable, and stale loaded bytes are reconciled by the documented bootstrap/override path.

This dated host observation is historical runtime evidence, not a live claim about the currently installed skill URI and not a cryptographic attestation of the installed ZIP bytes. For distributable artifacts, continue to use the GitHub Actions `plugin-manifest.json` + `SHA256SUMS` provenance path described above.

## License

Project Leader is distributed under a **proprietary / All Rights Reserved** license selected by the repository Owner. The repository does not grant a general open-source reuse license. See `LICENSE` for the complete terms; third-party components and services retain their own licenses and terms.
