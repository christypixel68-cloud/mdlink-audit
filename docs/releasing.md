# Release preparation

[Project overview](../README.md) · [Contributing](../CONTRIBUTING.md)

Source and versioned distribution artifacts are available on [GitHub](https://github.com/christypixel68-cloud/mdlink-audit/releases). The package has not been published to PyPI. Use this checklist to verify a candidate before creating a versioned release or publishing distribution artifacts.

## Verify a candidate

Use Python 3.11 or later from the repository root:

```sh
python -m pip install ".[dev]" "twine>=6,<8"
python -m ruff check .
python -m ruff format --check .
python -m pytest -q
python -m mdlink_audit --fail-on-empty
python examples/demo.py
python -m build
python -m twine check dist/*
python scripts/smoke_wheel.py
```

The wheel smoke test expects a single wheel in `dist/`. It downloads dependency wheels into a temporary directory, creates a fresh virtual environment, installs with `--no-index`, and exercises the installed module and console command against a temporary repository. The checker's audit itself makes no network requests.

To verify the pre-commit integration, install `pre-commit>=4,<5` and run `python scripts/smoke_precommit.py`. It installs the actual hook into a temporary consumer repository, checks an unchanged Markdown document when only an image is selected, and verifies failure before and success after correcting the image path. Hook installation may download dependencies.

The [CI workflow](../.github/workflows/ci.yml) configures Linux, Windows, and macOS checks, Python 3.11–3.14, a minimum-parser compatibility job, and package verification. The composite Action is also installed and exercised on all three operating systems, including a deliberately broken HTML link and its correction. Review the [Actions results](https://github.com/christypixel68-cloud/mdlink-audit/actions/workflows/ci.yml) for the exact commit being released; a local test does not establish that every configured platform passed. Symlink fixtures skip only when the host cannot create symlinks.

## Inspect artifacts

Inspect the generated wheel and source archive before distribution. Confirm that the wheel includes the CLI modules and license, and that the source archive includes documentation, tests, examples, and the release verification script. Exclude virtual environments, caches, credentials, and unrelated workspace content.

Build into a directory containing only the current version. Keep previous artifacts elsewhere before running the clean-wheel smoke test. Upload the wheel, source archive, and a SHA-256 checksum file to a GitHub release targeting the exact passing commit. Download the public artifacts and verify their hashes before announcing the release. Do not move an existing release tag to a different commit.

Check the version in `pyproject.toml` against `src/mdlink_audit/__init__.py`. Record real changes and limitations in [CHANGELOG.md](../CHANGELOG.md). Package metadata and repository links must refer to the actual public repository before publication.

## Publish deliberately

Create a release only after reviewing the candidate and passing the intended platform checks. If publishing to a package index, verify ownership and name availability there first; the source checkout does not reserve the name. Prefer a dedicated publishing environment with trusted publishing over storing API tokens in this repository. Do not reuse an already-published version number.

Keep release notes factual: list the changes, tests that ran, known limitations, and upgrade effects. Do not describe configured jobs as successful until they have run.
