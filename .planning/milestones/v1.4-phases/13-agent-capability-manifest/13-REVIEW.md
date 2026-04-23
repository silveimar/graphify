---
phase: 13-agent-capability-manifest
status: issues_found
depth: standard
reviewer: gsd-code-reviewer
reviewed: 2026-04-17T22:45:00-06:00
files_reviewed: 22
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
---

# Phase 13: Code Review Report

**Reviewed:** 2026-04-17T22:45:00-06:00
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

Phase 13 (Agent Capability Manifest + SEED-002 harness export) delivers two tightly-scoped utility surfaces: (1) a deterministic MCP capability manifest with a CI drift gate and (2) a utilities-only harness exporter emitting SOUL/HEARTBEAT/USER markdown plus a round-trip fidelity manifest. The code is well-structured, carries strong inline comments tying implementation to REQ-IDs (MANIFEST-06..10, HARNESS-01..08), and uses safe patterns: atomic `.tmp + os.replace` writes, sorted-key canonical JSON for hashing, `string.Template.safe_substitute` (no Jinja2), and `frozenset` allow-lists.

D-73 boundary is intact: `graphify/harness_export.py` imports no skill / LLM modules; `graphify/watch.py` and `graphify/pipeline.py` contain no reference to `harness` or `export_claude_harness`. The manifest hook in `graphify/export.py:302-309` runs only inside `to_json()` (the graph-export success path) — not from a timer or file watcher.

However, the review surfaced **2 Critical**, **7 Warnings**, and **5 Info** findings concentrated in three areas:

1. The HARNESS-07 secret-scanner regex suite has two material gaps (PEM private-key detector that only matches the header and `_OPENAI_KEY` over-broad pattern with high false-positive risk).
2. `validate_cli()` silently swallows validation errors through a bare `except Exception` and collapses every failure mode to exit-code 1 — which is the correct envelope but erases the distinction between "server.json genuinely drifted" and "PyYAML not installed" in CI logs.
3. Path confinement in `export_claude_harness` depends on `str(...).startswith(str(base))`, a known-fragile pattern that misfires when one resolved path is a prefix of another sibling.

No auto-trigger vector was found. No skill or LLM imports were found inside `harness_export.py`. Invariants for determinism (sort keys, sorted visited, frozen clock seam) are correctly wired.

## Critical Issues

### CR-01: PEM private-key detector matches only the header, ignoring the actual key body

**File:** `graphify/harness_export.py:54`
**Issue:** `_PEM_PRIVATE_KEY = re.compile(r"-----BEGIN[ A-Z]+PRIVATE KEY-----")` matches the armor header only. In redaction mode this substitutes only the 29–34 byte header with `[REDACTED]` and leaves the entire base64 body (plus the `-----END ... PRIVATE KEY-----` footer) untouched in the annotation field. An annotation containing a full RSA private key will emit with the body 100% preserved and only the opening line redacted — a false sense of security for a critical pattern.

**Fix:**
```python
_PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN[ A-Z]+PRIVATE KEY-----"
    r".*?"
    r"-----END[ A-Z]+PRIVATE KEY-----",
    re.DOTALL,
)
```
Add a regression test that asserts the redacted string contains neither `-----END` nor any base64 characters from the original body.

### CR-02: `_OPENAI_KEY` pattern is dangerously broad and will redact legitimate tokens like `sk-learn-...`

**File:** `graphify/harness_export.py:53`
**Issue:** `_OPENAI_KEY = re.compile(r"sk-[A-Za-z0-9]{20,}")` matches any token starting with `sk-` followed by 20+ alphanumerics. Real OpenAI keys have fixed lengths (`sk-<48>`, `sk-proj-<64>`, `sk-ant-api03-...`) and legitimate unrelated identifiers frequently collide (`sk-learn-20240101abcdefghij`, package names, etc.). In `mode="error"`, this causes legitimate exports to fail with exit-code 3. In `mode="redact"`, it silently mangles unrelated content.

**Fix:** Tighten anchoring and require documented vendor prefixes:
```python
_OPENAI_KEY = re.compile(
    r"\b(?:sk-proj-[A-Za-z0-9_-]{64,}|sk-[A-Za-z0-9]{48,})\b"
)
```
Add tests for false-positive avoidance and real-key detection.

## Warnings

### WR-01: AWS access-key pattern drops common `ASIA` temporary-credential prefix

**File:** `graphify/harness_export.py:51`
**Issue:** `_AWS_KEY = re.compile(r"AKIA[0-9A-Z]{16}")` matches only long-term IAM access keys. AWS STS/SSO/role credentials use `ASIA`, `AGPA`, `AIDA`, etc. — prefixes now more common than `AKIA` in cloud-native workloads.

**Fix:**
```python
_AWS_KEY = re.compile(r"(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA|AIPA)[0-9A-Z]{16}")
```

### WR-02: `validate_cli` bare `except Exception` collapses all failure modes

**File:** `graphify/capability.py:221-226`
**Issue:** Catches missing PyYAML, corrupt `capability_tool_meta.yaml`, missing `jsonschema`, malformed `server.json` — all flattened into the same message. Violates CLAUDE.md § Error Handling.

**Fix:** Narrow the catch and surface the exception type:
```python
except (json.JSONDecodeError, yaml.YAMLError, ImportError,
        FileNotFoundError, KeyError, TypeError) as exc:
    lines.append(f"error: capability validate failed: {type(exc).__name__}: {exc}")
    ...
```

