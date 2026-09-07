# Roadmap

[Project overview](../README.md) · [Design](design.md)

Version 0.2.0 adds opt-in static HTML checking, a composite Action, and a reproducible [public-repository evaluation](validation.md). The following items remain proposed work. Priorities should follow reproducible problems and feedback from users.

1. **Expand heading compatibility fixtures.** Compare repeated headings, punctuation, emoji, inline code, and Unicode against documented renderer behavior. Record remaining differences instead of claiming blanket compatibility.
2. **Improve diagnostic locations.** Expand nested-list and blockquote fixtures, then investigate column locations without introducing brittle source matching.
3. **Validate real adoption.** Help interested maintainers reproduce an audit and document confirmed fixes or integrations with their permission. Author-run corpus tests are not adoption or endorsements.
4. **Evaluate documentation framework conventions.** The MkDocs and uv snapshots exposed generated files, attribute-list IDs, and site-root paths. Define explicit opt-in handling for these cases before adding framework behavior; keep build-context limitations visible.
5. **Measure larger-repository performance.** Build a reproducible benchmark with many sources and shared targets, then optimize measured filesystem and parsing costs while preserving boundary and casing checks.
6. **Evaluate package-index distribution.** GitHub releases provide source and wheel artifacts. A PyPI release requires checking name availability and ownership, setting up trusted publishing, and verifying a release candidate through [release preparation](releasing.md).

To propose a change, describe the failing documentation pattern, expected behavior, and how the result can be tested. Small fixtures are more useful than feature counts.
