---
phase: 65
plan: 02
subsystem: cache, llm-scoring, confidence, evidence, prompts
tags: [cache, llm-scoring, confidence, evidence, prompts, graphify]
requires: [65-01]
provides:
  - graphify.prompts.PROMPT_VERSION
  - graphify.prompts.SCORING_PROMPT_TEMPLATE
  - graphify.cache.load_confidence
  - graphify.cache.save_confidence
  - graphify.cache._confidence_cache_key
  - graphify.cache.confidence_cache_dir
  - graphify.cache._sanitize_prompt_version
  - graphify.extract.score_concept_code_edges_for_file
  - graphify.extract._finalize_evidence
affects:
  - INFERRED concept↔code edges from _resolve_cross_file_imports now carry
    confidence_score + evidence
  - EXTRACTED baseline (Phase 53 D-53.10) preserved — uniform 1.0 only on EXTRACTED
  - Drift gate: every shipped graphify/skill*.md must reference PROMPT_VERSION
tech-stack:
  added: []
  patterns:
    - second cache namespace under graphify-out/cache/confidence/ (Q6)
    - sha256(prompt_version || NUL || model_id || NUL || file_hash) key composition
    - skill-orchestrated scoring hook (Q1) — no new Python deps (CLAUDE.md)
    - evidence sanitization via security.sanitize_label (control-char strip + len cap)
key-files:
  created:
    - graphify/prompts.py
    - tests/test_confidence_cache.py
    - tests/test_extract_confidence.py
    - tests/test_skill_prompt_drift.py
  modified:
    - graphify/cache.py
    - graphify/extract.py
    - graphify/skill.md
    - graphify/skill-aider.md
    - graphify/skill-claw.md
    - graphify/skill-codex.md
    - graphify/skill-copilot.md
    - graphify/skill-droid.md
    - graphify/skill-excalidraw.md
    - graphify/skill-opencode.md
    - graphify/skill-trae.md
    - graphify/skill-windows.md
decisions:
  - "Confidence cache uses file_hash(path, model_id='') so the supplied model_id participates ONLY through _confidence_cache_key — keeps AST cache namespace orthogonal (Pitfall #1)."
  - "Single INFERRED concept↔code emission site exists in extract.py today: the cross-class 'uses' edge in _resolve_cross_file_imports (line ~2285 post-insert). Scoring is applied after batch construction, before return — keeping the function pure and the edge dict shape stable."
  - "Drift-gate test enumerates Path('graphify').glob('skill*.md') rather than a hardcoded 7-file list, so every shipped skill file (10 today) is enforced. This is a stricter superset of the plan's 7-file requirement."
  - "Default scorer fallback returns (0.5, '') per edge so structural pipeline keeps working when the skill layer is absent. Real per-edge scoring is dispatched by graphify/skill*.md and persisted via save_confidence — no Anthropic SDK in Python (CLAUDE.md no-new-deps)."
metrics:
  duration: ~12m
  completed: 2026-05-06
---

# Phase 65 Plan 02: per-edge confidence scoring + cache split + prompt-version drift gate — Summary

One-liner: Replace the uniform `confidence_score: 1.0` baseline for INFERRED concept↔code edges with a skill-orchestrated per-edge scorer + sanitized evidence, persisted in a second cache namespace keyed on `sha256(prompt_version || model_id || file_hash)` so prompt/model bumps invalidate only confidence entries while the AST cache stays byte-untouched.

## What shipped

1. **`graphify/prompts.py`** (new, 19 lines) — `PROMPT_VERSION = "1.13.0"` plus `SCORING_PROMPT_TEMPLATE`. Module docstring documents the drift-gate contract.

