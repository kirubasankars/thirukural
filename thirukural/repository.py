"""Read verses from the SQLite corpus."""

import sqlite3
from contextlib import closing
from pathlib import Path

from thirukural.model import Verse
from thirukural.paths import DB_PATH

_QUERY = """
SELECT CAST(kurals.id AS INTEGER) AS id,
       kurals.kural,
       kurals.title,
       vilakams.content
FROM kurals
JOIN vilakams ON kurals.id = vilakams.id
ORDER BY kurals.id
"""


def load_verses(db_path: Path = DB_PATH) -> list[Verse]:
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(_QUERY).fetchall()
    return [
        Verse(number=int(row[0]), kural=row[1], title=row[2], explanation=row[3])
        for row in rows
    ]
