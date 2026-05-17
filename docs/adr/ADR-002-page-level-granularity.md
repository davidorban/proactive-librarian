# ADR-002: Chunk granularity — one markdown file per PDF page

- **Status**: proposed
- **Date**: 2026-05-17
- **Tags**: retrieval, granularity, file-layout

## Context

The Librarian's core value proposition is **citations with page numbers**: queries should return results like `Report.pdf:p.42`, not just `Report.pdf`. Three granularities considered:

1. **File-level** — one document per PDF. Backend returns file matches; page info is lost.
2. **Page-level** — one markdown file per PDF page, anchored by filename. Backend returns `(file, page)` matches usable for citation.
3. **Paragraph / semantic-chunk level** — splits within pages on token boundaries. Better retrieval precision but loses cleanly cite-able physical-document references.

Earlier attempts with per-PDF markdown files using `## Page N` headers as in-text markers exhibited two problems:

- When a backend's snippet chunk spans page boundaries or matches near the document head, parsing `## Page N` from the snippet collapses everything to `p.1` (or the wrong page).
- Embedded YAML frontmatter (used for metadata) gets indexed alongside content, leaking `sha1: ...` and `source_pdf: ...` into citation snippets.

## Decision

**One markdown file per PDF page.** The file path is the citation:

```
<derived_root>/<rel-pdf-stem>/p<NNNN>.md
```

The page number is parsed from the filename (`p0042.md` → 42), never from content. Each markdown file contains **only the page's extracted text** — no frontmatter, no headers, no inline markers. Metadata lives in a per-PDF `_meta.json` sidecar (excluded from indexing by the `_` prefix convention).

## Consequences

### Positive
- Citations are physical and unambiguous (`Brief.pdf:p.27`).
- Markdown deep-links `[Source](file.pdf#page=27)` open the PDF at the right page in most viewers (Obsidian, Preview, Acrobat, browsers).
- The backend can't leak metadata into snippets because there isn't any in the indexed content.
- Recall is preserved — granularity affects what's *returned* (the unit of citation), not what's *searched*.

### Negative
- High file count: ~1.4k PDFs averaging 50 pages = ~67k markdown files. Modern filesystems (APFS, ext4) handle this fine; older or networked filesystems may not.
- Extraction must preserve page boundaries (`pypdf` iterates per-page natively; the implementation is straightforward).
- For backends that index per-file, the index is larger than the per-PDF alternative.

### Neutral
- Page-filename convention (`pNNNN.md` with configurable zero-padding) becomes a contract between `ingest.py` and `query.py`. Documented in `config.py` and the README.

## Links

- README — "Why page-per-file?" section
- ADR-001 (storage substrate) — relies on file-as-document semantics for citation.
- ADR-004 (PDF canonical, markdown derivative) — explains why the markdown can be page-fragmented without losing semantics.
