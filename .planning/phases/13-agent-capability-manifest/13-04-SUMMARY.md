---
phase: 13-agent-capability-manifest
plan: 04
subsystem: api
tags: [harness, hardening, secrets, fidelity, seed-002]

requires:
  - phase: 13-agent-capability-manifest
    plan: 03
    provides: "`export_claude_harness`, `ANNOTATION_ALLOW_LIST`, `_filter_annotations_allowlist`, `_clock` kwarg seam, atomic-write pattern"
provides:
  - "`graphify.harness_export.SECRET_PATTERNS` — module-level tuple of 7 compiled (name, regex) pairs covering AWS access keys, GitHub PATs, OpenAI keys, Slack tokens, Bearer tokens, PEM private-key headers, and email:password credential pairs"
  - "`scan_annotations_for_secrets(annotations, *, mode='redact') -> tuple[cleaned, findings]` — scans every string field NOT in `ANNOTATION_ALLOW_LIST`; mode='error' raises `ValueError` listing offending annotation ids"
  - "`_redact_secrets(value) -> tuple[str, list[str]]` — helper that applies SECRET_PATTERNS in declaration order, replacing each match with the literal marker `[REDACTED]`"
  - "`export_claude_harness(..., secrets_mode='redact')` — new kwarg; when `include_annotations=True` the scanner runs before the allow-list skip so redaction is visible in output"
  - "`graphify harness export --include-annotations --secrets-mode {redact,error}` — CLI flags on top of Plan 03's subcommand; error mode exits code 3 with `[graphify]`-prefixed stderr listing offending ids"
  - "`_sha256_file(path) -> str` + `_write_fidelity_manifest(harness_dir, written, *, prior, target)` — per-file SHA-256 + byte-length manifest written via `.tmp` + `os.replace` to `graphify-out/harness/fidelity.json`"
  - "`set_clock(fn)` + module-level `_default_clock` — override hook for pinning `generated_at` across runs (kwarg `_clock` still takes precedence)"
  - "`round_trip` field on `fidelity.json`: `'first-export'` on initial run, `'byte-equal'` when every file matches prior manifest, `'drift'` when any file changed"
  - "`[graphify] harness export: round_trip=<status>` stable, grep-friendly stderr summary line emitted after every export"
affects: [Phase 14 Obsidian commands, Phase 15 async enrichment, Phase 17 chat — all can opt into the harness export path knowing credentials are either redacted or blocked]

tech-stack:
  added: []
  patterns:
    - "Inline regex suite as module-level `tuple[tuple[str, re.Pattern[str]], ...]` compiled once at import — preferred over a separate module file while pattern count stays ≤15 (fewer files per planner guidance)"
    - "Allow-list + delta-scan: fields in `ANNOTATION_ALLOW_LIST` bypass scrubbing; only the delta (free-text `body`, `peer_id`, and unknown keys) is scanned. Allow-list fields are user-facing safe and mutating them would break downstream consumers"
    - "Exit-code contract: 0 success, 2 argparse/schema/target error, 3 secret-scan failure — distinguishes security gate from generic misuse for CI integration"
    - "Round-trip fidelity via SHA-256-keyed manifest rather than full-file diff: cheap O(n) per run, detects byte-level drift without storing prior outputs"
    - "Clock seam kwarg > module override > system clock — lets tests pin determinism without requiring a global mutation, while `set_clock` enables long-running process overrides (e.g., CI fidelity gates)"

key-files:
  created: []
  modified:
    - graphify/harness_export.py
    - graphify/__main__.py
    - tests/test_harness_export.py

