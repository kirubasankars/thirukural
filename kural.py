#!/usr/bin/env python3
"""Build docs/index.html, or search it with ``python kural.py search <word>``."""

import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        from thirukural.search import main as search_main

        raise SystemExit(search_main(sys.argv[2:]))
    from thirukural.build import main

    raise SystemExit(main())
