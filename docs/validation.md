# Public repository validation

This is an author-run evaluation of public source snapshots, recorded on
2026-09-07. These repositories have **not** been claimed as users, adopters,
endorsers, or contributors to mdlink-audit. No upstream issues or pull requests
were submitted as part of this evaluation.

The purpose is to exercise real documentation and identify useful findings and
unsupported syntax. The sample was selected for accessible Python-tooling
documentation and different document structures; it is not a random sample or a
precision, recall, or performance benchmark.

## Snapshot and scope

Every run selected the **whole checkout** (`--scope .`), using built-in directory
exclusions with no additional exclusions or ignored links. Checkout configuration
files were deliberately not loaded. All five worktrees were clean, and the script
verified that their Git revisions, status, and Markdown bytes stayed unchanged.
It read local Git metadata and source files; it did not install, import, or run
the evaluated repositories, build their sites, or request their linked URLs.

Counts below are link occurrences. "Reports" means diagnostics from the tool,
not confirmed defects in a repository or its published website.

| Repository at fixed commit | Markdown files | Default local links / reports | With HTML local links / reports |
| --- | ---: | ---: | ---: |
| [pypa/pipx @ c490b45](https://github.com/pypa/pipx/commit/c490b45bc4d18f8968d527ec2d37b8af36eb4361) | 9 | 0 / 0 | 0 / 0 |
| [Textualize/rich @ 9d8f9a3](https://github.com/Textualize/rich/commit/9d8f9a372cc5916fd4781fec207ced7ddac2f08f) | 45 | 11 / 0 | 11 / 0 |
| [pre-commit/pre-commit @ a9bba55](https://github.com/pre-commit/pre-commit/commit/a9bba55a3f74068b53f4bd4d831d7e05e34eae6c) | 3 | 1 / 1 | 1 / 1 |
| [mkdocs/mkdocs @ 2862536](https://github.com/mkdocs/mkdocs/commit/2862536793b3c67d9d83c33e0dd6d50a791928f8) | 37 | 353 / 31 | 366 / 43 |
| [astral-sh/uv @ 18d7dfc](https://github.com/astral-sh/uv/commit/18d7dfc0636973ff1f3720bf784fcfcc4a6d2656) | 202 | 486 / 56 | 486 / 56 |
| Total | 296 | 851 / 88 | 864 / 100 |

Zero reports is not comprehensive validation: pipx has zero local link
occurrences in this scope, while most links in rich are external and skipped.
Default mode skipped 7,451 external links; HTML mode skipped 7,476. Neither mode
checks external destinations or expands site-generator syntax.

## Manual review of representative reports

| Source evidence | Classification and interpretation |
| --- | --- |
| [pre-commit CHANGELOG line 1590](https://github.com/pre-commit/pre-commit/blob/a9bba55a3f74068b53f4bd4d831d7e05e34eae6c/CHANGELOG.md#L1590) targets `#1105`; the setext heading at line 1608 is `1.10.5 - 2018-08-06`. | Confirmed stale anchor in the source snapshot. Its heading slug is `1105---2018-08-06`; there is no `1105` anchor. |
| [uv changelog line 364](https://github.com/astral-sh/uv/blob/18d7dfc0636973ff1f3720bf784fcfcc4a6d2656/changelogs/0.4.x.md#L364) puts parentheses inside an angle-bracket destination. | Confirmed malformed destination in the source snapshot. The parsed destination starts with `(https:` and becomes a relative path instead of an HTTPS URL. |
| [uv FastAPI guide line 46](https://github.com/astral-sh/uv/blob/18d7dfc0636973ff1f3720bf784fcfcc4a6d2656/docs/guides/integration/fastapi.md#L46) targets `#unpackaged-applications`. | Confirmed absent anchor in the linked source snapshot. The relevant [current section](https://github.com/astral-sh/uv/blob/18d7dfc0636973ff1f3720bf784fcfcc4a6d2656/docs/concepts/projects/init.md#L259) is "Creating a project without a build system". |
| The other 54 uv reports target `docs/reference/cli.md`, `settings.md`, or `environment.md`. | Generated files are absent from the raw checkout. The [documentation workflow](https://github.com/astral-sh/uv/blob/18d7dfc0636973ff1f3720bf784fcfcc4a6d2656/.github/workflows/check-docs.yml#L27) generates them before the site build. These reports are not evidence of broken published links. |
| MkDocs links into [contributing.md](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/about/contributing.md) and [cli.md](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/user-guide/cli.md). | Unsupported include directives and generated command documentation. The source files do not contain the eventual headings. |
| MkDocs links to [locale anchors](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/user-guide/choosing-your-theme.md#L122). | Unsupported Markdown attribute-list IDs such as `{ #mkdocs-locale }`, not missing ordinary headings. Enabling static HTML does not implement this extension. |
| MkDocs [integration fixture](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/mkdocs/tests/integration/subpages/docs/index.md#L23) targets `/image.png`. | Fixture site-root semantics differ from repository-root semantics. The fixture's image exists under its nested `docs` directory; this is not an established documentation defect. |
| Twelve additional HTML reports in MkDocs, including [getting-started/](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/index.md#L17) and [theme images](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/user-guide/choosing-your-theme.md#L27). | Generated site routes and asset paths resolved relative to rendered pages. Static HTML support does not simulate the site's output layout. |
| MkDocs [release notes line 124](https://github.com/mkdocs/mkdocs/blob/2862536793b3c67d9d83c33e0dd6d50a791928f8/docs/about/release-notes.md#L124) uses `configuration.md/#enabled-option`. | Candidate source-path typo: a Markdown filename has a trailing slash. Published-site behavior was not tested, so this remains a candidate for upstream review. |

Other site assets, such as the MkDocs theme favicon, also need build context.
This review does not label every diagnostic a bug, estimate false-negative rates,
or establish that all supported syntax in the sample has been manually reviewed.
The [supported scope and limits](usage.md) remain the interpretation boundary.

## Reproduce

Use the mdlink-audit source accompanying this document and install its dependencies
as described in [Contributing](../CONTRIBUTING.md). Obtain clean local checkouts at
the exact commits linked above, then run from the mdlink-audit repository root:

```sh
python scripts/audit_corpus.py ../corpus/pipx ../corpus/rich ../corpus/pre-commit ../corpus/mkdocs ../corpus/uv --output ../corpus/default.json
python scripts/audit_corpus.py ../corpus/pipx ../corpus/rich ../corpus/pre-commit ../corpus/mkdocs ../corpus/uv --include-html --output ../corpus/html.json
```

Replace the paths with your own existing checkouts. The output parent directory
must exist, and the output must be outside every audited checkout. Both runs above
return exit code **1** because they contain reports; **2** means an operational
error. The JSON is still written when a checkout has reports or an operational
error. For a smaller experiment, repeat `--scope README.md --scope docs`; record
that changed selection and do not compare its counts to this whole-checkout table.

The script never clones or fetches. It records the configuration (including the
HTML flag), exact Git commits, selected paths, package and script hashes, Python
and parser versions, every selected Markdown file's SHA-256, a combined manifest
digest, and full diagnostics. Keep these JSON files with your own evaluation
records. The original full results are retained outside this repository as
`.validation-mdlink/results/corpus-default.json` and `corpus-html.json`. Download
the published [default report](https://github.com/christypixel68-cloud/mdlink-audit/releases/download/v0.2.0/corpus-default.json)
and [HTML report](https://github.com/christypixel68-cloud/mdlink-audit/releases/download/v0.2.0/corpus-html.json)
from the v0.2.0 release. In those copies, `checkout` and `report.root` replace
absolute machine paths with `owner/repository`; `publication_note` records this
normalization. Findings, hashes, and audit configuration are preserved. Third-party
source files are not redistributed. These artifacts record author testing, not
external adoption.

The recorded environment was Windows 10, Python 3.14.5, markdown-it-py 4.2.0, and
mdlink-audit 0.2.0. The package-source manifest digest was
`ad4b076665c2f7d670bff272a1e69e8950775f9bf2642831cad7146c53e6d4b6`.
These are raw byte hashes: Git's line-ending conversion affects them. This run
used `core.autocrlf=true`, subject to each repository's attributes. A checkout
with LF instead of CRLF can produce the same diagnostics and different hashes.

| Checkout | Markdown manifest SHA-256 |
| --- | --- |
| pipx | `06c4a8072526af31e30f4766d9d6b5a8990d0165a227e6bf16b7a21ffecc5bee` |
| rich | `09c7eaea328fbee3fb600d6fd30567195fe3768c1093e3bece7729f482db70e6` |
| pre-commit | `10d1c4f7ddfe57b1e9d455598c8669fb1ed4b60048106625eb44722eb2d8de4b` |
| mkdocs | `ef9a9bd05db219a3b5d45c353ae8fce444c9e794eb34576076e5203ef064cf6d` |
| uv | `5829ef29e3944bd1de995524b0cfbf80521365d48f84500278e5cb11b458e969` |
