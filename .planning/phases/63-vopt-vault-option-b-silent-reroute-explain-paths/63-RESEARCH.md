# Phase 63: VOPT — Vault Option B Silent Reroute & `--explain-paths` — Research

**Researched:** 2026-05-05
**Domain:** CLI path-resolution / vault detection / stderr breadcrumb contract
**Confidence:** HIGH (direct code inspection of locked surfaces)

<user_constraints>
## User Constraints (from 63-CONTEXT.md)

### Locked Decisions
- **D-01 — Breadcrumb format (VOPT-02):** Two-line `[graphify] info: / hint:` shape, mirroring the Phase 64 stderr contract. Exact wording:
  ```
  [graphify] info: vault CWD without .graphify/profile.yaml — Option B reroute active
    hint: outputs → <abs path>/.graphify-out/
  ```
  When a legacy `graphify-out/` is also present, append a third line:
  ```
    hint: legacy graphify-out/ detected — run `graphify doctor` to review
  ```
  Phase 64 (AUDIT-A) will need to extend its valid-prefix list from `error:` to `error: | info:` when locking the snapshot.
- **D-02 — Trigger precedence (VOPT-01):** Strict trigger. Option B fires **only** when ALL of: (1) CWD has `.obsidian/`, (2) CWD has no `.graphify/profile.yaml`, (3) no `--output`, (4) no `--obsidian-dir`. Any explicit path flag suppresses Option B and routes through the higher-precedence layers from 70.1's chain.
- **D-03 — `--explain-paths` (VOPT-03):** Plain-text key:value rows on **stdout**, exit 0, pipeline does **not** run. Fields: `cwd`, `vault`, `profile`, `resolved out`, `resolution` (one of `flag-output | flag-obsidian-dir | profile | option-b (silent reroute) | default`). JSON deferred.
- **D-04 — Legacy `graphify-out/`:** Detect-only (third hint line). No move, no delete, no migration.

### Claude's Discretion
- Whether to add `resolve_option_b()` as a new helper or extend `resolve_output()` with an Option B branch.
- Internal name of the new `ResolvedSource` literal (`"option-b"` is suggested by CONTEXT but not locked).
- Whether `--explain-paths` is parsed before or after the global `--vault` strip step.

### Deferred Ideas (OUT OF SCOPE)
- JSON output for `--explain-paths` (no `--json` flag this phase).
- Auto-migration of legacy `graphify-out/` (lives in `graphify doctor` / `update-vault --migrate-legacy`).
- Dot-prefix override (`--vault-out-dir-name`).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VOPT-01 | When CWD is an Obsidian vault but no `.graphify/profile.yaml` exists, output reroutes silently to a hidden `.graphify-out/` inside the vault. | New branch in `resolve_output()` (graphify/output.py:307) replacing today's `_refuse(...)` at line 313; new `ResolvedSource` value `"option-b"`; both `notes_dir` and `artifacts_dir` set to `<vault>/.graphify-out/` (NB: `<vault>/.graphify-out/obsidian/` for `notes_dir` to mirror legacy default shape). |
| VOPT-02 | Unconditional one-line `[graphify]` stderr breadcrumb (locked to two-line `info:`/`hint:` per D-01) on every Option B run. | Replace VAULT-08 single-line `vault detected at ...` print at output.py:332/409 with the two-line shape *only on the option-b branch*. Existing `_emit_vault_error()` helper (output.py:84) is the closest pattern but emits `error:`; a sibling `_emit_vault_info()` is the cleanest extension. |
| VOPT-03 | `graphify --explain-paths` flag dumps resolved paths + active profile and exits without running the pipeline. | New top-level subcommand-style flag intercepted in `main()` (graphify/__main__.py:1565) before any dispatch. Calls `resolve_execution_paths(Path.cwd(), ...)`, prints the 5-row table to stdout, `raise SystemExit(0)`. |
</phase_requirements>

## Summary

The path-resolution architecture is mature and unusually clean: a single `ResolvedOutput` namedtuple flows from one resolver (`resolve_output`/`resolve_execution_paths`) into every command's writer. Phase 63 slots cleanly into a *single existing decision point* — the `if not profile_yaml.exists(): raise _refuse(...)` branch at `graphify/output.py:312–315`. That refusal, today the only behavior when a vault has no profile, is exactly what Option B replaces.

There is **one significant landmine**: the `_check_vault_cwd_gate` helper in `graphify/__main__.py:1517` (VCWD-03) *also* refuses on the same condition (vault CWD + no profile + no override) and runs **before** `resolve_output()` reaches its own refusal. Phase 63 must change behavior in *both* places, or the gate fires first and Option B is unreachable. CONTEXT D-02 explicitly states that the absence of `--output` and `--obsidian-dir` should *trigger* Option B — but VCWD-03 currently treats that exact combination as a fatal refusal (exit code 2). This is the most important coordination point for the planner.

