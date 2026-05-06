# Phase 66 — Discussion Log

**Date**: 2026-05-06
**Mode**: discuss (--chain)

## Areas selected
All four presented gray areas selected:
1. CLI surface & repo input
2. Repo namespace + signal thresholds
3. Manifest shape & location
4. GRAPH_REPORT Federation section format

## Q&A

### Area 1 — CLI surface & repo input
- **Q**: How should users specify peer repos to federate with?
  - Options: repeatable `--federate-with PATH` (rec) | `.graphify/federate.yaml` manifest | hybrid
  - **Selected**: repeatable `--federate-with PATH`
- **Q**: What artifact does each peer expose?
  - Options: existing `graphify-out/export.json` (rec) | new dedicated federation export | live re-extraction
  - **Selected**: existing `export.json`

### Area 2 — Repo namespace + signal thresholds
- **Q**: Value for `{repo}` in `{repo}::{id}`?
  - Options: directory basename (rec) | `PATH=ALIAS` syntax | derive from peer PROJECT.md/pyproject
  - **Selected**: directory basename; collision → hard error
- **Q**: Definition of 'shared neighborhood' for AND check?
  - Options: Jaccard ≥ 0.5 over 1-hop neighbor labels (rec) | absolute count ≥ N | Jaccard over namespaced ids
  - **Selected**: Jaccard ≥ 0.5 over 1-hop neighbor labels (case-folded)
- **Q**: Definition of 'source-path overlap'?
  - Options: ≥1 shared `source_file` basename (rec) | ≥2-segment shared suffix | shared extension only
  - **Selected**: ≥1 shared basename
- **Q**: Use of Phase 65 `confidence_score`?
  - Options: tiebreaker only (rec) | hard floor at 0.5 | not used
  - **Selected**: tiebreaker only when neighborhood Jaccard ties

### Area 3 — Manifest shape & location
- **Q**: Path & format?
  - Options: `graphify-out/federation-manifest.json` (rec) | YAML | append-only `.jsonl`
  - **Selected**: JSON via vault-aware artifacts dir; rewritten each run
- **Q**: Schema?
  - Options: full provenance (rec) | minimal
  - **Selected**: full provenance — merged_id, contributing[{repo, original_id, label, source_files}], signals{label_match, neighborhood_jaccard, shared_basenames}, optional tiebreaker_score

### Area 4 — GRAPH_REPORT Federation section
- **Q**: Render & placement?
  - Options: markdown table after Communities, omit on zero merges (rec) | bullet list per merge | always render with placeholder line
  - **Selected**: table after Communities / before Calibration; omitted entirely on zero merges

## Deferred ideas
- `--federate-with PATH=ALIAS` syntax (only needed when collisions occur in practice)
- Append-only `federation-history.jsonl` (Phase 67 CDRIFT scope)
- `.graphify/federate.yaml` declarative manifest
- Confidence_score hard floor (defer to tuning phase post-CCONF calibration data)
- Auto-derive repo label from PROJECT.md / pyproject
- Bullet/verbose Federation section rendering

## Claude's discretion (no question asked)
- Pipeline placement: `graphify/federate.py` called from `build.py` between `_normalize_concept_code_edges` and `cluster.py` (locked by CFED-04, no gray area).
- Canonical merged-id derivation: lexicographic min across namespaced contributing ids (deterministic, locked by CFED-02).
- Failure mode for missing peer `export.json`: hard fail with two-line stderr per Phase 64 contract.
- No new dependencies (stdlib `json` + existing `networkx`); aligns with CLAUDE.md.
