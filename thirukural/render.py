"""Render verses into the slide markup the published deck already uses."""

import re
from html import escape
from unicodedata import normalize

from thirukural.model import Verse, closes_chapter, opens_chapter

# The historical templates use these words as placeholders. "kural" is a
# prefix of the other names, so each name is swapped for a sentinel that
# does not itself contain "kural", and commentary text is never scanned.
_TOKENS = (
    ("kural_explaination", "\x00E\x00"),
    ("kural_title", "\x00T\x00"),
    ("kural_id", "\x00I\x00"),
    ("kural", "\x00V\x00"),
)
_TOKEN_FOR = dict(_TOKENS)
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)

_ID_BLOCK = """
    <div class="sl-block k_id" data-block-type="text">
        kural_id
    </div>
"""

_TITLE_BLOCK = """
    <div class="sl-block k_t" data-block-type="text">
        kural_title
    </div>
"""

_EXPLANATION_BLOCK = """
    <div class="sl-block k_e" data-block-type="text">
        <span style="position: absolute; left: -25px; top: 5px;">-</span><span style="font-size:0.7em">kural_explaination</span>
    </div>
"""

_SECTION = """
    <section data-background-color="#222222" data-transition="convex">
        <div class="sl-block" data-block-type="text" style="height: auto; width: 666px; left: 134px; top: 240px;z-index: 10; color: rgb(255, 255, 255);">
            kural            
        </div>
        kural_id
        kural_title
        kural_explaination
    </section>
"""


def _protect(template: str) -> str:
    protected = template
    for name, token in _TOKENS:
        protected = protected.replace(name, token)
    return protected


def _fill(template: str, **values: str) -> str:
    protected = _protect(template)
    for name, value in values.items():
        token = _TOKEN_FOR[name]
        if token not in protected:
            raise KeyError(name)
        protected = protected.replace(token, value)
    leftover = [name for name, token in _TOKENS if token in protected]
    if leftover:
        raise KeyError(leftover)
    return protected


def _plain(value: str, *, compose: bool) -> str:
    if compose:
        value = normalize("NFC", value)
    return escape(value, quote=False)


def format_couplet(kural: str) -> str:
    """Turn a stored couplet into two paragraphs.

    The second line is shown with a single trailing period. A break may be
    written as ``<br>``, ``<br/>``, or ``<br />``.
    """
    parts = _BREAK.split(kural)
    if len(parts) < 2:
        raise ValueError("couplet is missing a line break")
    parts[1] = parts[1].strip().rstrip(".") + "."
    return "".join(f"<p>{_plain(part, compose=True)}</p>" for part in parts)


def _verse_slide(verse: Verse) -> str:
    try:
        couplet = format_couplet(verse.kural)
    except ValueError as exc:
        raise ValueError(f"kural {verse.number}: {exc}") from exc
    return _fill(
        _SECTION,
        kural=couplet,
        kural_id=_fill(_ID_BLOCK, kural_id=str(verse.number)),
        kural_title=_fill(_TITLE_BLOCK, kural_title=_plain(verse.title, compose=False)),
        kural_explaination=_fill(
            _EXPLANATION_BLOCK,
            kural_explaination=_plain(verse.explanation, compose=False),
        ),
    )


def _chapter_slide(title: str) -> str:
    slide = _fill(
        _SECTION,
        kural=f"<p>{_plain(title, compose=True)}</p>",
        kural_id="",
        kural_title="",
        kural_explaination="",
    )
    return "<section>" + slide.replace(
        'data-transition="convex"',
        'data-autoslide="4000"',
    )


def render_slides(verses: list[Verse]) -> str:
    """Build one vertical stack per group of ten verses.

    The divider slide uses the title stored on the first verse of that
    group. A few later rows in the corpus carry a neighboring chapter's
    title; the divider stays with the opening verse, which is how the
    published deck is grouped.
    """
    chunks: list[str] = []
    for verse in verses:
        chunk = _chapter_slide(verse.title) if opens_chapter(verse.number) else ""
        chunk += _verse_slide(verse)
        if closes_chapter(verse.number):
            chunk += "</section>"
        chunks.append(chunk)
    return "\n".join(chunks)
