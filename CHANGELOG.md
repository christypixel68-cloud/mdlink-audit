# Changelog

## 0.2.0 — HTML links and CI integration

- Added opt-in static HTML `href`/`src` validation and arbitrary HTML element IDs inside Markdown, preserving the default Markdown-only behavior.
- Added `include_html` configuration and `--include-html` / `--no-include-html` CLI overrides.
- Added a composite GitHub Action with multiline path inputs, configuration overrides, isolated Python subprocesses, and failure propagation.
- Added actual composite Action smoke checks for Linux, Windows, and macOS, including broken and corrected links.
- Run the pre-commit hook for all commits so changes to images and other linked targets trigger an audit even when no Markdown source changed.
- Added an offline corpus audit script that records repository revisions, source hashes, scan scope, and raw findings, with representative findings explained in the validation report.
- Retained JSON report schema version `1` and exit statuses `0`, `1`, and `2`.

## 0.1.0 — initial implementation

This entry describes the initial source implementation. It does not indicate a PyPI publication.

- Added offline validation of Markdown file links, image paths, Markdown heading fragments, and static HTML `<a>` anchors.
- Added repository-root and relative path resolution with Unicode and URL-encoded path handling.
- Added filename casing checks and rejection of targets outside the selected root.
- Added text, JSON, and GitHub Actions output formats.
- Added top-level TOML exclusions and ignored-link patterns, with additional CLI patterns.
- Added configurable empty-scan failure, contributor documentation, and issue templates.
- Added advisory suggestions for nearby filenames, headings, and corrected path casing.
- Added closed YAML front matter exclusion while preserving diagnostic line numbers.
- Rejected drive-qualified path segments on Windows and refreshed per-run caches when an auditor is reused.
- Prevented recursive discovery through Windows directory junctions and added boundary regression cases.
- Added CI configuration for Python 3.11–3.14 and three operating systems, minimum parser checks, and package verification.
- Added a broken-then-fixed demo and a clean-environment wheel smoke test.
