"""Word search over the verse, its commentary, and its chapter name."""

import json
import subprocess
import unittest
from pathlib import Path

from thirukural.english_glossary import ENGLISH, english_groups
from thirukural.model import Verse
from thirukural.repository import load_verses
from thirukural.search import (
    SUFFIXES,
    format_hits,
    search,
    slide_position,
    token_forms,
)


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.verses = load_verses()

    def test_slide_position_matches_the_deck(self) -> None:
        self.assertEqual(slide_position(1), (1, 1))
        self.assertEqual(slide_position(10), (1, 10))
        self.assertEqual(slide_position(11), (2, 1))
        self.assertEqual(slide_position(1330), (133, 10))

    def test_inflected_word_reaches_the_plain_word(self) -> None:
        self.assertEqual(
            token_forms("மழையால்"),
            ["மழையால்", "மழையால", "மழைய", "மழை"],
        )
        self.assertEqual(token_forms("கடவுள்"), ["கடவுள்", "கடவுள"])

    def test_rain_verses_lead_when_the_word_is_in_the_couplet(self) -> None:
        hits = search(self.verses, "மழை", limit=None)
        self.assertGreaterEqual(len(hits), 15)
        self.assertEqual([hit.number for hit in hits[:2]], [12, 15])
        self.assertEqual(hits[0].matched, "குறள்")

    def test_inflection_finds_the_same_rain_verses(self) -> None:
        plain = {hit.number for hit in search(self.verses, "மழை", limit=None)}
        inflected = {hit.number for hit in search(self.verses, "மழையால்", limit=None)}
        self.assertEqual(plain, inflected)

    def test_commentary_and_chapter_name_are_searchable(self) -> None:
        hits = search(self.verses, "கடவுள்", limit=None)
        by_number = {hit.number: hit for hit in hits}
        self.assertIn(1, by_number)
        self.assertEqual(by_number[1].title, "கடவுள் வாழ்த்து")
        self.assertEqual(by_number[77].matched, "விளக்கம்")
        self.assertLess(
            next(i for i, hit in enumerate(hits) if hit.number == 77),
            next(i for i, hit in enumerate(hits) if hit.number == 1),
        )

    def test_every_query_word_must_match(self) -> None:
        verse = Verse(1, "மழை<br/>\r\nபெய்யும்", "வான்", "மழை பெய்தது")
        self.assertEqual(search([verse], "மழை கடவுள்"), [])
        self.assertEqual(search([verse], "மழை வான்")[0].number, 1)

    def test_short_query_is_ignored(self) -> None:
        self.assertEqual(search(self.verses, "அ"), [])
        self.assertIn("இல்லை", format_hits([]))

    def test_english_word_finds_the_rain_and_god_verses(self) -> None:
        rain = search(self.verses, "rain", limit=None)
        self.assertEqual([hit.number for hit in rain[:2]], [12, 15])
        self.assertIn(1, {hit.number for hit in search(self.verses, "god", limit=None)})
        friends = {hit.number for hit in search(self.verses, "friendship", limit=None)}
        self.assertIn(781, friends)
        false_friends = {hit.number for hit in search(self.verses, "false friendship", limit=None)}
        self.assertIn(821, false_friends)
        self.assertNotIn(781, false_friends)
        self.assertEqual(search(self.verses, "xyzzy"), [])
        self.assertEqual(english_groups("the rain"), [("மழை", "வான்")])
        self.assertIsNone(english_groups("மழை"))
        self.assertIn("No matching", format_hits([], empty="No matching Thirukural."))

    def test_every_english_gloss_matches_a_verse(self) -> None:
        missing = [
            f"{phrase} → {alternative}"
            for phrase, alternatives in ENGLISH.items()
            for alternative in alternatives
            if not search(self.verses, alternative, limit=1)
        ]
        self.assertEqual(missing, [])

    def test_browser_search_uses_the_same_endings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = """
        const { createSearch } = require(process.argv[1]);
        const suffixes = JSON.parse(process.argv[2]);
        const english = process.argv[3] ? JSON.parse(process.argv[3]) : {};
        const api = createSearch(suffixes, english);
        const index = [{
          n: 12, h: 1, v: 2, title: "வான் சிறப்பு",
          kural: "துப்பாய தூஉம் மழை.", note: "மழை பெய்யும்"
        }, {
          n: 1, h: 1, v: 1, title: "கடவுள் வாழ்த்து",
          kural: "அகர முதல", note: "உலகம் கடவுளில் தொடங்குகிறது."
        }];
        const rain = api.search(index, "மழையால்").map((hit) => hit.n);
        const god = api.search(index, "கடவுள்").map((hit) => hit.n + ":" + hit.where);
        const rainEn = api.search(index, "rain").map((hit) => hit.n);
        const unknown = api.search(index, "notaword").map((hit) => hit.n);
        console.log(JSON.stringify({
          forms: api.tokenForms("மழையால்", suffixes),
          rain: rain,
          god: god,
          rainEn: rainEn,
          unknown: unknown,
          groups: api.englishGroups("friend's test")
        }));
        """
        completed = subprocess.run(
            [
                "node",
                "-e",
                script,
                str(root / "thirukural" / "search_client.js"),
                json.dumps(list(SUFFIXES), ensure_ascii=False),
                json.dumps(
                    {phrase: list(alts) for phrase, alts in ENGLISH.items()},
                    ensure_ascii=False,
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(completed.stdout)
        self.assertEqual(report["forms"], ["மழையால்", "மழையால", "மழைய", "மழை"])
        self.assertEqual(report["rain"], [12])
        self.assertEqual(report["god"], ["1:விளக்கம்"])
        self.assertEqual(report["rainEn"], [12])
        self.assertEqual(report["unknown"], [])
        self.assertEqual(report["groups"], [["நட்பு ஆராய்தல்"]])

    def test_sample_verse_round_trip(self) -> None:
        verse = Verse(3, "முதல்<br/>\r\nஇரண்டாம்", "தலைப்பு", "விளக்கம் இங்கே")
        hits = search([verse], "இரண்டாம்", limit=5)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].couplet, "முதல்\nஇரண்டாம்.")
        self.assertEqual(hits[0].slide, (1, 3))
