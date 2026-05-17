# ADR-001: Storage substrate — reuse an existing local search engine, don't ship a new one

- **Status**: proposed
- **Date**: 2026-05-17
- **Tags**: storage, retrieval, scope

## Context

The Librarian indexes ~1k–10k PDFs averaging tens of pages each — translating to tens of thousands of page-level chunks once extracted. Three retrieval substrates were considered:

1. **A local hybrid search engine like [QMD](https://github.com/eatonphil/qmd)** — BM25 + vectors + LLM reranking in a single binary. Walks a directory of markdown, builds a fast local index. Already on many developer machines.
2. **A standalone vector database** (chromadb, lance, lancedb, pgvector). Domain-specific, supports re-ranking pipelines, scales to millions of chunks.
3. **A metadata-only catalog** (JSON/SQLite indexed by filename and frontmatter). Cheapest to maintain; useless for semantic matching.

Below ~100k chunks, the operational overhead of a dedicated vector DB (process lifecycle, schema management, embedding cost) outweighs the retrieval-quality benefit. A local hybrid search engine fits the scale and the "single user on a laptop" use case.

Metadata-only fails immediately because the core query pattern is semantic ("find passages on X"), not structured.

## Decision

Treat the retrieval substrate as **pluggable but ship only a QMD adapter in v0.1.0**. The `Backend` config dataclass and `run_qmd_query` function are the integration surface; adding a chromadb, meilisearch, or other adapter requires implementing one function with the same return shape.

QMD is the default because (a) it's local-first, (b) it does hybrid lex+vec out of the box, (c) it walks a directory tree of markdown without schema/migrations, and (d) the per-file output layout (ADR-002) maps cleanly onto its file-as-document model.

## Consequences

### Positive
- No new infrastructure to operate at v0.1.0 scale.
- Reversible: the `BackendConfig.type` field is the migration switch — implement a new adapter and swap.
- Hybrid lex+vec for free at this scale.

### Negative
- No custom re-ranking pipeline (e.g., HyDE-then-cross-encoder) without writing a new backend.
- Limited to backends that return file-path-based results we can parse for page numbers (see ADR-002).

### Neutral
- Couples v0.1.0 to QMD's subprocess interface. Future MCP-aware backend would replace `subprocess.run` with a tool call but keep the same return shape.

## Links

- README — Quickstart section
- ADR-002 (page-level granularity) — relies on the file-as-document model assumed here.
- ADR-005 (no new services) — the deployment-shape consequence of this decision.
