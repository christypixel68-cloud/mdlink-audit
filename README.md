# mdlink-audit

Check local Markdown links before a rename, a move, or a release breaks your documentation.

**mdlink-audit** is a small Python command-line tool for checking file links, image paths, and Markdown heading fragments inside a repository. It runs offline and can report failures in your terminal, as JSON, or as GitHub Actions annotations.

[中文说明](README.zh-CN.md) · [Usage](docs/usage.md) · [Design and limitations](docs/design.md) · [Contributing](CONTRIBUTING.md)

## What it checks

- Relative links and repository-root links, such as `../guide.md` and `/docs/guide.md`.
- File and image targets, including Chinese filenames and URL-encoded spaces.
- Heading fragments in Markdown files, including links within the same document.
- Filename casing, including on Windows, to catch links that would fail on a case-sensitive runner.
- Targets that escape the selected repository root, including symlinks that point outside it.
- Suggestions for close filename and heading matches, without modifying your documents.

Closed YAML front matter, code examples, and comments are excluded from link extraction.

External URLs and protocol links are skipped; no requests are made to check them. Raw HTML `href`/`src`, MDX expressions, and documentation framework routes are outside the current scope.

## Try it

Requires **Python 3.11 or later**. Clone the repository and install it:

```sh
git clone https://github.com/christypixel68-cloud/mdlink-audit.git
cd mdlink-audit
python -m pip install .
python -m mdlink_audit --help
python -m mdlink_audit .
```

The installed command is also available as `mdlink-audit`:

```sh
mdlink-audit --root /path/to/repository
mdlink-audit README.md docs --format text
mdlink-audit --format json
```

To see a temporary repository fail with a casing error and a stale heading, then pass after both are fixed:

```sh
python examples/demo.py
```

By default, the root is the nearest parent directory containing `.git`, starting at the working directory; if none exists, it is the working directory. With no paths, the tool scans the root. Explicit paths are relative to the working directory and must stay inside the selected root.

Exit status is `0` when no link issues are found, `1` when links fail validation, and `2` for invalid input, configuration, or read errors. An empty scan passes by default; use `--fail-on-empty` to treat it as an input error.

## Configuration

Place `.mdlink-audit.toml` in the repository root:

```toml
exclude = ["generated/**", "vendor/**"]
ignore_links = ["/generated-api/*"]
```

These are top-level keys, with no table header. You can also pass `--config`, repeat `--exclude`, or repeat `--ignore-link`. See the [usage guide](docs/usage.md) before ignoring links: an ignored destination is no longer validated.

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
      - run: python -m pip install "git+https://github.com/christypixel68-cloud/mdlink-audit.git@main"
      - run: mdlink-audit --format github --fail-on-empty
```

Source is available on [GitHub](https://github.com/christypixel68-cloud/mdlink-audit); the package has not been published to PyPI. Use the source installation instructions above. Replace `main` in the workflow example with a reviewed commit for reproducible adoption. The installed checker itself runs without network access.

## Scope and status

This is an initial `0.1.0` implementation. Other link checkers already cover overlapping use cases; this project focuses on an offline Python workflow with local paths, heading validation, and actionable CI output. It is not a full GitHub renderer and does not claim complete GitHub Flavored Markdown compatibility.

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
