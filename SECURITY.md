# Security policy

mdlink-audit checks local repository content. It does not need credentials or network access during an audit.

## Report a suspected vulnerability

Please do not publish sensitive exploit details, credentials, or private repository content in a public issue.

If the repository's **Security** tab offers **Report a vulnerability**, use GitHub's private reporting flow. If that option is unavailable, open a public issue that only asks for a private reporting channel and does not include exploit details. No private email address or response-time guarantee is currently advertised.

A useful private report includes the affected version, platform, minimal reproduction, expected boundary, observed behavior, and potential impact. Remove unrelated personal or confidential data.

## Scope

Potential issues include reading a target outside the selected root, unsafe handling of untrusted paths, and unsafe output escaping. Ordinary missing links, unsupported syntax, and parser compatibility differences are usually regular bugs.

The tool's root restriction is a validation rule, not a sandbox for hostile filesystem activity. Audit untrusted repositories with normal least-privilege permissions, and review dependency and workflow changes before adopting them.

## Supported versions

During early `0.x` development, fixes target the latest release and development version. There is no long-term support branch yet. Confirm the current changelog before reporting an issue already addressed by a newer version.
