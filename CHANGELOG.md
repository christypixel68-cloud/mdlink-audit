# Changelog

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
