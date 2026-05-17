# Changelog

## 0.1.0 — 2026-05-17

Initial standalone release, extracted from a personal-vault skill. Everything that was hardcoded in the original is now configurable via `proactive-librarian.yaml` or CLI flags.

### Added

- `librarian ingest` — walk a PDF directory, extract per-page text via pypdf, write a deterministic cache.
- `librarian query` — hybrid lex+vec retrieval through a QMD backend; returns `file.pdf:p.N` citations.
- Page-per-file output layout: `<derived>/<rel-pdf-stem>/p<NNNN>.md`. Page numbers come from filenames, not snippet parsing.
- Pure-content markdown files (metadata moved to per-PDF `_meta.json` sidecars + global `_manifest.json`) so the retrieval backend can't leak metadata into snippets.
- Configurable subject/geography taxonomy with an optional enforcement mode.
- AES-encrypted PDF support via `cryptography>=3.1`.
- Surrogate-character sanitisation for PDFs with emoji or 4-byte characters.
- `_failures.json` written every run with a per-PDF reason (encrypted / open-error / write-error / taxonomy).
- 36+ pytest cases covering sha1 streaming, path mapping, manifest persistence, atomic writes, failure logging, and taxonomy validation.

### Architecture

- 5 ADRs under `docs/adr/` document the load-bearing decisions: storage substrate (QMD), chunk granularity (page-level), invocation mode (explicit), source-of-truth (PDFs canonical), stack placement (CLI + QMD adapter).
