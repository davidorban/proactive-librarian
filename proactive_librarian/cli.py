"""Command-line entry: `librarian ingest` and `librarian query`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from proactive_librarian import __version__
from proactive_librarian.config import load_config


def _add_common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", type=Path, default=None,
                   help="Path to proactive-librarian.yaml (overrides default discovery)")
    p.add_argument("--pdf-root", type=str, default=None,
                   help="Override pdf_root from config")
    p.add_argument("--collection", type=str, default=None,
                   help="Override backend collection_name")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="librarian",
        description="Index a PDF library and answer queries with page-accurate citations.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    # --- ingest ---
    ing = sub.add_parser("ingest", help="Walk pdf_root and refresh the cache")
    _add_common_args(ing)
    ing.add_argument("--full", action="store_true",
                     help="Ignore manifest sha1 cache; re-extract every PDF")
    ing.add_argument("--incremental", action="store_true", default=True,
                     help="Default mode: only process new or sha1-changed PDFs")
    ing.add_argument("--dry-run", action="store_true",
                     help="Walk + validate + sha1 but write nothing")
    ing.add_argument("--limit", type=int, default=0,
                     help="Process at most N PDFs (useful for testing)")
    ing.add_argument("--category", type=str, default=None,
                     help="Only process PDFs under this exact top-level subject")
    ing.add_argument("--clean", action="store_true",
                     help="Delete the derived cache first (use for format migrations)")
    ing.add_argument("--verbose", "-v", action="store_true",
                     help="Print every file decision")

    # --- query ---
    qry = sub.add_parser("query", help="Search the indexed library")
    _add_common_args(qry)
    qry.add_argument("query", type=str, help="Natural language query")
    qry.add_argument("--limit", "-n", type=int, default=5,
                     help="Max results (default 5)")
    qry.add_argument("--json", action="store_true",
                     help="Raw JSON output instead of formatted citations")

    return parser


def _build_overrides(args: argparse.Namespace) -> dict:
    overrides: dict = {}
    if getattr(args, "pdf_root", None):
        overrides["pdf_root"] = args.pdf_root
    if getattr(args, "collection", None):
        overrides["collection_name"] = args.collection
    return overrides


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(
            explicit_path=args.config,
            cli_overrides=_build_overrides(args),
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    if args.command == "ingest":
        from proactive_librarian.ingest import run_ingest
        stats = run_ingest(
            config,
            full=args.full,
            dry_run=args.dry_run,
            limit=args.limit,
            category=args.category,
            clean=args.clean,
            verbose=args.verbose,
        )
        return 1 if stats.errors > 0 else 0

    if args.command == "query":
        from proactive_librarian.query import run_query
        return run_query(
            args.query, config, limit=args.limit, as_json=args.json,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
