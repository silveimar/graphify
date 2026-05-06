# Phase 64: AUDIT-A — stderr Format Snapshot Lock & Sweep - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 64-audit-a-stderr-format-snapshot-lock-sweep
**Areas discussed:** Snapshot mechanism, Outlier sweep scope, Skill regex fixture, Prefix policy

---

## Snapshot Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Golden text file | `tests/fixtures/stderr_contract.txt` with all canonical lines; tests assert exact match. Diff is human-reviewable in PRs, no new dep, plays well with the existing pure-unit test convention. | ✓ |
| syrupy per-call snapshots | Adds syrupy as a test dep; each test captures stderr inline via `assert_match_snapshot`. Easier to update with `--snapshot-update` but adds a dependency CI must install. | |
| Parameterized hand-written asserts | Pure `pytest.parametrize` with regex assertions per call site. No fixture file, but updates require code edits and the contract is scattered across the test. | |

**User's choice:** Golden text file (Recommended)
**Notes:** Aligns with project's "no new required dependencies" constraint and existing fixture-based test patterns.

---

## Outlier Sweep Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Grep-and-migrate-all | After snapshot lands, grep for `[graphify]` lines in `graphify/`, classify any one-liner as an outlier, migrate every one to two-line. Maximizes contract uniformity. | ✓ |
| Explicit allowlist | Migrate only the 1–2 named outliers (start with `__main__.py:~2745`) plus anything discovered during the snapshot RED. | |
| Snapshot-driven only | Run the snapshot test, migrate exactly what it flags, stop. Lowest risk but might miss code paths the test suite doesn't exercise. | |

**User's choice:** Grep-and-migrate-all (Recommended)
**Notes:** Surface is bounded; better to clear it fully than leave a known-drift backlog.

---

## Skill Regex Fixture

| Option | Description | Selected |
|--------|-------------|----------|
| Hand-curated `(platform, regex)` list | Test fixture is a Python list of tuples copied from each SKILL.md. Round-trip test: each canonical stderr line in `stderr_contract.txt` must be parsed by every regex. Simple, explicit, drift-detectable. | ✓ |
| Auto-extract from SKILL.md files | Parser scans the 7 platform files at test time, extracts regex blocks via a marker comment. Zero copy-paste drift, but adds parser complexity and depends on a markup convention in skill files. | |
| Both — auto-extract + assert it matches the hand-curated list | Belt and braces: hand-curate, but also auto-extract and fail if they diverge. Best drift detection, most code to maintain. | |

**User's choice:** Hand-curated list (Recommended)
**Notes:** Code-review-driven drift detection is sufficient for a 7-file surface that changes rarely.

---

## Prefix Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Lock today's reality: `error:` + `info:` | Snapshot covers exactly what ships today. Strict whitelist — any new prefix in the future requires an explicit phase to extend the contract. | ✓ |
| Lock + reserve `warn:`/`debug:` slots | Today's contract plus pre-blessed slots so future phases can add them without contract churn. | |
| Strict-whitelist, fail-closed on unknown prefix | Today's contract plus an active assertion that no other prefix appears in stderr across the suite. Strongest guarantee, possibly noisy. | |

**User's choice:** Lock today's reality: `error:` + `info:` (Recommended)
**Notes:** Forces deliberate evolution of the stderr contract; aligns with Phase 63's introduction of `info:` (memory 6060).

---

## Claude's Discretion

- Exact filename of the snapshot fixture (`stderr_contract.txt` is a working name).
- Round-trip parse test mechanics (parametrize axes, per-platform vs combined).
- Whether snapshot tests invoke emitters directly or via subprocess CLI capture.

## Deferred Ideas

- `warn:` / `debug:` prefix expansion — own phase if needed.
- Auto-extracting regexes from SKILL.md files.
- Fail-closed assertion against unknown prefixes anywhere in the test suite.
