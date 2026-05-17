# proactive-librarian

> Index a PDF library and answer queries with **page-accurate citations**.

A small, opinionated tool that turns a directory of PDFs into a search index, then returns citations like `Report.pdf:p.27` when you query it. Built for a single user filling a single niche: drafting deliverables that quote their own research library.

## Why

If you have hundreds or thousands of PDFs and you regularly need to cite them in memos/briefs/decks, the friction is brutal — folder grep is slow, file names lie, Ctrl+F across multiple PDFs is unworkable. This tool removes that friction:

- Run `librarian ingest` once (and after adding PDFs) — it extracts text per page into a deterministic cache.
- Run `librarian query "your topic"` — get the top hits with file + page number, ready to paste into your draft.

It's not a chatbot, not a RAG framework, not a vector database. It's a sharp tool that solves one job well.

## Quickstart

```bash
# 1. Install
pip install proactive-librarian

# 2. Install the search backend
# Currently we ship with a QMD adapter — install QMD: https://github.com/eatonphil/qmd
# (or bring your own backend; see docs/adr/ADR-001 for the rationale)

# 3. Point at your PDF library
cat > proactive-librarian.yaml <<EOF
pdf_root: /path/to/your/pdfs
collection_name: research
EOF

# 4. Index
librarian ingest --full        # first run; takes ~30 min for ~1,400 PDFs

# 5. Tell your backend about the new cache (one-time, see backend docs)

# 6. Query
librarian query "stablecoin regulation in the UAE"
```

## What it produces

```
<pdf_root>/.derived/
├── _manifest.json                    # sha1 cache for incremental re-ingest
├── _failures.json                    # last run's failed-PDF list (with reasons)
└── <rel-pdf-stem-tree>/
    ├── _meta.json                    # per-PDF metadata sidecar (NOT indexed)
    ├── p0001.md                      # pure page text — no frontmatter
    ├── p0002.md
    └── ...
```

The cache is **reproducible** from the PDFs. It's safe to delete and rebuild. By default it lives next to the PDFs in `.derived/` and is gitignored.

## Why page-per-file?

Two problems with single-file-per-PDF chunking:

1. **Search backends leak metadata into snippets.** YAML frontmatter at the top of a markdown file gets indexed alongside the content. Without isolation, your citation snippets end up containing `sha1: abc...` and `source_pdf: path/to/foo.pdf`. Awkward.
2. **Page numbers become unreliable.** When a chunk spans page boundaries (or matches near the document head), parsing `## Page N` markers from the snippet collapses everything to `p.1`. Citations lose precision.

Page-per-file solves both: the markdown contains only the page's text (no frontmatter to leak), and the page number is a property of the file path (`p0042.md` → page 42), not parsed from content.

The trade-off is a high file count (1,377 PDFs averaging ~50 pages = ~67k markdown files). Modern filesystems (APFS, ext4) handle this without issue.

## Configuration

`proactive-librarian.yaml` in the current directory, or pass `--config /path/to/config.yaml`:

```yaml
# Required
pdf_root: /path/to/pdfs

# Optional (with defaults shown)
derived_dir: .derived              # relative to pdf_root
collection_name: research          # backend collection key

# Optional: enforce a subject category taxonomy
# (see examples/taxonomy.example.yaml)
taxonomy:
  enabled: false
  allowed_subjects: []
  # When enabled, the first path component under pdf_root must match one of these.
  # PDFs with unknown subjects fail ingest with an actionable error.

# Optional: QMD backend overrides
backend:
  type: qmd
  binary: qmd                      # on PATH, or absolute path
  timeout_seconds: 30
```

If no config file is present, the tool runs with permissive defaults (`pdf_root: .`, no taxonomy enforcement).

## Architecture

Five load-bearing decisions, each in its own ADR under `docs/adr/`:

- **[ADR-001](docs/adr/ADR-001-storage-substrate.md)** — Why QMD and not a standalone vector DB.
- **[ADR-002](docs/adr/ADR-002-page-level-granularity.md)** — Why page-per-file and not paragraph chunks.
- **[ADR-003](docs/adr/ADR-003-explicit-invocation.md)** — Why explicit CLI and not an ambient hook (yet).
- **[ADR-004](docs/adr/ADR-004-pdf-canonical-cache.md)** — Why PDFs stay canonical and the markdown is a disposable cache.
- **[ADR-005](docs/adr/ADR-005-no-new-services.md)** — Why a Python package, not a service or MCP server.

## Development

```bash
git clone https://github.com/davidorban/proactive-librarian
cd proactive-librarian
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT. See [LICENSE](LICENSE).

## Status

v0.1.0 — single-user production use; API will stabilise as a few more substrates and surfaces are tried. Issues and contributions welcome.
