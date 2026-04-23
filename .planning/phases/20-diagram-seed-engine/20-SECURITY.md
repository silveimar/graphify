---
phase: 20
slug: diagram-seed-engine
status: verified
threats_open: 0
threats_total: 20
threats_closed: 17
threats_accepted: 3
asvs_level: 1
audited_at: 2026-04-23
---

# Phase 20 — Security

> Per-phase security contract for the Diagram Seed Engine (plans 20-01, 20-02, 20-03). Verifies every threat declared in the plan threat models against implemented code and tests.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Graph loader → analyze.detect_user_seeds | NetworkX graph from `graphify-out/graph.json` — node `tags` attribute may be malformed | Node attribute dicts (untrusted shape) |
| analyze.detect_user_seeds → seed.write_seeds | Seed descriptors (id, label, layout_hint) | In-process Python dicts |
| seed.write_seeds → filesystem | Seed JSON + manifest written under `graphify-out/seeds/` | Files on disk (atomic replace) |
| MCP client → serve._run_{list,get}_diagram_seeds_core | Agent-provided `seed_id` arguments | Strings (untrusted, validated by `_SEED_ID_RE`) |
| serve → filesystem | Reads from `graphify-out/seeds/` | Files on disk (read-only) |

---

## Threat Register

### Plan 20-01 — analyze.detect_user_seeds

| Threat ID | Category | Component | Disposition | Mitigation | Evidence | Status |
|-----------|----------|-----------|-------------|------------|----------|--------|
| T-20-01-01 | Tampering | analyze.py `detect_user_seeds` | mitigate | `isinstance(tag, str)` guard before matching tag prefix | `graphify/analyze.py:721` (`if not isinstance(tag, str):`); test `tests/test_analyze.py:633` (`test_detect_user_seeds_tolerates_malformed_tags`) | CLOSED |
| T-20-01-02 | Injection | analyze.py `detect_user_seeds` | mitigate | Layout hint suffix captured opaquely; validation deferred to 20-02 allowlist | `graphify/analyze.py:727` (`layout_hint = suffix if suffix else None`); validation at `graphify/seed.py:149` | CLOSED |
| T-20-01-03 | EoP | analyze.py / seed.py | mitigate | Grep denylist test asserts no direct frontmatter writes in analyze.py or seed.py; tag write-back goes through `graphify.merge.compute_merge_plan` only | `tests/test_analyze.py:659-722` (denylist test) | CLOSED |
| T-20-01-04 | DoS | analyze.py | accept | Single-pass scan; upstream graph loader already caps node count | PLAN rationale — single-pass over `G.nodes(data=True)`; no recursion | ACCEPTED |
| T-20-01-05 | Info Disclosure | analyze.py | accept | `possible_diagram_seed` boolean — same trust boundary as `graph.json` | PLAN rationale — boolean attribute inside already-trusted graph object | ACCEPTED |

### Plan 20-02 — graphify/seed.py

| Threat ID | Category | Component | Disposition | Mitigation | Evidence | Status |
|-----------|----------|-----------|-------------|------------|----------|--------|
| T-20-02-01 | Tampering | `_select_layout_type` | mitigate | Layout hint validated against `_VALID_LAYOUT_TYPES` allowlist; unknown hints fall through to heuristic | `graphify/seed.py:35` (`_VALID_LAYOUT_TYPES`), `seed.py:149` (`if layout_hint is not None and layout_hint in _VALID_LAYOUT_TYPES:`) | CLOSED |
| T-20-02-02 | Tampering | filename generation | mitigate | Filenames use `_make_id`-derived node IDs (lowercase alphanumeric + underscore); `_safe_filename_stem` adds defense-in-depth | `graphify/seed.py:390` (`_safe_filename_stem`); used at `seed.py:508,524` | CLOSED |
| T-20-02-03 | DoS | seed.build_all | mitigate | Radius-2 ego-graph; O(k²) dedup with k ≤ 20 + user seeds; cap enforced BEFORE I/O | `graphify/seed.py:230-231` (ego_graph radius=1,2); `seed.py:413` (comment "apply max_seeds=20 cap BEFORE I/O"); `seed.py:535-549` (cap logic) | CLOSED |
| T-20-02-04 | EoP | path construction | mitigate | All writes via `_write_atomic`; paths built as `graphify_out / "seeds" / filename` with no user-controlled path component | `graphify/seed.py:73` (`_write_atomic`); `seed.py:524-527` (filename built from sanitized seed_id, written via `_write_atomic`) | CLOSED |
| T-20-02-05 | EoP | vault path | mitigate | Grep denylist test asserts seed.py writes only via atomic helpers; vault path uses `compute_merge_plan` only | `tests/test_analyze.py:659-722` (denylist covers seed.py) | CLOSED |
| T-20-02-06 | Tampering | `_load_seeds_manifest` | mitigate | Catches `JSONDecodeError/OSError/ValueError`; warns and treats as empty | `graphify/seed.py:106` (`except (json.JSONDecodeError, OSError, ValueError):`); test `tests/test_seed.py:541` (`test_rerun_with_corrupt_prior_manifest_is_safe`) | CLOSED |
| T-20-02-07 | Info Disclosure | seed JSON files | accept | Seed JSON stored inside `graphify-out/` — same trust boundary as existing artifacts | PLAN rationale — graphify-out already holds graph.json, communities, etc. | ACCEPTED |
| T-20-02-08 | Repudiation | manifest schema | mitigate | Manifest entries include `dropped_due_to_cap` + `rank_at_drop` for audit trail | `graphify/seed.py:535-549`; tests `tests/test_seed.py:324-329,350,380,395-475` | CLOSED |

