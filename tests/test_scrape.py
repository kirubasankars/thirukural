"""Parser and storage tests for the Dinamalar downloader."""

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from thirukural.model import COMMENTARY_AUTHOR
from thirukural.repository import load_verses
from thirukural.scrape import (
    canonical_kural,
    ensure_schema,
    parse_kural_page,
    store_kural,
)


def _page(kural_txt: str, number: int = 1, title: str = "கடவுள் வாழ்த்து") -> str:
    payload = {
        "props": {
            "pageProps": {
                "responseListingMain": {
                    "breadcrumb": [{"title": title}],
                    "newlist": {
                        "data": [
                            {
                                "kural_No": number,
                                "kural_txt": kural_txt,
                                "kural_vilakkam_salaman_papaya": (
                                    "எழுத்துக்கள் எல்லாம் அகரத்தில் தொடங்குகின்றன; "
                                    "(அது போல) உலகம் கடவுளில் தொடங்குகிறது."
                                ),
                            }
                        ]
                    },
                }
            }
        }
    }
    body = json.dumps(payload, ensure_ascii=False)
    return f'<script id="__NEXT_DATA__" type="application/json">{body}</script>'


class ScrapeTests(unittest.TestCase):
    def test_line_break_matches_the_corpus(self) -> None:
        conn = sqlite3.connect(Path(__file__).resolve().parents[1] / "src" / "kural.db")
        stored = dict(conn.execute("SELECT id, kural FROM kurals WHERE id IN (1, 2, 10)"))
        conn.close()
        samples = {
            1: "அகர முதல எழுத்தெல்லாம் ஆதி <br>\nபகவன் முதற்றே உலகு",
            2: "கற்றதனால் ஆய பயனென்கொல் வாலறிவன்<br>\nநற்றாள் தொழாஅர் எனின்",
            10: "பிறவிப் பெருங்கடல் நீந்துவர் நீந்தார்<br>\r\nஇறைவன் அடிசேரா தார்",
        }
        for number, text in samples.items():
            self.assertEqual(canonical_kural(text), stored[number])
            self.assertEqual(canonical_kural(canonical_kural(text)), stored[number])

    def test_parse_reads_the_embedded_record(self) -> None:
        parsed = parse_kural_page(
            _page("அகர முதல எழுத்தெல்லாம் ஆதி <br>\nபகவன் முதற்றே உலகு")
        )
        self.assertEqual(parsed.number, 1)
        self.assertEqual(parsed.title, "கடவுள் வாழ்த்து")
        self.assertEqual(
            parsed.kural,
            "அகர முதல எழுத்தெல்லாம் ஆதி <br/>\r\nபகவன் முதற்றே உலகு",
        )
        self.assertIn("அகரத்தில்", parsed.explanation)

    def test_parse_rejects_a_page_without_the_payload(self) -> None:
        with self.assertRaises(ValueError):
            parse_kural_page("<html><p class='clsMaink'>old</p></html>")

    def test_store_replaces_an_existing_verse(self) -> None:
        parsed = parse_kural_page(
            _page("அகர முதல எழுத்தெல்லாம் ஆதி <br>\nபகவன் முதற்றே உலகு")
        )
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "kural.db"
            conn = sqlite3.connect(db_path)
            ensure_schema(conn)
            store_kural(conn, parsed)
            store_kural(conn, parsed)
            rows = conn.execute("SELECT author, content FROM vilakams").fetchall()
            conn.close()
            verses = load_verses(db_path)
        self.assertEqual(len(verses), 1)
        self.assertEqual(verses[0].number, parsed.number)
        self.assertEqual(verses[0].kural, parsed.kural)
        self.assertEqual(verses[0].title, parsed.title)
        self.assertEqual(verses[0].explanation, parsed.explanation)
        self.assertEqual(rows, [(COMMENTARY_AUTHOR, parsed.explanation)])
