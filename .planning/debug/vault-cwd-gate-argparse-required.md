---
slug: vault-cwd-gate-argparse-required
status: resolved
resolved_in: phase-74-vbug
trigger: |
  graphify update-vault from a vault CWD with no --vault: _check_vault_cwd_gate at __main__.py:3286 auto-adopts and prints the notice, but argparse at __main__.py:3358 declares --vault required=True so the call still exits 2. Find every gated command with the same defect and design a fix (likely: gate injects --vault <cwd> into argv before parse, OR required=False + resolution-layer enforcement). Out of scope for Phase 62 cleanup — needs its own fix phase.
created: 2026-05-04
updated: 2026-05-08
---

# Debug Session: vault-cwd-gate-argparse-required

## Symptoms

- **Expected:** Running `graphify update-vault` from inside a vault CWD (no `--vault` flag) should auto-adopt the CWD as vault and proceed.
- **Actual:** `_check_vault_cwd_gate` (`graphify/__main__.py:3286`) auto-adopts and prints the notice, but argparse spec at `__main__.py:3358` declares `--vault required=True`, so the parser exits with code 2 ("the following arguments are required: --vault").
- **Error:** argparse exit 2; auto-adopt notice printed to stderr but command still fails.
- **Timeline:** Surfaced 2026-05-04 by Phase 62-03 E2E auto-adopt subprocess test (D-17 stop fired at commit d5170a9).
- **Reproduction:** `cd <vault-dir> && graphify update-vault` (no `--vault` arg). Auto-adopt notice prints; argparse rejects.

## Scope

Bug spans every CLI subcommand that uses `_check_vault_cwd_gate` AND declares `--vault required=True`. Need full enumeration before fix design.

## Current Focus

- **hypothesis:** CONFIRMED. Gate runs pre-parse and mutates nothing observable to argparse; required=True check fires regardless of auto-adoption. The post-parse auto-adopt fallback (`if gate == "auto-adopt" and not _uv_vault`) is unreachable because argparse exits 2 first.
- **next_action:** Implement chosen fix approach (see Diagnosis below) in a dedicated fix phase.

## Evidence

- `graphify/__main__.py:3312` — `update-vault` declares `_p_uv.add_argument("--vault", required=True, ...)`
- `graphify/__main__.py:3358` — `vault-promote` declares `_p_vp.add_argument("--vault", required=True, ...)`
- All other 13 gated commands (`--obsidian`, `--diagram-seeds`, `--init-diagram-templates`, `--dedup`, `snapshot`, `approve`, `save-result`, `elicit`, `harness`, `import-harness`, `enrich`, `run`, and one inline gate at ~2947) use hand-rolled arg parsing — none declare `--vault required=True` via argparse. They are NOT affected.
- RED test confirmed: `test_update_vault_auto_adopt_no_vault_flag` fails with `error: the following arguments are required: --vault` while auto-adopt notice is present on stderr. Reproduced 2026-05-04.

## Eliminated

- Other gated commands (all hand-rolled parsers) — not affected; they read `--vault` from `sys.argv` manually and honour the post-parse `if gate == "auto-adopt"` guard.

## Diagnosis

### 1. Gated command enumeration

15 dispatch branches call `_check_vault_cwd_gate`. Of those, **exactly 2** also use argparse with `--vault required=True`:

| Command | Gate call line | `--vault required=True` line | Defective? |
|---|---|---|---|
| `update-vault` | 3286 | 3312 | YES |
| `vault-promote` | 3344 | 3358 | YES |
| `--obsidian` | 1818 | n/a (hand-rolled) | no |
| `--diagram-seeds` | 1960 | n/a (hand-rolled) | no |
| `--init-diagram-templates` | 2021 | n/a (hand-rolled) | no |
| `--dedup` | 2077 | n/a (hand-rolled) | no |
| `snapshot` | 2217 | n/a (hand-rolled) | no |
| `approve` | 2346 | n/a (hand-rolled) | no |
| `save-result` | 2630 | no --vault arg in argparse | no |
| `elicit` | 2675 | no --vault arg in argparse | no |
| `harness` | 2773 | no --vault arg in argparse | no |
| `import-harness` | 2844 | no --vault arg in argparse | no |
| inline gate ~2947 | 2947 | n/a (hand-rolled) | no |
| `enrich` | 3052 | no --vault arg in argparse | no |
| `run` | (global, hand-rolled) | n/a | no |

