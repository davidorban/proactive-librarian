"""Retrieval engine — hybrid lex+vec search via the configured backend.

Currently only a QMD backend is implemented. Adding others is a matter of:
1. Implementing `run_backend_query(query, config) -> list[dict]`.
2. Wiring it in via `config.backend.type`.

The dict shape returned by any backend must include at least:
- `file`: a path-like string ending in `/pNNNN.md`
- `score`: a float
- `snippet`: a string
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from proactive_librarian.config import Config


PAGE_FNAME_RE = re.compile(r"/p(\d+)\.md$", re.IGNORECASE)
URI_PREFIX_RE = re.compile(r"^[a-z]+://[^/]+/")


def find_backend_binary(config: Config) -> Optional[str]:
    """Resolve the backend binary path (config override > PATH lookup)."""
    if Path(config.backend.binary).is_absolute() and Path(config.backend.binary).exists():
        return config.backend.binary
    return shutil.which(config.backend.binary)


def run_qmd_query(query: str, config: Config, limit: int) -> list[dict[str, Any]]:
    """Execute a hybrid lex+vec query against the QMD backend.

    Returns parsed JSON results or [] on failure.
    """
    qmd = find_backend_binary(config)
    if qmd is None:
        print(
            f"Backend binary {config.backend.binary!r} not found on PATH "
            f"or at the configured location.",
            file=sys.stderr,
        )
        return []

    structured = f"lex: {query}\nvec: {query}"
    cmd = [
        qmd, "query", structured,
        "--collection", config.collection_name,
        "--json",
        "-n", str(limit),
        "--min-score", "0.0",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=config.backend.timeout_seconds, check=True,
        )
        data = json.loads(result.stdout)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("results", [])
        return []
    except subprocess.TimeoutExpired:
        print(f"Backend query timed out after {config.backend.timeout_seconds}s "
              "(reindex in progress?)", file=sys.stderr)
        return []
    except subprocess.CalledProcessError as e:
        print(f"Backend query failed (rc={e.returncode}): {e.stderr}", file=sys.stderr)
        return []
    except json.JSONDecodeError:
        print("Failed to parse backend JSON output", file=sys.stderr)
        return []


def parse_result_path(result: dict[str, Any]) -> tuple[Optional[str], Optional[int]]:
    """Extract (pdf_rel_path, page_number) from a backend result.

    Returns (None, None) for results that don't match the page-per-file layout
    — callers should filter those out (commonly stale cache entries during
    reindex).
    """
    raw = (result.get("file") or result.get("path") or "").strip()
    if not raw:
        return None, None

    # Strip any URI scheme prefix the backend added (e.g. qmd://research/...)
    rel = URI_PREFIX_RE.sub("", raw)

    m = PAGE_FNAME_RE.search(rel)
    if not m:
        return None, None

    page = int(m.group(1))
    parent = rel[: m.start()]
    return parent + ".pdf", page


def format_citation(result: dict[str, Any]) -> Optional[str]:
    """Format a single result. Returns None if the result isn't in v2 layout."""
    pdf_rel, page = parse_result_path(result)
    if pdf_rel is None or page is None:
        return None

    snippet = (result.get("snippet") or "").strip()
    snippet = re.sub(r"\s+", " ", snippet)
    if len(snippet) > 320:
        snippet = snippet[:317] + "..."

    score = result.get("score", 0.0)
    label = Path(pdf_rel).name
    header = f"**{label}**:p.{page}  (score {score:.2f})"
    return f"{header}\n> {snippet}\n"


def run_query(
    query: str, config: Config, *, limit: int = 5, as_json: bool = False
) -> int:
    """Top-level query entry. Returns process exit code."""
    backend = config.backend.type
    if backend != "qmd":
        print(f"Unknown backend type: {backend!r}. Only 'qmd' is implemented.",
              file=sys.stderr)
        return 2

    # Over-fetch then filter, so stale cache entries during reindex don't
    # crowd out the visible results.
    raw = run_qmd_query(query, config, limit * 3)
    valid = [r for r in raw if parse_result_path(r)[1] is not None][:limit]

    if not valid:
        if raw:
            print("Found results but none in the page-per-file layout — backend "
                  "index may be stale. Re-trigger reindex and retry.")
        else:
            print("No results found.")
        return 0

    if as_json:
        enriched = []
        for r in valid:
            pdf_rel, page = parse_result_path(r)
            enriched.append({**r, "_pdf_rel": pdf_rel, "_page": page})
        print(json.dumps({"query": query, "results": enriched}, indent=2))
        return 0

    print(f'\nTop {len(valid)} results for: "{query}"\n' + "=" * 60 + "\n")
    for i, r in enumerate(valid, 1):
        formatted = format_citation(r)
        if formatted:
            print(f"{i}. {formatted}")
            print("-" * 40)
    print("\nTip: paste the bold lines into your draft.")
    return 0
