"""The builder keeps the slide markup and adds word search."""

import os
import tempfile
import unittest
from pathlib import Path

from thirukural.build import apply_template, build
from thirukural.model import Verse
from thirukural.paths import TEMPLATE_PATH
from thirukural.render import format_couplet, render_slides
from thirukural.repository import load_verses


def _assert_same(testcase: unittest.TestCase, expected: str, actual: str) -> None:
    if expected == actual:
        return
    limit = min(len(expected), len(actual))
    index = next(
        (i for i in range(limit) if expected[i] != actual[i]),
        limit,
    )
    start = max(0, index - 80)
    raise AssertionError(
        f"mismatch at {index} (lengths {len(expected)} and {len(actual)})\n"
        f"expected: {expected[start:index + 80]!r}\n"
        f"actual:   {actual[start:index + 80]!r}"
    )


class DeckTests(unittest.TestCase):
    def test_corpus_has_every_verse(self) -> None:
        verses = load_verses()
        self.assertEqual(len(verses), 1330)
        self.assertEqual(verses[0].number, 1)
        self.assertEqual(verses[-1].number, 1330)

    def test_couplet_keeps_the_first_line_and_closes_the_second(self) -> None:
        verses = {verse.number: verse for verse in load_verses()}
        self.assertEqual(
            format_couplet(verses[1].kural),
            "<p>அகர முதல எழுத்தெல்லாம் ஆதி </p><p>பகவன் முதற்றே உலகு.</p>",
        )
        # A break written with a different tag still becomes two paragraphs.
        self.assertEqual(
            format_couplet("முதல்<br>இரண்டாம்"),
            "<p>முதல்</p><p>இரண்டாம்.</p>",
        )

    def test_commentary_can_mention_template_words(self) -> None:
        verse = Verse(
            number=2,
            kural="முதல்<br/>\r\nஇரண்டாம்",
            title="அதிகாரம்",
            explanation="the kural_title and kural remain",
        )
        slides = render_slides([verse])
        self.assertIn("the kural_title and kural remain", slides)
        self.assertIn("\n        2\n", slides)

    def test_text_is_escaped(self) -> None:
        verse = Verse(
            number=1,
            kural="முதல்<br/>\r\nஇரண்டாம்",
            title="a < b",
            explanation="x & y",
        )
        slides = render_slides([verse])
        self.assertIn("a &lt; b", slides)
        self.assertIn("x &amp; y", slides)
        self.assertNotIn("a < b", slides)

    def test_published_groups_and_verse_count(self) -> None:
        slides = render_slides(load_verses())
        self.assertEqual(slides.count('data-autoslide="4000"'), 133)
        self.assertEqual(slides.count('class="sl-block k_id"'), 1330)
        self.assertTrue(slides.startswith("<section>\n"))
        self.assertTrue(slides.endswith("</section>"))

    def test_build_keeps_slide_markup_and_adds_search(self) -> None:
        verses = load_verses()
        expected = apply_template(
            TEMPLATE_PATH.read_text(encoding="utf-8"),
            render_slides(verses),
        )
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                output = Path(tmp) / "index.html"
                build(output_path=output)
            finally:
                os.chdir(previous)
            document = output.read_bytes().decode("utf-8")
        start = document.find("<!-- kural-search:start -->")
        end = document.find("<!-- kural-search:end -->")
        self.assertGreater(start, 0)
        self.assertGreater(end, start)
        closing = document.find("\n", end)
        bare = document[:start] + document[closing + 1 :]
        _assert_same(self, expected, bare)
        self.assertIn("தேடு", document)
        self.assertIn("kural-narrow", document)
        self.assertIn("rain, god, மழை", document)
        self.assertIn('"n":12', document)
        self.assertEqual(Path.cwd(), previous)
