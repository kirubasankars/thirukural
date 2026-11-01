"""Download Thirukural verses from dinamalar.com into SQLite.

Dinamalar now serves each verse as a Next.js page. The verse text, chapter
title, and Solomon Pappaiah commentary are read from the embedded page
data. Line breaks are stored as ``<br/>\\r\\n``, which is the form already
in ``src/kural.db``. Re-running a verse replaces that row instead of
inserting another copy.

A refresh can change a verse's stored chapter name. The 2020 scrape
kept the neighboring chapter on some rows (verse 202, for example);
the current page breadcrumb is what gets stored now, and rebuilding
the deck after that would change those slides.
"""

import argparse
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from thirukural.model import COMMENTARY_AUTHOR, TOTAL_VERSES, chapter_number
from thirukural.paths import DB_PATH

PAGE_URL = "https://www.dinamalar.com/thirukural/{chapter}/{number}"
USER_AGENT = "thirukural-deck (https://github.com/kirubasankars/thirukural)"

_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedKural:
    number: int
    kural: str
    title: str
    explanation: str


def canonical_kural(text: str) -> str:
    """Store a couplet with the line break used by the local corpus."""
    parts = _BREAK.split(text, maxsplit=1)
    if len(parts) != 2:
        raise ValueError("kural text is missing a line break")
    return parts[0] + "<br/>\r\n" + parts[1].lstrip("\r\n")


def parse_kural_page(html: str) -> ParsedKural:
    match = _NEXT_DATA.search(html)
    if not match:
        raise ValueError("page is missing the Thirukural payload")
    try:
        payload = json.loads(match.group(1))
        listing = payload["props"]["pageProps"]["responseListingMain"]
        item = listing["newlist"]["data"][0]
        title = str(listing["breadcrumb"][0]["title"]).strip()
        kural = str(item["kural_txt"])
        explanation = str(item["kural_vilakkam_salaman_papaya"]).strip()
        number = int(item["kural_No"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("page payload is not a Thirukural detail record") from exc
    if not title or not kural.strip() or not explanation:
        raise ValueError("page payload is missing the verse, title, or commentary")
    return ParsedKural(
        number=number,
        kural=canonical_kural(kural),
        title=title,
        explanation=explanation,
    )


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS kurals (id, kural, title)")
    conn.execute("CREATE TABLE IF NOT EXISTS vilakams (id, author, content)")
    conn.commit()


def store_kural(conn: sqlite3.Connection, kural: ParsedKural) -> None:
    with conn:
        conn.execute("DELETE FROM vilakams WHERE id = ?", (kural.number,))
        conn.execute("DELETE FROM kurals WHERE id = ?", (kural.number,))
        conn.execute(
            "INSERT INTO kurals (id, kural, title) VALUES (?, ?, ?)",
            (kural.number, kural.kural, kural.title),
        )
        conn.execute(
            "INSERT INTO vilakams (id, author, content) VALUES (?, ?, ?)",
            (kural.number, COMMENTARY_AUTHOR, kural.explanation),
        )


def fetch_kural(session, number: int) -> ParsedKural:
    import requests

    url = PAGE_URL.format(chapter=chapter_number(number), number=number)
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"failed to download kural {number} from {url}") from exc
    parsed = parse_kural_page(response.text)
    if parsed.number != number:
        raise ValueError(f"expected kural {number}, {url} returned {parsed.number}")
    return parsed


def scrape(
    db_path: Path,
    start: int,
    end: int,
    delay: float,
    dry_run: bool,
) -> None:
    import requests

    conn = None if dry_run else sqlite3.connect(db_path)
    try:
        with requests.Session() as session:
            session.headers["User-Agent"] = USER_AGENT
            if conn is not None:
                ensure_schema(conn)
            for number in range(start, end + 1):
                if number != start and delay:
                    time.sleep(delay)
                parsed = fetch_kural(session, number)
                if conn is not None:
                    store_kural(conn, parsed)
                print(f"{parsed.number} {parsed.title}")
    finally:
        if conn is not None:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download Thirukural verses from dinamalar.com into SQLite"
    )
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=TOTAL_VERSES)
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Seconds to wait between requests",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and parse without writing the database",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.start <= args.end <= TOTAL_VERSES:
        parser.error(f"verse numbers must be inside 1..{TOTAL_VERSES}")
    if args.delay < 0:
        parser.error("delay must be zero or greater")
    scrape(args.db, args.start, args.end, args.delay, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
