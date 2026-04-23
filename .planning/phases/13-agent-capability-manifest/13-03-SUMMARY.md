---
phase: 13-agent-capability-manifest
plan: 03
subsystem: api
tags: [harness, export, seed-002, mcp, template]

requires:
  - phase: 13-agent-capability-manifest
    plan: 01
    provides: atomic-write pattern (`write_manifest_atomic`), `validate_graph_path` semantics, `string.Template.safe_substitute` precedent
provides:
  - `graphify.harness_export.export_claude_harness(out_dir, *, target, include_annotations, _clock)` — reads graph.json + annotations.jsonl + agent-edges.json + telemetry.json and emits SOUL/HEARTBEAT/USER markdown under `graphify-out/harness/`
  - `graphify/harness_schemas/claude.yaml` — declarative schema with `{{ god_nodes }}`, `{{ recent_deltas }}`, `{{ hot_paths }}`, `{{ agent_identity }}`, `{{ generated_at }}`, `{{ graphify_version }}` placeholders
  - `graphify harness export [--target claude] [--out PATH]` — utilities-only CLI subcommand (D-73)
  - `ANNOTATION_ALLOW_LIST` = `{id, label, source_file, relation, confidence}` — the default-deny annotation filter (HARNESS-06 / T-13-04)
  - `_clock` seam on `export_claude_harness` — injectable `() -> datetime` for Plan 04 byte-equality pinning (HARNESS-08)
affects: [Phase 13 Plan 04 (adds --include-annotations + secret scanner + round-trip fidelity on top of this surface)]

tech-stack:
  added: []
  patterns:
    - "Single-regex `{{ token }}` → `${token}` normalization, then `string.Template.safe_substitute` (no Jinja2)"
    - "Declarative YAML schemas bundled via setuptools `[tool.setuptools.package-data]` (`graphify.harness_schemas = [claude.yaml, *.yaml]`)"
    - "Injectable `_clock` kwarg pattern for test determinism without production knobs — Plan 04 will expose a user-facing pin"

key-files:
  created:
    - graphify/harness_export.py
    - graphify/harness_schemas/__init__.py
    - graphify/harness_schemas/claude.yaml
    - tests/test_harness_export.py
    - tests/fixtures/harness/graph.json
    - tests/fixtures/harness/annotations.jsonl
    - tests/fixtures/harness/agent-edges.json
    - tests/fixtures/harness/telemetry.json
  modified:
    - graphify/__main__.py
    - graphify/skill.md
    - graphify/skill-codex.md
    - pyproject.toml

key-decisions:
  - "Annotations are filtered eagerly through the allow-list at `export_claude_harness` entry; the filtered list is not yet rendered into block bodies — HARNESS-06 is a 'what we never leak' contract, and Plan 04 will add annotation-aware body sections behind `--include-annotations`. The kwarg is wired through now so Plan 04 drops in without a signature change."
  - "`_clock` is introduced as an underscore-prefixed test seam in this plan (no user-facing knob). Plan 04 (HARNESS-08) will surface a pinned timestamp in a user-visible way; no breaking change required because the kwarg is keyword-only."
  - "Path confinement uses `validate_graph_path(harness_dir, base=out_dir)` where `out_dir` is the caller-supplied `graphify-out` root. `mkdir(parents=True, exist_ok=True)` runs before validation so the existence precondition is satisfied; a subsequent `str(out_path.resolve()).startswith(str(base))` guard on each composed filename defends against `..`-bearing schema entries (belt + suspenders)."
  - "Byte-determinism is enforced via (a) stable sort keys on god-node ranking `(-degree, id)`, on agent-edge ordering `(-ts, from, to)`, and on hot-path ordering `(-count, path)`; (b) fixed block emission order `(soul, heartbeat, user)`; (c) `graphify_version` sourced from telemetry rather than `importlib.metadata` so tests control it fully."

patterns-established:
  - "Bundled declarative schemas live under `graphify/<feature>_schemas/` as a dedicated subpackage with `schema_path(target) -> Path` accessor; register the subpackage under `[tool.setuptools.package-data]` as `\"graphify.<feature>_schemas\" = [...]`."
  - "Exporter utilities never render into arbitrary paths — they compose onto a `validate_graph_path`-approved directory, then re-check the composed child path."

