# Sources and provenance

Primary references used by the Project Leader control plane are recorded here with a stable URL and the date on which this repository rechecked the source. Product/runtime behavior is still validated against live repository and host evidence; a documentation link is not execution proof.

## ChatGPT plugins and marketplace import

OpenAI Help Center, checked 2026-10-07:

- Plugins in ChatGPT: https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- Importing and syncing plugin marketplaces from GitHub: https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github

These references support the distribution model used here: a GitHub-backed marketplace can expose plugins, plugins can include skills and required apps, and workspace synchronization does not itself grant provider access.

## Plugin manifest schema

Agent Plugins schema used by both package manifests, checked 2026-10-07:

- https://agent-plugins.org/schemas/1.0.0/plugin.schema.json

The package builder also validates the repository's stricter local identity, asset, connector and provenance requirements before producing installable ZIPs.

## Project-manager orchestration reference

OpenAI Cookbook:

- Repository: https://github.com/openai/openai-cookbook
- Notebook: https://github.com/openai/openai-cookbook/blob/main/examples/codex/codex_mcp_agents_sdk/building_consistent_workflows_codex_cli_agents_sdk.ipynb
- Registry entry: https://github.com/openai/openai-cookbook/blob/main/registry.yaml
- Checked: 2026-10-07.

Relevant idea: a project manager coordinates specialist roles, verifies evidence, and applies gatekeeping before transitions. Project Leader adapts that idea; it does not copy the notebook implementation.

## GitHub Actions event-policy readiness

GitHub documentation, checked 2026-10-07:

- Securely using pull_request_target: https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target
- About Actions policies: https://docs.github.com/en/actions/concepts/about-actions-policies
- Controlling who can execute GitHub Actions workflows: https://docs.github.com/en/actions/how-tos/administer/control-workflow-execution
- Actions policies REST API: https://docs.github.com/en/rest/actions/policies

GitHub states that the default public-repository policy blocking `pull_request_target` is currently in evaluate mode and is scheduled for enforcement on 2026-11-02 for affected repositories. Project Leader records this as a governance-readiness dependency; the code does not silently change repository Actions policy.

## License provenance

The OpenAI Cookbook is MIT licensed. That fact applies to the Cookbook, not automatically to this repository. Project Leader currently has no Owner-selected repository license; choosing one is a separate Owner/legal-distribution decision and must not be inferred from referenced sources.
