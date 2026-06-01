# proactive-librarian

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.1.0-orange.svg)](CHANGELOG.md)

> Turn a directory of PDFs into a searchable index and get back **page-accurate citations** like `Report.pdf:p.27`.

`proactive-librarian` indexes a large document library once, then answers queries with the exact file **and page number** — ready to paste into a memo, brief, paper, or deck. It is a sharp, single-purpose CLI tool: not a chatbot, not a RAG framework, not a vector database you have to operate. Backend-agnostic, with a [QMD](https://github.com/eatonphil/qmd) adapter shipped in the box.

It replaces the brutal friction of citing your own research at scale — folder grep is slow, filenames lie, and Ctrl+F across thousands of PDFs is unworkable.

## Features

- 📄 **Page-accurate citations** — results come back as `file.pdf:p.N`, the page number derived from the cache path, not parsed (and mis-parsed) from a snippet.
- 🔍 **Hybrid retrieval** — keyword + semantic search via the backend (QMD adapter included; bring your own).
- ♻️ **Deterministic, reproducible cache** — rebuildable from the PDFs at any time; safe to delete.
- 🧱 **Page-per-file layout** — pure page text with no metadata leakage into snippets (see [why](#why-page-per-file)).
- 🔐 **Robust ingest** — handles AES-encrypted PDFs, sanitises surrogate/4-byte characters, and logs every failure with a reason to `_failures.json`.
- 🗂️ **Optional taxonomy enforcement** — constrain the library to a known subject/geography scheme and fail loudly on stragglers.
- ⚡ **Incremental** — sha1 manifest means re-ingest only touches changed PDFs.
- ✅ **Tested** — 36+ pytest cases over hashing, path mapping, manifest persistence, atomic writes, failure logging, and taxonomy validation.

## Who it's for

Built originally for one person's research-citation workflow, but it solves a general problem — **anyone who maintains a large PDF/document library and needs to quote it with precision**:

- researchers and analysts citing a corpus of papers/reports,
- policy, legal, and compliance teams working from regulatory documents,
- technical writers and maintainers grounding docs in source material,
- AI agents/assistants that need **citation-grounded retrieval** they can shell out to (`librarian query "…"`).

## Install

Not yet on PyPI. Install from source:

```bash
pip install git+https://github.com/davidorban/proactive-librarian
# or, for local development:
git clone https://github.com/davidorban/proactive-librarian
cd proactive-librarian
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

You also need a search backend. The shipped adapter targets **QMD** — install it from https://github.com/eatonphil/qmd (or implement another backend; see [ADR-001](docs/adr/ADR-001-storage-substrate.md)).

## Quickstart

```bash
# 1. Point at your PDF library
cat > proactive-librarian.yaml <<'EOF'
pdf_root: /path/to/your/pdfs
collection_name: research
EOF

# 2. Index (first run; ~30 min for ~1,400 PDFs, then incremental)
librarian ingest --full

# 3. Tell your backend about the new cache (one-time; see backend docs)

# 4. Query
librarian query "stablecoin regulation in the UAE"
```

Example output:

```
1. Digital-Assets-Regulatory-Landscape.pdf:p.27   (0.81)
   "...the payment-token services regulation establishes a licensing regime for fiat-backed..."
2. ADGM-Virtual-Asset-Framework-2025.pdf:p.12      (0.74)
   "...issuers must maintain reserves on a 1:1 basis, audited monthly by an approved..."
3. Stablecoin-Market-Structure.pdf:p.4             (0.69)
   "...redemption-at-par guarantees are the load-bearing assumption behind..."
```

Paste the `file.pdf:p.N` straight into your draft.

## What it produces

```
<pdf_root>/.derived/
├── _manifest.json                    # sha1 cache for incremental re-ingest
├── _failures.json                    # last run's failed PDFs (with reasons)
└── <rel-pdf-stem-tree>/
    ├── _meta.json                    # per-PDF metadata sidecar (NOT indexed)
    ├── p0001.md                      # pure page text — no frontmatter
    ├── p0002.md
    └── ...
```

The cache lives next to the PDFs in `.derived/` (gitignored), is **reproducible** from the source PDFs, and is safe to delete and rebuild. The PDFs stay canonical; the markdown is a disposable index ([ADR-004](docs/adr/ADR-004-pdf-canonical-cache.md)).

## Why page-per-file?

Single-file-per-PDF chunking has two failure modes:

1. **Metadata leaks into snippets.** YAML frontmatter gets indexed with the content, so citation snippets end up containing `sha1: abc…` and `source_pdf: …`.
2. **Page numbers become unreliable.** When a chunk spans page boundaries, parsing `## Page N` markers collapses everything to `p.1` and citations lose precision.

Page-per-file fixes both: each markdown file holds only one page's text (nothing to leak), and the page number is a property of the path (`p0042.md` → page 42). The trade-off is a high file count (~1,377 PDFs × ~50 pages ≈ 67k files); modern filesystems (APFS, ext4) handle it fine. Full rationale in [ADR-002](docs/adr/ADR-002-page-level-granularity.md).

## Configuration

`proactive-librarian.yaml` in the working directory, or `--config /path/to/config.yaml`:

```yaml
# Required
pdf_root: /path/to/pdfs

# Optional (defaults shown)
derived_dir: .derived              # relative to pdf_root
collection_name: research          # backend collection key

taxonomy:                          # optional subject-category enforcement
  enabled: false
  allowed_subjects: []             # first path component under pdf_root must match

backend:
  type: qmd
  binary: qmd                      # on PATH, or an absolute path
  timeout_seconds: 30
```

With no config file present, it runs with permissive defaults (`pdf_root: .`, no taxonomy). See [`examples/`](examples/) for annotated config and taxonomy files.

## Architecture

Five load-bearing decisions, each documented as an ADR:

| ADR | Decision |
|-----|----------|
| [ADR-001](docs/adr/ADR-001-storage-substrate.md) | QMD as the search substrate, not a standalone vector DB |
| [ADR-002](docs/adr/ADR-002-page-level-granularity.md) | Page-per-file granularity, not paragraph chunks |
| [ADR-003](docs/adr/ADR-003-explicit-invocation.md) | Explicit CLI invocation, not an ambient hook (yet) |
| [ADR-004](docs/adr/ADR-004-pdf-canonical-cache.md) | PDFs canonical; markdown is a disposable cache |
| [ADR-005](docs/adr/ADR-005-no-new-services.md) | A Python package + adapter, not a long-running service |

## Development

```bash
pip install -e ".[dev]"
pytest          # 36+ cases
ruff check .    # lint
```

## Roadmap

- Additional backends beyond QMD (the adapter boundary already exists).
- Publish to PyPI for a plain `pip install proactive-librarian`.
- Optional ambient/agent invocation surface (the explicit-CLI decision in ADR-003 is revisitable as adoption grows).
- Richer query output formats (JSON, BibTeX-style citation export).

## Contributing

Issues and pull requests welcome. The codebase is small and well-tested — run `pytest` and `ruff check .` before opening a PR. If you're adding a backend, start from the QMD adapter and the ADR-001 rationale.

## License

[MIT](LICENSE) © David Orban.

## Status

**v0.1.0** — in single-user production use; the API will stabilise as more backends and surfaces are added. The cache format and CLI are stable. See [CHANGELOG.md](CHANGELOG.md).