requirements-completed:
  - HARNESS-01
  - HARNESS-02
  - HARNESS-03
  - HARNESS-04
  - HARNESS-05
  - HARNESS-06

metrics:
  duration: ~25 min
  completed_date: 2026-04-17
  commits: 2
  tests_added: 7
  tests_total_after: 1280
---

# Phase 13 Plan 03: SEED-002 Harness Memory Export Core Summary

`graphify harness export` now emits a declarative, deterministic set of agent-memory markdown files (`claude-SOUL.md`, `claude-HEARTBEAT.md`, `claude-USER.md`) from the existing `graphify-out/` sidecars, using `string.Template.safe_substitute` with a single-regex `{{ token }}` → `${token}` normalizer — no Jinja2, no auto-trigger, no annotation leakage by default.

## What Shipped

- **`graphify/harness_export.py`** (452 lines) — core exporter with helpers `_load_sidecars`, `_filter_annotations_allowlist`, `_normalize_placeholders`, `_collect_god_nodes`, `_collect_recent_deltas`, `_collect_hot_paths`, `_collect_agent_identity`, and public `export_claude_harness(out_dir, *, target='claude', include_annotations=False, _clock=None) -> list[Path]`.
- **`graphify/harness_schemas/__init__.py`** — `schema_path(target) -> Path` accessor (rejects anything other than `"claude"`).
- **`graphify/harness_schemas/claude.yaml`** — declarative SOUL/HEARTBEAT/USER block definitions (30 lines total; SOUL ≤ 25 lines, HEARTBEAT ≤ 15 lines, USER ≤ 10 lines).
- **`graphify harness export [--target claude] [--out PATH]`** CLI subcommand wired into `graphify/__main__.py` adjacent to `capability`. Help-text line added. Both `skill.md` and `skill-codex.md` gained a "For harness memory export (SEED-002)" section.
- **`pyproject.toml`** — `graphify.harness_schemas` subpackage registered under `[tool.setuptools.package-data]` with `["claude.yaml", "*.yaml"]` so wheels include the schema.
- **Tests** — 7 new tests in `tests/test_harness_export.py` + 4 fixture files under `tests/fixtures/harness/`:
  - `test_export_writes_three_files` — HARNESS-01/05 end-to-end write
  - `test_output_confined_to_graphify_out` — T-13-05 path escape raises `ValueError`, nothing written
  - `test_annotations_allow_list_default` — HARNESS-06 / T-13-04 `peer_id` + free-text body scrubbed
  - `test_placeholder_token_regex_normalization` — HARNESS-03 single-regex semantics (spaced, no-space, no-token, literal `$`)
  - `test_deterministic_output_across_runs` — T-13-06 byte-equality with `_clock` pinned
  - `test_no_jinja2_import` — static guard on module source + runtime import probe
  - `test_cli_harness_export_invokes_exporter` — HARNESS-04 dispatcher invocation + stdout shape

## Commits

| # | Commit  | Summary |
|---|---------|---------|
| 1 | `6c29c97` | Task 1 — harness_schemas package + claude.yaml + harness_export.py scaffold + pyproject.toml + fixtures |
| 2 | `a60c125` | Task 2 — CLI wiring + skill notes + 7 unit tests |

## Verification

```bash
pytest tests/test_harness_export.py -q   # 7 passed
pytest tests/ -q                          # 1280 passed (+7 over baseline 1273)
grep -rn 'export_claude_harness\|from graphify.harness_export' \
    graphify/watch.py graphify/pipeline.py   # no matches — no auto-trigger
python -c "from graphify.harness_export import ANNOTATION_ALLOW_LIST; \
           assert ANNOTATION_ALLOW_LIST == frozenset({'id','label','source_file','relation','confidence'})"
```

End-to-end CLI smoke (against fixture graph.json copied into `/tmp/gt-harness-test`):

