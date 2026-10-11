# Project Leader project context

Project Leader is an independent project and reusable control skill.

This directory does **not** register or own external projects. Target-project architecture, implementation, CI, releases, and durable state belong to the active target repository.

Project Leader discovers the active target from current Project context, Owner instruction, and live GitHub evidence.

Current Project Leader-owned project context in this directory:

- `standing-authority.json` — durable Owner standing autonomy for the Project Leader runtime.
- `policies/project-leader.json` — Project Leader's own repository policy.

External target projects use an explicitly selected target-specific central policy only when one is intentionally maintained. Otherwise Project Leader uses `../control/generic-project-policy.json` and narrows each task from the target project's own architecture and live state.

Historical project-specific bootstrap snapshots or registry entries are not part of the current runtime and should not be reintroduced.
