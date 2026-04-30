# Phase 39 — Verification

**Phase:** 39-tacit-to-explicit-onboarding-elicitation  
**Requirements:** ELIC-01 — ELIC-07 (`.planning/REQUIREMENTS.md`)

## Goal

Guided elicitation produces validated extraction-shaped output, harness-aligned artifacts, path-safe writes, offline tests, and discovery-first documentation — all traceable to shipped plans **`39-01` … `39-05`**.

## Requirement coverage

| REQ-ID | Summary | Evidence |
|--------|---------|----------|
| **ELIC-01** | CLI + library parity; scripted backbone + gated deepening | `graphify elicit` (`graphify/__main__.py`); `graphify/elicit.py` (`run_scripted_elicitation`, etc.); `tests/test_main_flags.py`; **`39-04-SUMMARY.md`** |
| **ELIC-02** | Validated `nodes`/`edges`; merge ordering into `build()` | `tests/test_elicit.py` (`validate_extraction`, merge tests); `graphify/build.py`; sidecar merge — **also Phase 43** (`migration.py`, `watch.py`, **`43-VERIFICATION.md`**) for callers that invoke `build()` |
| **ELIC-03** | Harness SOUL/HEARTBEAT/USER shapes | `write_elicitation_harness_markdown`, `tests/test_elicit.py`; harness export suite **`tests/test_harness_export.py`**; **`39-03-SUMMARY.md`** |
| **ELIC-04** | Idempotent merge vs overwrite | `save_elicitation_sidecar` merge behavior; **`tests/test_elicit.py`** (`test_second_save_without_force_merges_by_id`); `docs/ELICITATION.md` / CLI `--help` |
| **ELIC-05** | Path confinement | **`tests/test_elicit.py`** (`test_save_rejects_path_escape`); `validate_graph_path` usage in **`graphify/elicit.py`** |
| **ELIC-06** | Offline tests | **`tests/test_elicit.py`** — no network; run under CI per **`39-UAT.md`** |
| **ELIC-07** | Discovery doc | **`docs/ELICITATION.md`**; README pointers; merge surfaces vs `run` clarified in **Phase 43** docs |

## Nyquist / validation notes

- Scripted UAT captured in **`39-UAT.md`** (status complete).
- Deep security matrix for elicitation-specific sinks: see phase **`39-PATTERNS.md`** and **`tests/test_elicit.py`**.

## Automated verification

Minimum elicitation gate:

```bash
pytest tests/test_elicit.py -q
```

Broader CLI + regression (as used in phase execution):

```bash
pytest tests/test_elicit.py tests/test_main_flags.py -q
pytest tests/ -q
```

**Last full-suite spot-check:** green at Phase 43 milestone (`1947+` passed; environment-dependent).

## Status

**passed** — acceptance criteria for ELIC-01–07 are satisfied by library, tests, and docs above; **ELIC-02** pipeline surfaces are explicitly completed for **`update-vault`** / **`watch`** in **Phase 43**.