2. **`graphify/cache.py`** — five new helpers added after `save_cached`:
   - `_sanitize_prompt_version(s)` — mirrors `_sanitize_model_id`, rejects `..`, `/`, `\`, empty, >512 chars.
   - `_confidence_cache_key(prompt_version, model_id, file_hash_str)` — sha256 over NUL-joined components.
   - `confidence_cache_dir(root)` — `graphify-out/cache/confidence/`.
   - `load_confidence(...)` / `save_confidence(...)` — atomic-write pattern mirroring `save_cached`. Critically uses `file_hash(path, model_id="")` so the AST cache namespace is untouched even when callers pass a non-empty `model_id` to the confidence side.

3. **`graphify/extract.py`** — three additions at module top:
   - Import `PROMPT_VERSION`, `sanitize_label`.
   - `_finalize_evidence(raw)`: `raw[:280]` → `sanitize_label(...)` (control-char strip + 256-char hard cap).
   - `score_concept_code_edges_for_file(path, edges)`: skill-orchestrated hook (Q1). Default no-op fallback returns `(0.5, "")` per edge.
   - At the end of `_resolve_cross_file_imports` (the only INFERRED concept↔code emission site in extract.py today), INFERRED edges are grouped per-file, scored via the hook in batches, clamped to `[0.0, 1.0]`, and stamped with sanitized evidence — **before** `return new_edges`.

4. **10 skill files** — appended a Phase 65 confidence-scoring section referencing `prompt_version 1.13.0` to every `graphify/skill*.md` file. The drift-gate test parametrizes over `glob("skill*.md")` so future-added skill files are automatically enforced.

5. **3 new test files (23 tests, all green)**:
   - `tests/test_confidence_cache.py` (7): prompt_version invalidation, model invalidation isolation, file-hash idempotence, AST-cache byte-untouched after confidence mutations, dir layout, traversal rejection, Windows-safe filenames.
   - `tests/test_extract_confidence.py` (5): no-uniform-one, score variance, evidence presence + 280-cap + control-char strip, EXTRACTED baseline preserved, default scorer shape contract.
   - `tests/test_skill_prompt_drift.py` (1 + N parametrized): every shipped `skill*.md` references `PROMPT_VERSION`.

## Commits

- `c8ff1ac` test(65-02): add failing tests for confidence cache + scored emission + skill drift gate (RED)
- `34442ad` feat(65-02): per-edge confidence scoring + cache split + prompt_version drift gate (GREEN)

## Verification

- `pytest tests/test_confidence_cache.py tests/test_extract_confidence.py tests/test_skill_prompt_drift.py -q` → 23 passed.
- `pytest tests/ -q` → 2312 passed, 1 xfailed, 1 unrelated pre-existing failure (`tests/test_migration.py::test_preview_expands_risky_action_rows`, present on `main` before Phase 65; logged in `deferred-items.md`, out-of-scope per executor instructions).
- AST cache regression: `tests/test_cache.py` fully green — confirms namespace isolation.
- Phase 53 invariant preserved: `graphify/build.py:_normalize_concept_code_edges` was NOT modified; existing `max(confidence_score)` merge already handles non-uniform input scores.
- Phase 64 stderr contract preserved: scorer's no-op fallback emits no output; no new prints introduced.
- No new dependencies: `pyproject.toml` untouched.

## Deviations from Plan

### [Rule 3 — Blocking] Plan line numbers for INFERRED sites were stale
The plan stated three INFERRED concept↔code sites at lines `596`, `1211–1231`, and `2252` in `extract.py`. On inspection, lines 596/1211/1221/1231 are all **EXTRACTED** structural emissions (Lua imports, Blade `@include`, livewire components, `wire:click` bindings) — the plan itself reaffirms this in the "Do NOT touch EXTRACTED concept↔code emission at line 596" note. The only INFERRED concept↔code emission in `extract.py` today is the Python cross-class `uses` edge in `_resolve_cross_file_imports` (line ~2252 in the original file, ~2285 after the new top-level imports). Scoring was applied to that single site, which is in line with the plan's intent ("only the INFERRED sibling gets scored"). All other concept↔code edges are produced by the LLM-orchestrated semantic-extraction step in `graphify/skill*.md`, not by `extract.py`.

### [Rule 3 — Blocking] Skill file roster differed from plan
The plan named 7 platform skill files including `skill-openclaw.md` and `skill-trae-cn.md`. The actual repo has 10 `skill*.md` files: the OpenClaw variant is named `skill-claw.md`, and there is no `skill-trae-cn.md` (Trae CN reuses `skill-trae.md` per `__main__.py:_PLATFORM_CONFIG`). The drift-gate test was widened to `Path("graphify").glob("skill*.md")` and the PROMPT_VERSION reference was appended to all 10 shipped files — a stricter superset of the plan requirement.

### [Process note] `_finalize_evidence` cap interaction
The plan specifies a 280-char evidence cap, while `security.sanitize_label` further caps at 256 chars (`_MAX_LABEL_LEN`). The implementation slices to 280 first then runs `sanitize_label`, so the effective cap on disk is min(280, 256) = 256. Tests assert `len(evidence) <= 280`, which is satisfied. If the project later needs a true 280-byte evidence channel, raise `_MAX_LABEL_LEN` or introduce a dedicated evidence sanitizer.

## Known Stubs

`score_concept_code_edges_for_file` returns `(0.5, "")` for every edge as the default no-op fallback. This is intentional per Q1 — the actual per-edge LLM scoring is dispatched by the skill orchestrator (`graphify/skill*.md` Step 3B). No Anthropic SDK is added to the Python package (CLAUDE.md "no new required deps"). The fallback shape is unit-tested; real scoring lands when the skill begins writing into `save_confidence(...)`.

## Threat Flags

None — all new file I/O is confined to `graphify-out/cache/confidence/` per `security.py` patterns. `_sanitize_prompt_version` rejects path-traversal payloads. Evidence strings pass through `sanitize_label` (control-char strip). No new network surface, auth path, or schema-boundary change.

## Self-Check: PASSED

- `graphify/prompts.py` exists with `PROMPT_VERSION = "1.13.0"`.
- `graphify/cache.py` exposes all 5 confidence helpers (verified by import in `tests/test_confidence_cache.py`).
- `graphify/extract.py` exposes `score_concept_code_edges_for_file` and `_finalize_evidence` at module scope (verified by import in `tests/test_extract_confidence.py`).
- All 10 `graphify/skill*.md` files contain `1.13.0`.
- Commits `c8ff1ac` and `34442ad` exist on `main`.
- All 23 new tests pass; full suite shows no new failures attributable to this plan.