key-decisions:
  - "Kept `SECRET_PATTERNS` inline in `harness_export.py` rather than extracting to a separate `harness_secret_scanner.py`. At 7 patterns, inline is cleaner and matches planning_context 'fewer files is better' guidance; future extraction is trivial if the suite grows past 15."
  - "Scanner runs BEFORE allow-list skip when `include_annotations=True` — redaction is visible in output and findings count accurately reflects the raw annotation content. If the scanner ran after filtering, redacted markers would be invisible to the caller because the fields would already have been dropped."
  - "Allow-list fields (`id`, `label`, `source_file`, `relation`, `confidence`) are explicitly exempted from scanning. These are downstream-consumer-visible and secret-shaped content in these fields represents a contract violation upstream, not something this layer should silently rewrite. The security gate lives in annotation free-text fields where credentials realistically leak."
  - "Email-credential pattern requires `@` preceding the `:` (`[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+:[...]{8,}`) rather than just `:` — drops false positives on ordinary prose containing colons. Acceptable residual: ordinary passwords without email prefixes won't match, but those are a separate class the planner did not ask us to catch."
  - "Fidelity manifest written INSIDE the already-`validate_graph_path`-approved `harness_dir`, so path confinement is inherited from Plan 03 with no new security boundary to defend."
  - "Drift test uses a clock-change (legitimate schema/timestamp drift) rather than post-hoc file tampering, because re-running `export_claude_harness` rewrites the SOUL/HEARTBEAT/USER bytes idempotently — tampering would be overwritten before the comparison. A clock change is the canonical 'something upstream changed' signal the round-trip manifest is designed to catch."
  - "Corrupt prior `fidelity.json` is treated as `first-export` rather than `drift`. A JSON decode failure cannot distinguish tampering from a legitimate v1→v2 format migration, and 'drift' on an unreadable file would be a false positive that masks the real signal."
  - "Kwarg-first clock resolution (`_clock or _default_clock`) preserves Plan 03's existing test surface — `_clock=_frozen_clock` kwarg still works exactly as before, no test churn. `set_clock` adds a new capability without breaking the old one."

patterns-established:
  - "Single-layer scanner on audit boundaries: compile regexes once at import, expose a tuple for introspection, provide both a raw `_redact(value)` and an annotation-shape-aware `scan_annotations_for_secrets` wrapper. Same pattern applies to future export surfaces (enrichment overlay, argumentation transcripts) if/when they gain free-text annotation paths."
  - "Content-hash round-trip manifest: SHA-256 + byte-length per output file, `round_trip: first-export/byte-equal/drift` status field, stable stderr one-liner. Same pattern usable for any deterministic exporter that needs CI to detect silent divergence (Phase 15 enrichment overlay, Phase 18 focus context snapshots)."
  - "Three-tier exit codes for CLI subcommands: 0=success, 2=argparse/schema/target, 3=security-gate-failure. Gives CI and humans a meaningful signal without parsing stderr."

requirements-completed:
  - HARNESS-07
  - HARNESS-08

metrics:
  duration: ~35 minutes (autonomous execution)
  tasks_completed: 2
  tests_added: 15
  tests_updated: 2 (existing tests reflect 4-file output contract)
  tests_total_harness: 22 (all passing)
  tests_total_suite: 1295 (all passing)
  files_changed: 3
  lines_added: 629
  lines_removed: 21
  completed_date: 2026-04-17
---

# Phase 13 Plan 04: HARNESS-07 Secret Scanner + HARNESS-08 Round-Trip Fidelity Summary

Close the two SEED-002 P2 hardening items — add a 7-pattern regex scanner gating the `--include-annotations` path, and a SHA-256-keyed round-trip fidelity manifest so repeated exports prove they haven't diverged. This completes Phase 13; all 18 REQ-IDs (MANIFEST-01..10 + HARNESS-01..08) now ship.

## Objective

HARNESS-07 (T-13-07): When users opt into `--include-annotations`, annotation free-text fields must never silently leak credentials into SOUL/HEARTBEAT/USER output. The scanner either redacts matches inline with the literal marker `[REDACTED]` (default, `mode=redact`) or refuses the export with a non-zero exit listing the offending annotation id (`mode=error`).

HARNESS-08 (T-13-08): Two successive `graphify harness export` runs on the same inputs must be provably byte-equal. `graphify-out/harness/fidelity.json` records per-file SHA-256 + byte-length; the `round_trip` field flips from `first-export` → `byte-equal` on a clean rerun, or `first-export` → `drift` if any upstream (schema, clock, fixtures) has shifted.

Both additions extend — never modify — Plan 03's `export_claude_harness` contract. `--include-annotations` without `--secrets-mode` defaults to `redact`; absence of `--include-annotations` keeps Plan 03's allow-list behavior unchanged.

## Deliverables

### SECRET_PATTERNS — 7-family coverage (inline, HARNESS-07)

