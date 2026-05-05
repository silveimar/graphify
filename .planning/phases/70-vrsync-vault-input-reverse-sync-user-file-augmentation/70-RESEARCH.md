# Phase 70: VRSYNC — Vault → Input Reverse-Sync & User-File Augmentation - Research

**Researched:** 2026-05-05
**Domain:** Markdown reverse-sync + frontmatter augmentation for vault-aware Obsidian integrations
**Confidence:** HIGH (codebase-internal — all primitives already exist, this is integration work, not greenfield)

## Summary

Phase 70 ships two tightly-coupled features on top of the Phase 69 vault-profile foundation:

1. **`graphify reverse-sync` CLI command** — copies new/changed markdown from `profile.vault_path` user folders back into `profile.input_path`, with three modes (`always_ask`/`never_copy`/`always_copy`), JSONL audit log at `.graphify/reverse-sync-log.jsonl`, an `auto_on_run` hook into `graphify run`/`update-vault`, and a `git add -p`-style per-file prompt (Y/n/d/A/Q) gated on TTY presence.
2. **User-file frontmatter augmentation** — graphify-side writes that touch user files (under `profile.user_only_folders`) are restricted to a strict additive frontmatter merge (allowlist: `tags`, `related_to`, `up`, `references`, `comments`, `analysis`, `type`, plus `community` only when `augment.allow_community: true`). Body content stays byte-identical (property test required by D-07 and Success Criterion 5).

**Primary recommendation:** Build a new `graphify/reverse_sync.py` module (mirrors single-purpose module convention: `cache.py`, `doctor.py`, `vault_promote.py`). Keep augmentation as a small new helper inside `vault_promote.py` since it lives on the same write-path the Phase 69 `_preflight_check_user_only_folders()` already gates — augmentation is the "yes, this user-namespace write is allowed, but only via this contract" branch of that gate. **Do not** introduce PyYAML or `python-frontmatter` on the read/write hot path: graphify already has hand-rolled frontmatter primitives (`profile._dump_frontmatter`, `merge._parse_frontmatter`, `merge._find_body_start`) that are the deliberate symmetric pair (D-23 in `merge.py` comments).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reverse-sync detection (vault → input change set) | `graphify/reverse_sync.py` (new) | `graphify/cache.py` (SHA256 helper) | Single-direction file walk + hash compare; matches `cache.py`/`detect.py` pure-function style |
| Per-file conflict prompt (Y/n/d/A/Q) | `graphify/reverse_sync.py` | `sys.stdin.isatty()` | TTY-gated UX kept in the sync module so it can be unit-tested with a mocked input function |
| JSONL append audit log | `graphify/reverse_sync.py` | `serve._append_annotation` pattern | Reuse the exact one-liner pattern (`open(path,"a") as f: f.write(json.dumps(record)+"\n")`) |
| Profile schema additions (`reverse_sync.*`, `augment.allow_*`) | `graphify/profile.py` | — | Add to `_DEFAULT_PROFILE`; `reverse_sync` and `augment` keys are already in `_VALID_TOP_LEVEL_KEYS` (Phase 70 placeholders) |
| User-file frontmatter augmentation merge | `graphify/vault_promote.py` (new helper) | `merge.py` primitives | Sits on the same write path the Phase 69 user-folder refusal gates; augmentation is the allowed branch |
| `auto_on_run` hook | `graphify/__main__.py:2936` (`run`) and `:3283` (`update-vault`) | — | Single early-stage call before the parent pipeline; warn-and-continue per D-11 |
| Doctor `=== Reverse-Sync ===` section | `graphify/doctor.py` | — | Mirror of Phase 69-04 `=== Legacy Artifacts ===` section pattern |

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VRSYNC-01 | New `graphify reverse-sync` command — modes (always_ask/never_copy/always_copy), `--yes`, JSONL log, `auto_on_run`, SHA256 detection via `cache.py` | All primitives present: `cache.py` SHA256 helper, `serve._append_annotation` JSONL pattern, Phase 69 `_preflight_check_user_only_folders` user-folder list, two-flag CLI precedent (`--migrate-legacy[-apply]`) |
| VPROF-03 (augmentation half) | Allowlist-only frontmatter merge into user files; body byte-identical | `merge.py` already has `_parse_frontmatter` + `_find_body_start` + `_apply_field_policy`(union/preserve/replace); reuse with a different policy table |

## Standard Stack