**Primary recommendation:** Add Option B as a new branch inside `resolve_output()` (replacing the `_refuse` at output.py:313), introduce `"option-b"` as a `ResolvedSource` literal, and downgrade `_check_vault_cwd_gate`'s VCWD-03 refusal to "n/a" when no `--output`/`--obsidian-dir` are set (the new resolver branch handles it). `--explain-paths` is a clean early-exit added in `main()` immediately after the global flag strip.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Option B trigger detection | `graphify/output.py` (resolver) | `graphify/__main__.py` (gate harmonization) | Single resolver owns the `--output > profile > --obsidian-dir > default` chain today; Option B is the new "between profile-missing and default" rung. |
| Two-line `info:`/`hint:` breadcrumb | `graphify/output.py` | — | Stderr emission for `source=` values already lives at `output.py:332` and `:409`; new branch follows same pattern. |
| `--explain-paths` flag parse + early exit | `graphify/__main__.py` `main()` | — | Mirrors the `--version` early-exit at `__main__.py:1571`; no pipeline imports needed. |
| Legacy `graphify-out/` detection | `graphify/output.py` (data) + `graphify/__main__.py` (display) | — | Pure filesystem check (`(vault / "graphify-out").is_dir()`) — can live with the breadcrumb emission. |
| Non-vault CWD (regression-safe) | `graphify/output.py:301–305` (default branch) | — | Untouched: `default_graphify_artifacts_dir()` and the no-vault `ResolvedOutput(source="default")` path remain byte-identical. |

## Code Context — Verified File:Line Map

### `graphify/output.py` (415 lines)