| # | name                 | Regex                                                                   | Notes                                             |
|---|----------------------|-------------------------------------------------------------------------|---------------------------------------------------|
| 1 | `aws_access_key`     | `AKIA[0-9A-Z]{16}`                                                      | AWS IAM access key id                             |
| 2 | `github_pat`         | `ghp_[A-Za-z0-9]{36}`                                                   | GitHub personal access token (classic)            |
| 3 | `openai_api_key`     | `sk-[A-Za-z0-9]{20,}`                                                   | OpenAI API key                                    |
| 4 | `slack_token`        | `xox[baprs]-[A-Za-z0-9-]+`                                              | Slack bot/app/user/refresh/webhook token          |
| 5 | `bearer_token`       | `Bearer\s+[A-Za-z0-9._-]{20,}`                                          | Generic Authorization header                      |
| 6 | `pem_private_key`    | `-----BEGIN[ A-Z]+PRIVATE KEY-----`                                     | Any PEM private key header (RSA/EC/DSA/OPENSSH)   |
| 7 | `email_credential`   | `[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+:[A-Za-z0-9@#$%^&*()_+=!\-]{8,}`     | email:password form (requires `@` before `:`)     |

All compiled once at module import. The executor added NO patterns beyond the seven the plan required; the `email_credential` heuristic is scoped to require an `@` before the `:` to keep false-positives on prose-with-colons low.

### Scanner API

```python
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...]  # 7 entries

def _redact_secrets(value: str) -> tuple[str, list[str]]:
    """Return (cleaned_value, matched_pattern_names)."""

def scan_annotations_for_secrets(
    annotations: list[dict[str, Any]],
    *,
    mode: str = "redact",           # 'redact' | 'error'
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Returns (cleaned_annotations, findings).
    findings: [{'id': str, 'field': str, 'patterns': list[str]}, ...]
    mode='error' raises ValueError on any match, listing offending ids."""
```

Scan scope: every string value whose key is NOT in `ANNOTATION_ALLOW_LIST`. Allow-list fields (`id`, `label`, `source_file`, `relation`, `confidence`) bypass scrubbing.

### Fidelity manifest schema (HARNESS-08)

`graphify-out/harness/fidelity.json`:

```json
{
  "version": 1,
  "target": "claude",
  "round_trip": "first-export" | "byte-equal" | "drift",
  "files": {
    "claude-SOUL.md":      {"sha256": "<64-hex>", "bytes": 842},
    "claude-HEARTBEAT.md": {"sha256": "<64-hex>", "bytes": 512},
    "claude-USER.md":      {"sha256": "<64-hex>", "bytes": 237}
  }
}
```

Written atomically via `.tmp` + `os.replace`. JSON dumps with `indent=2, sort_keys=True, ensure_ascii=False` + trailing newline so the file itself is byte-stable across identical inputs.

### Clock seam

```python
def _system_clock() -> datetime: ...                # default
_default_clock: Callable[[], datetime] = _system_clock

def set_clock(fn: Callable[[], datetime]) -> None:  # module override
    global _default_clock
    _default_clock = fn
```

Resolution order inside `export_claude_harness`: `_clock kwarg > _default_clock > system wall clock`. Kwarg-first preserves Plan 03's existing `_clock=_frozen_clock` test contract with zero churn.

### CLI surface

```
graphify harness export [--target claude] [--out PATH]
                        [--include-annotations]
                        [--secrets-mode {redact,error}]
```

- `--include-annotations`: opt-in to full annotation set (runs scanner first).
- `--secrets-mode redact` (default): matches replaced with `[REDACTED]`, export continues, stderr summarizes count.
- `--secrets-mode error`: any match aborts the export with exit code 3 and a stable `[graphify]`-prefixed stderr message listing offending annotation ids.

### Stderr contracts

- Redaction summary: `[graphify] harness export: redacted <N> secret match(es) across <M> annotation(s)`
- Round-trip status (every run): `[graphify] harness export: round_trip={first-export|byte-equal|drift}`
- Error-mode failure: `[graphify] harness export: secret patterns detected in annotations; offending annotation ids: ['a1', ...]. Re-run with --secrets-mode redact to continue.`

## Tests (22 total in test_harness_export.py; 15 added)

### HARNESS-07 / T-13-07