### Core (already in repo — no new deps)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `hashlib` | 3.10+ | SHA256 of file bytes for change detection | `cache.py:25` already uses it — reuse `file_hash()` directly [VERIFIED: graphify/cache.py:25-30] |
| Python stdlib `difflib.unified_diff` | 3.10+ | `[d]` prompt diff body (D-02) | No `rich` dep needed; CONTEXT.md "Claude's Discretion" explicitly endorses stdlib here |
| Python stdlib `json` | 3.10+ | JSONL serialization | `serve._append_annotation` precedent [VERIFIED: graphify/serve.py:36-40] |
| Python stdlib `argparse` | 3.10+ | New `reverse-sync` subcommand | Phase 69-04 `--migrate-legacy[-apply]` precedent [VERIFIED: graphify/__main__.py:3319-3324] |
| Python stdlib `sys.stdin.isatty()` | 3.10+ | Non-TTY detection (D-13) | No precedent in `__main__.py` (no existing `input()` calls) — but isatty is the standard idiom |
| `graphify.cache.file_hash()` | internal | Reuse for `hash_before`/`hash_after` JSONL fields | Already SHA256s file body (skipping frontmatter for `.md` — see Pitfall 4 below) [VERIFIED: graphify/cache.py:11-17, 65-72] |
| `graphify.merge._parse_frontmatter` | internal | Read user-file frontmatter without PyYAML on hot path | Hand-rolled symmetric inverse of `_dump_frontmatter` per D-23 in `merge.py` [VERIFIED: graphify/merge.py:198] |
| `graphify.merge._find_body_start` | internal | Compute body byte index — critical for byte-identical body invariant (D-07) | [VERIFIED: graphify/merge.py:614-628] |
| `graphify.profile._dump_frontmatter` | internal | Re-emit frontmatter after augmentation | Preserves dict insertion order; symmetric with `_parse_frontmatter` [VERIFIED: graphify/profile.py:1753] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled `_parse_frontmatter` | `python-frontmatter` lib | Rejected — adds optional dep, breaks D-07 byte-identical guarantee (any third-party YAML loader normalizes whitespace/quotes), and contradicts merge.py:133 explicit comment "DO NOT introduce PyYAML on the read path" |
| `rich` for diff coloring | stdlib `difflib.unified_diff` | CONTEXT.md "Claude's Discretion" already calls this — stdlib is fine |
| Lockfile around JSONL append | bare `open(path, "a")` | Single-process CLI; serve.py uses bare append (line 38) — same trust model |

**Installation:** No new dependencies.

**Version verification:** No package version bumps required for Phase 70 (no new deps). `pyproject.toml` is unchanged. Skill stamp / manifest hash refresh applies only if a new milestone ships at end of v1.13.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────────────────────┐
   user CLI ──────► │ graphify reverse-sync                │
                    │ (or auto_on_run hook from run/uv)    │
                    └────────────────┬─────────────────────┘
                                     │
                                     ▼
              ┌──────────────────────────────────────────┐
              │ load_profile(vault_dir)                  │
              │  → reverse_sync.{mode,memory_path,       │
              │      auto_on_run}                        │
              │  → user_only_folders (Phase 69)          │
              │  → augment.allow_community               │
              └────────────────┬─────────────────────────┘
                               │
                               ▼
   vault_path  ──────► [scan user_only_folders, *.md, recursive]  (D-08, D-09)
                               │
                               ▼
                  ┌─────────────────────────────┐
                  │ pair (vault_rel, input_rel) │
                  │ hash_before, hash_after     │
                  │ via cache.file_hash()       │
                  └────────┬────────────────────┘
                           │
                ┌──────────┴──────────────────────────┐
                │ classify each pair:                 │
                │   new   = vault has, input missing  │
                │   update= both exist, hashes differ │
                │   skip  = hashes match              │
                │   vault_deleted = input has, vault  │
                │       missing (D-10 log only)       │
                └──────────┬──────────────────────────┘
                           │
                           ▼
            ┌──────────────────────────────────┐
            │ mode dispatch:                   │
            │  always_ask → prompt(Y/n/d/A/Q)  │
            │  always_copy → write             │
            │  never_copy → log only           │
            │  --yes → override always_ask     │
            │  non-TTY+always_ask → skip (D-13)│
            └────┬─────────────────────────────┘
                 │
                 ▼
       ┌─────────────────────────┐    ┌─────────────────────────────┐
       │ copy file into          │    │ append JSONL line:          │
       │ profile.input_path/     │───►│ {ts, vault_path, input_path,│
       │ <mirrored relpath>      │    │  action, diff_summary,      │
       │ (security.py confine)   │    │  hash_before, hash_after}   │
       └─────────────────────────┘    └─────────────────────────────┘

  ─── Augmentation half (orthogonal pipeline, runs inside update-vault) ───

   classify_nodes()
       │
       ▼
   _preflight_check_user_only_folders()  ← Phase 69 gate
       │
       ├── target NOT in user folders ──► normal write_note()
       │
       └── target IS in user folders   ──► augment_user_file_frontmatter()  (NEW Phase 70)
                                              │
                                              ├── _parse_frontmatter(existing_text)
                                              ├── apply allowlist merge
                                              │     • lists: union, preserve user order (D-04)
                                              │     • scalars: only-if-absent (D-05)
                                              │     • community: only if augment.allow_community
                                              ├── re-emit via _dump_frontmatter
                                              └── concatenate with body[_find_body_start:]
                                                  ── INVARIANT: body bytes unchanged (D-07)
