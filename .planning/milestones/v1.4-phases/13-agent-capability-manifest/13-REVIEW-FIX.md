---
phase: 13
phase_name: agent-capability-manifest
fix_scope: critical_warning
findings_in_scope: 9
fixed: 9
skipped: 0
iteration: 1
status: all_fixed
generated_at: 2026-04-20T17:17:56Z
review_path: .planning/phases/13-agent-capability-manifest/13-REVIEW.md
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-04-20T17:17:56Z
**Source review:** `.planning/phases/13-agent-capability-manifest/13-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (2 Critical + 7 Warning; Info skipped per `fix_scope=critical_warning`)
- Fixed: 9
- Skipped: 0

All Critical and Warning findings were fixed. Each fix is its own atomic
commit. Full pytest suite (1304 tests) is green after the last commit.

## Fixed Issues

### CR-01: PEM private-key detector matches only the header

**Files modified:** `graphify/harness_export.py`, `tests/test_harness_export.py`
**Commit:** `32e2702`
**Applied fix:** Extended `_PEM_PRIVATE_KEY` to match the entire PEM block
(BEGIN header + base64 body + END footer) using `re.DOTALL` and a
non-greedy `.*?` between the header and footer. Added regression test
`test_scanner_redacts_full_pem_private_key_body` that asserts both the
base64 body and the END footer are removed after redaction.

### CR-02: `_OPENAI_KEY` regex too broad

**Files modified:** `graphify/harness_export.py`, `tests/test_harness_export.py`
**Commit:** `4094c6d`
**Applied fix:** Replaced `sk-[A-Za-z0-9]{20,}` with
`\b(?:sk-proj-[A-Za-z0-9_-]{64,}|sk-[A-Za-z0-9]{48,})\b` so only the
documented OpenAI shapes match. Updated the existing positive test to
use a 48-char key and added two new tests:
`test_scanner_detects_openai_proj_key` (positive) and
`test_scanner_does_not_match_sk_learn_or_short_sk_tokens` (negative —
asserts `sk-learn-*`, short tokens, and 47-char near-misses are NOT
redacted).

### WR-01: AWS access-key pattern misses ASIA/AGPA/AIDA/AROA

**Files modified:** `graphify/harness_export.py`, `tests/test_harness_export.py`
**Commit:** `5c28173`
**Applied fix:** Extended `_AWS_KEY` to
`(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|AIPA)[0-9A-Z]{16}`. Added
`test_scanner_detects_aws_temporary_credentials` that asserts every
prefix in the documented set is redacted.

### WR-02: `validate_cli` bare `except Exception` collapses failure modes

**Files modified:** `graphify/capability.py`, `tests/test_capability.py`
**Commit:** `6eeb1d8`
**Applied fix:** Replaced bare `except Exception` with a narrowed catch:
`(json.JSONDecodeError, yaml.YAMLError, jsonschema.exceptions.ValidationError,
ImportError, FileNotFoundError, KeyError, TypeError, ValueError)`. Surface
`type(exc).__name__` in the error message so CI logs distinguish failure
modes. Added explicit `ImportError` early-exit branches for PyYAML and
jsonschema with the `pip install 'graphifyy[mcp]'` hint. New regression
test `test_validate_cli_narrows_exception_type_in_message`.

### WR-03: Path-confinement uses fragile `startswith`

**Files modified:** `graphify/harness_export.py`, `tests/test_harness_export.py`
**Commit:** `67c8585`
**Applied fix:** Replaced both `str(...).startswith(str(base))` guards
with `Path.resolve().relative_to(base)` (Python 3.10+, project already
requires it). Added `test_path_guard_rejects_sibling_prefix_collision`
that asserts a sibling like `/tmp/outX/harness` passes the lexical guard
but fails the new semantic guard.

### WR-04: Drift-gate error lacks field-level diff

**Files modified:** `graphify/capability.py`, `tests/test_capability.py`
**Commit:** `6eeb1d8` (combined with WR-02 — same function)
**Applied fix:** When the committed and live hashes differ, the error
block now reports `graphify_version` and `tool_count` for both committed
and built manifests so operators can identify which field changed
without rebuilding locally. New regression test
`test_validate_cli_drift_message_includes_field_diff`.

### WR-05: `_neg_ts` builds Unicode-complement DESC sort keys

**Files modified:** `graphify/harness_export.py`
**Commit:** `0e6a2ba`
**Applied fix:** Replaced the `chr(0x10FFFF - ord(c))` per-character key
with Python's stable two-pass sort: ASC sort by `(from, to)` first, then
DESC sort by `ts`. Removed the now-unused `_neg_ts` helper. Round-trip
byte-equal fidelity test continues to pass with the new ordering,
confirming output stability for the fixture corpus.

### WR-06: `_load_sidecars` skips corrupt JSONL lines silently

**Files modified:** `graphify/harness_export.py`, `tests/test_harness_export.py`
**Commit:** `6da8ad4`
**Applied fix:** Added a `skipped_lines` counter inside the
`annotations.jsonl` loop and emit
`[graphify] warning: skipped N corrupt annotations.jsonl line(s); kept M`
once after the loop so a half-truncated sidecar is visible at a glance.
Per-line notices are retained for actionable debugging. New regression
test `test_load_sidecars_summary_when_corrupt_jsonl_lines`.

### WR-07: `extract_tool_examples` over-strips multi-line Examples

**Files modified:** `graphify/capability.py`, `tests/test_capability.py`
**Commit:** `9dabb3e`
**Applied fix:** Rewrote the grammar to (1) treat blank lines inside the
Examples block as entry-separators rather than block terminators,
(2) terminate only on a section header (`Args:`, `Returns:`, ...) or EOF,
and (3) run the collected block through `textwrap.dedent` so common
leading whitespace is stripped once but relative indentation inside each
entry is preserved. Updated the three affected existing tests to use
blank-line separators (the standard Numpy/Google docstring convention)
and added `test_extract_tool_examples_preserves_multiline_indentation`.
Verified the live manifest content hash is unchanged (no current tool
ships an Examples block).

---

**Verification summary:**
- Tier 1 (re-read): performed for every fix.
- Tier 2 (syntax + targeted tests): pytest exercised after every commit;
  47 capability + harness_export tests green.
- Full suite sanity check: `pytest tests/ -q` → 1304 passed.
- Manifest hash stability: `canonical_manifest_hash(build_manifest_dict())`
  matches committed `server.json._meta.manifest_content_hash`.

_Fixed: 2026-04-20T17:17:56Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