### Plan 20-03 — MCP tools (list_diagram_seeds / get_diagram_seed)

| Threat ID | Category | Component | Disposition | Mitigation | Evidence | Status |
|-----------|----------|-----------|-------------|------------|----------|--------|
| T-20-03-01 | Path Traversal | `_run_get_diagram_seed_core` | mitigate | `seed_id` validated against `_SEED_ID_RE`; `Path.resolve()` + `startswith(seeds_dir.resolve())` confinement | `graphify/serve.py:2559` (`_SEED_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")`), `serve.py:2708` (regex check), `serve.py:2716-2719` (resolve + startswith); test `tests/test_serve.py:3371` (`test_get_diagram_seed_rejects_path_traversal`) | CLOSED |
| T-20-03-02 | DoS | get_diagram_seed | mitigate | `budget` arg caps response (default 2000); truncation path | `graphify/serve.py:1705-1706` (budget clamp); `serve.py:1509-1510` for query-graph budget; seed tool threads `budget` through core | CLOSED |
| T-20-03-03 | Tampering | seed file parsing | mitigate | `try/except (json.JSONDecodeError, OSError, UnicodeDecodeError)` → `status=corrupt` envelope | `graphify/serve.py:2726` (except clause in get_diagram_seed); test `tests/test_serve.py:3338` (`test_get_diagram_seed_corrupt_file`) | CLOSED |
| T-20-03-04 | Tampering | manifest parsing in list tool | mitigate | `try/except` around manifest read → `status=no_seeds` / `corrupt`; per-seed-file parse also guarded | `graphify/serve.py:2605` (manifest), `serve.py:2634` (per-file); test `tests/test_serve.py:3293` (`test_list_diagram_seeds_corrupt_manifest_resilient`) | CLOSED |
| T-20-03-05 | EoP | serve.py ↔ registry drift | mitigate | Startup invariant asserts `len(_handlers) == len(registry tools)` — MANIFEST-05 atomic-pair commit rule | `graphify/serve.py:3358-3359` (`if {t.name for t in _reg_tools} != set(_handlers.keys()): raise RuntimeError("MCP tool registry and _handlers keys must match (MANIFEST-05)")`) | CLOSED |
| T-20-03-06 | Info Disclosure | resolved_from_alias | accept | Intentional transparency — agents need to know when aliases were redirected | PLAN rationale — CHAT-07/T-17-05 precedent | ACCEPTED |
| T-20-03-07 | Repudiation | alias redirects | mitigate | `resolved_from_alias` meta field records every redirect | `graphify/serve.py:2662-2663,2773-2774` (meta population in both seed tools) | CLOSED |

**Totals:** 20 threats — 17 CLOSED, 0 OPEN, 3 ACCEPTED.

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-20-01 | T-20-01-04 | DoS — single-pass scan over `G.nodes(data=True)`; upstream graph loader caps node count; no recursion or quadratic behavior in detect_user_seeds | Phase 20 planner | 2026-04-23 |
| AR-20-02 | T-20-01-05 | Info disclosure — `possible_diagram_seed` boolean lives on node attributes inside `graphify-out/graph.json`, which is already the system's trusted artifact | Phase 20 planner | 2026-04-23 |
| AR-20-03 | T-20-02-07 | Info disclosure — seed JSON files are stored inside `graphify-out/seeds/`, same trust boundary as existing graphify artifacts (graph.json, communities, analysis) | Phase 20 planner | 2026-04-23 |
| AR-20-04 | T-20-03-06 | Info disclosure — `resolved_from_alias` meta field is intentional transparency so agents understand when their requested `seed_id` was redirected through the D-16 alias map (precedent: CHAT-07 / T-17-05) | Phase 20 planner | 2026-04-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Unregistered Flags

No Threat Flags sections present in 20-01-SUMMARY.md, 20-02-SUMMARY.md, or 20-03-SUMMARY.md. Nothing to reconcile.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Accepted | Run By |
|------------|---------------|--------|------|----------|--------|
| 2026-04-23 | 20 | 17 | 0 | 3 | gsd-secure-phase (Claude Opus 4.7) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-23
