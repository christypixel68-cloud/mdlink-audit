"""Opt-in static HTML extraction follows Markdown boundaries and source lines."""

import pytest

from mdlink_audit.parser import Link, parse_markdown


def test_html_is_opt_in_and_existing_explicit_anchors_still_work():
    source = (
        '<div id="container"><a name="legacy" id="anchor" href="guide.md">'
        '<img src="picture.png"></a></div>\n'
    )
    assert parse_markdown(source).links == ()
    assert parse_markdown(source).anchors == frozenset({"legacy", "anchor"})
    document = parse_markdown(source, include_html=True)
    assert document.links == (Link("guide.md", 1), Link("picture.png", 1, True))
    assert document.anchors == frozenset({"container", "legacy", "anchor"})


def test_html_option_is_keyword_only():
    with pytest.raises(TypeError):
        parse_markdown("", True)


def test_block_links_use_opening_tag_line_across_multiline_attributes():
    document = parse_markdown(
        "# Title\n\n<div>\n"
        "  <a\n    href='docs/guide.md'\n  >Guide</a>\n"
        '  <img\n    src="images/chart.svg"\n  />\n'
        "</div>\n\n[Markdown](other.md)\n",
        include_html=True,
    )
    assert document.links == (
        Link("docs/guide.md", 4),
        Link("images/chart.svg", 7, True),
        Link("other.md", 12),
    )


def test_inline_links_keep_document_order_and_lines_across_fragments():
    document = parse_markdown(
        'Intro <a href="first.md">first</a> [second](second.md)\n'
        "more prose\n"
        '<img\n src="third.svg"> and <a href=fourth.md>fourth</a>\n'
        "\n\n[ending](last.md)\n",
        include_html=True,
    )
    assert document.links == (
        Link("first.md", 1),
        Link("second.md", 1),
        Link("third.svg", 3, True),
        Link("fourth.md", 4),
        Link("last.md", 7),
    )


@pytest.mark.parametrize("attribute", ['href="guide.md"', "href='guide.md'", "HREF=guide.md"])
def test_quoted_and_unquoted_attributes_and_case_insensitive_names(attribute):
    document = parse_markdown(f"<A {attribute}>Guide</A>", include_html=True)
    assert document.links == (Link("guide.md", 1),)


def test_html_entities_decode_once_without_decoding_percent_escapes():
    document = parse_markdown(
        '<a href="文档/安装&#32;指南.md?x=1&amp;y=2#开始">Guide</a>\n'
        '<a href="file%2520name.md#literal&amp;amp;anchor">Once</a>\n'
        '<span id="A&amp;B&#x4e2d;"></span>\n',
        include_html=True,
    )
    assert document.links == (
        Link("文档/安装 指南.md?x=1&y=2#开始", 1),
        Link("file%2520name.md#literal&amp;anchor", 2),
    )
    assert document.anchors == frozenset({"A&B中"})


def test_angle_brackets_inside_quoted_attribute_are_not_nested_markup():
    document = parse_markdown(
        '<div title="<img src=hidden.png>" id="visible">\n'
        "<a href='guide.md?value=a>b'>Guide</a>\n</div>\n",
        include_html=True,
    )
    assert document.links == (Link("guide.md?value=a>b", 2),)
    assert document.anchors == frozenset({"visible"})


def test_all_ids_but_only_anchor_names_are_collected():
    document = parse_markdown(
        '<section id="Section"><h2 id="Heading">Title</h2>\n'
        '<input name="not-an-anchor"><a name="Legacy"></a>\n'
        '<div id=""></div><span id></span></section>\n',
        include_html=True,
    )
    assert document.anchors == frozenset({"Section", "Heading", "Legacy"})


def test_href_and_src_resources_from_multiple_tags():
    document = parse_markdown(
        '<div><link href="theme.css"><video src="movie.mp4">\n'
        '<source src="audio.ogg"></video><iframe src="page.html"></iframe>\n'
        '<script src="app.js"></script><img src="cover.svg" /></div>\n',
        include_html=True,
    )
    assert document.links == (
        Link("theme.css", 1),
        Link("movie.mp4", 1),
        Link("audio.ogg", 2),
        Link("page.html", 2),
        Link("app.js", 3),
        Link("cover.svg", 3, True),
    )


def test_empty_url_is_reported_but_missing_attribute_value_is_ignored():
    document = parse_markdown('<a href="">Self</a><a href>None</a>', include_html=True)
    assert document.links == (Link("", 1),)


def test_code_comments_and_front_matter_do_not_produce_html_links_or_ids():
    document = parse_markdown(
        '---\ntitle: \'<a href="metadata.md" id="metadata">\'\n---\n'
        '```html\n<a href="fenced.md" id="fenced">\n```\n\n'
        '    <img src="indented.svg" id="indented">\n\n'
        '`<a href="inline.md" id="inline">`\n\n'
        '<!--\n<a href="comment.md" id="comment">\n-->\n\n'
        'Text <!-- <img src="inline-comment.svg" id="inline-comment"> --> '
        '<a href="real.md" id="real">Real</a>\n',
        include_html=True,
    )
    assert document.links == (Link("real.md", 16),)
    assert document.anchors == frozenset({"real"})


@pytest.mark.parametrize("tag", ["script", "style"])
def test_raw_text_block_bodies_are_ignored(tag):
    document = parse_markdown(
        f'<{tag} id="resource">\n'
        '<a href="fake.md" id="fake">\n'
        "[fake](also-fake.md)\n"
        f"</{tag}>\n\n"
        '<a href="real.md">Real</a>\n',
        include_html=True,
    )
    assert document.links == (Link("real.md", 6),)
    assert document.anchors == frozenset({"resource"})


