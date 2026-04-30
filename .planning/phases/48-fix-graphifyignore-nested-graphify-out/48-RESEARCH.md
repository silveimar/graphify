# Phase 48 — Research

**Question:** What do we need to know to plan `.graphifyignore` / nested `graphify-out` consolidation?

## Findings

### Duplicate ignore prompts

- **`detect._is_ignored`** matches paths under `root` against patterns from **`.graphifyignore`** (multi-file upward walk) plus **`resolved.exclude_globs`**. Nested output pruning and **`skipped["exclude-glob"]`** already use the combined pattern list.
- **`doctor._build_recommended_fixes`** appends the **`WOULD_SELF_INGEST`** fix unconditionally when **`would_self_ingest`** is true, via a synthetic sentinel. The fix text always suggests **`graphify-out/**`** in `.graphifyignore`, **without** checking whether an existing pattern already excludes the problematic destination paths.
- **Gap:** Operators can already declare `**/graphify-out/**` (or equivalent) and still see the same boilerplate fix — roadmap success criterion 1.

### Nested output sprawl

- **`_SELF_OUTPUT_DIRS`** and **`nested_output_dirname`** in **`corpus_prune`** centralize recognition of `graphify-out` / `graphify_out` directory names during walks.
- **`ResolvedOutput`** from **`resolve_output`** defines canonical **`artifacts_dir`** / **`notes_dir`**. Phase 48 must ensure **new** runs do not create additional nested trees under corpus subtrees when a canonical root is configured — audit **mkdir** / default path construction in **`__main__.py`**, export/pipeline helpers, and any code that assumes `cwd / "graphify-out"` without consulting **`resolved`**.

### Parity with Phase 45

- **`collect_files`** already threads **`resolved`** and **`build_prior_files`** (Phase 45). Any new “would this nested path be ignored?” helper should be callable from **detect**, **extract**, and **doctor** (D-45.08 family).

## Risks

- **False negatives:** Over-suppressing doctor hints could hide a real self-ingestion risk if ignore matching is looser than actual walk behavior — tests must use the **same** predicate as production.
- **False positives on fix hints:** Tight coupling to **`_is_ignored`** avoids drift.

## Recommendation

1. Introduce a small **shared predicate** (e.g. “nested graphify output under corpus is fully excluded by effective ignore globs for these paths”) built on **`_is_ignored`** + **`_load_graphifyignore`** + **`resolved.exclude_globs`**, used by **doctor** to **suppress** the **`WOULD_SELF_INGEST`** graphifyignore fix when redundant (**wave 01**).
2. Audit and fix **artifact root** creation so writes never initialize a **new** nested **`graphify-out/`** under scan roots when **`resolved.artifacts_dir`** points elsewhere; add **`tmp_path`** regression tests and a short doc note (**wave 02**).

## RESEARCH COMPLETE
