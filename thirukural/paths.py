"""Locations of the corpus, the slide shell, and the published deck."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "src" / "kural.db"
TEMPLATE_PATH = ROOT / "src" / "template.html"
OUTPUT_PATH = ROOT / "docs" / "index.html"