```

### Recommended Project Structure

```
graphify/
├── reverse_sync.py    # NEW — change detection, prompt UX, JSONL log, mode dispatch
├── profile.py         # extend _DEFAULT_PROFILE.reverse_sync + .augment; add validators
├── vault_promote.py   # add augment_user_file_frontmatter() helper
├── doctor.py          # add reverse-sync pending-conflicts section
└── __main__.py        # register `reverse-sync` subcommand; auto_on_run hooks
tests/
├── test_reverse_sync.py    # NEW — unit + property tests for body-identity
├── test_vault_promote.py   # extend with augmentation merge tests
├── test_profile.py         # extend with v2.1 schema tests
├── test_doctor.py          # extend with reverse-sync section
└── test_cli_run.py         # extend with auto_on_run hook integration
```

### Pattern 1: New CLI subcommand registration

**What:** Add `elif cmd == "reverse-sync":` block to `__main__.py:main()` near `update-vault` (`:3283`).
**Example (mirrors Phase 69-04 `--migrate-legacy[-apply]`):**

```python
# Source: graphify/__main__.py:3296-3324 (Phase 69-04 precedent)
elif cmd == "reverse-sync":
    import argparse as _ap
    _p_rs = _ap.ArgumentParser(prog="graphify reverse-sync")
    _p_rs.add_argument("--vault", required=False, default=None)
    _p_rs.add_argument("--input", required=False, default=None,
                       help="Override profile.input_path")
    _p_rs.add_argument("--yes", action="store_true",
                       help="Override always_ask mode (does NOT override never_copy per D-12)")
    _p_rs.add_argument("--mode", choices=["always_ask", "always_copy", "never_copy"],
                       default=None, help="Override profile.reverse_sync.mode")
    opts = _p_rs.parse_args(sys.argv[2:])
    from graphify.reverse_sync import run_reverse_sync
    result = run_reverse_sync(
        vault_dir=Path(opts.vault) if opts.vault else Path.cwd(),
        input_dir_override=Path(opts.input) if opts.input else None,
        mode_override=opts.mode,
        yes=opts.yes,
    )
    _cli_exit(0 if not result["failed"] else 1)
```

### Pattern 2: Auto-on-run hook (warn-and-continue per D-11)

**What:** Early-stage call inside both `cmd == "run"` (`__main__.py:2936`) and `cmd == "update-vault"` (`:3283`) blocks, gated by `profile.reverse_sync.auto_on_run`.
**Where:** Right after `load_profile(vault_dir)` resolves, before `run_corpus()` / `update_vault()` is invoked.

```python
# Pseudocode for auto_on_run integration
_profile = load_profile(_vault_dir)
if _profile.get("reverse_sync", {}).get("auto_on_run", False):
    try:
        from graphify.reverse_sync import run_reverse_sync
        _rs_result = run_reverse_sync(_vault_dir, auto_on_run=True)
        if _rs_result.get("conflicts_skipped", 0):
            print(f"[graphify] reverse-sync: {_rs_result['conflicts_skipped']} "
                  f"conflicts skipped — run 'graphify reverse-sync' to resolve",
                  file=sys.stderr)
    except Exception as exc:
        # D-11: warn-and-continue, never block parent command
        print(f"[graphify] reverse-sync: skipped due to error: {exc}",
              file=sys.stderr)
# ...continue with normal run_corpus / update_vault
```

### Pattern 3: Augmentation merge (body-byte-identical guarantee)

```python
# Source: synthesizes graphify/merge.py:198 (_parse_frontmatter), :614 (_find_body_start),
#         graphify/profile.py:1753 (_dump_frontmatter)
def augment_user_file_frontmatter(
    target: Path,
    augmentations: dict,
    profile: dict,
) -> tuple[Path, list[str]]:
    """Merge allowlist frontmatter keys into a user file. Body bytes unchanged (D-07).

    Returns (path, changed_keys). Read-modify-write atomically via .tmp.
    """
    from graphify.merge import _parse_frontmatter, _find_body_start
    from graphify.profile import _dump_frontmatter

    text = target.read_text(encoding="utf-8")
    body_start = _find_body_start(text)
    body = text[body_start:]   # ← captured before any mutation; written back verbatim
    existing_fm = _parse_frontmatter(text) or {}

    allowlist_lists = {"tags", "related_to", "up", "references"}  # D-04
    allowlist_scalars = {"comments", "analysis", "type"}            # D-05
    if profile.get("augment", {}).get("allow_community", False):
        allowlist_scalars = allowlist_scalars | {"community"}      # D-16

    merged = dict(existing_fm)  # preserve user order
    changed: list[str] = []
    for key, new_value in augmentations.items():
        if key in allowlist_lists:
            cur = list(merged.get(key, []))
            additions = [v for v in new_value if v not in cur]
            if additions:
                merged[key] = cur + additions  # D-04: append at end, preserve order
                changed.append(key)
        elif key in allowlist_scalars:
            if key not in merged:
                merged[key] = new_value      # D-05: only-if-absent
                changed.append(key)
        # else: silently ignored — not in allowlist
    if not changed:
        return target, []

    new_fm = _dump_frontmatter(merged)
    new_text = new_fm + ("\n" if not body.startswith("\n") else "") + body
    # Atomic write
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, target)
    return target, changed
