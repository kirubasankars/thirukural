"""One phonetic key for Tamil script and romanized Tamil.

Long and short vowels collapse. ``ழ`` shares a key with ``zh`` and ``l``,
and ``த`` / ``ட`` share a key with ``th``, ``dh``, ``t``, and ``d``. An
optional ``a`` between consonants covers spellings such as ``kadavul``
for ``கடவுள்``.
"""

from __future__ import annotations

_CONSONANTS = {
    "க": "k",
    "ங": "ng",
    "ச": "c",
    "ஞ": "nj",
    "ட": "t",
    "ண": "n",
    "த": "t",
    "ந": "n",
    "ப": "p",
    "ம": "m",
    "ய": "y",
    "ர": "r",
    "ல": "l",
    "வ": "v",
    "ழ": "l",
    "ள": "l",
    "ற": "r",
    "ன": "n",
    "ஜ": "j",
    "ஷ": "c",
    "ஸ": "c",
    "ஹ": "h",
}
_VOWEL_SIGNS = {
    "ா": "a",
    "ி": "i",
    "ீ": "i",
    "ு": "u",
    "ூ": "u",
    "ெ": "e",
    "ே": "e",
    "ை": "e",
    "ொ": "o",
    "ோ": "o",
    "ௌ": "o",
}
_INDEPENDENT = {
    "அ": "a",
    "ஆ": "a",
    "இ": "i",
    "ஈ": "i",
    "உ": "u",
    "ஊ": "u",
    "எ": "e",
    "ஏ": "e",
    "ஐ": "e",
    "ஒ": "o",
    "ஓ": "o",
    "ஔ": "o",
}
_PULLI = "\u0bcd"
_VOWELS = frozenset({"a", "e", "i", "o", "u"})
_COMBINING = frozenset({_PULLI, *_VOWEL_SIGNS})


def aksharas(text: str) -> int:
    """Letters, counting a consonant and its vowel sign as one."""
    return sum(1 for char in text if char not in _COMBINING)
_LATIN = (
    ("zh", "l"),
    ("th", "t"),
    ("dh", "t"),
    ("aa", "a"),
    ("ee", "i"),
    ("ii", "i"),
    ("oo", "u"),
    ("uu", "u"),
    ("ai", "e"),
    ("au", "o"),
    ("ch", "c"),
    ("sh", "c"),
    ("ng", "ng"),
    ("nj", "nj"),
    ("ny", "nj"),
)
_LATIN_SINGLE = {
    "a": "a",
    "e": "e",
    "i": "i",
    "o": "o",
    "u": "u",
    "k": "k",
    "g": "k",
    "s": "c",
    "c": "c",
    "t": "t",
    "d": "t",
    "n": "n",
    "m": "m",
    "y": "y",
    "r": "r",
    "l": "l",
    "v": "v",
    "w": "v",
    "p": "p",
    "b": "p",
    "z": "l",
    "j": "j",
    "f": "p",
    "h": "",
}


def phonemes(text: str) -> tuple[str, ...] | None:
    """Phonemes for a Tamil word or a romanized word.

    ``None`` means the text is not Tamil and not romanized Tamil.
    """
    if any("\u0b80" <= char <= "\u0bff" for char in text):
        return _tamil_phonemes(text)
    return _latin_phonemes(text)


def loose(parts: tuple[str, ...]) -> tuple[str, ...]:
    """Drop the short vowel ``a`` when it sits between two consonants."""
    folded: list[str] = []
    for index, part in enumerate(parts):
        if (
            part == "a"
            and folded
            and folded[-1] not in _VOWELS
            and index + 1 < len(parts)
            and parts[index + 1] not in _VOWELS
        ):
            continue
        folded.append(part)
    return tuple(folded)


def match_kind(query: tuple[str, ...], word: tuple[str, ...]) -> str | None:
    """How a romanized word meets a Tamil word. ``None`` is a miss."""
    if not query or not word:
        return None
    if query == word or loose(query) == loose(word):
        return "whole"
    # The corpus word may carry an ending (மழையால் for mazhai). A longer
    # query is not treated as an ending, or kadavul would hit காத.
    if _extends(word, query):
        return "boundary"
    if _extends(loose(word), loose(query)):
        return "stem"
    return None


def _extends(longer: tuple[str, ...], shorter: tuple[str, ...]) -> bool:
    """True when ``longer`` is ``shorter`` plus a short inflection."""
    extra = len(longer) - len(shorter)
    return len(shorter) >= 4 and 0 < extra <= 4 and longer[: len(shorter)] == shorter


def _tamil_phonemes(text: str) -> tuple[str, ...]:
    parts: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in _INDEPENDENT:
            parts.append(_INDEPENDENT[char])
            index += 1
            continue
        if char in _CONSONANTS:
            parts.append(_CONSONANTS[char])
            index += 1
            if index < len(text) and text[index] == _PULLI:
                index += 1
            elif index < len(text) and text[index] in _VOWEL_SIGNS:
                parts.append(_VOWEL_SIGNS[text[index]])
                index += 1
            else:
                parts.append("a")
            continue
        index += 1
    return tuple(parts)


def _latin_phonemes(text: str) -> tuple[str, ...] | None:
    folded = text.casefold()
    parts: list[str] = []
    index = 0
    while index < len(folded):
        matched = False
        for digraph, phoneme in _LATIN:
            if folded.startswith(digraph, index):
                parts.append(phoneme)
                index += len(digraph)
                matched = True
                break
        if matched:
            continue
        phoneme = _LATIN_SINGLE.get(folded[index])
        if phoneme is None:
            return None
        if phoneme:
            parts.append(phoneme)
        index += 1
    return tuple(parts)
