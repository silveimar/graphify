# Phase 39 — Pattern map (new code → existing analogs)

| New area | Closest existing module(s) | Patterns to copy |
|----------|---------------------------|------------------|
| Elicitation library core | `graphify/harness_export.py` | Module docstring with scope/decisions; pure functions + small CLI shim in `__main__`; no skill imports from library code |
| State / session persistence | `graphify/seed.py`, `graphify/cache.py` | JSON under `graphify-out` (or resolved artifacts); atomic write (`tmp` + replace) where durability matters |
| Extraction merge | `graphify/build.py` | List concat + documented last-wins; comments explaining ordering; call `validate_extraction` before `build_from_json` |
| Schema validation | `graphify/validate.py` | Same node/edge required fields; return list of errors, don’t raise in validator |
| Output roots | `graphify/output.py`, `graphify/security.py` | `resolve_output()` for defaults; `validate_graph_path` for every user-influenced path |
| CLI wiring | `graphify/__main__.py` (`harness` branch) | Nested ArgumentParser; lazy `from graphify.X import Y` inside branch to keep `install` light |
| Tests | `tests/test_harness_export.py`, `tests/test_build.py` (if present) | `tmp_path` only; frozen clocks if timestamps; no network; copy fixtures pattern |
| Markdown / long-form docs | `docs/vault-adapter.md`, phase 36 docs | Actionable steps; link to requirements IDs (ELIC-*) |
| Skills | `graphify/skill.md`, `skill-codex.md`, … | Thin wrapper: “invoke `graphify elicit …`” / same argv — **no** duplicate interview copy (D-01) |

## File headers

- New Python files: `from __future__ import annotations` first line after optional module docstring; single-line module docstring describing phase + REQ ties.

## Test file naming

- Primary: `tests/test_elicit.py` (mirrors `test_harness_export.py` naming).
- If `build.py` merge grows large: add focused tests in `tests/test_build.py` only if file exists; else keep merge tests co-located in `test_elicit.py` with `build.build` imports.

## Security confinement checklist (executors)

- [ ] Every write path resolved under `ResolvedOutput.artifacts_dir` or validated `graphify-out` root.
- [ ] User text → `security` sanitizers before node `label` / file body.
- [ ] Sidecar read: reject paths outside artifacts dir; max file size consistent with existing JSON sidecar patterns.
