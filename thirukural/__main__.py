"""Command line entry for ``python -m thirukural``."""

import argparse
import sys

from thirukural.build import main as build_main
from thirukural.scrape import main as scrape_main
from thirukural.search import main as search_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thirukural deck tools")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="Write docs/index.html")
    sub.add_parser("search", help="Find verses for a word")
    sub.add_parser("scrape", help="Refresh src/kural.db from dinamalar.com")
    args, rest = parser.parse_known_args(argv)
    if args.command == "build":
        return build_main(rest)
    if args.command == "search":
        return search_main(rest)
    return scrape_main(rest)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
