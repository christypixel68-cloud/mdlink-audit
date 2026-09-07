# mdlink-audit

[![CI](https://github.com/christypixel68-cloud/mdlink-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/christypixel68-cloud/mdlink-audit/actions/workflows/ci.yml)

Check local Markdown links before a rename, a move, or a release breaks your documentation.

**mdlink-audit** is a small Python command-line tool for checking file links, image paths, and Markdown heading fragments inside a repository. It runs offline and can report failures in your terminal, as JSON, or as GitHub Actions annotations.

[中文说明](README.zh-CN.md) · [Usage](docs/usage.md) · [GitHub Action](docs/github-action.md) · [Repository validation](docs/validation.md) · [Contributing](CONTRIBUTING.md)

## What it checks

- Relative links and repository-root links, such as `../guide.md` and `/docs/guide.md`.
- File and image targets, including Chinese filenames and URL-encoded spaces.
- Heading fragments in Markdown files, including links within the same document.
- Filename casing, including on Windows, to catch links that would fail on a case-sensitive runner.
- Targets that escape the selected repository root, including symlinks that point outside it.
- Suggestions for close filename and heading matches, without modifying your documents.
- Opt-in static HTML `href`/`src` links and element IDs inside Markdown.

Closed YAML front matter, code examples, and comments are excluded from link extraction.

External URLs and protocol links are skipped; no requests are made to check them. MDX expressions, `srcset`, CSS URLs, and documentation framework routes are outside the current scope.

## Try it

Requires **Python 3.11 or later**. Install the versioned source with pip and Git, then run the checker from the repository you want to audit:

```sh
python -m pip install "git+https://github.com/christypixel68-cloud/mdlink-audit.git@v0.2.0"
python -m mdlink_audit --help
python -m mdlink_audit .
```

Alternatively, download a wheel from the [GitHub release](https://github.com/christypixel68-cloud/mdlink-audit/releases/tag/v0.2.0) and install it with `python -m pip install path/to/downloaded.whl`. The package is not published to PyPI.

The installed command is also available as `mdlink-audit`:

```sh
mdlink-audit --root /path/to/repository
mdlink-audit README.md docs --format text
mdlink-audit --format json
```

From a source checkout, run the temporary broken-then-fixed demonstration:

```sh
git clone https://github.com/christypixel68-cloud/mdlink-audit.git
cd mdlink-audit
python examples/demo.py
```

By default, the root is the nearest parent directory containing `.git`, starting at the working directory; if none exists, it is the working directory. With no paths, the tool scans the root. Explicit paths are relative to the working directory and must stay inside the selected root.

Exit status is `0` when no link issues are found, `1` when links fail validation, and `2` for invalid input, configuration, or read errors. An empty scan passes by default; use `--fail-on-empty` to treat it as an input error.

## Configuration

Place `.mdlink-audit.toml` in the repository root:

```toml
exclude = ["generated/**", "vendor/**"]
ignore_links = ["/generated-api/*"]
include_html = true
```

These are top-level keys, with no table header. HTML checking defaults to off; use `include_html = true` or `--include-html` to include static HTML links and IDs. You can also pass `--config`, repeat `--exclude`, or repeat `--ignore-link`. See the [usage guide](docs/usage.md) before ignoring links: an ignored destination is no longer validated.

## GitHub Actions

The [project CI workflow](.github/workflows/ci.yml) runs on pushes and pull requests. Another repository can use a workflow such as:

```yaml
name: Documentation links
on: [push, pull_request]

permissions:
  contents: read

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6
        with:
          python-version: "3.11"
      - uses: christypixel68-cloud/mdlink-audit@v0.2.0
        with:
          include-html: 'true'
```

The action checks the whole repository and fails on an empty scan by default. See [action inputs](docs/github-action.md#inputs) for path and configuration options. Pin actions to reviewed full commit SHAs for reproducible use. Installation may download dependencies; the installed checker itself runs without network access.

## pre-commit

Add this to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/christypixel68-cloud/mdlink-audit
    rev: v0.2.0
    hooks:
      - id: mdlink-audit
```

The hook scans the entire repository on every invocation, including commits that only move or remove images or other linked files. This catches inbound links whose source Markdown was not edited.

## Scope and status

Version `0.2.0` is an early release. Other link checkers already cover overlapping use cases; this project focuses on an offline Python workflow with local paths, heading validation, and actionable CI output. It is not a full GitHub renderer and does not claim complete GitHub Flavored Markdown compatibility.

Please read the [known limitations](docs/design.md#known-limitations) before using it as a release gate. The [roadmap](docs/roadmap.md) describes proposed improvements, and the [changelog](CHANGELOG.md) records implemented changes.

## Development

```sh
python -m pip install ".[dev]"
python -m ruff check .
python -m ruff format --check .
python -m pytest
python -m mdlink_audit . --fail-on-empty
```

Small reproduction cases and cross-platform fixes are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

See [release preparation](docs/releasing.md) for building and verifying installable artifacts.

## License

MIT. See [LICENSE](LICENSE).