```

**INVARIANT (D-07):** `body == new_text[_find_body_start(new_text):]` byte-for-byte. The property test must verify this for arbitrarily-shaped bodies (random bytes, no-trailing-newline, BOM, CRLF, embedded `---` lines).

### Anti-Patterns to Avoid

- **Anti-pattern: PyYAML round-trip for user files.** `yaml.safe_load`/`yaml.dump` reformats whitespace, normalizes quotes, and reorders keys. **Don't.** Use the existing hand-rolled `_parse_frontmatter`/`_dump_frontmatter` pair. (`merge.py:133` comment is explicit about this.)
- **Anti-pattern: Wholesale file rewrite for augmentation.** Re-rendering the whole note via Phase 69's `write_note()` violates D-07 because it might re-render the body. Only the frontmatter block may change.
- **Anti-pattern: Calling `cache.file_hash(path)` for change detection.** `cache._body_content()` strips frontmatter for `.md` files (see `cache.py:11-17`) — that's the right semantic for the *extraction cache* (skip re-extracting when only frontmatter changed) but WRONG for reverse-sync, where a user editing frontmatter in the vault is a real change to mirror. **Use a dedicated raw-bytes SHA256 helper for reverse-sync** (one-liner `hashlib.sha256(path.read_bytes()).hexdigest()` — `vault_promote.py:641` already does exactly this).
- **Anti-pattern: Truncating/rotating the JSONL log inside graphify.** Per D-15, append-only, user-managed. Same trust model as `profile.yaml.bak`.
- **Anti-pattern: Using `--yes` to bypass `never_copy`.** Per D-12, orthogonal flags. Document in `--yes` help string.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frontmatter parse | New YAML parser | `merge._parse_frontmatter` | Already symmetric inverse of `_dump_frontmatter`, exhaustively tested in `test_merge.py` (145 tests) |
| Frontmatter emit | New emitter | `profile._dump_frontmatter` | Order-preserving, type-dispatched, used everywhere |
| File hashing | New SHA256 wrapper | `hashlib.sha256(path.read_bytes()).hexdigest()` (already in `vault_promote.py:641`) | Raw bytes — required for reverse-sync; do NOT use `cache.file_hash` (frontmatter-stripped) |
| JSONL append | New atomic-append helper | `serve._append_annotation` pattern (4 lines) | Bare `open(p,"a"); f.write(json.dumps(rec)+"\n")` — single-process CLI |
| Profile schema validation | New validator | Add to `validate_profile()` in `profile.py:765`, follow VPROF-02 pattern | Returns `list[str]` of errors (project convention) |
| Doctor section | New report renderer | Extend `DoctorReport` dataclass + add lines to `format_report` | Mirror Phase 69-04 legacy-artifacts section (`doctor.py:614-628`) |
| Two-flag CLI safety | New flag-pair pattern | Phase 69-04 `--migrate-legacy[-apply]` precedent | `__main__.py:3319-3324`, plus `--yes` orthogonal to `--mode` per D-12 |

**Key insight:** Phase 70 is almost entirely composition of existing primitives. The only genuinely new code is: (a) the prompt UX (Y/n/d/A/Q loop), (b) change-set computation, (c) JSONL log schema, (d) augmentation merge function. Everything else is wiring.

## Runtime State Inventory

This is **not** a rename/refactor phase — it's an additive feature phase. The only state graphify touches at runtime that's relevant:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `.graphify/reverse-sync-log.jsonl` (NEW; user-managed, append-only) | Create-on-first-write; no migration |
| Live service config | None — graphify is a CLI, no live services | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None — no version bump or new deps | None |

**Existing-vault interaction:** The phase consumes Phase 69's `profile.user_only_folders` list. Existing vaults that ran Phase 69's silent v1→v2 migrator continue to work. Profiles missing the `reverse_sync` or `augment` keys fall back to defaults from `_DEFAULT_PROFILE` via `_deep_merge` — **no separate v2→v2.1 migrator needed**, additions are pure additive defaults. (Confirmed by inspecting `profile.py:670` — `_deep_merge(_DEFAULT_PROFILE, resolved.composed)` already supplies missing keys.)

## Common Pitfalls

### Pitfall 1: `cache.file_hash()` strips frontmatter — wrong for reverse-sync
**What goes wrong:** A user adds `tags: [foo]` to a vault file's frontmatter. `cache.file_hash()` returns the same hash before/after (it strips frontmatter for `.md` per `cache.py:11-17`), so reverse-sync misses the change.
**Why it happens:** `file_hash` was designed for the extraction cache, where frontmatter changes shouldn't invalidate semantic extraction.
**How to avoid:** Use raw-bytes SHA256 for reverse-sync change detection. `vault_promote.py:641` already has the right pattern: `hashlib.sha256(path.read_bytes()).hexdigest()`. Document this in the new module's docstring.
**Warning signs:** Property tests catch this immediately — write a vault file, change only frontmatter, assert reverse-sync flags `update`.

### Pitfall 2: `_dump_frontmatter` does not emit a trailing newline
**What goes wrong:** `_dump_frontmatter` returns `"---\nkey: val\n---"` with NO trailing `\n`. Naive concat with body produces `"---\n...---body..."` corrupting the closing fence.
**Why it happens:** The dumper is a string emitter, not a file writer.
**How to avoid:** Always append `"\n"` between frontmatter block and body, BUT only if body doesn't start with `\n`. The augmentation example above does this conditionally. Guard with a unit test: round-trip a known-good file unchanged.
**Warning signs:** Body byte-identity property test fails on the first random input.

### Pitfall 3: BOM, CRLF, no-trailing-newline edge cases
**What goes wrong:** Vault files authored on Windows (CRLF), files with BOM, or files without final `\n` may break naive frontmatter detection (`text.startswith("---")` is BOM-sensitive).
**Why it happens:** Different editors / platforms.
**How to avoid:** (a) In the parser entry, optionally strip leading BOM (`﻿`). (b) Property test must include CRLF and no-trailing-newline cases. (c) When reading: `read_text(encoding="utf-8")` for parse, `read_bytes()` for hash — never confuse the two.
**Warning signs:** Hypothesis-style randomized property test produces a body with `\r\n` and the augmented file's body bytes differ.

### Pitfall 4: Profile validation silently falls back to `_DEFAULT_PROFILE`
**What goes wrong:** A typo in `reverse_sync.mode` (e.g., `mode: alway_ask`) yields a validation error, and `load_profile` returns `_DEFAULT_PROFILE` (line 663-668). Reverse-sync then runs with `mode={}` (default placeholder), masking the typo.
**Why it happens:** Project convention is fail-soft on profile errors with stderr `[graphify] profile error:` output.
**How to avoid:** Add explicit validation to `validate_profile()` for the new keys (mode in {ask,copy,never}, memory_path is a string, auto_on_run is bool, augment.* are bools). Follow Phase 69's pattern of returning errors as `list[str]`.
**Warning signs:** Test that injects a bad mode literal and asserts an error message is in `validate_profile(profile)` return.

### Pitfall 5: `auto_on_run` re-entrancy / infinite loop
**What goes wrong:** Reverse-sync writes into `input_path`, then `graphify run` re-extracts, then triggers `auto_on_run` again, etc.
**Why it happens:** The hook fires at start of `run`/`update-vault`, but reverse-sync mutates the input that those commands process.
**How to avoid:** The hook must be one-shot per command invocation. Pass a `from_auto_on_run=True` flag (or a process-local `_already_synced_this_run` guard) so reverse-sync itself does not retrigger. Cleanest: gate the auto-call inside `run`/`update-vault` BEFORE the pipeline; reverse-sync itself does NOT call `run`. So actually no re-entrancy — but document the invariant.
**Warning signs:** Recursive subprocess calls in test logs.

### Pitfall 6: Non-TTY environments under `always_ask` (D-13)
**What goes wrong:** CI runs `graphify run` with `auto_on_run: true` and mode `always_ask`. There's no TTY. If the prompt naively calls `input()`, it raises `EOFError` and crashes the parent command.
**Why it happens:** Subprocess pipelines, CI runners.
**How to avoid:** First check `sys.stdin.isatty() and sys.stdout.isatty()`. Per D-13, treat non-TTY as "skip conflicts" (log as `skipped_conflict`). Per D-11, the parent command continues with stderr summary.
**Warning signs:** Test that pipes stdin (`subprocess.run(..., stdin=subprocess.DEVNULL)`) and asserts no crash.

### Pitfall 7: Trailing-newline ambiguity in body capture
**What goes wrong:** `_find_body_start` returns the byte index *after* the closing `---\n`. If the body is empty (file is frontmatter-only), `body = ""`. Concatenating `_dump_frontmatter(...) + "" ` produces a file with no trailing newline (Obsidian tolerates this; some editors don't).
**Why it happens:** Edge case in body capture.
**How to avoid:** Decide explicitly: preserve the source file's trailing-newline state. If original `text` ended with `\n`, ensure the new file does too. Property test the round-trip.
**Warning signs:** `assert original_bytes == roundtrip_bytes` fails on empty-body inputs.

### Pitfall 8: Manifest-hash overwrite guard interaction
**What goes wrong:** Phase 69 preserved the manifest-hash overwrite guard at `vault_promote.py:702-732`. Augmentation modifies a user file but doesn't update the manifest. Next `update-vault` run sees the file's hash differ from manifest and refuses to write (treats it as user-modified — which is technically correct).
**Why it happens:** Augmentation is intentionally NOT manifest-tracked (graphify must not "own" user files).
**How to avoid:** This is actually correct behavior. Document explicitly: augmented user files are NOT added to the manifest; the next run will re-augment idempotently because of D-04/D-05 (lists union, scalars only-if-absent → no diff).
**Warning signs:** Test: augment a user file twice; second run produces zero changes.

## Code Examples

### JSONL append (verbatim from existing pattern)
```python
# Source: graphify/serve.py:36-40
def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

