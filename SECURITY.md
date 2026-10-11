# Security policy

## Supported versions

Security fixes are developed against the current default branch and the latest verified plugin packages documented in `PLUGIN_SETUP.md` and `CHANGELOG.md`.

## Reporting a vulnerability

Do not publish credentials, tokens, exploit details, proof-of-concept payloads, or other sensitive information in a public issue.

For this public GitHub repository, the preferred private route is GitHub's **Security -> Report a vulnerability** flow when Private Vulnerability Reporting is enabled. GitHub repository security advisories keep the report and remediation discussion private until the maintainer chooses publication.

Repository security page:
https://github.com/martaxi-boss/Project-leader/security

GitHub reference:
https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/repository-security-advisories

If the repository does not expose **Report a vulnerability**, do not put vulnerability details in an issue. A separate private reporting address or enabling GitHub Private Vulnerability Reporting requires an explicit Owner governance/contact decision; Project Leader will not invent or publish a personal contact address.

## Scope

Security reports are especially relevant when they involve authorization bypass, Human Gate bypass, unintended repository mutation, secret exposure, duplicate/ambiguous writes, recovery-loop behavior, trusted-CI identity, or plugin packaging integrity.