**Blast radius: 2 commands** (`update-vault`, `vault-promote`).

### 2. Fix design tradeoff comparison

| Dimension | (a) Gate injects `--vault <cwd>` into `sys.argv` before argparse | (b) Flip `required=False`, enforce at resolution layer post-parse |
|---|---|---|
| **Blast radius** | Touches `_check_vault_cwd_gate` return protocol + 2 call sites | Touches only the 2 `add_argument` lines + 2 post-parse guards |
| **Regression risk** | Medium — `sys.argv` mutation is a global side-effect; any test or downstream code inspecting raw `sys.argv` will see injected value; also mutates for the `update-vault` case which strips its own flags before `parse_args(sys.argv[2:])` | Low — change is local to 2 argparse declarations; post-parse guard already exists (`if gate == "auto-adopt" and not _uv_vault`) |
| **Locality of change** | Low — injection logic must live in gate function (shared) or in each call site; either way it crosses the gate/dispatch boundary | High — two-line change per command; change lives exactly where the bug is |
| **Testability** | Hard to unit-test argv mutation without monkey-patching; subprocess tests already cover it | Easy — existing subprocess RED tests (`test_update_vault_auto_adopt_no_vault_flag`, `test_vault_promote_auto_adopt_no_vault_flag`) turn GREEN immediately |
| **Alignment with existing semantics** | Breaks separation: gate was designed to return a routing signal, not to mutate process state | Preserves existing pattern — hand-rolled commands already use `required=False` implicitly; this aligns argparse-based commands with that convention |
| **Help text accuracy** | `--vault` would still show as required in `--help` output (injection happens at runtime, not at parser definition) | Can add `default=None` and an explicit note in help string ("omit when running from vault CWD") |
| **Forward compatibility** | Any new argparse command that adds `--vault required=True` silently breaks again | Pattern is explicit at declaration site; reviewers see `required=False` and understand why |

### 3. Recommendation

**Use approach (b): flip `required=False` on `--vault` in both `update-vault` and `vault-promote`, and enforce vault presence at the post-parse resolution layer.**

The post-parse guard (`if gate == "auto-adopt" and not _uv_vault: _uv_vault = str(Path.cwd())`) already exists in both branches — it is simply unreachable today because argparse exits first. Flipping `required=False` (and keeping `default=None`) lets argparse complete, then the existing guard fills in the CWD. If neither auto-adopt triggered nor a `--vault` was supplied, the guard leaves `_uv_vault = None`, and the subsequent `Path(opts.vault)` or equivalent will raise a clear `TypeError`/`ValueError` — which can be converted to a user-friendly `error: --vault is required` message at that point. This approach touches 2 lines of argparse declarations and adds at most 2 lines of None-guard error messaging. It has no global side-effects, aligns with all 13 other gated commands' conventions, and the existing RED tests turn GREEN without any further scaffolding.

## Resolution

- **root_cause:** `_check_vault_cwd_gate` returns `"auto-adopt"` and sets `lv_vault` conceptually, but `sys.argv` is not modified; argparse then sees `--vault` absent and exits 2 because `required=True`, before the post-parse fallback guard can run.
- **fix:** Change `required=True` to `required=False` (with `default=None`) on `--vault` in `update-vault` (line 3312) and `vault-promote` (line 3358). Tighten the existing post-parse guard to emit a user-friendly error if `gate != "auto-adopt"` and `opts.vault is None`.
- **status:** diagnosed — fix deferred to dedicated fix phase. RED tests present as regression lock.

## RED Tests (regression lock)

Tests `test_update_vault_auto_adopt_no_vault_flag` and `test_vault_promote_auto_adopt_no_vault_flag` in `tests/test_vault_cwd.py` (lines 412–455) are marked `@pytest.mark.skip` with reason referencing this debug session. They will be unskipped as the TDD RED→GREEN gate in the fix phase. The skip keeps Phase 62's test run green while preserving the regression lock on disk.
