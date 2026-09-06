# Usage

[Project overview](../README.md) · [Design and limitations](design.md)

## Installation

Use Python 3.11 or later. Install from a local checkout:

```sh
python -m pip install .
```

The distribution depends on `markdown-it-py` version 3 or 4. No network access is needed while auditing documents. Installation may need network access to resolve dependencies.

The CLI is available as either `mdlink-audit` or `python -m mdlink_audit`.

## Choose the repository and scan paths

```sh
mdlink-audit
mdlink-audit README.md docs
mdlink-audit --root /path/to/repository
```

Without `--root`, the tool walks upward from the working directory to the nearest directory containing `.git`. It also recognizes a `.git` file, as used in a Git worktree. If no Git root is found, the working directory becomes the root.

With no positional paths, the tool scans the selected root. Each explicit path is resolved relative to the working directory, even when `--root` is given. Paths must remain inside the selected root. A directory is searched for Markdown files; a file selects an individual Markdown source. Both `.md` and `.markdown` extensions are recognized, case-insensitively. When running outside the repository, pass its absolute root and either omit paths or use absolute paths within it.

The root also defines the meaning of links beginning with `/`. These are repository-root paths, not operating-system absolute paths. Ordinary relative link targets resolve from the directory containing the Markdown source.

## Command reference

```text
mdlink-audit [paths ...]
  [--root PATH]
  [--format text|json|github]
  [--config PATH]
  [--exclude GLOB ...]
  [--ignore-link GLOB ...]
  [--fail-on-empty]
  [--version]
```

Repeat the option itself to supply several patterns:

```sh
mdlink-audit --exclude "vendor/**" --exclude "generated/**"
mdlink-audit --ignore-link "/generated-api/*" --ignore-link "generated/*"
```

| Option | Purpose |
| --- | --- |
| `paths` | Markdown files or directories to scan; defaults to the root. |
| `--root PATH` | Set the repository boundary and base for `/` links. |
| `--format text` | Human-readable terminal results; the default. |
| `--format json` | Machine-readable audit results. |
| `--format github` | GitHub Actions workflow annotations. |
| `--config PATH` | Read a specified TOML configuration file. |
| `--exclude GLOB` | Exclude matching Markdown source paths from scanning. Repeatable. |
| `--ignore-link GLOB` | Skip matching link destinations. Repeatable. |
| `--fail-on-empty` | Exit with status `2` if no Markdown source files are selected. |
| `--version` | Print the installed version. |

Quote patterns so your shell does not expand them before the checker receives them.

## Configuration

The checker automatically loads `.mdlink-audit.toml` from the selected root when it exists. Use `--config` to choose a different configuration file.

```toml
exclude = ["vendor/**", "generated/**"]
ignore_links = ["/generated-api/*"]
```

Both values are arrays of strings at the top level. Do not wrap them in `[tool.mdlink-audit]` or another table. CLI patterns are added to the configuration patterns; they do not replace them. `exclude` selects source files to omit; it is not a way to ignore a missing destination. `ignore_links` skips matching link destinations completely. Keep exceptions narrow and explain why they are needed in TOML comments.

Exclusions match case-sensitive, repository-relative paths using forward slashes and Python-style `fnmatch` patterns. An initial `**/` also matches a file directly under the root; `generated/**` can exclude an entire directory. These are glob patterns, not regular expressions or `.gitignore` rules. In particular, Python `fnmatch` allows `*` to match `/` within a path.

The following directory names are excluded at every depth by default: `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `build`, `dist`, `.tox`, `.pytest_cache`, and `.ruff_cache`. Custom patterns add to these defaults. The `.github` directory is scanned normally.

Ignored-link patterns are tested against both the parser-normalized destination and its once URL-decoded form. For example, a destination containing `%20` may match a pattern containing a literal space. Ignored destinations contribute to the skipped count and are not checked for existence or headings.

## Link examples

The following fenced example illustrates supported Markdown forms; the filenames are hypothetical:

```markdown
[Guide](docs/guide.md)
[Repository file](/docs/guide.md)
[Section](docs/guide.md#installation)
[This page](#usage)
[Chinese path](docs/中文说明.md)
[Encoded space](docs/getting%20started.md)
![Diagram](images/diagram.png)

[Reference link][guide]
[guide]: docs/guide.md
```

Markdown files with fragments are checked against the destination document's headings and static HTML `<a id="...">` or `<a name="...">` anchors. Fragments on non-Markdown targets are not interpreted as document headings. A directory target is checked for existence only; a fragment on it is not checked against a README. Use exact filename casing even when your local filesystem accepts other casing.

Links with external protocols, such as `https:`, `mailto:`, and `data:`, and protocol-relative URLs are skipped and counted as skipped destinations. An offline pass therefore says nothing about whether an external website is reachable.

## Read the results

```sh
mdlink-audit --format text
mdlink-audit --format json > mdlink-report.json
mdlink-audit --format github
```

Text output is intended for local fixes. JSON is intended for scripts. GitHub output produces workflow annotations so a CI failure can point to the source document. Link locations usually identify the opening bracket of the link; see [location precision](design.md#location-precision).

JSON audit reports use `schema_version: 1` and include the selected `root`, a `summary` with `files_scanned`, `links_checked`, `links_skipped`, and `issues` counts, skipped counts by `external` and `ignored` reason, and an `issues` array. Each issue contains `file`, `line`, `target`, `code`, `message`, and `suggestion`. A suggestion is a candidate link string, or `null` when no close match exists. It is advisory: no files are modified, and a suggested path may still need its fragment corrected. Audit-time input, configuration, or read failures produce an error object containing `schema_version` and `error` and return status `2`. Command-line syntax errors, such as unknown options, use the argument parser's standard error output instead.

For example, a `#instal` link can suggest `#install`; `docs/Guide.md` can suggest the on-disk spelling `docs/guide.md`. Suggestions preserve the query string and repository-root versus relative path style.

At the beginning of a document, a `---` line followed by a closing `---` or `...` line is treated as YAML front matter. It is ignored for links and headings while source line numbers are preserved. An unclosed block is parsed as ordinary Markdown.

| Exit code | Meaning |
| --- | --- |
| `0` | No link issues; an empty scan also succeeds unless `--fail-on-empty` is set. |
| `1` | At least one link issue, such as a missing target or heading. |
| `2` | Invalid configuration, input, or a read error; also an empty scan with `--fail-on-empty`. |

Use the process exit code as the CI gate. Do not assume that receiving a report means validation succeeded.

## Troubleshooting

- **A link works on Windows but fails here:** check each path component's casing against the actual filenames.
- **A `/docs/...` link resolves unexpectedly:** verify the selected `--root`; leading `/` is relative to that root.
- **A generated route is reported as missing:** the checker validates filesystem targets. Build the real target before auditing or add a narrow `ignore_links` entry.
- **A symlink points to an existing file but fails:** targets outside the selected root are not read. Keep audited documentation and targets inside the root.
- **No documents were checked:** verify paths and exclusions, and use `--fail-on-empty` in CI.
- **An HTML or MDX link is absent from results:** those syntaxes are outside the current parser scope.

For a bug report, include a minimal source file, any destination file, the exact command, root and working directory, Python version, operating system, and actual output. Remove private paths and content before sharing.
