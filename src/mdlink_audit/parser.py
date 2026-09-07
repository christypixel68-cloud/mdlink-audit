"""Extract local-link candidates and common GitHub-style heading anchors.

Markdown syntax is parsed by markdown-it-py rather than regular expressions.
This is a documented subset of GitHub's rendering, not a full GFM renderer:
raw HTML href/src are opt-in; generated site routes and GitHub emoji expansion
are not interpreted. Link positions identify the opening bracket or HTML tag,
including multiline paragraphs; unusual nested block containers may have
approximate line numbers.
"""

from __future__ import annotations

import string
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from markdown_it.rules_inline.autolink import autolink
from markdown_it.rules_inline.html_inline import html_inline
from markdown_it.rules_inline.image import image
from markdown_it.rules_inline.link import link
from markdown_it.rules_inline.state_inline import StateInline
from markdown_it.token import Token


@dataclass(frozen=True)
class Link:
    """One Markdown/HTML link or resource, with a one-based source line."""

    target: str
    line: int
    is_image: bool = False


@dataclass(frozen=True)
class ParsedDocument:
    links: tuple[Link, ...]
    anchors: frozenset[str]


InlineRule = Callable[[StateInline, bool], bool]
_LINE_OFFSET = "mdlink_audit_line_offset"
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def _with_line_offset(rule: InlineRule, token_type: str) -> InlineRule:
    """Annotate the token created by a rule without changing Markdown parsing."""

    def tracked(state: StateInline, silent: bool) -> bool:
        start = state.pos
        token_count = len(state.tokens)
        matched = rule(state, silent)
        if matched and not silent:
            # A link rule recursively tokenizes its label; the first matching
            # token is the outer link. Inner images retain their own offsets.
            for token in state.tokens[token_count:]:
                if token.type == token_type:
                    token.meta[_LINE_OFFSET] = state.src.count("\n", 0, start)
                    break
        return matched

    return tracked


def _markdown_parser() -> MarkdownIt:
    parser = MarkdownIt("commonmark", {"html": True})
    parser.enable(["table", "strikethrough"])
    parser.inline.ruler.at("link", _with_line_offset(link, "link_open"))
    parser.inline.ruler.at("image", _with_line_offset(image, "image"))
    parser.inline.ruler.at("autolink", _with_line_offset(autolink, "link_open"))
    parser.inline.ruler.at("html_inline", _with_line_offset(html_inline, "html_inline"))
    return parser


class _AnchorHTMLParser(HTMLParser):
    """Read static HTML tokens while preserving their document source lines.

    Only tokens that Markdown recognizes as HTML are fed here. Padding omitted
    source lines keeps HTMLParser's positions useful across separate fragments.
    Its raw-text handling also prevents tags inside script/style being read.
    """

    def __init__(self, links: list[Link], *, include_html: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: set[str] = set()
        self.links = links
        self.include_html = include_html
        self.raw_tag: str | None = None
        self._fed_line = 1

    def feed_at(self, content: str, line: int) -> None:
        padding = "\n" * max(0, line - self._fed_line)
        self.feed(padding + content)
        self._fed_line += len(padding) + content.count("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is None:
                continue
            if value and (
                (tag == "a" and key in {"name", "id"}) or (self.include_html and key == "id")
            ):
                self.anchors.add(value)
            if self.include_html and key in {"href", "src"}:
                self.links.append(
                    Link(value, self.getpos()[0], is_image=tag == "img" and key == "src")
                )
        if tag in {"script", "style"}:
            self.raw_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self.raw_tag:
            self.raw_tag = None

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def _heading_text(tokens: Sequence[Token]) -> str:
    """Approximate HTML textContent, preserving code and formatted link text."""
    pieces: list[str] = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            pieces.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            pieces.append("\n")
        # Image alt text is an attribute, not textContent of the heading.
        # Raw HTML tags and comments contribute no text of their own.
    return "".join(pieces)


def _heading_slug(text: str) -> str:
    # HTML Pipeline uses ASCII downcasing and Unicode Word characters. GitHub's
    # own heading example preserves Greek capital Theta. This deliberately
    # avoids Python's Unicode-wide lower() and ASCII-only slug libraries.
    # https://github.com/gjtorikian/html-pipeline/blob/v2.14.3/lib/html/pipeline/toc_filter.rb
    # markdown-it already removes the heading's syntactic outer whitespace.
    # Preserve spaces remaining beside an image/HTML tag, as textContent does.
    lowered = text.translate(_ASCII_LOWER)
    return "".join(
        "-" if char == " " else char
        for char in lowered
        if char in {" ", "-"}
        or unicodedata.category(char)[0] in {"L", "M", "N"}
        or unicodedata.category(char) == "Pc"
    )


def parse_markdown(text: str, *, include_html: bool = False) -> ParsedDocument:
    """Parse supported links and anchors without reading files or the network.

    Targets use markdown-it-py's normalized URLs: Unicode and spaces can be
    percent-encoded. The filesystem checker should split the URL first, then
    percent-decode its path and fragment once. Reference destinations are
    emitted at each use, not at their definition.

    With include_html, static href/src attributes and all element IDs are read
    from Markdown's HTML tokens. HTML attribute entities are decoded once; URL
    percent escapes remain intact. HTML positions identify the opening tag.
    This is not a browser DOM parser: generated attributes, srcset, CSS URLs,
    and malformed-markup recovery beyond HTMLParser are unsupported.
    """
    # A closed YAML front matter block is metadata, not rendered Markdown.
    # Replace it with blank lines to keep diagnostic positions unchanged.
    text = text.removeprefix("\ufeff")
    lines = text.splitlines(keepends=True)
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], 1):
            if line.strip() in {"---", "..."}:
                text = "\n" * (index + 1) + "".join(lines[index + 1 :])
                break
    tokens = _markdown_parser().parse(text)
    links: list[Link] = []
    generated_anchors: set[str] = set()
    next_suffix: dict[str, int] = {}
    custom = _AnchorHTMLParser(links, include_html=include_html)
    in_heading = False

    for token in tokens:
        if token.type == "heading_open":
            in_heading = True
        elif token.type == "heading_close":
            in_heading = False
        elif token.type == "html_block":
            custom.feed_at(token.content, token.map[0] + 1 if token.map else 1)
        elif token.type == "inline":
            children = token.children or []
            base_line = token.map[0] + 1 if token.map else 1
            if in_heading and not (include_html and custom.raw_tag is not None):
                # An inline script/style can remain open across Markdown
                # blocks. Any apparent heading in its body is raw HTML text.
                base = _heading_slug(_heading_text(children))
                slug = base
                suffix = next_suffix.get(base, 0)
                while slug in generated_anchors:
                    suffix += 1
                    slug = f"{base}-{suffix}"
                next_suffix[base] = suffix
                generated_anchors.add(slug)
            for child in children:
                if child.type == "html_inline":
                    custom.feed_at(child.content, base_line + child.meta.get(_LINE_OFFSET, 0))
                    continue
                if include_html and custom.raw_tag is not None:
                    # Markdown can tokenize script/style bodies within an
                    # inline paragraph; these links are raw text in HTML.
                    continue
                if child.type in {"link_open", "image"}:
                    is_image = child.type == "image"
                    target = child.attrGet("src" if is_image else "href")
                    if target is not None:
                        links.append(
                            Link(
                                target=target,
                                line=base_line + child.meta.get(_LINE_OFFSET, 0),
                                is_image=is_image,
                            )
                        )

    custom.close()
    return ParsedDocument(tuple(links), frozenset(generated_anchors | custom.anchors))
