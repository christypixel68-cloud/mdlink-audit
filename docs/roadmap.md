# Roadmap

[Project overview](../README.md) · [Design](design.md)

The following items are proposed work, not completed features or delivery promises. Priorities should follow reproducible problems from real repositories.

1. **Expand heading compatibility fixtures.** Compare repeated headings, punctuation, emoji, inline code, and Unicode against documented renderer behavior. Record remaining differences instead of claiming blanket compatibility.
2. **Improve diagnostic locations.** Expand nested-list and blockquote fixtures, then investigate column locations without introducing brittle source matching.
3. **Add opt-in HTML link support.** Define safe static extraction for `href`, `src`, and IDs on other HTML elements, with tests for malformed HTML and escaped content. Keep the current static `<a>` anchor support and its limits clear.
4. **Evaluate documentation framework conventions.** Gather actual cases for extensionless routes and directory indexes. Specify explicit opt-in rules before adding framework behavior.
5. **Measure larger-repository performance.** Build a reproducible benchmark with many sources and shared targets, then optimize measured filesystem and parsing costs while preserving boundary and casing checks.
6. **Complete public release distribution.** The local build and wheel smoke-test procedure is in [release preparation](releasing.md). Run the configured platform jobs on GitHub, verify repository and package-index ownership, and review versioning before publishing a package-index release.

To propose a change, describe the failing documentation pattern, expected behavior, and how the result can be tested. Small fixtures are more useful than feature counts.