@pytest.mark.parametrize("tag", ["script", "style"])
def test_raw_text_inline_bodies_do_not_leak_markdown_or_html_links(tag):
    document = parse_markdown(
        f'Prefix <{tag}>[fake](markdown.md) <a href="fake.md" id="fake">\n'
        f'continued</{tag}> <a href="real.md" id="real">Real</a>\n'
        "[after](after.md)\n",
        include_html=True,
    )
    assert document.links == (Link("real.md", 2), Link("after.md", 3))
    assert document.anchors == frozenset({"real"})


def test_unclosed_inline_script_keeps_later_html_and_markdown_as_raw_text():
    document = parse_markdown(
        "Prefix <script>[fake](markdown.md)\n\n"
        '<a href="fake.md" id="fake">\n\n'
        "[also fake](later.md)\n",
        include_html=True,
    )
    assert document.links == ()
    assert document.anchors == frozenset()


def test_html_is_not_inferred_from_escaped_markup_or_image_alt_text():
    document = parse_markdown(
        '&lt;a href="escaped.md"&gt;\n![<img src="alt.svg">](real.svg)\n',
        include_html=True,
    )
    assert document.links == (Link("real.svg", 2, True),)


def test_crlf_blockquotes_and_html_source_positions():
    document = parse_markdown(
        '# Title\r\n\r\n> Intro\r\n> <a\r\n> href="guide.md">Guide</a>\r\n'
        '\r\n<div>\r\n<img src="chart.svg">\r\n</div>\r\n',
        include_html=True,
    )
    assert document.links == (Link("guide.md", 4), Link("chart.svg", 8, True))


def test_unmatched_end_tags_do_not_prevent_later_links():
    document = parse_markdown(
        '<div></p><a href=guide.md>Guide</span>\n<img src="chart.svg">\n',
        include_html=True,
    )
    assert document.links == (Link("guide.md", 1), Link("chart.svg", 2, True))


def test_unterminated_html_attribute_is_not_a_complete_link():
    document = parse_markdown('<div>\n<a href="unterminated.md\n', include_html=True)
    assert document.links == ()


def test_css_srcset_and_dynamic_attributes_are_not_interpreted():
    document = parse_markdown(
        '<div style="background:url(css.png)" :href="dynamic.md">\n'
        '<img srcset="one.svg 1x, two.svg 2x" data-src="lazy.svg">\n</div>\n',
        include_html=True,
    )
    assert document.links == ()


@pytest.mark.parametrize("tag", ["script", "style"])
def test_raw_text_across_markdown_blocks_does_not_create_heading_anchors(tag):
    source = (
        f"Prefix <{tag}>\n\n# Fake [bad](absent.md)\n\n</{tag}>\n\n# Real\n\n[after](real.md)\n"
    )
    document = parse_markdown(source, include_html=True)
    assert document.links == (Link("real.md", 9),)
    assert document.anchors == frozenset({"real"})
    # The option preserves existing Markdown-only behavior when disabled.
    default = parse_markdown(source)
    assert default.links == (Link("absent.md", 3), Link("real.md", 9))
    assert default.anchors == frozenset({"fake-bad", "real"})


@pytest.mark.parametrize("tag", ["script", "style"])
def test_raw_text_ignores_other_tag_names_and_code_formatted_end_tags(tag):
    other_tag = "style" if tag == "script" else "script"
    document = parse_markdown(
        f"Prefix <{tag}>\n"
        f'<{other_tag}><a href="fake.md" id="fake"></{other_tag}>\n'
        f'`</{tag}>` <a href="still-fake.md" id="still-fake">\n'
        f'</{tag}> <a href="real.md" id="real">Real</a>\n',
        include_html=True,
    )
    assert document.links == (Link("real.md", 4),)
    assert document.anchors == frozenset({"real"})


def test_mixed_html_blocks_inline_tags_and_containers_keep_source_lines():
    document = parse_markdown(
        '<div>\n<a href="block.md">block</a>\n</div>\n\n'
        'Plain text\nwith a <span id="inline">span</span>\n\n'
        '> Quoted <a\n> href="quote.md">quote</a>\n\n'
        '* <img\n  src="list.svg"> and [markdown](list.md)\n\n'
        '<section>\n  <a href="last.md">last</a>\n</section>\n',
        include_html=True,
    )
    assert document.links == (
        Link("block.md", 2),
        Link("quote.md", 8),
        Link("list.svg", 11, True),
        Link("list.md", 12),
        Link("last.md", 15),
    )
    assert document.anchors == frozenset({"inline"})


def test_entity_newlines_do_not_shift_later_source_positions():
    document = parse_markdown(
        'Intro <a href="first.md" title="&#10;&#13;">first</a>\n'
        '<span id="A&amp;amp;B"></span> <a href="second.md">second</a>\n\n'
        '<a\n href="third.md">third</a>\n',
        include_html=True,
    )
    assert document.links == (
        Link("first.md", 1),
        Link("second.md", 2),
        Link("third.md", 4),
    )
    assert document.anchors == frozenset({"A&amp;B"})


def test_default_legacy_anchors_work_across_multiline_fragments():
    source = (
        'Intro <a\n name="Legacy&amp;Anchor">legacy</a>\n\n'
        '<div>\n<a\n id="Other&amp;amp;Anchor"></a>\n</div>\n'
    )
    document = parse_markdown(source)
    assert document.links == ()
    assert document.anchors == frozenset({"Legacy&Anchor", "Other&amp;Anchor"})
