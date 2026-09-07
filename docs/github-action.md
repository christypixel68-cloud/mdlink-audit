# GitHub Action

Use `mdlink-audit` after checking out your repository and selecting Python 3.11 or
later. The composite action installs the source at the action revision you select,
then checks your checkout with GitHub Actions annotations.

## Workflow

The following example uses `v0.2.0`. For reproducible use, replace the version tag
with the full, reviewed commit SHA for the release.

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
          python-version: '3.11'
      - uses: christypixel68-cloud/mdlink-audit@v0.2.0
        with:
          paths: |
            README.md
            docs
```

The action uses the existing `python` on the runner; it does not choose or install
a Python version. It supports hosted Linux, macOS, and Windows runners with
Python 3.11 or later and pip. Installation can download build tools and Python
dependencies. The link check itself runs offline.

## Inputs

| Input | Default | Meaning |
| --- | --- | --- |
| `paths` | Empty | Markdown files or directories, one per line. Empty scans `root`. |
| `root` | `.` (workspace) | Repository boundary for resolving and validating links. |
| `config` | Empty | Explicit TOML configuration file. Otherwise uses `root/.mdlink-audit.toml` when present. |
| `exclude` | Empty | Additional file exclusion globs, one per line. |
| `ignore-links` | Empty | Additional link destination globs to skip, one per line. |
| `include-html` | Empty | `true` checks supported HTML `href`/`src` links; `false` disables it. Empty follows the TOML `include_html` setting. |
| `fail-on-empty` | `true` | Fail if no Markdown files are selected. Set `false` to allow an empty scan. |

`paths`, `root`, and `config` are relative to `GITHUB_WORKSPACE`, unless absolute.
Changing `root` does not change this base. For example, if `root: website`, use
`paths: website/docs`, or leave `paths` empty to scan all of `website`. The
checker's root containment rules still apply to all selected paths.

List inputs split on newlines, trim surrounding whitespace, and skip blank lines.
Spaces inside a path are preserved. Do not add shell quotes around a path or
separate paths with commas. Paths are literal filenames or directories, not glob
patterns. The `exclude` and `ignore-links` inputs accept globs and add to those in
the TOML file. See the [usage guide](usage.md) for configuration details.

```yaml
- uses: christypixel68-cloud/mdlink-audit@v0.2.0
  with:
    paths: |
      README.md
      docs/User Guide.md
    config: .github/mdlink-audit.toml
    exclude: |
      generated/**
      vendor/**
    ignore-links: |
      /generated-api/*
    include-html: 'true'
    fail-on-empty: 'true'
```

Boolean values accept `true` or `false`, ignoring case and surrounding whitespace.
An empty `include-html` preserves the configuration default; an empty
`fail-on-empty` uses `true`. Values such as `yes` and `0` are rejected before
installation. All inputs travel through environment variables to Python argument
lists, so shell expressions are literal text and cannot add CLI options.

## Results and permissions

The action prints `--format github` annotations for broken links and preserves the
CLI exit status: `0` for a passing scan, `1` for link issues, and `2` for input,
configuration, or read errors. Setup or installation failures also fail the step.
No write token or pull request comments are required; `contents: read` is enough
for the checkout in the example.

## Testing changes to the action

Within this repository, check out the revision being tested, set up Python, and
use `uses: ./` to exercise the local action. Test this on Linux, macOS, and Windows
before releasing. For a focused check without installing or downloading anything:

```sh
python -m pytest tests/test_action_entry.py
```

Those tests replace subprocess execution and cover input parsing, literal argv
handling, installation failure, and exit status propagation. They do not replace
an actual runner test of the composite action.
