"""Find verses from a word in the couplet, commentary, or chapter name."""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from unicodedata import normalize

from thirukural.english_glossary import ENGLISH, LatinPlan, english_groups, latin_plan
from thirukural.model import TOTAL_VERSES, VERSES_PER_CHAPTER, Verse
from thirukural.paths import DB_PATH
from thirukural.phonetic import aksharas, match_kind, phonemes
from thirukural.repository import load_verses

# Longer endings first. A derived stem is kept only when at least three
# letters remain, so a short word such as அறம் is not reduced to அற.
SUFFIXES = (
    "த்திலிருந்து",
    "த்தினால்",
    "த்திற்கு",
    "த்திலே",
    "த்தில்",
    "த்தை",
    "த்து",
    "களிலிருந்து",
    "களால்",
    "களில்",
    "களை",
    "களுக்கு",
    "களிடம்",
    "கள்",
    "ிலிருந்து",
    "ினால்",
    "ிடம்",
    "ோடு",
    "ுடன்",
    "ால்",
    "ில்",
    "க்கு",
    "யின்",
    "ின்",
    "ை",
    "ம்",
    "ு",
)

_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SPACE = re.compile(r"\s+")
_FIELD_WEIGHT = {"குறள்": 100, "விளக்கம்": 10, "அதிகாரம்": 1}
# A whole word outranks a word that merely begins with the query, and that
# outranks a string buried inside a longer word. The couplet stays above
# the commentary, which stays above the chapter title. A buried hit stays
# below every whole-word hit, including one that is only in the title.
_RANK = {
    ("குறள்", "whole"): 640,
    ("குறள்", "boundary"): 560,
    ("குறள்", "stem"): 480,
    ("விளக்கம்", "whole"): 320,
    ("விளக்கம்", "boundary"): 240,
    ("விளக்கம்", "stem"): 160,
    ("அதிகாரம்", "whole"): 80,
    ("அதிகாரம்", "boundary"): 60,
    ("அதிகாரம்", "stem"): 40,
    ("குறள்", "buried"): 30,
    ("விளக்கம்", "buried"): 20,
    ("அதிகாரம்", "buried"): 10,
}
_THEME = 10000
_CLIENT = Path(__file__).with_name("search_client.js")


@dataclass(frozen=True)
class SearchHit:
    number: int
    title: str
    couplet: str
    explanation: str
    matched: str
    term: str
    score: int

    @property
    def slide(self) -> tuple[int, int]:
        return slide_position(self.number)


def slide_position(number: int) -> tuple[int, int]:
    """Reveal indices for a verse. The title slide occupies horizontal 0."""
    chapter = (number - 1) // VERSES_PER_CHAPTER
    row = (number - 1) % VERSES_PER_CHAPTER
    return chapter + 1, row + 1


def normalize_text(value: str) -> str:
    text = _BREAK.sub(" ", value or "")
    text = normalize("NFC", text).replace("\u200c", "").replace("\u200d", "")
    return _SPACE.sub(" ", text).strip().casefold()


def couplet_text(kural: str) -> str:
    parts = _BREAK.split(kural, maxsplit=1)
    lines = [parts[0].strip()]
    if len(parts) > 1:
        lines.append(parts[1].strip().rstrip(".") + ".")
    return "\n".join(line for line in lines if line)


def _with_open_consonant(form: str) -> str | None:
    """Drop a final pulli so கடவுள் also matches கடவுளில்."""
    if form.endswith("\u0bcd") and len(form) - 1 >= 3:
        return form[:-1]
    return None


def token_forms(token: str) -> list[str]:
    forms: list[str] = []

    def add(form: str | None) -> None:
        if form and form not in forms:
            forms.append(form)

    add(token)
    add(_with_open_consonant(token))
    for suffix in SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            stem = token[: -len(suffix)]
            add(stem)
            add(_with_open_consonant(stem))
            glide = "ய்" if stem.endswith("ய்") else "ய" if stem.endswith("ய") else ""
            if glide and len(stem) - len(glide) >= 3:
                bare = stem[: -len(glide)]
                add(bare)
                add(_with_open_consonant(bare))
            break
    return forms