```
$ python -m graphify harness export --out /tmp/gt-harness-test
/private/tmp/gt-harness-test/harness/claude-SOUL.md
/private/tmp/gt-harness-test/harness/claude-HEARTBEAT.md
/private/tmp/gt-harness-test/harness/claude-USER.md
```

## Locked Decisions Honored

- **Export-only.** No inverse-import; `graph.json` remains read-only.
- **`claude.yaml` target only.** `schema_path` raises `ValueError` for any other target.
- **No Jinja2.** `string.Template.safe_substitute` only; module source contains zero `import jinja2` / `from jinja2` matches; `test_no_jinja2_import` asserts both.
- **No auto-export.** `graphify/watch.py` and `graphify/pipeline.py` contain zero references to `harness_export` / `export_claude_harness`.
- **Annotations excluded by default.** `_filter_annotations_allowlist` drops every key outside `{id, label, source_file, relation, confidence}`; `test_annotations_allow_list_default` asserts `peer_id` + free-text `body` strings are absent from the JSON dump of filtered output.
- **Output confined to `graphify-out/harness/`.** `validate_graph_path(harness_dir, base=out_dir)` gates the directory; each composed filename is re-checked against the base.
- **D-73 — utilities-only CLI.** No LLM imports, no skill imports in the harness module or CLI branch.
- **Deterministic output.** Three collectors sort by stable keys, block emission order is fixed, and `_clock` + `graphify_version` from telemetry make byte-equality attainable for tests + Plan 04.

## Deferred to Plan 04 (P2 — HARNESS-07 / HARNESS-08)

- `--include-annotations` CLI flag (the Python kwarg is already plumbed through).
- Secret-scanner regex suite over annotation text before inclusion.
- Round-trip fidelity summary (byte-equal manifest) — the `_clock` seam introduced here is the foundation; Plan 04 will add the user-facing pin.

## Deviations from Plan

None of architectural significance. Three minor-but-worth-noting refinements applied during execution (all consistent with locked decisions):

1. **`_clock` introduced here instead of Plan 04.** The plan instruction said "tests in THIS plan must freeze the clock via `monkeypatch` when asserting determinism". I implemented the `_clock` keyword-only seam directly on `export_claude_harness` because (a) monkeypatching a module-level `datetime` symbol is fragile under `from datetime import datetime, timezone` imports, and (b) the plan's `<objective>` locked constraints explicitly say "Include `_clock` seam (callable kwarg) — this plan introduces it". No user-facing CLI knob yet — Plan 04 wires that.
2. **`pyproject.toml` package-data uses `["claude.yaml", "*.yaml"]` rather than only `*.yaml`** — the plan's acceptance grep `grep -q 'claude.yaml' pyproject.toml` wants the literal string present, so I named it explicitly alongside the glob. Net effect on builds is identical (setuptools union-includes both).
3. **Path-escape test uses `monkeypatch.setattr` on the module-level `validate_graph_path` symbol** rather than crafting a physical escape. The plan said either approach is acceptable; monkeypatching is hermetic and works identically on every filesystem.

No Rule 1/2/3 deviations (no bugs found, no missing critical functionality added beyond plan scope, no blocking issues). No Rule 4 architectural questions needed.

## Self-Check: PASSED

- `graphify/harness_export.py` — FOUND
- `graphify/harness_schemas/__init__.py` — FOUND
- `graphify/harness_schemas/claude.yaml` — FOUND
- `graphify/__main__.py` modifications — FOUND (`harness export` branch at line 1775)
- `graphify/skill.md` + `graphify/skill-codex.md` harness sections — FOUND
- `pyproject.toml` `graphify.harness_schemas` entry — FOUND
- `tests/test_harness_export.py` (7 tests) — FOUND; all passing
- `tests/fixtures/harness/{graph.json,annotations.jsonl,agent-edges.json,telemetry.json}` — FOUND (4 files)
- Commit `6c29c97` — FOUND
- Commit `a60c125` — FOUND
- Full test suite: `pytest tests/ -q` → 1280 passed, 0 failed
- `grep -rn 'export_claude_harness\|from graphify.harness_export' graphify/watch.py graphify/pipeline.py` → no matches