### WR-03: Path-confinement check uses `startswith(str(base))` — fragile prefix collision

**File:** `graphify/harness_export.py:587-590` and `646-649`
**Issue:** String-prefix comparison on paths: if `base = /tmp/out` and `validated_dir = /tmp/outX/harness`, the guard passes. The primary `validate_graph_path()` uses `Path.relative_to()` correctly, but the secondary guards are fragile.

**Fix:**
```python
try:
    validated_dir.resolve().relative_to(base)
except ValueError:
    raise ValueError(f"harness_dir {validated_dir} escaped base {base}")
```

### WR-04: MANIFEST-09 drift-gate error message lacks field-level diff for triage

**File:** `graphify/capability.py:212-220`
**Issue:** When live hash != committed hash, the error shows only the hashes. Operators cannot tell whether the drift is from `graphify_version` (env issue), `tool_count` (a new tool added), or `_meta.examples` (docstring change).

**Fix:** Include `graphify_version` and `tool_count` in the stderr block so the diff is legible.

### WR-05: `_neg_ts` builds DESC string sort keys instead of using Python's stable sort

**File:** `graphify/harness_export.py:370-381`
**Issue:** `chr(0x10FFFF - ord(c))` produces unreadable sort keys and can produce noncharacter codepoints that blow up JSON serialization on some platforms. Python's stable sort makes this trivial without the trick.

**Fix:** Two-pass stable sort:
```python
ranked = sorted(sanitized, key=lambda e: (e["from"], e["to"]))
ranked.sort(key=lambda e: e["ts"], reverse=True)
ranked = ranked[:limit]
```

### WR-06: `_load_sidecars` silently skips corrupt JSON lines with no summary

**File:** `graphify/harness_export.py:201-212, 224-230, 246-253`
**Issue:** Malformed lines are logged individually to stderr with `continue`, but no aggregate count is emitted. A half-truncated sidecar yields a quietly-partial harness.

**Fix:** Aggregate a `skipped_lines` counter and emit a single summary per sidecar.

### WR-07: `extract_tool_examples` over-strips multi-line `Examples:` blocks

**File:** `graphify/capability.py:38-77`
**Issue:** `.strip()` on each line collapses indentation, so multi-line code examples lose structure. Current usage is short single-line examples, but the schema is `_meta.examples: list[str]` with no length contract — future authors may add multi-line examples and silently lose structure.

**Fix:** Either use `textwrap.dedent()` + block-split to preserve multi-line, or document the single-line constraint in the capability.py docstring and add a test that asserts/warns on multi-line blocks.

## Info

### IN-01: `ANNOTATION_ALLOW_LIST` dict-comp relies on CPython 3.7+ insertion order for HARNESS-08

**File:** `graphify/harness_export.py:27-30, 279-287`
**Fix:** Add a one-line comment reaffirming the dependency:
```python
# Order preserved: CPython dict (3.7+) keeps insertion order, so two runs
# over identical input produce byte-equal filtered output (HARNESS-08).
```

### IN-02: `_email_credential` regex has false-positive risk on URL-like prose

**File:** `graphify/harness_export.py:57-59`
**Fix:** Add inline documentation about the high false-positive surface; callers should treat matches as advisory.

### IN-03: `build_manifest_dict` uses `except Exception` twice for optional-dep guards

**File:** `graphify/capability.py:143-146`, `graphify/mcp_tool_registry.py:257, 265`
**Fix:** Narrow to `(ImportError, AttributeError, TypeError)`.

### IN-04: `validate_cli` does not emit a helpful install hint when `jsonschema` / `PyYAML` are missing

**File:** `pyproject.toml:44`, `graphify/capability.py:179-185`
**Fix:** Add an explicit `ImportError` catch in `validate_cli` that points to `pip install 'graphifyy[mcp]'`.

### IN-05: "No auto-trigger" contract is not asserted by any test

**File:** `graphify/skill.md:1667`, `graphify/skill-codex.md:1344`
**Fix:** Add a grep-style test to `tests/test_harness_export.py`:
```python
def test_no_auto_trigger_from_pipeline_or_watch():
    """D-73: harness export must remain utilities-only."""
    for mod_name in ("graphify/pipeline.py", "graphify/watch.py", "graphify/export.py"):
        src = (Path(graphify.__file__).parent.parent / mod_name).read_text()
        assert "export_claude_harness" not in src
        assert "harness_export" not in src
```

---

**Scope notes:**
- **D-73 boundary**: verified clean — `watch.py` and `pipeline.py` contain zero references to `harness_export` or `export_claude_harness`.
- **Auto-trigger**: only auto-hook is `write_runtime_manifest()` in `graphify/export.py:302-309`, which runs only inside `to_json()` success path. This is intended MANIFEST-02 behaviour.
- **Determinism invariants**: manifest hash uses `sort_keys=True, separators=(",", ":"), ensure_ascii=False`; harness emission uses sorted visited, sorted degree ranking, and `_BLOCK_ORDER` tuple — correct for byte-equality when the clock seam is pinned.
- **Allow-list integrity**: `ANNOTATION_ALLOW_LIST` is a module-level `frozenset[str]` (immutable) and correctly applied in both the default path and the secret-scan path.
- **`_meta.examples` uniformity**: every tool carries the field — verified by `test_meta_examples_uniform_when_absent` and unconditional assignment on `graphify/capability.py:120`.

---

**Files reviewed:** 22

_Reviewed: 2026-04-17T22:45:00-06:00_
_Reviewer: gsd-code-reviewer_
_Depth: standard_