def _fields(verse: Verse) -> dict[str, str]:
    return {
        "குறள்": normalize_text(couplet_text(verse.kural)),
        "விளக்கம்": normalize_text(verse.explanation),
        "அதிகாரம்": normalize_text(verse.title),
    }


@dataclass(frozen=True)
class _Scored:
    score: int
    where: str
    term: str


_TRAILING = ".,;:!?\"'“”‘’()[]{}…。·"


def _words(text: str) -> list[str]:
    words: list[str] = []
    for word in text.split(" "):
        cleaned = word.strip(_TRAILING)
        if len(cleaned) >= 2:
            words.append(cleaned)
    return words


def _kind(form: str, word: str, *, exact: bool) -> str | None:
    """How ``form`` meets one corpus word. ``None`` is a miss."""
    if len(form) < 2 or len(word) < 2:
        return None
    if word == form:
        return "whole" if exact else "stem"
    letters = aksharas(form)
    if word.startswith(form) and letters >= 2 and len(form) >= 3:
        return "boundary" if exact else "stem"
    # A short word such as கண் is a common ending, so only a longer
    # form may match the end of a compound (அறக்கடவுள்).
    if word.endswith(form) and letters >= 4:
        return "boundary" if exact else "stem"
    if exact and letters >= 4 and form in word:
        return "buried"
    return None


def _score_phrase(fields: dict[str, str], phrase: str) -> _Scored | None:
    """Score one phrase. Every word has to occur. ``None`` is a miss."""
    tokens = [token for token in normalize_text(phrase).split(" ") if len(token) >= 2]
    if not tokens:
        return None
    score = 0
    matched: str | None = None
    matched_rank = -1
    term = tokens[0]
    for token in tokens:
        forms = token_forms(token)
        best = 0
        best_where: str | None = None
        best_term = token
        for label, text in fields.items():
            for word in _words(text):
                for form in forms:
                    kind = _kind(form, word, exact=form == token)
                    if kind is None:
                        continue
                    rank = _RANK[(label, kind)]
                    if rank > best:
                        best = rank
                        best_where = label
                        best_term = word if kind == "whole" else form
        if best_where is None:
            return None
        score += best
        if best > matched_rank:
            matched_rank = best
            matched = best_where
            term = best_term
    if matched is None:
        return None
    if len(tokens) >= 2 and _theme(tokens, _words(fields["அதிகாரம்"])):
        score += _THEME
    return _Scored(score, matched, term)


def _theme(tokens: list[str], title_words: list[str]) -> bool:
    """True when every query word is a whole word of the chapter title."""
    if len(tokens) < 2:
        return False
    for token in tokens:
        forms = {form for form in token_forms(token) if form}
        if not any(word in forms for word in title_words):
            return False
    return True


def _score_groups(
    fields: dict[str, str], groups: list[tuple[str, ...]]
) -> _Scored | None:
    """Or inside a group, and across groups. Earlier glosses rank higher."""
    score = 0
    matched: str | None = None
    matched_rank = -1
    term = ""
    for alternatives in groups:
        best = 0
        best_scored: _Scored | None = None
        for index, alternative in enumerate(alternatives):
            scored = _score_phrase(fields, alternative)
            if scored is None:
                continue
            weight = scored.score + (len(alternatives) - index)
            if weight > best:
                best = weight
                best_scored = scored
        if best_scored is None:
            return None
        score += best
        rank = _FIELD_WEIGHT[best_scored.where]
        if rank > matched_rank:
            matched_rank = rank
            matched = best_scored.where
            term = best_scored.term
    if matched is None:
        return None
    return _Scored(score, matched, term)


