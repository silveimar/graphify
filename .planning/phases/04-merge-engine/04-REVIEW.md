---
phase: 04-merge-engine
reviewed: 2026-04-11T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - graphify/__init__.py
  - graphify/merge.py
  - graphify/profile.py
  - graphify/templates.py
  - tests/fixtures/vaults/empty/.gitkeep
  - tests/fixtures/vaults/fingerprint_stripped/Atlas/Dots/Things/Transformer.md
  - tests/fixtures/vaults/malformed_sentinel/Atlas/Dots/Things/Transformer.md
  - tests/fixtures/vaults/preserve_fields_edited/Atlas/Dots/Things/Transformer.md
  - tests/fixtures/vaults/pristine_graphify/Atlas/Dots/Things/Transformer.md
  - tests/fixtures/vaults/unmanaged_collision/Atlas/Dots/Things/Transformer.md
  - tests/fixtures/vaults/user_extended/Atlas/Dots/Things/Transformer.md
  - tests/test_merge.py
  - tests/test_profile.py
  - tests/test_templates.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 4 introduces the merge engine (`graphify/merge.py`), extends the profile
module with `field_policies` support, and ships six vault fixtures plus a large
test matrix. The code is clean, well-documented, and defensively written: the
hand-rolled frontmatter reader is a faithful inverse of `_dump_frontmatter`,
the sentinel parser refuses to self-heal, path confinement is gated everywhere,
and the apply path uses fsync + atomic rename with stale `.tmp` cleanup.

No Critical issues. Four Warnings cluster around edge cases where
`_merge_body_blocks` silently no-ops on malformed-but-parseable user input,
and around an order/ownership inconsistency in `_insert_with_canonical_neighbor`.
Info items cover fragile regexes, a duplicated sentinel grammar, and minor
style nits.

Tests are thorough and pin the locked behaviors well (T-04-01 adversarial
labels, M1–M10 traceability, content-hash skip, atomic-write failure recovery).

## Warnings

### WR-01: `_merge_body_blocks` silently fails when sentinel lines carry prefix/suffix text

**File:** `graphify/merge.py:560-585`
**Issue:** `_parse_sentinel_blocks` uses `re.search` (not `match`), so a line
like `prefix <!-- graphify:connections:start -->` or `<!--   graphify:foo:start   -->`
(extra inner whitespace) is accepted as a valid start marker. The extracted
block content is the line range between markers, as expected.

`_merge_body_blocks`, however, reconstructs the "old" text it wants to replace
as a strict literal:
```python
old = f"{start}\n{existing_content}\n{end}"
result = result.replace(old, replacement, 1)
```
where `start`/`end` are the canonical-spelling literals. If the real on-disk
line contains anything other than exactly `<!-- graphify:{name}:start -->` on
its own line, `result.replace(old, replacement, 1)` silently matches nothing.
The function still appends `name` to `changed`, so the caller believes the
block was refreshed even though the body is byte-identical.

Downstream, `apply_merge_plan` will write a file where `changed_blocks` lies
about what happened. Content-hash skip will paper over this when only the body
drifted, but if the frontmatter also changed the user-edited sentinel line is
preserved untouched while the plan claims otherwise — a silent correctness gap.

Graphify-authored content always uses the canonical form, so users only hit
this if they edit the marker line by hand. Still worth fixing because the
regex and the replace are asymmetric.

**Fix:** Either (a) tighten the sentinel regex to `^<!-- graphify:...:(start|end) -->\s*$`
so only canonical lines are recognized as markers, or (b) teach
`_merge_body_blocks` to do block-level surgery using the line indices returned
by `_parse_sentinel_blocks` (make the parser return `(start_idx, end_idx)`
per block and splice by line range):
```python
# Return shape: dict[str, tuple[int, int, str]]  # (start_line, end_line, content)
# Then in _merge_body_blocks, splice by line indices instead of string replace.
```
At minimum, assert the replace actually changed the string before appending
to `changed` so a future regression is loud, not silent.

### WR-02: `_insert_with_canonical_neighbor` docstring/implementation mismatch on empty-neighbor fallback

**File:** `graphify/merge.py:476-502`
**Issue:** The docstring of `_merge_frontmatter` (line 514) says new keys
"slotted after their nearest preceding canonical neighbor... falling back to
append at end." The helper `_insert_with_canonical_neighbor` actually inserts
at the *beginning* when no preceding canonical neighbor is found in `target`:
```python
if neighbor is None:
    new_dict[key] = value
    for k, v in target.items():
        new_dict[k] = v
    return new_dict
```

This silently prepends graphify-emitted keys in front of user-authored keys
whenever the existing file has no preceding canonical key. E.g. target =
`{"rank": 5}`, new key = `source_file` → output = `{"source_file": ..., "rank": 5}`
rather than `{"rank": 5, "source_file": ...}`.

Either the docstring or the implementation is wrong. Insert-at-start is
defensible (canonical keys belong first), but the comment lies about it.

