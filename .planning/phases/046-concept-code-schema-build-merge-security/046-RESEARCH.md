# Phase 46 — Technical Research

## RESEARCH COMPLETE

### Questions for planning

1. **`validate.py`** today does not whitelist `relation`; Phase 46 adds **stderr warnings** for unknown relations without failing validation (**D-46.11**).
2. **`build.build()`** concatenates edges then **`build_from_json`**; duplicate undirected pairs overwrite silently — normalization must **merge attributes** before `add_edge` (**D-46.08**, **D-46.09**).
3. **Inverse pair** `implemented_by` ↔ `implements`: normalize to **`implements` oriented code → concept** using `file_type == "code"` (**D-46.01**, **D-46.02**).
4. **Hyperedges**: skill examples use `implement` / `participate_in` / `form` — maintain **separate allowed set** (**D-46.03**, **D-46.11**).
5. **`graph.json`**: existing **`tests/test_confidence.py`** covers `build_from_json` → `to_json` round-trip — extend for merged **`implements`** edges (**CCODE-02**).
6. **Security**: **`report.py`** renders raw `relation` into markdown — route through **`sanitize_label_md`** (**CCODE-05**).

## Validation Architecture

- **Dimension 1–7:** Covered by pytest unit tests (`tests/test_validate.py`, `tests/test_build.py` or new `tests/test_concept_code_edges.py`, `tests/test_confidence.py`).
- **Dimension 8 (Nyquist):** Every plan task maps to an automated command; no watch-mode-only verification.
- **Regression harness:** `pytest tests/ -q` after wave 2; targeted files after each task.

### Recommended test commands

- Quick: `pytest tests/test_validate.py tests/test_confidence.py tests/test_concept_code_edges.py -q`
- Full: `pytest tests/ -q`
