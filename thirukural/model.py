"""Verse records stored in the local corpus."""

from dataclasses import dataclass

# Each adhigaram is a group of ten consecutive verses, 1–10, 11–20, …
VERSES_PER_CHAPTER = 10
TOTAL_VERSES = 1330
COMMENTARY_AUTHOR = "சாலமன் பாப்பையா"


@dataclass(frozen=True)
class Verse:
    number: int
    kural: str
    title: str
    explanation: str


def chapter_number(number: int) -> int:
    """Adhigaram index for a verse number in 1..1330."""
    return (number - 1) // VERSES_PER_CHAPTER + 1


def opens_chapter(number: int) -> bool:
    return number % VERSES_PER_CHAPTER == 1


def closes_chapter(number: int) -> bool:
    return number % VERSES_PER_CHAPTER == 0