def _score_roman(fields: dict[str, str], query: tuple[str, ...]) -> _Scored | None:
    best = 0
    where: str | None = None
    term = ""
    for label, text in fields.items():
        for word in _words(text):
            word_key = phonemes(word)
            if word_key is None:
                continue
            kind = match_kind(query, word_key)
            if kind is None:
                continue
            rank = _RANK[(label, kind)]
            if rank > best:
                best = rank
                where = label
                term = word
    if where is None:
        return None
    return _Scored(best, where, term)


def _active_roman(verses: list[Verse], pending: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Romanized leftovers that match at least one word in the corpus."""
    active: list[tuple[str, ...]] = []
    for word in pending:
        key = phonemes(word)
        if not key:
            continue
        if any(_score_roman(_fields(verse), key) is not None for verse in verses):
            active.append(key)
    return active


def _verse_number(query: str) -> int | None:
    text = query.strip()
    if not text.isdigit():
        return None
    number = int(text)
    if 1 <= number <= TOTAL_VERSES:
        return number
    return None


def _hit(verse: Verse, scored: _Scored) -> SearchHit:
    return SearchHit(
        number=verse.number,
        title=verse.title,
        couplet=couplet_text(verse.kural),
        explanation=verse.explanation.strip(),
        matched=scored.where,
        term=scored.term,
        score=scored.score,
    )


def search(verses: list[Verse], query: str, limit: int | None = 20) -> list[SearchHit]:
    number = _verse_number(query)
    if number is not None:
        found = [verse for verse in verses if verse.number == number]
        hits = [
            _hit(verse, _Scored(1, "குறள்", str(verse.number))) for verse in found
        ]
        return hits[:limit] if limit is not None else hits
    plan = latin_plan(query)
    roman: list[tuple[str, ...]] = []
    if plan is not None:
        if not plan.groups and not plan.pending:
            return []
        roman = _active_roman(verses, plan.pending)
        if not plan.groups and not roman:
            return []
    hits: list[SearchHit] = []
    for verse in verses:
        fields = _fields(verse)
        scored = _score_query(fields, query, plan, roman)
        if scored is None:
            continue
        hits.append(_hit(verse, scored))
    hits.sort(key=lambda hit: (-hit.score, hit.number))
    if limit is None:
        return hits
    return hits[:limit]


def _score_query(
    fields: dict[str, str],
    query: str,
    plan: LatinPlan | None,
    roman: list[tuple[str, ...]],
) -> _Scored | None:
    if plan is None:
        return _score_phrase(fields, query)
    scored = _score_groups(fields, list(plan.groups)) if plan.groups else None
    if plan.groups and scored is None:
        return None
    score = 0 if scored is None else scored.score
    where = None if scored is None else scored.where
    term = "" if scored is None else scored.term
    best = 0 if scored is None else _FIELD_WEIGHT[scored.where]
    for key in roman:
        roman_scored = _score_roman(fields, key)
        if roman_scored is None:
            return None
        score += roman_scored.score
        rank = _FIELD_WEIGHT[roman_scored.where]
        if rank > best:
            best = rank
            where = roman_scored.where
            term = roman_scored.term
    if where is None:
        return None
    return _Scored(score, where, term)


def format_hits(
    hits: list[SearchHit],
    total: int | None = None,
    *,
    empty: str = "பொருந்தும் குறள் இல்லை",
) -> str:
    if not hits:
        return empty + "\n"
    lines: list[str] = []
    for hit in hits:
        lines.append(f"{hit.number}\t{hit.title}\t{hit.matched}\t{hit.term}")
        lines.append(hit.couplet)
        lines.append("")
    shown = total if total is not None else len(hits)
    if shown > len(hits):
        lines.append(f"… {len(hits)} / {shown}")
    return "\n".join(lines).rstrip() + "\n"


def _js_json(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def render_search_panel(verses: list[Verse]) -> str:
    index = [
        {
            "n": verse.number,
            "h": slide_position(verse.number)[0],
            "v": slide_position(verse.number)[1],
            "title": verse.title,
            "kural": couplet_text(verse.kural),
            "note": verse.explanation.strip(),
        }
        for verse in verses
    ]
    client = _CLIENT.read_text(encoding="utf-8")
    glossary = {phrase: list(alternatives) for phrase, alternatives in ENGLISH.items()}
    return (
        _PANEL.replace("%%CLIENT%%", client)
        .replace("%%SUFFIXES%%", _js_json(list(SUFFIXES)))
        .replace("%%ENGLISH%%", _js_json(glossary))
        .replace("%%INDEX%%", _js_json(index))
    )


def add_search(document: str, verses: list[Verse]) -> str:
    panel = render_search_panel(verses)
    marker = "</body>"
    if document.count(marker) != 1:
        raise ValueError("template is missing </body>")
    return document.replace(marker, panel + marker, 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find Thirukural verses for a word")
    parser.add_argument("query", help="Word or phrase to look up")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    if args.limit < 1:
        parser.error("limit must be at least 1")
    verses = load_verses(args.db)
    found = search(verses, args.query, limit=None)
    empty = "பொருந்தும் குறள் இல்லை"
    if english_groups(args.query) is not None:
        empty = "No matching Thirukural."
    print(format_hits(found[: args.limit], total=len(found), empty=empty), end="")
    return 0


_PANEL = """<!-- kural-search:start -->
<style>
#kural-search-open {
  position: fixed;
  z-index: 100000;
  top: 12px;
  left: 12px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: rgba(17, 17, 17, 0.92);
  color: #f5f5f5;
  border-radius: 999px;
  padding: 8px 14px;
  font: 600 15px/1.2 "Nirmala UI", "Latha", "Noto Sans Tamil", sans-serif;
  cursor: pointer;
}
#kural-search {
  position: fixed;
  z-index: 100001;
  top: 0;
  left: 0;
  height: 100%;
  width: min(420px, 100%);
  display: flex;
  flex-direction: column;
  background: rgba(16, 16, 16, 0.97);
  color: #f3f3f3;
  box-shadow: 8px 0 28px rgba(0, 0, 0, 0.45);
  font-family: "Nirmala UI", "Latha", "Noto Sans Tamil", sans-serif;
}
#kural-search[hidden] { display: none !important; }
#kural-search header {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 14px 14px 8px;
}
#kural-search input {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
  background: #2a2a2a;
  color: #fff;
  border: 1px solid #555;
  border-radius: 8px;
  padding: 10px 12px;
  font: 18px/1.4 "Nirmala UI", "Latha", "Noto Sans Tamil", sans-serif;
}
#kural-search-close {
  border: 0;
  background: transparent;
  color: #ddd;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  padding: 4px 6px;
}
#kural-search-count {
  margin: 0;
  padding: 0 16px 8px;
  color: #9a9a9a;
  font-size: 13px;
}
#kural-search-results {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow: auto;
  flex: 1;
}
#kural-search-results button {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  color: inherit;
  border: 0;
  border-top: 1px solid #2c2c2c;
  padding: 12px 16px;
  cursor: pointer;
  font: 16px/1.45 "Nirmala UI", "Latha", "Noto Sans Tamil", sans-serif;
}
#kural-search-results button:hover,
#kural-search-results button:focus { background: #242424; }
#kural-search-results .meta { color: #9a9a9a; font-size: 13px; }
#kural-search-results .kural { color: #fff; margin-top: 4px; white-space: pre-line; }
#kural-search-results .note { color: #bdbdbd; font-size: 14px; margin-top: 4px; }
html.kural-narrow,
html.kural-narrow body {
  width: 100% !important;
  height: 100% !important;
  overflow: hidden !important;
  background: #222222 !important;
  overscroll-behavior: none;
}
html.kural-narrow .reveal-viewport,
html.kural-narrow .reveal {
  width: 100% !important;
  height: 100% !important;
  overflow: hidden !important;
}
html.kural-narrow #kural-search-open {
  top: auto;
  left: 16px;
  bottom: calc(16px + env(safe-area-inset-bottom));
  height: 44px;
  min-width: 82px;
  padding: 0 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
}
html.kural-narrow .reveal .playback {
  left: 106px !important;
  right: auto !important;
  bottom: calc(13px + env(safe-area-inset-bottom)) !important;
  transform: none !important;
}
html.kural-narrow .reveal .controls {
  right: 16px !important;
  bottom: calc(16px + env(safe-area-inset-bottom)) !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  width: auto !important;
  height: 44px !important;
}
html.kural-narrow .reveal .controls button {
  position: relative !important;
  left: auto !important;
  top: auto !important;
  right: auto !important;
  bottom: auto !important;
  width: 36px !important;
  height: 36px !important;
  margin: 0 !important;
  transform: none !important;
}
html.kural-narrow #kural-search {
  width: 100%;
  height: 100%;
  padding-bottom: env(safe-area-inset-bottom);
  box-sizing: border-box;
  box-shadow: none;
  background: #141414;
}
html.kural-narrow #kural-search header {
  padding-top: calc(14px + env(safe-area-inset-top));
}
html.kural-narrow #kural-search input { font-size: 16px; }
html.kural-narrow #kural-search-close { min-width: 44px; min-height: 44px; }
html.kural-narrow #kural-search-results button {
  min-height: 44px;
  padding: 14px 16px;
}
html.kural-narrow .reveal .slides {
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  transform: none !important;
}
html.kural-narrow .reveal .slides > section.stack {
  display: block !important;
  padding: 0 !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  overflow: hidden !important;
}
html.kural-narrow .reveal .slides section:not(.stack) {
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  justify-content: center !important;
  box-sizing: border-box !important;
  top: 0 !important;
  left: 0 !important;
  width: 100% !important;
  height: 100% !important;
  padding: calc(20px + env(safe-area-inset-top)) 16px calc(76px + env(safe-area-inset-bottom)) !important;
  overflow: hidden !important;
  text-align: left !important;
}
html.kural-narrow .reveal .slides section:not(.stack):not(:has(.k_id)) {
  align-items: center !important;
  text-align: center !important;
}
html.kural-narrow .reveal .slides section:not(.stack):not(:has(.k_id)) .sl-block,
html.kural-narrow .reveal .slides section:not(.stack):not(:has(.k_id)) .sl-block-content,
html.kural-narrow .reveal .slides section:not(.stack):not(:has(.k_id)) p {
  text-align: center !important;
  font-size: clamp(24px, 6.5vw, 34px) !important;
  font-weight: 700 !important;
}
html.kural-narrow .reveal .slides section .sl-block {
  position: relative !important;
  left: auto !important;
  top: auto !important;
  right: auto !important;
  width: 100% !important;
  max-width: 100% !important;
  height: auto !important;
  margin: 0 !important;
  transform: none !important;
}
html.kural-narrow .reveal .slides section .sl-block-style,
html.kural-narrow .reveal .slides section .sl-block-content {
  position: relative !important;
  transform: none !important;
  width: 100% !important;
  max-width: 100% !important;
}
html.kural-narrow .reveal .slides section:has(.k_id) > .sl-block:not(.k_id):not(.k_t):not(.k_e) {
  order: 3;
  display: flex !important;
  flex-direction: column !important;
  align-items: stretch !important;
  margin: 14px 0 16px !important;
  padding: 14px 12px !important;
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.14) !important;
  border-radius: 10px !important;
  box-sizing: border-box !important;
}
html.kural-narrow .reveal .slides section:has(.k_id) p {
  white-space: nowrap !important;
  width: 100% !important;
  font-size: 18px !important;
  font-weight: 600 !important;
  line-height: 1.5 !important;
  margin: 0 !important;
  text-align: left !important;
}
html.kural-narrow .reveal .slides section:has(.k_id) p + p {
  margin-top: 6px !important;
}
html.kural-narrow .k_id {
  order: 1;
  width: 100% !important;
  text-align: left !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  letter-spacing: 0.05em !important;
  color: #9a9a9a !important;
  margin-bottom: 4px !important;
}
html.kural-narrow .k_t {
  order: 2;
  width: 100% !important;
  left: auto !important;
  text-align: left !important;
  font-size: clamp(16px, 4.4vw, 20px) !important;
  font-weight: 600 !important;
  color: #e2e2e2 !important;
}
html.kural-narrow .k_e {
  order: 4;
  position: relative !important;
  left: auto !important;
  top: auto !important;
  width: 100% !important;
  font-size: clamp(13.5px, 3.8vw, 16px) !important;
  line-height: 1.55 !important;
  color: #d4d0d0 !important;
  text-align: left !important;
  overflow-wrap: break-word !important;
}
html.kural-narrow .k_e span { position: static !important; font-size: inherit !important; }
html.kural-narrow .k_e > span:first-child { display: none !important; }
</style>
<button id="kural-search-open" type="button">தேடு</button>
<div id="kural-search" hidden>
  <header>
    <input id="kural-search-input" type="search" lang="ta" placeholder="rain, god, மழை" autocomplete="off" enterkeyhint="search" aria-label="சொல்">
    <button id="kural-search-close" type="button" aria-label="மூடு">×</button>
  </header>
  <p id="kural-search-count"></p>
  <ol id="kural-search-results"></ol>
