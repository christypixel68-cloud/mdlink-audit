# Design

[Project overview](../README.md) · [Usage](usage.md) · [Roadmap](roadmap.md)

## Purpose

The checker answers a narrow question: do the local links written in a repository's Markdown point to available files and headings within the selected root?

The initial implementation favors a predictable offline command, a small Python dependency footprint, and reports useful in both a terminal and GitHub Actions. Existing Markdown and general-purpose link checkers already solve parts of this problem. This project does not claim to invent local-link checking or replace every documentation toolchain.

## Audit flow

1. Resolve the repository root, input paths, and TOML configuration.
2. Discover Markdown sources within the root, applying source exclusions.
3. Parse Markdown using `markdown-it-py` and collect link and image destinations.
4. Skip configured destinations and external protocols.
5. Resolve local paths, preserving the repository boundary and checking filename casing.
6. For Markdown fragments, compare the requested fragment with the destination headings.
7. Render results in the selected format and return an exit status.

Raw HTML is not executed or rendered. The checker does not request external URLs, execute code fences, or invoke a documentation site's build system.

Closed YAML front matter is replaced with blank lines before Markdown parsing, preserving source positions while excluding metadata. An initial `---` block must have a closing `---` or `...`; otherwise it remains ordinary Markdown.

## Repository boundary

The selected root provides a common base for links beginning with `/` and a boundary for local file reads. Relative destinations resolve from their source document. A path that leaves the root is an issue even if a matching file exists elsewhere on the machine. A symlink must not be used to read a destination outside the root.

Directory discovery does not recurse through symbolic links or Windows junctions, preventing directory cycles. Links explicitly targeting them still undergo repository-boundary checks.

Filename case is part of link correctness. A case-insensitive filesystem can hide mistakes that later break on Linux; the checker compares the spelling of path components with actual directory entries.

This boundary is a documentation validation rule, not an operating-system sandbox. Run the checker with ordinary least-privilege permissions when processing repositories you do not trust.

## Heading fragments

Heading fragments are derived from parsed Markdown headings. ASCII uppercase letters become lowercase, spaces become hyphens, and most punctuation is removed; Unicode letters, marks, numbers, and connector punctuation are retained. Repeated generated anchors receive numeric suffixes such as `installation-1`. Static `<a id="...">` and `<a name="...">` anchors are also collected.

The implementation follows a GitHub-style convention but does not embed GitHub's renderer. If a document depends on unusual punctuation, emoji expansion, custom identifiers, or renderer extensions, use a small reproduction to establish the behavior before relying on it.

Only Markdown targets are interpreted as heading-bearing documents. A fragment attached to another file type is outside the heading validation scope. Directory links are checked for existence only; their fragments are not resolved against a README or an index file.

## Location precision

Locations combine Markdown parser block mappings with tracked inline link positions. They usually identify the one-based line containing a link's opening bracket, including links in multiline paragraphs. Reference links are reported at their use rather than at the definition. Unusual nested block containers can still have approximate line numbers; columns are not reported.

## Known limitations

- External HTTP/HTTPS destinations are skipped. Availability, redirects, authentication, and rate limits are not evaluated.
- Raw HTML `href` and `src` attributes are not parsed as links. Only static `<a>` elements with `id` or `name` contribute explicit anchors; IDs on arbitrary HTML elements are not collected.
- MDX expressions, template variables, generated routes, extensionless routes, and framework-specific URL rewrites are not resolved.
- Markdown parsing is not a promise of full GitHub Flavored Markdown compatibility. Renderer-specific heading IDs can differ.
- Fragments inside PDFs, HTML files, SVGs, and other non-Markdown files are not validated.
- A readable, existing image or other file passes the path check; its content and rendering are not inspected.
- Unusual nested block containers can produce approximate diagnostic line numbers; exact columns are not available.
- Files are checked as they exist during the run. Simultaneous filesystem changes can affect results.

These limitations should remain visible in bug triage and release notes. Avoid broad ignore patterns that make unsupported content appear fully validated.

## Output contract

The CLI exposes text, JSON, and GitHub Actions formats. Exit code `1` indicates link issues and `2` indicates configuration, input, or read errors. The initial `0.1.0` release is an early interface; compatibility-affecting changes should be documented in the changelog and tested before a release.

Findings can include an advisory `suggestion`, selected from close existing sibling filenames or heading anchors. Case mismatches suggest the spelling found on disk. Suggested URLs preserve the query and fragment where applicable; they are not automatically applied or a promise that every part of the resulting link is valid.