### diff_summary stats string (D-03)
```python
# Stdlib only — no diff body in log
import difflib
def diff_summary(a: bytes, b: bytes) -> str:
    a_lines = a.decode("utf-8", errors="replace").splitlines()
    b_lines = b.decode("utf-8", errors="replace").splitlines()
    diff = list(difflib.unified_diff(a_lines, b_lines, lineterm=""))
    plus_lines = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    minus_lines = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    return f"+{plus_lines} -{minus_lines} lines, +{max(0,len(b)-len(a))} -{max(0,len(a)-len(b))} bytes"
```

### Per-file prompt (Y/n/d/A/Q)
```python
# Source: synthesized; mirrors `git add -p` ergonomics (D-01)
def prompt_per_file(rel_path: str, vault_text: str, input_text: str) -> str:
    """Returns 'yes' | 'no' | 'all' | 'quit'. Calls itself on '[d]'."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return "skip"  # D-13
    while True:
        ans = input(f"[graphify] copy {rel_path}? [Y/n/d/A/Q] ").strip().lower()
        if ans in ("", "y", "yes"):
            return "yes"
        if ans in ("n", "no"):
            return "no"
        if ans in ("a", "all"):
            return "all"
        if ans in ("q", "quit"):
            return "quit"
        if ans in ("d", "diff"):
            for line in difflib.unified_diff(
                input_text.splitlines(keepends=True),
                vault_text.splitlines(keepends=True),
                fromfile=f"input/{rel_path}",
                tofile=f"vault/{rel_path}",
            ):
                sys.stdout.write(line)
            sys.stdout.write("\n")
            continue  # D-02: re-prompt
        # unknown → re-prompt
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded vault folder writes | Profile-driven `graphify_folder_mapping` | Phase 69 (v1.13) | Reverse-sync uses the same profile-resolved paths |
| Phase 69 placeholder `reverse_sync: {}` | Real schema (mode, memory_path, auto_on_run) | Phase 70 | Additive only; no migrator needed |
| `cache.file_hash` for everything | Distinguish: frontmatter-stripped (extraction) vs raw bytes (reverse-sync) | Phase 70 | New helper or inline `hashlib.sha256(path.read_bytes())` for sync |

**Deprecated/outdated:** None — Phase 70 doesn't deprecate anything.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Hypothesis is acceptable to add as a `tests/` dependency for the property test (D-07) | Test Strategy | LOW — alternative: hand-rolled randomized loop using `random` + `itertools`. Project has no current Hypothesis usage [VERIFIED: grep -l "@given" tests/ → empty]; planner should pick stdlib randomized loop unless user opts in to Hypothesis. |
| A2 | `_find_body_start` returns byte indices that round-trip perfectly via `text[body_start:]` for all inputs | Pitfall 3 | MEDIUM — function signature returns byte index but operates on `str`; mixing `str` and `bytes` indexing is the most likely source of corruption. Test thoroughly. |
| A3 | `_dump_frontmatter` round-trip via `_parse_frontmatter` is lossless for the allowlist key types | Pattern 3 | MEDIUM — graphify-authored frontmatter round-trips, but user-authored frontmatter may use shapes the parser doesn't handle (multi-line strings, nested mappings). Allowlist keys are scalars + flat lists only; should be safe. Verify with a fixture-based round-trip test. |
| A4 | Phase 69's `_preflight_check_user_only_folders` is the correct chokepoint for augmentation routing | Architectural Map | LOW — Phase 69 verification confirmed this is THE write chokepoint (`vault_promote.py:1091-1092`) [VERIFIED: 69-VERIFICATION.md key-link table]. |
| A5 | `auto_on_run` does not need a recursion guard | Pitfall 5 | LOW — reverse-sync does not invoke `run`/`update-vault`, so the call graph is one-way. Document the invariant. |

## Test Strategy (TDD-aligned — `tdd_mode: true`)

Per `.planning/config.json:36`, TDD mode is enabled. **Wave 0** (test scaffolding before implementation) must create:

| File | Purpose | Wave 0 Gap |
|------|---------|-----------|
| `tests/test_reverse_sync.py` | Unit tests for change detection, mode dispatch, JSONL log schema, prompt UX with mocked input | NEW — covers VRSYNC-01 success criteria 1-4 |
| `tests/test_reverse_sync_property.py` (or merged into above) | Property test: `body_after == body_before` byte-identical for randomized inputs | NEW — covers VPROF-03 augmentation half / Success Criterion 5 (D-07) |
| `tests/test_vault_promote.py` (extend) | New tests for `augment_user_file_frontmatter()` — allowlist enforcement, `community` gate, idempotent re-augment | EXTEND — covers VPROF-03 augmentation half / Success Criterion 6 |
| `tests/test_profile.py` (extend) | Tests for `reverse_sync.*` and `augment.*` schema validation; missing-key default fallback | EXTEND |
| `tests/test_doctor.py` (extend) | Test new `=== Reverse-Sync ===` section formatting | EXTEND |
| `tests/test_cli_run.py` or `tests/test_commands.py` (extend) | Integration test: `auto_on_run: true` triggers reverse-sync at start of `run` and `update-vault`; failure warns-and-continues (D-11) | EXTEND |
| `tests/fixtures/vault_with_user_folders/` | Dual-tree fixture: vault dir + input dir with overlapping markdown files in `Atlas/` user folder | NEW — needed for end-to-end tests |

**Existing test infrastructure used:**
- `tmp_path` pytest fixture (project convention — no FS side effects outside `tmp_path`).
- `monkeypatch` for `sys.stdin.isatty`, `sys.stdout.isatty`, and `builtins.input`.
- No third-party deps (`pytest` only — already on Python 3.10/3.12 CI matrix).

**Property test approach (D-07 / Success Criterion 5):**
1. **Recommended:** stdlib `random` + a hand-rolled generator producing markdown bodies (LF/CRLF mix, BOM/no-BOM, embedded `---` lines, trailing-newline variants, empty body, large body). Loop 100+ iterations. Project has no Hypothesis precedent — keep it dep-free per CLAUDE.md "No new required dependencies".
2. **Optional:** add `hypothesis` to optional `[dev]` extra in `pyproject.toml`. **Risk:** new dep; A1 above flags this for user confirmation.
3. **Invariant:** for all generated bodies B, augmenting a file with arbitrary allowlist keys produces a file whose `[_find_body_start(text):]` slice equals B byte-for-byte.

## Validation Architecture

> Per `.planning/config.json` `nyquist_validation: true`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project convention) |
| Config file | none — pytest auto-discovers `tests/` |
| Quick run command | `pytest tests/test_reverse_sync.py tests/test_vault_promote.py tests/test_profile.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| VRSYNC-01 §1 (SHA256 detection + copy by mode) | reverse-sync detects new/changed files; copies per mode | unit | `pytest tests/test_reverse_sync.py::test_detects_new_file -x` | NEW Wave 0 |
| VRSYNC-01 §2 (JSONL log schema) | each event appends one valid JSON line with all 7 keys | unit | `pytest tests/test_reverse_sync.py::test_jsonl_log_schema -x` | NEW Wave 0 |
| VRSYNC-01 §3 (`--yes`, `never_copy`, `always_copy`) | mode + flag matrix | unit | `pytest tests/test_reverse_sync.py -k 'mode or yes' -x` | NEW Wave 0 |
| VRSYNC-01 §4 (`auto_on_run` true/false) | hook fires (or doesn't) at start of `run`/`update-vault` | integration | `pytest tests/test_cli_run.py::test_auto_on_run_hook -x` | EXTEND Wave 0 |
| VPROF-03 §5 (body byte-identical) | property test: random body bytes round-trip | property | `pytest tests/test_reverse_sync.py::test_body_byte_identical_property -x` | NEW Wave 0 |
| VPROF-03 §6 (`community` gate) | `community` key written iff `augment.allow_community: true` | unit | `pytest tests/test_vault_promote.py::test_community_gate -x` | EXTEND Wave 0 |
| D-04/D-05 (allowlist merge semantics) | lists union+order-preserve; scalars only-if-absent | unit | `pytest tests/test_vault_promote.py -k augment -x` | EXTEND Wave 0 |
| D-08 (scan only `user_only_folders`) | reverse-sync ignores files outside the list | unit | `pytest tests/test_reverse_sync.py::test_scope_user_only_folders -x` | NEW Wave 0 |
| D-09 (markdown only, recursive) | non-`.md` files ignored; subdirs mirrored | unit | `pytest tests/test_reverse_sync.py::test_markdown_only_recursive -x` | NEW Wave 0 |
| D-10 (vault deletions logged not propagated) | input file remains; JSONL has `vault_deleted` event | unit | `pytest tests/test_reverse_sync.py::test_vault_deleted_logged -x` | NEW Wave 0 |
| D-11 (warn-and-continue under auto_on_run) | parent command exits 0 with stderr summary | integration | `pytest tests/test_cli_run.py::test_auto_on_run_warn_continue -x` | EXTEND Wave 0 |
| D-12 (`--yes` does not override `never_copy`) | `--yes` + `never_copy` still logs only | unit | `pytest tests/test_reverse_sync.py::test_yes_does_not_override_never_copy -x` | NEW Wave 0 |
| D-13 (non-TTY skips conflicts under always_ask) | piped stdin → `skipped_conflict` action | unit | `pytest tests/test_reverse_sync.py::test_non_tty_skips -x` | NEW Wave 0 |
| D-14 (every event logged) | `copied`, `skipped_*`, `vault_deleted` enum exhaustive | unit | `pytest tests/test_reverse_sync.py::test_action_enum_exhaustive -x` | NEW Wave 0 |
| D-16 (community gate default false) | default profile leaves `community` absent | unit | `pytest tests/test_profile.py::test_default_augment_allow_community_false -x` | EXTEND Wave 0 |
| Doctor `=== Reverse-Sync ===` section | section appears in `format_report` output | unit | `pytest tests/test_doctor.py -k reverse_sync -x` | EXTEND Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_reverse_sync.py tests/test_vault_promote.py tests/test_profile.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`. Note: `tests/test_migration.py::test_preview_expands_risky_action_rows` is a known-pre-existing failure (Phase 69 verification documented this) and does NOT block Phase 70.

### Wave 0 Gaps
- [ ] `tests/test_reverse_sync.py` — covers VRSYNC-01 §1-3, D-08..D-14
- [ ] `tests/fixtures/vault_with_user_folders/` — dual-tree fixture
- [ ] Extend `tests/test_vault_promote.py` — augmentation merge tests (D-04, D-05, D-16)
- [ ] Extend `tests/test_profile.py` — schema validation for `reverse_sync.*` and `augment.*`
- [ ] Extend `tests/test_doctor.py` — `=== Reverse-Sync ===` section
- [ ] Extend `tests/test_cli_run.py` (or add `tests/test_auto_on_run.py`) — hook integration

**Framework install:** none — pytest already in CI matrix.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | CLI tool, no auth surface |
| V3 Session Management | no | stateless |
| V4 Access Control | yes (filesystem) | All vault→input copies pass through `graphify/security.py` path-confinement (must validate target stays inside `profile.input_path` root) |
| V5 Input Validation | yes | Profile schema validation extended for `reverse_sync.*` and `augment.*`; user prompt input validated against the Y/n/d/A/Q allowlist; JSON serialization via stdlib `json.dumps` |
| V6 Cryptography | no (hashing only, not crypto) | SHA256 used as content fingerprint, not for security |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via vault file relpath (e.g., `../../etc/passwd.md`) | Tampering | Validate target path is inside `profile.input_path` after `Path.resolve()`; reuse the `_validate_target` pattern from `merge.py:629` (resolves both vault and target via `.resolve()` to handle macOS `/tmp` symlink) |
| Symlink escape from vault user folder | Tampering | `Path.resolve(strict=True)` on each candidate; refuse if outside vault_dir |
| JSONL injection via filename containing `\n` | Tampering | `json.dumps(record, ensure_ascii=False)` escapes `\n`; record values are paths/strings, not raw user-controlled text |
| YAML injection via augmented frontmatter values | Tampering | `safe_frontmatter_value()` already quotes/escapes (`profile.py`); never call PyYAML on the write path |
| Body content modification (D-07 violation) | Tampering | Property test enforces byte-identity; reviewer must catch any deviation |
| Race condition: vault file changes mid-copy | TOCTOU | Read once into memory, hash, write atomically via `.tmp` + `os.replace`; if hash changes between scan and write, log and skip (re-runs idempotent per D-06) |

## Sources

### Primary (HIGH confidence — all in-repo)
- `graphify/cache.py:11-72` — SHA256 hashing utility, frontmatter-stripping caveat
- `graphify/profile.py:69-197` — `_DEFAULT_PROFILE`, `_VALID_TOP_LEVEL_KEYS` (already includes `reverse_sync`, `augment` placeholders)
- `graphify/profile.py:571-635` — `migrate_profile_v1_to_v2` (.bak pattern, idempotent)
- `graphify/profile.py:1753-1789` — `_dump_frontmatter`
- `graphify/profile.py:765-820` — `validate_profile`
- `graphify/merge.py:133-272` — `_parse_frontmatter` and rationale (D-23)
- `graphify/merge.py:614-628` — `_find_body_start`
- `graphify/merge.py:629-660` — `_validate_target` (path safety pattern)
- `graphify/merge.py:702-755` — `_merge_frontmatter` policy ladder (replace/union/preserve) — pattern reusable
- `graphify/vault_promote.py:641` — raw-bytes SHA256 helper (correct primitive for reverse-sync)
- `graphify/vault_promote.py:702-733` — manifest-hash overwrite guard (Phase 69 preserved)
- `graphify/vault_promote.py:959+` — `_preflight_check_user_only_folders` chokepoint (Phase 69)
- `graphify/serve.py:36-40` — `_append_annotation` JSONL pattern
- `graphify/__main__.py:2936-3360` — `cmd == "run"` and `cmd == "update-vault"` dispatch + `--migrate-legacy[-apply]` precedent
- `graphify/doctor.py:147-628` — `DoctorReport` dataclass + `format_report` section pattern
- `.planning/phases/69-...69-VERIFICATION.md` — Phase 69 invariants verified
- `.planning/REQUIREMENTS.md` (lines 50-60) — VPROF-03, VRSYNC-01 verbatim
- `.planning/ROADMAP.md` (Phase 70 block) — 6 success criteria

### Secondary (MEDIUM)
- `pyproject.toml` — confirms no Hypothesis, no python-frontmatter; Python 3.10/3.12 matrix
- `.planning/config.json` — `tdd_mode: true`, `nyquist_validation: true`, `commit_docs: true`

### Tertiary (LOW)
- None. All findings codebase-internal and verified.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every primitive used is already in the codebase, line-numbered above
- Architecture: HIGH — fits the established pure-function module convention; auto_on_run hook placement verified at `__main__.py:2936` and `:3283`
- Pitfalls: HIGH — most pitfalls (P1 cache hash, P2 trailing newline, P8 manifest interaction) are derived directly from reading existing code
- Test strategy: MEDIUM — Hypothesis vs stdlib random for property test is an open choice (A1)

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days; codebase is internally stable, but Phase 69 was just merged so wait at least one milestone before treating any line numbers as immutable).