</div>
<script>
%%CLIENT%%
</script>
<script>
(function () {
  var api = KuralSearch.createSearch(%%SUFFIXES%%, %%ENGLISH%%);
  var index = %%INDEX%%;
  var openButton = document.getElementById("kural-search-open");
  var panel = document.getElementById("kural-search");
  var input = document.getElementById("kural-search-input");
  var count = document.getElementById("kural-search-count");
  var results = document.getElementById("kural-search-results");
  var mouseWheel = true;

  function clip(value) {
    var text = String(value || "").replace(/\\s+/g, " ").trim();
    return text.length > 90 ? text.slice(0, 89) + "…" : text;
  }

  function setOpen(isOpen) {
    panel.hidden = !isOpen;
    openButton.hidden = isOpen;
    if (window.Reveal && Reveal.configure) {
      if (isOpen) mouseWheel = Reveal.getConfig().mouseWheel !== false;
      Reveal.configure({ mouseWheel: isOpen ? false : mouseWheel });
    }
    if (isOpen && window.Reveal && Reveal.toggleAutoSlide) Reveal.toggleAutoSlide(false);
    if (isOpen) input.focus();
    else input.blur();
  }

  function englishQuery(query) {
    return !/[\u0b80-\u0bff]/.test(query) && /[A-Za-z]/.test(query);
  }

  function fitSlide() {
    if (!window.Reveal || !Reveal.getCurrentSlide) return;
    var slide = Reveal.getCurrentSlide();
    if (!slide) return;
    var lines = slide.querySelectorAll(".sl-block:not(.k_id):not(.k_t):not(.k_e) p");
    var note = slide.querySelector(".k_e");
    for (var i = 0; i < lines.length; i++) lines[i].style.removeProperty("font-size");
    if (note) {
      note.style.removeProperty("font-size");
      note.style.removeProperty("line-height");
    }
    if (!document.documentElement.classList.contains("kural-narrow")) return;
    if (lines.length && slide.querySelector(".k_id")) {
      for (var cpx = 19; cpx >= 11; cpx -= 0.5) {
        for (var j = 0; j < lines.length; j++) {
          lines[j].style.setProperty("font-size", cpx + "px", "important");
        }
        var fitsWidth = true;
        for (var k = 0; k < lines.length; k++) {
          if (lines[k].scrollWidth > lines[k].clientWidth + 1) {
            fitsWidth = false;
            break;
          }
        }
        if (fitsWidth) break;
      }
    }
    if (!note) return;
    for (var px = 15.5; px >= 11.5; px -= 0.5) {
      if (slide.scrollHeight <= slide.clientHeight + 2) break;
      note.style.setProperty("font-size", px + "px", "important");
      note.style.setProperty("line-height", "1.45", "important");
    }
  }

  function fit() {
    var narrow = window.innerWidth <= 800;
    document.documentElement.classList.toggle("kural-narrow", narrow);
    if (!window.Reveal || !Reveal.configure || !Reveal.getConfig) return;
    var cfg = Reveal.getConfig();
    if (!fit.desktop) {
      fit.desktop = {
        width: cfg.width,
        height: cfg.height,
        margin: cfg.margin,
        minScale: cfg.minScale,
        maxScale: cfg.maxScale,
        center: cfg.center
      };
    }
    if (narrow) {
      Reveal.configure({
        width: window.innerWidth,
        height: window.innerHeight,
        margin: 0,
        minScale: 1,
        maxScale: 1,
        center: false
      });
    } else {
      Reveal.configure(fit.desktop);
    }
    if (Reveal.layout) Reveal.layout();
    fitSlide();
  }

  function show(query) {
    var trimmed = query.trim();
    var inEnglish = englishQuery(trimmed);
    results.innerHTML = "";
    if (!trimmed) {
      count.textContent = "குறள், விளக்கம், அதிகாரம் · rain, god, மழை";
      return;
    }
    if (!/^\\d+$/.test(trimmed) && trimmed.length < 2) {
      count.textContent = inEnglish ? "At least two letters" : "குறைந்தது இரண்டு எழுத்துகள்";
      return;
    }
    var found = api.search(index, query);
    var shown = found.slice(0, 40);
    var unit = inEnglish ? " verses" : " குறள்";
    var none = inEnglish ? "No matching Thirukural." : "பொருந்தும் குறள் இல்லை";
    count.textContent = found.length ? (shown.length < found.length ? shown.length + " / " + found.length + unit : found.length + unit) : none;
    shown.forEach(function (hit) {
      var item = document.createElement("li");
      var button = document.createElement("button");
      button.type = "button";
      button.innerHTML = '<div class="meta"></div><div class="kural"></div><div class="note"></div>';
      var meta = hit.n + "  " + hit.title + "  ·  " + hit.where;
      if (hit.term) meta += "  ·  " + hit.term;
      button.querySelector(".meta").textContent = meta;
      button.querySelector(".kural").textContent = hit.kural;
      button.querySelector(".note").textContent = clip(hit.note);
      button.addEventListener("click", function () {
        setOpen(false);
        if (window.Reveal && Reveal.slide) {
          Reveal.slide(hit.h, hit.v);
          if (Reveal.toggleAutoSlide) Reveal.toggleAutoSlide(false);
        }
      });
      item.appendChild(button);
      results.appendChild(item);
    });
  }

  openButton.addEventListener("click", function () { setOpen(true); });
  document.getElementById("kural-search-close").addEventListener("click", function () { setOpen(false); });
  input.addEventListener("input", function () { show(input.value); });
  panel.addEventListener("keydown", function (event) {
    event.stopPropagation();
    if (event.key === "Escape") setOpen(false);
  });
  window.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== input && panel.hidden) {
      event.preventDefault();
      setOpen(true);
    }
  });
  show("");
  if (window.Reveal && Reveal.isReady && Reveal.isReady()) fit();
  else if (window.Reveal && Reveal.on) Reveal.on("ready", fit);
  else window.addEventListener("load", fit);
  if (window.Reveal && Reveal.on) Reveal.on("slidechanged", fitSlide);
  window.addEventListener("resize", fit);
})();
</script>
<!-- kural-search:end -->
"""


if __name__ == "__main__":
    raise SystemExit(main())
