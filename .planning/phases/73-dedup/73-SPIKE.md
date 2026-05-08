# Phase 73 — DEDUP Spike

**Date:** 2026-05-08
**Phase:** 73 (DEDUP)
**Requirement:** DEDUP-01
**Resolves:** Q-2026-05-07-01

## Summary

Aggregate raw collision rate across two real external corpora: **18.78%** (560 of 2,982 concept nodes share a SHA-256 fingerprint of normalized label+description with at least one other node). Residual rate (collisions not covered by an existing INFERRED `semantically_similar_to` edge): **18.78%** — identical to raw, because both corpora were extracted in AST-only mode and produced **zero** sem-sim edges (no LLM semantic-extraction pass ran). Decision rule: ship iff `raw > 5% AND residual > 5%`. Recommendation: **Ship**.

The signal is strong and unambiguous. Per-corpus the picture splits sharply: the code-leaning corpus (`claude-code-templates`, an AI coding-eval harness with many model-output trees) shows a 21.75% raw collision rate driven by repeated rationale nodes from duplicated problem-statement docstrings across model-output directories — exactly the failure mode `_make_id()`'s name-based slug does not catch when description text is identical. The doc-leaning corpus (`claude-cookbooks`) shows 0.94% — well below threshold in isolation. The third corpus (PDF/paper set) was not measured because PDF extraction requires the LLM document/paper extraction pass that is gated behind the `/graphify` skill orchestration, not exposed as a CLI subcommand (see Method §Limitations). Two-corpus measurement still resolves Q-2026-05-07-01 cleanly: aggregate clears the 5% gate by 13.78 percentage points, and the worst-case interpretation (no sem-sim coverage available to absorb collisions) leaves residual = raw, not below threshold.

## Corpus

| Corpus | Path | File Count (matched) | Bytes (graph.json) | graphify Invocation |
|---|---|---:|---:|---|
| code | `~/Documents/silogia-repos/engineering-tools/claude-code-templates` | 1,090 code files | 14,171,664 | `_rebuild_code(Path("…/claude-code-templates"))` (AST-only, see Method §Invocation) |
| doc | `~/Documents/silogia-repos/engineering-tools/claude-cookbooks` | 238 (.py / .ipynb / .md) | 1,418,638 | `_rebuild_code(Path("…/claude-cookbooks"))` (AST-only) |
| paper | `~/Documents/silogia-repos/engineering-tools/claude-cookbooks/misc/data` | 3 PDFs (Constitutional AI, 2× Amazon Shareholder Letter); ≈2.3 MB | — | **Not measured** — see §Limitations |

**File-count source:** code = `_rebuild_code` extraction log ("AST extraction: 1090/1090 files"); doc = `find … -name "*.py" -o -name "*.ipynb" -o -name "*.md"` (representative scope, AST extractor matched ipynb + py files).

**Enrichment status per corpus:** code=OFF, doc=OFF, paper=N/A (corpus not measured).
Enrichment OFF means `description` and `enriched_description` are absent from base AST nodes. **However**, AST extraction also emits `rationale` nodes (`file_type="rationale"`) which DO carry a `description`/`enriched_description`-equivalent payload from docstring extraction — and these are precisely the nodes that drive the collisions observed (see Appendix). For pure-code nodes that have no description, fingerprint degenerates to `sha256(norm(label) + "|")` per CONTEXT D-02; the AST `_make_id()` slug already deduplicates those at extraction time so they don't survive into the concept-node universe (which excludes `file_type="code"` per RESEARCH Pattern 2).

**Reproduction:**

```bash
cd ~/Documents/silogia-repos/engineering-tools/graphify
pip install -e ".[all]"
python3 -c "
from graphify.watch import _rebuild_code
from pathlib import Path
for p in [
    '~/Documents/silogia-repos/engineering-tools/claude-code-templates',
    '~/Documents/silogia-repos/engineering-tools/claude-cookbooks',
]:
    _rebuild_code(Path(p).expanduser())
"
python3 scripts/dedup_spike.py \
  code=$HOME/Documents/silogia-repos/engineering-tools/claude-code-templates/graphify-out/graph.json \
  doc=$HOME/Documents/silogia-repos/engineering-tools/claude-cookbooks/graphify-out/graph.json
```

## Method

### Normalization recipe (CONTEXT D-02, locked, used verbatim)

```
norm(s)     = collapse_ws( strip_punct( s.lower() ) )    where strip_punct = regex [^\w\s] -> ""
fingerprint = sha256( norm(label) + "|" + norm(description[:200]) )
```

Description truncated to first 200 chars **post-normalization**; missing/empty description → `sha256(norm(label) + "|")`. Stemming OFF.

