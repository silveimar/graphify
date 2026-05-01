---
status: passed
phase: 45
phase_name: Baselines & Detect Self-Ingestion
verified: 2026-05-01
---

# Phase 45 — Verification

## Must-haves

| REQ / decision | Evidence |
|----------------|----------|
| **HYG-01** / D-45.01–D-45.03, D-45.08 | Shared **`corpus_prune`** + **`build_prior_files`** / **`dir_prune_reason`** wired in **`detect`** and **`extract.collect_files`** (`graphify/detect.py` L17–22, L490, L516; `graphify/extract.py` L14, L2892, L2926). Manifest skip telemetry: **`skipped["manifest"]`** branch prints one **`[graphify]`** stderr line (`graphify/detect.py` L594–597). |
| **HYG-01** / D-45.04–D-45.06 | **`corpus.dot_graphify`** schema + **`_dot_graphify_*`** in **`detect`**; CLI **`--dot-graphify-track`** / **`--apply-dot-graphify-track`** in **`__main__.py`** (`graphify/profile.py` L159+, `graphify/detect.py` L396+, `graphify/__main__.py` L2805+). |
| **HYG-02** / D-45.07 | **`tests/test_detect.py::test_detect_skips_dotfiles`** — see **Automated**. |
| **HYG-03** / D-45.08 | **`tests/test_extract.py::test_collect_files_from_dir`**, **`test_collect_files_skips_nested_graphify_out`** — see **Automated**. |

## Evidence details (grep anchors)

Representative lines (repo at **`f3343e6`**):

- `rg -n "build_prior_files|dir_prune_reason|corpus_prune" graphify/corpus_prune.py graphify/detect.py graphify/extract.py` → e.g. **`graphify/corpus_prune.py:99`**: `def build_prior_files(...)`; **`graphify/detect.py:490`**: `prior_files = build_prior_files(root, resolved)`.
- Manifest stderr path: **`graphify/detect.py:594–597`** — `if skipped["manifest"]:` … `print(..., file=sys.stderr)` including **`[graphify]`** and **`skipped`** count.
- Dot-graphify: **`graphify/profile.py:690`** — `corpus.dot_graphify must be a mapping`; **`graphify/__main__.py:2805`** — `--dot-graphify-track`.

## Automated

- **Focused slice:**  
  `pytest tests/test_detect.py::test_detect_skips_dotfiles tests/test_extract.py::test_collect_files_from_dir tests/test_extract.py::test_collect_files_skips_nested_graphify_out -q`  

  ```
  3 passed in 0.05s
  ```

- **Full gate:** `pytest tests/ -q` — **`1965 passed`**, **`1 xfailed`**, 8 warnings in **80.04s** (2026-05-01).

- **Commit:** `git rev-parse --short HEAD` → **`f3343e6`**.

## Gaps

**N/A** — full suite completed with exit code **0** (expected **xfail** count unchanged).

## human_verification

None (optional CLI smoke not required for HYG sign-off).
