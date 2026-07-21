from __future__ import annotations

import argparse
import json
from pathlib import Path

from api import analyze_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pystructure", description="Analyze Python project structure.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Python project.")
    analyze_parser.add_argument("path", type=Path, help="Root directory to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Output JSON")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        bundle = analyze_project(args.path)

        if args.json:
            print(json.dumps(bundle.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(f"Root: {bundle.analysis.root}")
            print(f"Modules: {len(bundle.analysis.modules)}")
            print(f"Nodes: {len(bundle.graph.nodes)}")
            print(f"Edges: {len(bundle.graph.edges)}")
        return 0

    parser.error("Unknown command")
    return 1