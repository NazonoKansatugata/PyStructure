from __future__ import annotations

import argparse
from pathlib import Path

from api import analyze_project
from exporter import GraphvizExporter, JsonExporter, TextExporter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pystructure", description="Analyze Python project structure.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Python project.")
    analyze_parser.add_argument("path", type=Path, help="Root directory to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Output JSON")
    analyze_parser.add_argument("--graphviz", action="store_true", help="Output Graphviz DOT")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        bundle = analyze_project(args.path)

        if args.json:
            print(JsonExporter().export(bundle.analysis, bundle.graph))
        elif args.graphviz:
            print(GraphvizExporter().export(bundle.analysis, bundle.graph))
        else:
            print(TextExporter().export(bundle.analysis, bundle.graph))
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())