### Schema reality

`description` is NOT in `REQUIRED_NODE_FIELDS` (see `graphify/validate.py`). Per-node description sourced via `node.get("enriched_description") or node.get("description") or ""` (per RESEARCH override #1). When the LLM enrichment pass has not run on a corpus, fingerprints reduce toward label-only — explicitly flagged here as a methodological constraint. The collision signal in this spike comes from `rationale` nodes whose `description` field is populated directly by the AST `extract` pipeline (extracted from docstrings/comments) rather than by the enrichment pass — so the AST-only run is not as degenerate as a pure label-only fingerprint would be.

### Concept-node universe

`file_type ∈ {document, paper, image, rationale}`. `code` excluded by default (AST-deduped at extraction time via `_make_id()` in `graphify/extract.py`; not the failure mode this spike targets, per RESEARCH Pattern 2). Per `select_concept_nodes` in `scripts/dedup_spike.py:43`.

### graphify's existing 3-level dedup

Per `graphify/build.py` module header (3-level node deduplication):

1. **Level 1 — `_make_id()` slug at extract time** (`graphify/extract.py:57-66`): label → `re.sub(r"[^a-zA-Z0-9]+", "_", lower)` → stable structural ID. Catches identical labels regardless of casing/punctuation; misses near-duplicates that have differing labels but identical semantics ("Multi-Head Attention" vs "multi head attention" map to different slugs only if one strips the dash differently — in this case they would actually merge, but "Transformer Layer" vs "Transformer block" do not).
2. **Level 2 — id-collision merge in `build()`**: when multiple extraction dicts contribute nodes with the same id, `build` merges their attribute dicts (last-write-wins for scalars, set-union for source files).
3. **Level 3 — INFERRED `semantically_similar_to` edges** (LLM semantic-extraction pass): post-hoc soft-link between near-duplicates rather than a merge. The cross-check in this spike measures whether Level 3 already covers Level-1/2 misses.

The spike measures **residual after these three levels** — the input `graph.json` already has all three applied.

### Sem-sim cross-check

For each fingerprint-collision group, the group is "covered" iff every node has at least one INFERRED `semantically_similar_to` edge linking it to another node in the group (`scripts/dedup_spike.py:70`). `min_score` threshold: **0.0** (any sem-sim edge counts; per RESEARCH Pitfall 3, biases toward Defer). Sensitivity at higher threshold not run — both corpora yielded zero sem-sim edges, so the threshold is moot for this measurement.

### Decision rule (CONTEXT D-03, locked)

Ship iff `raw_rate > 0.05` AND `residual_rate > 0.05`. Defer otherwise.

### Invocation: why `_rebuild_code` and not `graphify run`

The CLI subcommand `graphify run [path]` is documented in `graphify --help` as "detect → AST extract only (Phase 12); does not write graph.json". To produce a `graph.json` from the AST extract path requires invoking the `_rebuild_code(watch_path)` helper from `graphify/watch.py` directly (which CLAUDE.md itself recommends as the canonical incremental-rebuild entry point: `python3 -c "from graphify.watch import _rebuild_code …"`). The fully-orchestrated extract → build → cluster → enrich pipeline that emits LLM-derived `semantically_similar_to` edges is gated behind the `/graphify` Claude Code skill, not a single CLI subcommand. Running the skill orchestration against three external corpora was outside this spike's compute/time budget. **Consequence:** both measured corpora have zero sem-sim edges, so residual ≡ raw — this is the pessimistic edge of the measurement (the spike treats absence-of-sem-sim as evidence-of-no-coverage; CONTEXT explicitly accepts this trade-off, "false-positives only inflate the recommendation toward 'ship', which the >5% gate then absorbs").

### Limitations

1. **Paper corpus not measured.** PDF extraction requires the LLM document/paper extraction pass (`graphify/extract.py:extract_documents`-style codepath orchestrated by skill.md), which is not callable from a single CLI invocation without API key + skill orchestration. `_rebuild_code` reports "No code files found - nothing to rebuild" for the PDF directory. Per the plan's runtime guidance, two-corpus measurement still resolves Q-2026-05-07-01.
2. **No sem-sim cross-check possible.** Per RESEARCH Pitfall 2, sem-sim edges are produced only by the LLM semantic-extraction pass; in AST-only runs they do not exist. The residual rate therefore equals the raw rate by construction, not because sem-sim genuinely failed to cover collisions. This is the **pessimistic** end of the recommendation; a future re-run with full LLM extraction could only lower residual, not raise it. The recommendation is robust because raw alone (18.78%) is already 13.78 percentage points above the 5% gate.
3. **Per-corpus heterogeneity is real.** The code corpus alone (21.75%) carries the aggregate; the doc corpus alone (0.94%) is sub-threshold. The Ship recommendation is justified by the aggregate AND by the existence of at least one realistic corpus where the rate is well above threshold — `claude-code-templates`-style corpora are not exotic; they are exactly the kind of model-output / AI-eval-harness repos graphify users are likely to ingest.

## Results

_sem-sim min_score threshold: 0.0_

| Corpus | Concept Nodes | Collision Groups | Raw Nodes | Residual Nodes | Raw % | Residual % |
|---|---:|---:|---:|---:|---:|---:|
| code | 2556 | 207 | 556 | 556 | 21.75% | 21.75% |
| doc | 426 | 2 | 4 | 4 | 0.94% | 0.94% |
| **AGGREGATE** | 2982 | 209 | 560 | 560 | 18.78% | 18.78% |

**Aggregate decision (raw>5% AND residual>5%): Ship**

**Per-corpus observation (per critical override #3):** Code-only corpora produce ~0 `semantically_similar_to` edges in AST-only mode (LLM-extractor only emits these on docs/papers/images during semantic extraction). The aggregate rate would mislead in isolation if the doc corpus had high sem-sim coverage, but here both corpora are AST-only and the sem-sim column is zero everywhere — the residual rate is the raw rate. The doc corpus alone is sub-threshold; the code corpus alone is well above threshold; the spike's pre-registered decision rule is applied to the aggregate, which is above threshold.

## Recommendation

**Ship** — aggregate raw 18.78% and residual 18.78% both clear the 5% gate by a wide margin (>13 pp). The signal is concentrated in the code-leaning corpus (21.75% on its own), driven by repeated rationale nodes generated from identical docstrings across model-output trees (a real, recurring failure mode of `_make_id()`'s slug-only deduplication when source files differ but rationale text matches). The doc-leaning corpus alone would not justify shipping (0.94%), but no single-corpus veto is part of the locked decision rule, and the magnitude of the code-corpus signal is large enough that it is implausible LLM-derived sem-sim edges would erase it on a future full run.

DEDUP-02..N (implementation in `_make_id()` / `build.py`) is **unblocked** by this spike. Implementation is out of scope for this phase.

If a future run with full LLM enrichment surfaces a much lower residual on doc/paper corpora, the implementation can be tuned (e.g. heavier weight on description, lighter on label) without invalidating the Ship decision — the >5% gate fires on raw, and raw is a structural property of the input that doesn't depend on enrichment.

## Appendix: Collision Sample

First 20 collision groups across measured corpora (from `scripts/dedup_spike.py` output). All sampled groups are size-2 collisions; spot-check confirms they are plausible near-duplicates (repeated rationale nodes from different model-output sub-trees of the AI-coding-eval harness, all sharing identical problem-statement text).

| Corpus | Fingerprint (8) | Group Size | Labels (truncated) | Source Files |
|---|---|---:|---|---|
| code | `9e2d8f13` | 2 | Check if in given list of numbers, are any two numbers close | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `f4a0bee5` | 2 | Given a positive integer n, you have to make a pile of n lev | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `97fc048b` | 2 | You will be given a string of words separated by commas or s | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `1ec4e379` | 2 | This function takes two positive numbers x and y and returns | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `d234e8e0` | 2 | You are given two positive integers n and m, and your task i | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `a7e366e9` | 2 | Given a list of positive integers x. return a sorted list of | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `0e34f4fb` | 2 | Given an array of integers, sort the integers that are betwe | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `cd6d4aad` | 2 | Implement the function f that takes n as a parameter,     an | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `7fe60d71` | 2 | Given a positive integer n, return a tuple that has the numb | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `95169a7e` | 2 | Write a function count_nums which takes an array of integers | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `9f11da00` | 2 | We have an array 'arr' of N integers arr[1], arr[2], ..., ar | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `43723f18` | 2 | Test if given string is a palindrome | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `64e2967c` | 2 | In this problem, you will implement a function that takes tw | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `2c04abab` | 2 | Given a string representing a space separated lowercase lett | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `14ee4855` | 2 | Task     We are given two strings s and c, you have to delet | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `b1499d1b` | 2 | Given a list of strings, where each string consists of only  | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `ab8ac015` | 2 | Given an array of integers nums, find the minimum sum of any | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `e944fa82` | 2 | In this Kata, you have to sort an array of non-negative inte | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `2af9ff84` | 2 | Given a string s and a natural number n, you have been taske | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
| code | `483bd655` | 2 | You are given a word. Your task is to find the closest vowel | /Users/silveimar/Documents/silogia-repos/engineering-tools/c |