| Line | Symbol | Role |
|------|--------|------|
| 35–43 | `ResolvedSource` literal | Phase 63 must add `"option-b"` to this `Literal[...]` tuple. **[VERIFIED: read]** |
| 46–51 | `ResolvedOutput(NamedTuple)` | 6 fields: `vault_detected`, `vault_path`, `notes_dir`, `artifacts_dir`, `source`, `exclude_globs`. No schema change needed; `source="option-b"` reuses existing slot. |
| 53–66 | `default_graphify_artifacts_dir(target, *, resolved=None)` | **Must not change.** Branches on `resolved.source == "default"` → cwd-relative; else target-adjacent. Phase 63 must NOT add an `option-b` branch here — Option B sets `artifacts_dir` directly in the resolver and bypasses this helper. |
| 68–70 | `is_obsidian_vault(path)` | Strict CWD-only `.obsidian/` check. **Reusable** for `--explain-paths` and Option B trigger. |
| 84–101 | `_emit_vault_error(msg, hint, *, code=...)` | Two-line `error:`/`hint:` emitter. Phase 63 needs a sibling `_emit_vault_info(msg, hint, *, extra_hint=None)` — same shape, `info:` prefix, optional third line for legacy detection. |
| 287–415 | `resolve_output(cwd, *, cli_output=None)` | The dispatch. Today it has 5 explicit branches: cli_output+vault → cli-flag (line 296); cli_output+no-vault → cli-flag (327); no-vault default → "default" (301); vault no-profile → `_refuse` (313); vault+profile → mode dispatch (336+). **Phase 63 inserts a new branch between "vault, no profile" and the existing refuse:** if no `cli_output` *and* `--obsidian-dir` is not in play → Option B; else keep current refusal semantics. (NB: `resolve_output` itself doesn't see `--obsidian-dir` — that flag is parsed in `__main__.py`. See "D-02 routing" below.) |
| 312–315 | `_refuse(...)` for "no profile" | **The line that becomes Option B.** Today: hard exit 1. After: replaced with Option B branch when `--obsidian-dir` not set; preserved as `_refuse` when `--obsidian-dir` *is* set (D-02 strict trigger). |
| 332, 409 | VAULT-08 detection report (`vault detected at ...`) | Existing single-line `[graphify]` print pattern. The new `info:`/`hint:` shape is a *different* contract — Phase 63 emits **both** (or skips VAULT-08 on the option-b branch — planner choice; CONTEXT does not specify). Recommend: skip VAULT-08 on `source="option-b"`, emit only the new two-line shape. |

### `graphify/__main__.py` (3556 lines)

| Line | Symbol | Role |
|------|--------|------|
| 1502–1514 | `_resolve_cli_paths(cli_output, ...)` | Single-entry vault/output resolver used by run/--obsidian/elicit/import-harness/doctor. **Phase 63 sees no change here** — it just gets a new `resolved.source == "option-b"` value. |
| 1517–1561 | `_check_vault_cwd_gate(cmd, *, has_explicit_route, write_into_vault)` | **THE LANDMINE.** Lines 1554–1560: when CWD is vault, no profile, no explicit-route, no `--write-into-vault` → raises `_emit_vault_error(... refusing to write..., code=EXIT_VAULT_GATE=2)`. This fires *before* `resolve_output()` is called and currently makes Option B unreachable. **Phase 63 must downgrade this branch:** when `--obsidian-dir` and `--output` are absent, return `"n/a"` (or new `"option-b"`) instead of refusing — let the resolver handle it. The `has_explicit_route` parameter today only counts vault pins (`--vault`, `GRAPHIFY_VAULT`, `--vault-list`); it does NOT count `--obsidian-dir` or `--output`. The planner needs to thread one of those signals in. |
| 1565–1700 | `main()` entry / global flag strip / help | `--vault` and `--write-into-vault` global strip happens at 1566–1567; `--version` early-exit at 1571. **`--explain-paths` early-exit slots in immediately after, before the dispatch table.** No argparse — manual argv scan, matching existing style. |
| 1597–1598 | Help text precedence line | `"Output destination precedence: --output > profile > --obsidian-dir > default."` Phase 63 must update to `"--output > profile > --obsidian-dir > option-b (vault) > default"` and add a `--explain-paths` row. |
| 1807–1857 | `--obsidian` command argv parse | Manual loop parsing `--obsidian-dir`, `--output`, `--graph`, `--dry-run`, etc. Tracks `user_passed_obsidian_dir` (1820, 1843, 1845). **This `user_passed_obsidian_dir` flag is the signal that must reach the gate / resolver to suppress Option B per D-02.** Currently it's local to the `--obsidian` block. |
| 1869–1888 | Precedence chain (post-70.1) | Comments line 1869 read `"Precedence (D-08): --output > profile > --obsidian-dir > legacy default"`. **Phase 63 inserts Option B between `--obsidian-dir` and `legacy default`.** When `cli_output is None` and `not user_passed_obsidian_dir` and `resolved.source == "option-b"` → set `obsidian_dir = str(resolved.notes_dir)` (which is `<vault>/.graphify-out/obsidian` per VOPT-01 spec). |
| 1944 | `to_obsidian(G, communities, obsidian_dir, ...)` | Receives the resolved string path. **Already absolute** post-70.1 (line 1884 `Path(obsidian_dir).resolve()`). Option B's `<vault>/.graphify-out/...` is an absolute path → no re-resolution risk. ✓ |
| 2961–3010 | `run` subcommand argv parse | Same pattern as `--obsidian`: manual `--output` parse, calls `_resolve_cli_paths()`. Does **not** parse `--obsidian-dir` (run uses different output semantics). For `run`, Option B trigger is simpler: just `cli_output is None` + vault + no-profile. |
| 3050–3056 | `out_dir` selection in `run` | `default_graphify_artifacts_dir(target, resolved=resolved) if resolved.source == "default" else resolved.artifacts_dir`. **Phase 63: option-b path uses `resolved.artifacts_dir` directly** (since the resolver sets it to `<vault>/.graphify-out/`), so this branch correctly takes the `else` arm. ✓ |

### Argparse pattern detail (D-03 — where `--explain-paths` lands)

graphify uses **manual argv parsing** (no argparse for top-level dispatch). Per-subcommand argparse is constructed inline (e.g., line 2716 for `elicit`, 2882 for `import-harness`). **Recommendation for `--explain-paths`:** treat as a special pre-dispatch flag like `--version` (line 1571). Detect it in the global argv after vault-flag strip, before subcommand dispatch. This avoids attaching it to any subcommand's argparse.

```python
# Insertion point: graphify/__main__.py near line 1571, after _pop_global_write_into_vault
if "--explain-paths" in sys.argv:
    _print_explain_paths_table()  # new helper
    raise SystemExit(0)
```

`_print_explain_paths_table()` calls `resolve_execution_paths(Path.cwd(), cli_output=None, ...)` (silently — wrap in `contextlib.redirect_stderr(io.StringIO())` to suppress VAULT-08/info breadcrumbs, since `--explain-paths` is meant to be quiet introspection). Pattern already exists in `resolve_vault_for_parity()` at output.py:236.

## Vault Detection Pattern (verified)

Single canonical detection: `graphify.output.is_obsidian_vault(path) -> bool` returns `(path / ".obsidian").is_dir()`. Strict CWD-only — no parent walk. **Used by:** `resolve_execution_paths`, `_check_vault_cwd_gate`, `_ensure_vault_root`, `_list_vault_roots_from_list_file`, and the VAUX-01 parity helper. **Phase 63 reuses this directly** — no new vault-detection helper. **[VERIFIED: graphify/output.py:68]**

Profile detection is even simpler: `(cwd / ".graphify" / "profile.yaml").exists()` — used inline in 3 places (output.py:312, 318, __main__.py:1545). No helper exists; Phase 63 can inline the same check.

## `default_graphify_artifacts_dir()` Signature & Callers

```python
# graphify/output.py:53
def default_graphify_artifacts_dir(
    target: Path,
    *,
    resolved: ResolvedOutput | None = None,
) -> Path:
```

**Callers (verified via grep):**
- `graphify/__main__.py:3050–3053` (`run` cmd, `out_dir` selection)
- `graphify/pipeline.py:27–32` (`run_corpus`, when `out_dir is None`)

Both branch on `resolved.source == "default"`. **Phase 63 must verify Option B never reaches this helper** — i.e., the resolver must set `artifacts_dir` to `<vault>/.graphify-out/` so the `else` arm at __main__.py:3056 takes over and bypasses this helper. This is the "Non-vault CWDs continue to use `default_graphify_artifacts_dir()`" guarantee from Success Criterion #4.

## Skill-File Stderr Regex Parsers

**Searched all 9 skill variants** (`graphify/skill*.md`): claude, codex, opencode, claw, droid, trae, copilot, aider, windows. **No regex parsers** that consume the `[graphify]` stderr contract were found. The skill files contain `print(f'[graphify] ...')` *emissions* (e.g., `Clustered N files into M batches`) but not parsers. **[VERIFIED: grep -rn "info:\\|regex\\|re\\.match\\|GRAPHIFY_STDERR" graphify/skill*.md]**

**Implication for D-01 / Phase 64 contract:** there is no current skill-side parser to break. The Phase 64 AUDIT-A snapshot test is the *only* downstream consumer of the stderr prefix list. Phase 63 may emit `info:` freely now; Phase 64 will widen its regex from `^\[graphify\] error:` to `^\[graphify\] (error|info):` when it locks the snapshot.

## Existing Test Patterns (verified shape)

### `tests/test_output_path_matrix.py` (283 lines, added Phase 70.1)

- Pure unit tests with `tmp_path` only (no `monkeypatch.chdir`).
- Helper `_make_vault(tmp_path, name="uat70-vault")` creates `tmp_path/<name>/.obsidian/` + `.graphify/profile.yaml` with the canonical `output: {mode: vault-relative, path: .}` profile.
- Sentinel helper `_no_doubled_segment(notes_dir, vault_name)` guards against the 70.1 nested-vault bug. **Reusable for Option B regression.**
- Tests pass `cwd` directly to `resolve_output(cwd, cli_output=...)` — no chdir; this is the cleanest pattern for Phase 63 Option B tests too.

**Phase 63 slot-in tests (proposed pattern):**
```python
def test_option_b_vault_no_profile_reroutes_to_hidden(tmp_path, capsys):
    vault = tmp_path / "vault-no-profile"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    # NB: no .graphify/profile.yaml
    resolved = resolve_output(vault)
    assert resolved.source == "option-b"
    assert resolved.notes_dir == (vault / ".graphify-out" / "obsidian").resolve()
    assert resolved.artifacts_dir == (vault / ".graphify-out").resolve()
    err = capsys.readouterr().err
    assert "info: vault CWD without .graphify/profile.yaml" in err
    assert "outputs → " in err

def test_option_b_suppressed_by_cli_output(tmp_path):
    vault = ...; resolved = resolve_output(vault, cli_output=str(tmp_path / "out"))
    assert resolved.source == "cli-flag"  # Option B suppressed

def test_option_b_legacy_dir_emits_third_hint(tmp_path, capsys):
    vault = ...; (vault / "graphify-out").mkdir()
    resolve_output(vault); err = capsys.readouterr().err
    assert "legacy graphify-out/ detected" in err
```

### `tests/test_vault_cwd.py` (492 lines)

Subprocess-style tests using `_graphify(...)` helper; assert exit codes (`EXIT_VAULT_GATE = 2`). **Phase 63 must update these tests:** the existing "vault no-profile → exit 2" expectation must flip to "vault no-profile → exit 0 with Option B reroute." Search for assertions on `proc.returncode == 2` and on the literal string `"refusing to write into Obsidian vault"` — these will need adjustment.

### Routing-audit tests (Success Criterion #4)

`tests/test_routing_audit.py` (29 lines) tests `RoutingAudit.flush(out)` writing `routing.json` to a `tmp_path / "graphify-out"` dir under non-vault CWD. **Does NOT touch the resolver.** Phase 63 changes do not flow into this file. ✓

`tests/test_output.py:448–472` (`test_default_graphify_artifacts_dir_*`) tests the helper directly with `resolved.source="default"`. **Phase 63 must not change this helper's behavior** — these tests are the canary for non-vault regression.

## Common Pitfalls

### Pitfall 1: VCWD-03 gate masking Option B (the landmine)
**What goes wrong:** `_check_vault_cwd_gate` at `__main__.py:1554` raises `EXIT_VAULT_GATE=2` *before* `resolve_output()` is called. Without coordination, Option B never fires and tests still see exit 2.
**Why it happens:** VCWD-03 was added in Phase 62 specifically to refuse this exact condition. Phase 63 redefines the policy: silent reroute instead of refusal.
**How to avoid:** When changing `resolve_output()`, also change `_check_vault_cwd_gate` so the "vault + no profile + no explicit route + no write_into_vault" branch returns `"n/a"` (let resolver handle) when `--obsidian-dir`/`--output` are absent. Thread `user_passed_obsidian_dir` and `cli_output is not None` into `has_explicit_route` *or* add a new param `cli_path_override: bool` for clarity.
**Warning sign:** Tests for VCWD-03 refusal in `tests/test_vault_cwd.py` still passing after the resolver change → gate change was missed.

### Pitfall 2: VAULT-08 detection report duplicating the new info breadcrumb
**What goes wrong:** `resolve_output()` emits `[graphify] vault detected at ...` for every vault resolution (output.py:332, 409). On the option-b branch, this would emit *before* the new two-line breadcrumb, producing 3 stderr lines instead of 2 (or 4 with legacy detection).
**How to avoid:** On the new option-b branch, **do not** emit the VAULT-08 line — emit only the `info:`/`hint:` two-line shape. Or update Phase 64 contract to expect both. CONTEXT D-01 says "exactly one two-line breadcrumb" → suppress VAULT-08 on option-b. **[ASSUMED — CONTEXT does not literally say "suppress VAULT-08" but the count is unambiguous]**

### Pitfall 3: `--explain-paths` running with side-effecting resolver
**What goes wrong:** `resolve_execution_paths` emits stderr (VAULT-08, D-09 precedence, auto-adopt notice) and can `raise SystemExit(2)` on `--vault-list` failures. Calling it from `--explain-paths` would print resolution noise on stderr alongside the introspection table.
**How to avoid:** Wrap the call in `contextlib.redirect_stderr(io.StringIO())` and catch `SystemExit` to print a `resolution: error: <reason>` row instead. Pattern already exists in `resolve_vault_for_parity()` at output.py:236–264.

### Pitfall 4: 70.1 absolute-path fix bypass
**What goes wrong:** Plan 70.1-02 fixed nested-vault by resolving `obsidian_dir` to absolute (line 1884) before passing to `to_obsidian`. If Option B's path comes from `resolved.notes_dir` (already absolute via `.resolve()`) but flows through a different code path that doesn't re-check absoluteness, the bug could resurface.
**How to avoid:** Verify `resolved.notes_dir` for `source="option-b"` is constructed as `(vault_path / ".graphify-out" / "obsidian").resolve()` — explicit `.resolve()` in the resolver, not relying on later joins.

### Pitfall 5: `.graphify-out/` collision with `.graphify/profile.yaml`
**What goes wrong:** Both `.graphify` (existing convention) and `.graphify-out` (new) start with the same hyphen-less prefix. A naive `rglob(".graphify*")` or `.graphifyignore` rule could match both.
**How to avoid:** Audit `graphify/detect.py` and `graphify/security.py` for any prefix-matching patterns on `.graphify`. If `.graphifyignore` doesn't already include `.graphify-out/`, add it (Phase 63 writes to `.graphify-out/`, but the next graphify run from inside the vault would self-ingest its own outputs without an ignore rule). **[VERIFY in plan: grep `.graphify[/*]` in detect.py and security.py]**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vault detection | Custom `.obsidian/` walker | `is_obsidian_vault(path)` (output.py:68) | Already strict CWD-only, single source of truth |
| Two-line stderr emission | New `print(..., file=sys.stderr)` pair | Sibling helper `_emit_vault_info()` modeled on `_emit_vault_error()` (output.py:84) | Phase 64 will lock the contract; one helper = one regex |
| Path-resolution dispatch | New top-level resolver | Extend `resolve_output()` with `option-b` branch | Single resolver invariant from Phase 27/41 — `_resolve_cli_paths` is the only entry |
| `ResolvedOutput` extension | Subclass / new struct | Add `"option-b"` to `ResolvedSource` Literal (output.py:35) | NamedTuple already has slot for `source`; no schema change |
| Argparse for `--explain-paths` | argparse subparser | Manual argv check (mirror `--version` at __main__.py:1571) | Top-level flags are not argparsed in this CLI |

## Architecture Patterns

### System Architecture Diagram

```
sys.argv
   │
   ▼
main() ──── strip --vault/--vault-list/--write-into-vault (1566–1567)
   │
   ├── if "--version" → exit 0  [existing pattern at 1571]
   │
   ├── if "--explain-paths" → [NEW: Phase 63]
   │     → resolve_execution_paths(cwd, ...) [stderr suppressed]
   │     → print 5-row key:value table to stdout
   │     → exit 0
   │
   ▼
dispatch on sys.argv[1] ─→ "run" / "--obsidian" / "elicit" / ...
   │
   │  per-cmd argv parse: --output, --obsidian-dir, ...
   │  user_passed_obsidian_dir (bool), cli_output (str|None)
   │
   ▼
_check_vault_cwd_gate(...) ─[MODIFIED: Phase 63]
   │                          when vault + no-profile + no-cli_path-override
   │                          → return "n/a" (let resolver Option B run)
   ▼
_resolve_cli_paths(cli_output, ...) → resolve_execution_paths()
   │                                 → resolve_output(cwd, cli_output=...)
   │
   │   resolve_output branches:
   │     • cli_output set + vault    → source=cli-flag (296)
   │     • cli_output set + no-vault → source=cli-flag (327)
   │     • no-vault                  → source=default  (301)
   │     • vault + no-profile        → [NEW: Phase 63]
   │                                    if not user_passed_obsidian_dir:
   │                                      → source=option-b
   │                                      → notes_dir = <vault>/.graphify-out/obsidian
   │                                      → artifacts_dir = <vault>/.graphify-out
   │                                      → emit two-line info:/hint: breadcrumb
   │                                      → if (vault/graphify-out).is_dir(): emit 3rd hint
   │                                    else: keep current _refuse() (D-02 strict)
   │     • vault + profile           → mode dispatch (336+, unchanged)
   │
   ▼
ResolvedOutput → writer (to_obsidian / run_corpus)
```

### Recommended Project Structure (Phase 63 deltas)

```
graphify/
├── output.py        # +Option B branch in resolve_output, +_emit_vault_info helper, +"option-b" Literal
├── __main__.py      # +--explain-paths early-exit, +VCWD-03 gate downgrade, +help text update
└── (no new files)

tests/
├── test_output_path_matrix.py  # +5 Option B cases (trigger, suppression by --output / --obsidian-dir, breadcrumb shape, legacy hint)
├── test_vault_cwd.py            # ~3 expectation updates (exit 2 → exit 0 + reroute)
├── test_explain_paths.py        # NEW: 5–8 cases covering D-03 table format
└── test_output.py               # unchanged (regression canary)
```

### Pattern: Two-line stderr breadcrumb helper

```python
# graphify/output.py — new sibling of _emit_vault_error
def _emit_vault_info(msg: str, hint: str, *, extra_hint: str | None = None) -> None:
    """Emit [graphify] info: + hint: lines (+ optional 3rd hint) per Phase 63 D-01."""
    print(f"[graphify] info: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    if extra_hint is not None:
        print(f"  hint: {extra_hint}", file=sys.stderr)
```

### Pattern: Option B branch in resolve_output

```python
# graphify/output.py — replaces lines 312–315 (_refuse for missing profile)
profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
if not profile_yaml.exists():
    # Phase 63 Option B: silent reroute to <vault>/.graphify-out/ when no
    # explicit path flag was passed. Strict trigger per D-02 — caller signals
    # via cli_output (already None on this branch) and via NOT calling us
    # when --obsidian-dir was set (gate in __main__.py).
    notes_dir = (cwd_resolved / ".graphify-out" / "obsidian").resolve()
    artifacts_dir = (cwd_resolved / ".graphify-out").resolve()
    extra = None
    if (cwd_resolved / "graphify-out").is_dir():
        extra = "legacy graphify-out/ detected — run `graphify doctor` to review"
    _emit_vault_info(
        "vault CWD without .graphify/profile.yaml — Option B reroute active",
        f"outputs → {artifacts_dir}/",
        extra_hint=extra,
    )
    return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "option-b")
```

NB: The strict-trigger D-02 gating for `--obsidian-dir` cannot live in `resolve_output()` because that function has no view of `--obsidian-dir`. Two options for the planner:
1. **Add a parameter** `obsidian_dir_override: bool = False` to `resolve_output` / `resolve_execution_paths`; suppress Option B (`raise _refuse(...)`) when True. Touches `_resolve_cli_paths` signature too.
2. **Suppress at call site:** keep `_refuse` in resolver as-is when `cli_output is None and obsidian_dir_override`; have `__main__.py:1875` (the `elif user_passed_obsidian_dir:` arm) catch the SystemExit and proceed with the user's `--obsidian-dir`. **More fragile.**

Option 1 is cleaner and matches the existing `cli_output` parameter shape.

### Pattern: `--explain-paths` table

```python
# graphify/__main__.py — early-exit helper near main()
def _print_explain_paths_table() -> None:
    import contextlib, io
    from graphify.output import resolve_execution_paths
    cwd = Path.cwd().resolve()
    profile_path = cwd / ".graphify" / "profile.yaml"
    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            resolved = resolve_execution_paths(cwd)
        resolution_label = {
            "cli-flag": "flag-output",
            "profile": "profile",
            "option-b": "option-b (silent reroute)",
            "default": "default",
            "vault-cli": "profile",      # pin promotes to profile
            "vault-env": "profile",
            "vault-list": "profile",
        }[resolved.source]
        out = resolved.notes_dir
    except SystemExit:
        resolution_label = "error (see stderr)"
        out = "<unresolved>"
    print(f"cwd:           {cwd}")
    print(f"vault:         {'yes' if (cwd / '.obsidian').is_dir() else 'no'}  (.obsidian/ present)")
    print(f"profile:       {profile_path if profile_path.exists() else '<none>'}")
    print(f"resolved out:  {out}")
    print(f"resolution:    {resolution_label}")
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (Python 3.10+) |
| Config file | `pyproject.toml` (project section) — no separate pytest.ini |
| Quick run command | `pytest tests/test_output_path_matrix.py tests/test_explain_paths.py -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VOPT-01 | Vault no-profile reroutes to `<vault>/.graphify-out/` | unit | `pytest tests/test_output_path_matrix.py::test_option_b_vault_no_profile_reroutes_to_hidden -x` | ❌ Wave 0 (add to existing matrix file) |
| VOPT-01 | `--obsidian-dir` set → Option B suppressed | unit | `pytest tests/test_output_path_matrix.py::test_option_b_suppressed_by_obsidian_dir -x` | ❌ Wave 0 |
| VOPT-01 | `--output` set → Option B suppressed | unit | `pytest tests/test_output_path_matrix.py::test_option_b_suppressed_by_cli_output -x` | ❌ Wave 0 |
| VOPT-01 | Non-vault CWD unaffected (regression) | unit | `pytest tests/test_output.py::test_default_graphify_artifacts_dir_nonvault_uses_cwd_not_target_subdir -x` | ✅ exists |
| VOPT-02 | Two-line `info:`/`hint:` breadcrumb shape | unit (capsys) | `pytest tests/test_output_path_matrix.py::test_option_b_breadcrumb_shape -x` | ❌ Wave 0 |
| VOPT-02 | Third hint line when legacy `graphify-out/` present | unit | `pytest tests/test_output_path_matrix.py::test_option_b_legacy_dir_emits_third_hint -x` | ❌ Wave 0 |
| VOPT-03 | `--explain-paths` prints 5 rows, exit 0, no pipeline | integration (subprocess) | `pytest tests/test_explain_paths.py -x` | ❌ Wave 0 |
| VOPT-03 | `--explain-paths` reports `option-b` resolution label | unit | `pytest tests/test_explain_paths.py::test_explain_paths_reports_option_b -x` | ❌ Wave 0 |
| Cross | VCWD-03 refusal expectations updated | unit | `pytest tests/test_vault_cwd.py -k "no_profile" -x` | ✅ exists, needs updates |
| Cross | Routing-audit unaffected (Success #4) | unit | `pytest tests/test_routing_audit.py -x` | ✅ exists |

### Sampling Rate
- **Per task commit:** `pytest tests/test_output_path_matrix.py tests/test_explain_paths.py tests/test_vault_cwd.py tests/test_output.py -q`
- **Per wave merge:** `pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_explain_paths.py` — new file, covers VOPT-03 (table format, exit 0, no pipeline)
- [ ] Add 5–6 Option B cases to `tests/test_output_path_matrix.py` (file exists, just appending)
- [ ] Update assertions in `tests/test_vault_cwd.py` for the no-profile branch (was exit 2 refusal, now exit 0 + reroute)
- [ ] Verify `tests/test_routing_audit.py` still green (no changes expected)

## Project Constraints (from CLAUDE.md)

- Python 3.10+; CI tests on 3.10 and 3.12
- No new required dependencies (PyYAML already optional, used only by profile branch)
- Pure unit tests; `tmp_path` only; no fs side-effects elsewhere
- All file paths confined per `graphify/security.py` rules — `<vault>/.graphify-out/` lives inside the vault, satisfying confinement (vault root replaces the typical `graphify-out/` confinement target)
- No linter/formatter — match existing style in `output.py` and `__main__.py`
- Commit one logical change per task (no `--no-verify`)
- After modifying code, run the graphify watch rebuild snippet (per CLAUDE.md graphify section)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `notes_dir` for Option B is `<vault>/.graphify-out/obsidian/`, mirroring legacy default shape `graphify-out/obsidian/`. CONTEXT only specifies `<vault>/.graphify-out/` for outputs/artifacts, not the obsidian sub-segment. | Code Examples / Pattern: Option B branch | If wrong: notes write directly to `<vault>/.graphify-out/` and downstream `to_obsidian` may not nest correctly. **Confirm with user before plan freeze.** [ASSUMED] |
| A2 | VAULT-08 detection report (`vault detected at ...`) should be **suppressed** on the option-b branch to keep the breadcrumb count at "exactly one two-line" per CONTEXT. | Pitfall 2 | If wrong (i.e., emit both): Phase 64 contract regex needs to accept VAULT-08 + info: as a 3-line cluster. [ASSUMED] |
| A3 | The cleanest D-02 strict-trigger plumbing is to add `obsidian_dir_override: bool` to `resolve_output()` rather than catching SystemExit in `__main__.py`. | Pattern: Option B branch | If wrong direction is chosen, gate harmonization gets messier but no behavior changes. [ASSUMED] |
| A4 | `.graphify-out/` does not collide with existing `.graphify/` ignore rules. Pitfall 5 flags this for verification but I did not grep `detect.py`/`security.py` directly. | Common Pitfalls / Pitfall 5 | Self-ingest loop on second run from inside vault; outputs would re-enter corpus. **Verify in Plan Wave 0.** [ASSUMED] |
| A5 | No skill-file regex parser will break if Phase 63 emits `info:` before Phase 64 lands. Verified absence of regex consumers but Phase 64 itself is not yet implemented. | Skill-File Stderr Regex Parsers | If a parser exists outside the searched paths, it would reject `info:` until updated. [VERIFIED for in-repo skills; ASSUMED for external skill consumers] |

## Open Questions

1. **Should VAULT-08 single-line detection report fire on the option-b branch?**
   - What we know: CONTEXT D-01 says "exactly one two-line `[graphify] info: / hint:` stderr breadcrumb."
   - What's unclear: Whether "exactly one breadcrumb" means "the only stderr line is the new one" or "exactly one *info* breadcrumb, plus the existing VAULT-08."
   - Recommendation: Suppress VAULT-08 on option-b. Surface in discuss-phase if user disagrees.

2. **Strict trigger plumbing — parameter or call-site suppression?**
   - What we know: D-02 says `--obsidian-dir` suppresses Option B.
   - What's unclear: Whether to add `obsidian_dir_override: bool` to `resolve_output`/`resolve_execution_paths` or keep the suppression in `__main__.py:1875` (catching `_refuse`'s SystemExit).
   - Recommendation: Add the parameter. Cleaner, testable in isolation, threads through `_resolve_cli_paths` once.

3. **`<vault>/.graphify-out/obsidian/` vs `<vault>/.graphify-out/`?**
   - What we know: VOPT-01 says outputs go under `<vault>/.graphify-out/`.
   - What's unclear: Whether obsidian notes specifically go in `.graphify-out/obsidian/` (legacy parity) or directly in `.graphify-out/`.
   - Recommendation: Use `.graphify-out/obsidian/` for `notes_dir`, `.graphify-out/` for `artifacts_dir` — matches the legacy default's split (output.py:303–304: `Path("graphify-out/obsidian")` for notes, `Path("graphify-out")` for artifacts). Confirm in discuss-phase.

4. **Should `--explain-paths` participate in vault pin precedence (`--vault`, `GRAPHIFY_VAULT`)?**
   - What we know: D-03 says it prints "resolved output paths and active vault profile."
   - What's unclear: Whether `graphify --vault /some/vault --explain-paths` should resolve against `/some/vault` or against CWD.
   - Recommendation: Yes, honor pins (call `resolve_execution_paths`, not just `resolve_output`). Matches user intuition of "explain what `graphify run` would do."

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.10+ | — |
| pytest | Tests | ✓ (pip install -e ".[all]") | — | — |
| PyYAML | Profile loading (option-b path skips this — no profile to parse) | optional | — | Option B doesn't load profile, so PyYAML absence is fine |

No external dependencies. Phase 63 is purely code/test/doc changes.

## Sources

### Primary (HIGH confidence) — direct code reads
- `graphify/output.py:1–415` (full read) — resolver logic, ResolvedOutput, helpers
- `graphify/__main__.py:1397–1700, 1800–1970, 2960–3060` — CLI dispatch, gates, --obsidian/run paths
- `tests/test_output_path_matrix.py:1–140` — fixture & test patterns post-70.1
- `tests/test_routing_audit.py:1–29` — non-vault regression canary
- `tests/test_vault_cwd.py:440–492` — VCWD-03 expectation shape
- `tests/test_output.py:448–472` — `default_graphify_artifacts_dir` regression test
- `.planning/phases/63-vopt-...-explain-paths/63-CONTEXT.md` — locked decisions
- `.planning/phases/70.1-vfix-.../70.1-CONTEXT.md` — precedence chain established
- `CLAUDE.md` — project-level constraints

### Secondary (MEDIUM confidence) — derived
- Skill-file scan for stderr regex parsers (grep across 9 platforms, 0 matches)
- Caller graph for `default_graphify_artifacts_dir` (grep, 2 callers in `__main__.py` + `pipeline.py`)

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — file:line references verified by direct read
- Architecture: HIGH — single resolver, single dispatch, well-mapped
- Pitfalls: HIGH — VCWD-03 collision found by tracing the gate before reading the resolver; would have been a planning landmine

**Research date:** 2026-05-05
**Valid until:** 2026-06-05 (30 days; assumes no further rewrites of `output.py` resolver)

## RESEARCH COMPLETE
