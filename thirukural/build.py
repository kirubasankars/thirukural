"""Fill the slide shell and write docs/index.html."""

import argparse
from pathlib import Path

from thirukural.paths import DB_PATH, OUTPUT_PATH, TEMPLATE_PATH
from thirukural.render import render_slides
from thirukural.repository import load_verses

_PLACEHOLDER = "kural_list"


def apply_template(template_text: str, slides: str) -> str:
    """Insert slides at ``kural_list``.

    The shell is a Slides.com export. The deck that is already published
    was produced by stripping every line of that export, so the same
    whitespace is kept here.
    """
    if template_text.count(_PLACEHOLDER) != 1:
        raise ValueError(f"template must contain {_PLACEHOLDER} once")
    lines = [
        line.strip().replace(_PLACEHOLDER, slides)
        for line in template_text.splitlines()
    ]
    return "\n".join(lines) + "\n"


def build(
    db_path: Path = DB_PATH,
    template_path: Path = TEMPLATE_PATH,
    output_path: Path = OUTPUT_PATH,
) -> None:
    verses = load_verses(db_path)
    slides = render_slides(verses)
    document = apply_template(template_path.read_text(encoding="utf-8"), slides)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Thirukural slide deck")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--template", type=Path, default=TEMPLATE_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args(argv)
    build(args.db, args.template, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
