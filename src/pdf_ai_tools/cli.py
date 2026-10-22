"""Command line entry for pdf-ai-tools.

No arguments on a pipe starts the MCP server (see frozen_main).
A terminal with no arguments prints help.
"""

from __future__ import annotations

import argparse
import sys

from pdf_ai_tools.mcp_server import package_version
from pdf_ai_tools.render import render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pdf-ai-tools",
        description=(
            "PDF tools for an agent. No arguments on a pipe starts the MCP server."
        ),
    )
    parser.add_argument("--version", action="version", version=package_version())
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("list-palettes", help="Print built-in palettes as TOON")
    sub.add_parser("list-templates", help="Print built-in templates as TOON")
    args = parser.parse_args(argv)

    if args.command == "list-palettes":
        from pdf_ai_tools.tools import pdf_list_palettes

        sys.stdout.write(render(pdf_list_palettes()))
        sys.stdout.write("\n")
        return 0
    if args.command == "list-templates":
        from pdf_ai_tools.tools import pdf_list_templates

        sys.stdout.write(render(pdf_list_templates()))
        sys.stdout.write("\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
