"""Behavioral examples for source positions and supported Markdown syntax."""

from urllib.parse import unquote

import pytest

from mdlink_audit.parser import Link, parse_markdown


def test_inline_images_and_reference_variants_report_use_lines():
    document = parse_markdown(
        "[inline](guide.md)\n"
        "![picture](images/chart.svg)\n"
        "[named][guide]\n"
        "[guide][]\n"
        "[guide]\n"
        "![photo][image]\n\n"
        '[guide]: docs/guide.md "Guide"\n'
        "[image]: images/photo.png\n"
    )
    assert document.links == (
        Link("guide.md", 1),
        Link("images/chart.svg", 2, True),
        Link("docs/guide.md", 3),
        Link("docs/guide.md", 4),
        Link("docs/guide.md", 5),
        Link("images/photo.png", 6, True),
    )


def test_unused_reference_definitions_are_not_links():
    assert parse_markdown("[unused]: missing.md\n").links == ()


def test_multiline_paragraph_link_labels_and_destinations_keep_opening_line():
    document = parse_markdown(
        "Introduction\n"
        "still introduction\n"
        "[a label\n"
        "continued](\n"
        "  docs/guide.md\n"
        ") and [second](other.md)\n"
    )
    assert document.links == (Link("docs/guide.md", 3), Link("other.md", 6))


def test_link_wrapped_image_has_independent_line_numbers():
    document = parse_markdown("[\n![preview](preview.png)\n](full.png)\n")
    assert document.links == (Link("full.png", 1), Link("preview.png", 2, True))


def test_pseudo_links_and_headings_in_code_or_comments_are_ignored():
    document = parse_markdown(
        "```md\n# fake\n[bad](fenced.md)\n```\n\n"
        "    [bad](indented.md)\n\n"
        "`[bad](inline.md)`\n\n"
        "<!--\n# hidden\n[bad](comment.md)\n<a name='hidden'>\n-->\n\n"
        "text <!-- [bad](inline-comment.md) --> [good](ok.md)\n"
    )
    assert [item.target for item in document.links] == ["ok.md"]
    assert document.anchors == frozenset()


def test_backtick_lengths_and_tilde_fences_are_parsed():
    document = parse_markdown(
        "`` a ` [bad](code.md) `` [good](good.md)\n\n"
        "~~~~\n[bad](fenced.md)\n~~~\n[bad](still-fenced.md)\n~~~~\n"
    )
    assert document.links == (Link("good.md", 1),)


def test_heading_formatting_unicode_and_setext():
    document = parse_markdown(
        "# 中文 *使用* 与 `API` [指南](guide.md)！\n\n"
        "A **Setext** Heading\n--------------------\n\n"
        "## A  B Θ É e\u0301 under_score\n"
    )
    assert document.anchors == frozenset(
        {"中文-使用-与-api-指南", "a-setext-heading", "a--b-Θ-É-e\u0301-under_score"}
    )


def test_heading_duplicate_suffixes_avoid_global_collisions():
    document = parse_markdown("# Foo\n# Foo-1\n# Foo\n# Foo\n# Foo-1\n")
    assert document.anchors == frozenset({"foo", "foo-1", "foo-2", "foo-3", "foo-1-1"})


def test_custom_anchors_do_not_participate_in_heading_numbering():
    document = parse_markdown(
        '<a name="hello"></a>\n\n'
        "# Hello\n# Hello\n\n"
        '<a id="Custom&amp;Name"></a>\n\n'
        'A paragraph <a\n name="多行锚点"></a>.\n'
    )
    assert document.anchors == frozenset({"hello", "hello-1", "Custom&Name", "多行锚点"})


def test_raw_html_links_images_and_non_anchor_ids_are_not_supported():
    document = parse_markdown(
        '<a href="missing.md">raw</a>\n\n'
        '<img src="missing.png">\n\n'
        '<div id="not-an-anchor"></div>\n'
    )
    assert document.links == ()
    assert document.anchors == frozenset()


def test_unicode_spaces_and_literal_hash_are_url_encoded_without_losing_meaning():
    document = parse_markdown(
        "[中文](<文档/安装 指南.md#开始使用>)\n"
        "[hash](docs/file%23name.md)\n"
        "[encoded](docs/already%20encoded.md)\n"
    )
    assert unquote(document.links[0].target) == "文档/安装 指南.md#开始使用"
    assert document.links[1].target == "docs/file%23name.md"
    assert document.links[2].target == "docs/already%20encoded.md"


def test_nested_parentheses_and_escaped_brackets_in_link_text():
    document = parse_markdown(r"[a \[label\]](docs/a(b).md) [b](docs/a\(b\).md)")
    assert [item.target for item in document.links] == ["docs/a(b).md", "docs/a(b).md"]


def test_crlf_and_blockquote_positions():
    document = parse_markdown("# Hello\r\n\r\n> quote\r\n> [guide](guide.md)\r\n")
    assert document.links == (Link("guide.md", 4),)


def test_markdown_table_links_and_strikethrough_heading_text():
    document = parse_markdown(
        "# ~~Old~~ Guide\n\n| File | Status |\n| --- | --- |\n| [guide](guide.md) | ready |\n"
    )
    assert document.links == (Link("guide.md", 5),)
    assert "old-guide" in document.anchors


@pytest.mark.parametrize("text", ["", "plain prose", "[undefined reference]", "\\[x](no.md)"])
def test_non_links_do_not_generate_findings(text):
    assert parse_markdown(text).links == ()


def test_heading_entities_inline_html_and_image_alt_text():
    document = parse_markdown("# Fish &amp; <em>Chips</em> `x_y` ![badge](badge.svg)\n")
    assert document.anchors == frozenset({"fish--chips-x_y-"})


def test_frozen_results_are_safe_to_cache():
    document = parse_markdown("[x](x.md)")
    assert isinstance(hash(document), int)


@pytest.mark.parametrize("terminator", ["---", "..."])
def test_closed_front_matter_ignored_without_changing_source_lines(terminator):
    document = parse_markdown(
        '\ufeff---\r\ntitle: "[metadata](absent.md)"\r\n'
        f"{terminator}\r\n# Real\r\n\r\n[body](guide.md)\r\n"
    )
    assert document.links == (Link("guide.md", 6),)
    assert document.anchors == frozenset({"real"})


def test_unclosed_front_matter_does_not_hide_body():
    document = parse_markdown("---\n# Real\n[body](missing.md)\n")
    assert document.links == (Link("missing.md", 3),)


def test_later_thematic_rule_does_not_hide_links():
    document = parse_markdown("# Heading\n\n---\n\n[body](guide.md)\n\n---\n")
    assert document.links == (Link("guide.md", 5),)
