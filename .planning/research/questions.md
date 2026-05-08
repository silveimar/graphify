# Open Research Questions

## Q-2026-05-07-01 — Node-level content-fingerprint dedup necessity

**Question:** Does graphify's `_make_id()` need SHA-256 content-fingerprint dedup (label/description normalization → hash → unique-id collapse), or is the existing name-based dedup sufficient at current corpus scales?

**Origin:** OB1 comparison (2026-05-07), P2 item #4 in `.planning/notes/ob1-comparison-2026-05-07.md`. OB1 ships `recipes/content-fingerprint-dedup` for thoughts; graphify has analogous dedup only at file-cache level, not at node level.

**Why it matters:** When the same concept is described in a PDF + a tweet + a repo doc, current behavior produces 3 separate concept nodes with similar labels. This pollutes community detection (Leiden treats them as distinct) and inflates god-node ranking.

**What to measure before implementing:**
1. On a representative multi-source corpus, count concept nodes whose normalized labels collide. Threshold of concern: >5% near-duplicate rate.
2. Inspect a sample — are the "duplicates" actually the same concept, or legitimately distinct (e.g., `Transformer` the model vs `transformer` the electrical component)?
3. Check whether INFERRED `semantically_similar_to` edges already cover this case adequately.

**Decision criteria:** If duplicate rate >5% AND duplicates are mostly genuine collisions AND `semantically_similar_to` does not collapse them in clustering, ship fingerprint dedup. Otherwise defer.

**Status:** Resolved 2026-05-08 — see [.planning/phases/73-dedup/73-SPIKE.md](.planning/phases/73-dedup/73-SPIKE.md) (Phase 73 DEDUP spike: aggregate raw 18.78%, residual 18.78%, recommendation **Ship**).
