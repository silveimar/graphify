# Phase 45 — Technical Research

**Phase:** Baselines & Detect Self-Ingestion  
**Date:** 2026-04-30  
**Question answered:** What must we know to implement CONTEXT decisions **D-45.01–D-45.09** safely?

## RESEARCH COMPLETE

### Current architecture (verified)

- **`detect()`** (`graphify/detect.py`): loads `.graphifyignore` via `_load_graphifyignore(root)`; builds `prior_files` **only when `resolved is not None`** from `_load_output_manifest(resolved.artifacts_dir)`; prunes dirs via `_is_nested_output`, `_is_ignored`, noise dirs; **`graphify-out/memory/`** second scan root preserved.
- **`collect_files()`** (`graphify/extract.py`): uses `_load_graphifyignore` + hidden-part skip + `rglob` or `os.walk`; **does not** apply `resolved`, nested-output pruning, or manifest skips → divergence vs **`detect()`** (D-45.08).
- **`run_corpus()`** (`graphify/pipeline.py`): derives code paths from **`detect()`** only — CLI path does not call **`collect_files`** for corpus dirs; parity still needed for **`extract -m`** / **`watch`** consistency and tests.
- **`_save_output_manifest`**: writes absolute paths in `files`; **`detect`** compares `str(p.resolve()) in prior_files` — D-45.03 “always skip manifest paths” is already shape-compatible once **`prior_files`** is populated from default **`graphify-out`** (D-45.02).
- **Doctor** (`graphify/doctor.py`): `_FIX_HINTS` suggests adding **`graphify-out/**`** to `.graphifyignore` — must align with improved matching / consolidated output (overlap with Phase 48; Phase 45 still fixes manifest + prompts coherence).

### Recommended implementation strategy

1. **Shared corpus pruning helper** (new module e.g. `graphify/corpus_prune.py` or private functions in `detect.py` imported by `extract.py`):
   - Single API to decide whether a **directory name** should be pruned during walk (noise, nested output basenames, ignore globs on child path).
   - Single API to compute **`prior_files`** from manifests: `(root, resolved) -> set[str]` where if **`resolved is None`** load **`root / "graphify-out" / output-manifest.json`** when present (D-45.02).
2. **Manifest skip telemetry**: after candidate loop, if `len(skipped["manifest"]) > 0`, **`print`** one stderr line: count + `graphify doctor` / `--dry-run` pointer (D-45.01); keep **`skipped`** dict populated for doctor preview.
3. **`.graphify/` profile section**: extend **`profile.yaml`** schema under a dedicated key (e.g. `corpus.dot_graphify:` with `include`, `exclude`, `discovered_paths`, `auto_track`) validated in **`profile.py`**; **`detect`** applies excludes before optional markdown inclusion; never classify **`profile.yaml`**, `*.yaml` config stubs list from CONTEXT as documents (D-45.04–05).
4. **Persistence (D-45.06)**: minimal viable — **`graphify doctor --apply-graphify-discovery`** or **`graphify run --sync-dot-graphify`** flag writes discovered eligible paths back to profile; optional **`auto_track: true`** for non-interactive CI-disabled environments — exact UX left to planner tasks.

### Risks

- **Manifest staleness**: D-45.03 strong skip may hide user files renamed into old output folders — document in **`docs/`** or doctor output.
- **Circular imports**: `extract` importing from `detect` — prefer **`corpus_prune`** thin module importing only **`output.ResolvedOutput`** types behind **`TYPE_CHECKING`** if needed.

---

## Validation Architecture

**Nyquist-aligned verification for this phase:**

| Dimension | How Phase 45 validates |
|-----------|-------------------------|
| **1 Coverage** | Every HYG-01..03 + CONTEXT D-45.xx mapped to a plan `requirements` / `must_haves`. |
| **2 Automation** | pytest: `tests/test_detect.py`, `tests/test_extract.py`, new fixture vault tests; no network. |
| **3 Regression** | Golden mini-vault fixture + manifest JSON samples under `tests/fixtures/`. |
| **4 Security** | Path resolution stays under corpus root; manifest paths normalized; no raw YAML execution. |
| **5 Performance** | Skip lists capped (`_SKIP_CAP`); no extra full-tree walks beyond current `detect`. |
| **6 Docs** | CLAUDE.md or vault doc snippet for operators (manifest + `.graphify` ingestion). |
| **7 Traceability** | REQUIREMENTS.md rows updated if new REQ IDs added for expanded scope. |
| **8 Nyquist meta** | `45-VALIDATION.md` sampling table + Wave 0 note “existing pytest infra”. |
