#!/usr/bin/env python3
"""Download Thirukural verses into src/kural.db."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from thirukural.scrape import main

if __name__ == "__main__":
    raise SystemExit(main())