**Fix:** Update the docstring in `_merge_frontmatter` to match the code:
```python
# D-66 ordering rule: keys already in `existing` keep their position;
# keys in `new` but not in `existing` are slotted after their nearest
# preceding canonical neighbor from _CANONICAL_KEY_ORDER. If no preceding
# canonical neighbor is present in `existing`, the new key is *prepended*
# so graphify-owned canonical keys always lead user-authored content.
```
And add a test pinning the prepend behavior (none currently exists in
`tests/test_merge.py` — `test_compute_field_order_preserved_after_merge` only
exercises the neighbor-found branch).

### WR-03: `_validate_target` trusts `relative_to` without resolving absolute candidates

**File:** `graphify/merge.py:462-469`
**Issue:**
```python
def _validate_target(candidate: Path, vault_dir: Path) -> Path:
    rel = candidate if not candidate.is_absolute() else candidate.relative_to(vault_dir)
    return validate_vault_path(rel, vault_dir)
```

When `candidate` is absolute, the code takes `candidate.relative_to(vault_dir)`
without resolving `candidate` first. On platforms where `vault_dir` resolves
through a symlink (`/tmp` → `/private/tmp` on macOS) but the incoming action
path is not resolved, `relative_to` raises `ValueError` even for paths that
*are* inside the vault after resolution. The caller catches the `ValueError`
and records the path as `SKIP_CONFLICT` / `unmanaged_file` or as a `failed`
write — both silently wrong.

Related: `compute_merge_plan` calls `_validate_target(raw_target, vault_dir)`
where `raw_target = Path(rn["target_path"])`. The test suite always passes a
relative `target_path` so the bug is masked. An external caller passing an
already-resolved absolute path would trip into the absolute branch, where the
symlink mismatch bites.

**Fix:** Resolve absolute candidates before `relative_to`:
```python
def _validate_target(candidate: Path, vault_dir: Path) -> Path:
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            rel = resolved.relative_to(vault_dir)
        except ValueError as exc:
            raise ValueError(
                f"{candidate!r} escapes vault directory {vault_dir}"
            ) from exc
    else:
        rel = candidate
    return validate_vault_path(rel, vault_dir)
```
Add a regression test pinning macOS `/tmp` vs `/private/tmp` symlink parity.

### WR-04: `_parse_frontmatter` float regex is too narrow — loses precision on user-hand-edited scalars

**File:** `graphify/merge.py:136`
**Issue:**
```python
_FM_FLOAT_RE = re.compile(r"^-?\d+\.\d{2}$")  # _dump_frontmatter always uses {:.2f}
```

The regex hardcodes *exactly two* decimal digits because
`_dump_frontmatter` emits floats via `f"{v:.2f}"`. Correct for graphify-authored
files. But when a user hand-edits a fingerprinted file and writes
`cohesion: 0.5` (one decimal) or `cohesion: 0.123` (three decimals), the
regex does not match → the value falls through to the ISO-date branch (no
match) → finally returns the bare string `"0.5"`.

On the next run, `_merge_frontmatter` compares `current="0.5"` (string) against
`new=0.5` (float). Because `"0.5" != 0.5`, `cohesion` is reported as changed
every run, plus the downstream dump re-emits as `0.50`. The file churns on
every re-run instead of staying stable.

It is also inconsistent with Python's built-in float parser. Users writing
`cohesion: 1e10` or `cohesion: .5` will be silently downgraded to strings.

**Fix:** Loosen the regex to match any well-formed decimal literal (still
stricter than YAML to avoid swallowing bare-string keywords):
```python
_FM_FLOAT_RE = re.compile(
    r"^-?(\d+\.\d+|\d+\.\d+[eE][-+]?\d+|\.\d+)$"
)
```
Or call `float(stripped)` inside a `try` block after the int branch, catching
`ValueError` to fall through to string. That mirrors `_dump_frontmatter`'s
isinstance ladder more symmetrically.

Add a round-trip test asserting `_parse_frontmatter` returns a `float` for
`cohesion: 0.5` and that a re-dump is idempotent.

## Info

### IN-01: Duplicated sentinel grammar between `merge.py` and `templates.py`

