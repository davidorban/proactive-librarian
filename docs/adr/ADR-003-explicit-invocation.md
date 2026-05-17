# ADR-003: Invocation mode — explicit CLI for v0.1.0

- **Status**: proposed
- **Date**: 2026-05-17
- **Tags**: ux, invocation, scope

## Context

The Librarian could surface relevant research in two fundamentally different modes:

1. **Explicit** — the user runs `librarian query "<topic>"` when they want suggestions. CLI invocation.
2. **Ambient** — a background hook (editor plugin / shell integration / desktop watcher) detects when the user is drafting a deliverable, extracts the topic from the current paragraph, and surfaces suggestions unprompted.

Ambient is technically buildable but doubles the design surface (when to fire / when to suppress / how to format / how to avoid noise) and adds a constant background side-effect on editing.

## Decision

**v0.1.0 ships explicit-only.** Invocation is `librarian query "<query>"` — a CLI that takes a string, returns the top results with citations, and exits.

Ambient mode is **deliberately deferred to a future release** as a separate decision, not built speculatively. A future ADR will revisit after v0.1.0 has accumulated usage data ("did the explicit invocation prove useful enough that ambient is worth the design cost?").

## Consequences

### Positive
- Minimal scope. v0.1.0 ships fast.
- No risk of unwanted background context injection that bloats prompts or surfaces irrelevant results.
- Usage is observable — each `librarian query` is a deliberate signal, useful for measuring whether ambient is worth building.
- The user retains full control over when retrieval happens.

### Negative
- Misses the "I didn't know to ask" use case. Some of the highest-leverage citation moments are when the user doesn't realise relevant research exists. Ambient mode would catch those.
- Friction: typing the query is non-zero cognitive overhead vs. background magic.

### Neutral
- Trivially reversible. Adding an ambient layer later is non-destructive — the CLI stays identical; the hook just becomes an additional caller of the same `run_query()` function.

## Links

- README — Quickstart shows the explicit invocation
- ADR-005 (no new services) — stack placement makes a future ambient layer trivial to add without changing v0.1.0 internals.
