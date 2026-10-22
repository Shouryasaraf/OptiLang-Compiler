from __future__ import annotations

import argparse
from pathlib import Path

from .compiler import CompileError, compile_source, format_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optilang",
        description="Compile and execute an OptiLang source file.",
    )
    parser.add_argument("source", type=Path, help="Path to an .ol source file")
    parser.add_argument("--html", type=Path, help="Write an offline visual explorer to this HTML file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = args.source.read_text(encoding="utf-8")
        result = compile_source(source)
        if args.html is not None:
            from .explorer import render_html
            args.html.write_text(render_html(source, result), encoding="utf-8")
    except OSError as error:
        print(f"Input error: {error}")
        return 2
    except CompileError as error:
        print(error)
        return 1
    print(format_result(result))
    if args.html is not None:
        print(f"\nEXPLORER: {args.html.resolve()}")
    return 0

