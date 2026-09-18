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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = args.source.read_text(encoding="utf-8")
        result = compile_source(source)
    except OSError as error:
        print(f"Input error: {error}")
        return 2
    except CompileError as error:
        print(error)
        return 1
    print(format_result(result))
    return 0