**File:** `graphify/merge.py:239-240`, `graphify/templates.py:62-63`
**Issue:** The sentinel start/end literals are defined in both modules as a
deliberate choice ("merge.py has NO dependency on templates.py — module
isolation" per the comment at `merge.py:238`). That comment makes the tradeoff
explicit, but the duplicated grammar creates a drift risk: changing the spelling
in one file silently breaks the other.

`test_malicious_label_does_not_break_sentinel_pairing` covers the parser
contract but not the literal-equality constraint.

**Fix:** Add a single test that imports the constants from both modules and
asserts equality, so a future typo or format change is caught immediately:
```python
def test_sentinel_grammar_mirrors_templates():
    from graphify.merge import _SENTINEL_START_RE, _SENTINEL_END_RE
    from graphify.templates import _SENTINEL_START_FMT, _SENTINEL_END_FMT
    assert _SENTINEL_START_RE.match(_SENTINEL_START_FMT.format(name="foo"))
    assert _SENTINEL_END_RE.match(_SENTINEL_END_FMT.format(name="foo"))
```

### IN-02: `_find_body_start` uses substring match instead of line-anchored regex

**File:** `graphify/merge.py:447-459`
**Issue:** `_find_body_start` uses `text.find("\n---", 3)` to locate the
closing frontmatter delimiter. `_parse_frontmatter` uses the regex
`^---\s*$` (line-anchored). The two are inconsistent — a body line
`---some commentary` would be matched by `find` but not by the regex. For
graphify-authored files the issue is moot (dumper never emits such content),
but having two different notions of "closing delimiter" in one module is a
maintenance smell.

**Fix:** Parse the closing delimiter once and share the result:
```python
def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_text_or_empty, body_text)."""
    if not text.startswith("---\n"):
        return "", text
    m = re.search(r"\n---\s*\n", text)
    if m is None:
        return "", text
    return text[: m.end()], text[m.end():]
```
Then drive both `_parse_frontmatter` and `_synthesize_file_text` off the
shared split.

### IN-03: Late `import hashlib` / `import os` inside `merge.py` body

**File:** `graphify/merge.py:737-738`
**Issue:** `hashlib` and `os` are imported at line 737–738, mid-module, right
before their first use. Every other stdlib import in this file is at the top.
This breaks the "imports at top: stdlib, then third-party, then local" rule
from `CLAUDE.md` → "Import Organization".

**Fix:** Move `import hashlib` and `import os` to the top of the file alongside
`import datetime`, `import re`, etc. Same for the late
`from typing import TypedDict` on line 417 — hoist it to the top.

### IN-04: `_apply_field_policy`'s "unknown mode" branch is silently dead

**File:** `graphify/merge.py:386-388`
**Issue:**
```python
# Unknown mode — treat as preserve (conservative)
return current
```
Since `_resolve_field_policy` always returns one of `replace`/`preserve`/`union`
(the unknown-key fallback is `"preserve"`, not a literal bypass), this branch
is unreachable in practice. The comment "conservative" is fine defensive
coding, but there is no test covering it.

**Fix:** Either add a test that exercises `_apply_field_policy("k", None, 1,
mode="bogus")` to pin the defensive behavior, or convert the branch into an
`assert False, f"unknown policy mode {mode!r}"` to match D-69's "fail loudly"
philosophy. Silently preserving on unexpected input contradicts the rest of
the module.

### IN-05: `compute_merge_plan` re-parses body via `_parse_sentinel_blocks` twice for changed-diff detection

**File:** `graphify/merge.py:655-697`
**Issue:** In the UPDATE strategy branch, `compute_merge_plan` parses the
existing body sentinel blocks once (line 655), then parses the *new* body
sentinel blocks (line 693), then calls `_merge_body_blocks` which is a pure
dry-run. That is fine for purity, but `apply_merge_plan` then re-parses both
bodies a second time inside `_synthesize_file_text` (lines 812-814). For a
single-node merge this is two extra parses; for a large vault it is 2× the
sentinel work per file.

Not a correctness issue — purely redundancy — but flagged because the
CONTEXT note about "re-run cheapness" in the must_haves list suggests
performance is on the phase radar.

**Fix:** Cache the parsed blocks as an optional field on `MergeAction` (or
pass them through to `_synthesize_file_text` from `apply_merge_plan` via a
helper). Given the out-of-scope notice for v1 performance, this can stay
open as a tech-debt note.

### IN-06: `malformed_sentinel` fixture is named for the wrong failure mode it actually exercises

**File:** `tests/fixtures/vaults/malformed_sentinel/Atlas/Dots/Things/Transformer.md`
**Issue:** The fixture intentionally leaves the wayfinder block unclosed
(opens `graphify:wayfinder:start` at line 16, then opens
`graphify:connections:start` at line 22 without closing wayfinder). The parser
will raise `_MalformedSentinel("nested start ... while 'wayfinder' still open")`
— which is a "nested start", not a "malformed wayfinder". The conflict_kind
in the test is `"malformed_sentinel"` which is correct as a category, but the
fixture is not actually exercising the "orphan end marker" or "unclosed block
at EOF" paths. Both branches in `_parse_sentinel_blocks` (lines 298–299 and
314–315) are currently uncovered by any fixture.

**Fix:** Either (a) add two more fixtures — `malformed_sentinel_orphan_end`
and `malformed_sentinel_unclosed_eof` — to cover the remaining branches, or
(b) add focused unit tests against `_parse_sentinel_blocks` directly (the
test file already has `test_parse_sentinel_blocks_unpaired_start_raises_malformed`
and `test_parse_sentinel_blocks_unpaired_end_raises_malformed` at
`tests/test_merge.py:198-208`, so coverage of those two branches is already
present at the unit-test level; this is an informational note that the
fixture vault does not add coverage a pure unit test doesn't already give).

---

_Reviewed: 2026-04-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
