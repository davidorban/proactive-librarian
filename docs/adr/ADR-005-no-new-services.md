# ADR-005: Stack placement — a Python package + CLI, not a service

- **Status**: proposed
- **Date**: 2026-05-17
- **Tags**: architecture, deployment

## Context

The Librarian's logic could live in three places:

1. **A long-running service** — a daemon (or MCP server) exposing `search_research(query)`, `cite_passage(file, page)`, `ingest()` over a network protocol. Clean separation, callable by any client.
2. **A Python package with a CLI** — `librarian ingest` and `librarian query` invoked from a shell. Stateless; no background process; talks to the search backend only when called.
3. **A library only** — no CLI, no entry points; consumers import functions and call them. Most flexible, most friction for casual users.

A long-running service makes sense at multi-user / multi-client scale. At the v0.1.0 scope (one user, one machine, one search backend), the operational cost (lifecycle, logging, restarts, port management) buys nothing.

A library-only API misses the "quick query from a terminal while drafting" use case that is most of what the tool is for.

## Decision

**Python package with a `librarian` CLI entry point**, packaged via `pyproject.toml`. Users `pip install proactive-librarian` and get two commands: `librarian ingest` and `librarian query`. Power users can `import proactive_librarian` and call `run_ingest()` / `run_query()` directly.

No service, no daemon, no MCP server in v0.1.0.

## Consequences

### Positive
- Trivial to install (`pip install`) and run (no service to manage).
- Stateless invocation — no background process to monitor, restart, or fail mysteriously.
- Library API is the same surface the CLI uses; programmatic consumers get exactly the same behaviour.
- Easy to embed in a larger pipeline (cron, GitHub Actions, custom scripts) without service-discovery concerns.

### Negative
- Not directly callable by other MCP clients without a thin wrapper. Each invocation pays subprocess startup + config-load cost (negligible — sub-100ms).
- Doesn't scale to multi-user out of the box. That's a future-ADR problem if it ever matters.

### Neutral
- Reversible: a future MCP server (or HTTP service) can wrap the existing `run_query()` function without rework. The CLI stays the user-facing interface; the service becomes one more caller of the same API.

## Links

- README — Quickstart shows the CLI shape.
- `pyproject.toml` — `[project.scripts]` table wires the `librarian` entry point.
- ADR-003 (explicit invocation) — the v0.1.0 deployment model assumes user-initiated CLI calls, not background services.
