# ADR-009: Parent Document Retrieval

## Status

Accepted

## Context

L1 chunks improve retrieval precision, but a single 512-token child chunk can
omit important neighbouring instructions. Consultation mode needs more coherent
context without changing the default analysis retrieval contract.

## Decision

The indexer persists parent metadata on every child chunk:

- `parent_id` / `section_id`: stable source + section identifier.
- `parent_text`: concatenated text for all chunks in the same parent section.

`HybridRetriever` and `HybridChromaRetriever` keep `use_parent_context: false`
as the default. When the flag is enabled, retrieval still ranks L1 child
chunks with BM25 + dense + RRF, then collapses hits by `parent_id` and returns
bounded parent section text. `parent_context_max_chars` limits each returned
parent context so the LLM prompt cannot grow without bound.

The Streamlit consultation mode passes `use_parent_context=True`; stateless
analysis continues to receive regular child chunks.

## Consequences

This design keeps the Chroma collection layout simple and backward-compatible:
older indexes without `parent_text` still work, falling back to the child chunk
text. A full reindex is required to get complete L2 parent sections.