- `test_secret_patterns_coverage` — 7 required names present
- `test_scanner_detects_aws_key` — `AKIAIOSFODNN7EXAMPLE` → `[REDACTED]`
- `test_scanner_detects_github_pat` — 36-char PAT redacted
- `test_scanner_detects_openai_key` — `sk-...` redacted
- `test_scanner_redact_mode` — annotation-shape wrapper returns cleaned + findings
- `test_scanner_error_mode_exits_nonzero` — mode='error' raises ValueError with offending id
- `test_scanner_skips_allowlist_fields` — secret-shaped `label` survives untouched
- `test_scanner_rejects_unknown_mode` — mode='bogus' raises ValueError
- `test_include_annotations_flag_invokes_scanner` — end-to-end; stderr shows redaction summary
- `test_cli_include_annotations_error_mode_exits_3` — CLI exits code 3 on PAT

### HARNESS-08 / T-13-08

- `test_fidelity_manifest_written` — schema + per-file SHA-256/bytes recorded; first run = `first-export`
- `test_round_trip_byte_equal_with_frozen_clock` — pinned clock → 2 runs → `byte-equal`; SHA-256 in manifest matches fresh on-disk hash
- `test_round_trip_drift_detected_when_schema_changes` — clock change → `drift`
- `test_clock_seam_overridable` — different clocks produce different SHA-256 in fidelity
- `test_set_clock_module_override` — module-level override works when no kwarg given

### Updated (2)

- `test_export_writes_three_files` — now asserts 4 returned paths (SOUL/HEARTBEAT/USER + fidelity.json)
- `test_cli_harness_export_invokes_exporter` — now asserts 4 printed lines

## Threat Mitigations

### T-13-07 — Credential leakage via `--include-annotations`

Scanner runs inline before any rendering touches the file system. 7 regex families cover the most common cloud and dev-tool credential shapes. Default `mode=redact` fails safe: the export still completes, but every match in non-allow-list fields becomes `[REDACTED]` and a stderr summary surfaces the redaction count. `mode=error` gives CI a hard-fail signal (exit code 3) that is distinguishable from argparse/schema errors (code 2). Residual risk: custom / vendor-specific tokens (e.g., Anthropic, Stripe, Twilio) are NOT in the suite — the 7-pattern coverage is a floor, not a ceiling; future plans can expand.

### T-13-08 — Silent drift between successive exports

Every run writes `fidelity.json` with per-file SHA-256 + byte-length. Successive runs compare against the prior manifest; a byte-level difference in ANY file flips `round_trip` from `byte-equal` to `drift`. CI can assert `round_trip == byte-equal` as a post-condition after identical inputs; a flip from `byte-equal` to `drift` signals an upstream schema, fixture, or rendering change that escaped review. Corrupt prior `fidelity.json` fails safe (treated as `first-export` rather than false-positive `drift`).

## Deviations from Plan

None. All locked constraints honored:

- Export-only (no inverse-import)
- claude.yaml target only
- No Jinja2 (inherits Plan 03's `string.Template.safe_substitute`)
- No auto-export (no watch.py wiring, no pipeline hook)
- Output confined to `graphify-out/harness/` (fidelity.json inherits Plan 03's path confinement)
- D-73 utilities-only (no LLM calls, no skill coupling)
- SECRET_PATTERNS inline (module-level tuple, no new file)
- `_clock` seam from Plan 03 preserved (kwarg-first; `set_clock` is additive)

## Phase 13 Completion

Plan 04 is the last plan in Phase 13. All 18 REQ-IDs now ship:

- MANIFEST-01..08 (Plan 01) — manifest generator + CLI + MCP tool + drift gate
- MANIFEST-09..10 (Plan 02) — CI gate + examples
- HARNESS-01..06 (Plan 03) — harness export core
- HARNESS-07..08 (Plan 04) — secret scanner + round-trip fidelity

## Verification

- `pytest tests/test_harness_export.py -q` — 22 passed
- `pytest tests/ -q` — 1295 passed, 2 warnings
- CLI integration (manual): `python -m graphify harness export --out /tmp/h` on fixture copy writes 4 files + prints paths + emits `round_trip=first-export`
- CLI integration (manual): `--include-annotations --secrets-mode error` on annotation-with-PAT exits code 3 with `[graphify]`-prefixed stderr listing `['a1']`

## Self-Check: PASSED

All files created/modified exist on disk:

- `graphify/harness_export.py` — modified
- `graphify/__main__.py` — modified
- `tests/test_harness_export.py` — modified
- `.planning/phases/13-agent-capability-manifest/13-04-SUMMARY.md` — created

Commit exists in `git log`:

- `1296f43` — `feat(13-04): HARNESS-07 secret scanner + HARNESS-08 round-trip fidelity`
