---
phase: 06
slug: graph-delta-analysis-staleness
status: verified
threats_open: 0
asvs_level: 1
created: 2026-04-12
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| user input → snapshot filename | `--name` flag value from CLI becomes part of filesystem path | User-supplied string → filename component |
| disk → snapshot load | JSON files in `snapshots/` could be hand-edited or corrupted | Untrusted JSON → graph deserialization |
| disk → staleness check | Source files on disk could have been modified by user or external process | File content/mtime → staleness classification |
| CLI args → file paths | `--graph`, `--from`, `--to` accept user-supplied file paths | User-supplied paths → file I/O |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Tampering | snapshot.py save_snapshot | mitigate | Atomic write via `os.replace(tmp, target)` — prevents partial writes on crash (`snapshot.py:67-73`) | closed |
| T-06-02 | Tampering | snapshot.py load_snapshot | mitigate | Validates required keys `"graph"` and `"communities"` exist; raises `ValueError` on missing (`snapshot.py:134-137`) | closed |
| T-06-03 | Information Disclosure | snapshot.py --name flag | mitigate | Name sanitized with `re.sub(r"[^\w-]", "_", name)[:64]` — no path traversal possible (`snapshot.py:43`) | closed |
| T-06-04 | Denial of Service | snapshot.py disk growth | mitigate | FIFO prune on every `save_snapshot` call; `snaps[:-cap]` deletion (`snapshot.py:76-78`) | closed |
| T-06-05 | Elevation of Privilege | snapshot.py path confinement | accept | Snapshots write only to `graphify-out/snapshots/` which is already in `.gitignore`; no user-controlled base path | closed |
| T-06-06 | Spoofing | classify_staleness | accept | Staleness is informational only (D-10); false FRESH/STALE does not affect pipeline behavior | closed |
| T-06-07 | Information Disclosure | render_delta_md | accept | Delta report shows file paths already visible in `graph.json`; no new information exposure | closed |
| T-06-08 | Tampering | render_delta_md node labels | mitigate | `_escape_pipe()` function escapes pipe characters in all markdown table cells (`delta.py:99-101`, used in all table renderers) | closed |
| T-06-09 | Denial of Service | classify_staleness SHA256 | accept | SHA256 bounded by file size; mtime fast-gate at `delta.py:83-88` skips hash for unchanged files | closed |
| T-06-10 | Tampering | CLI --graph path | mitigate | Validates `.json` suffix; resolves path with `.resolve()`; fails on non-existent files (`__main__.py:958-965`) | closed |
| T-06-11 | Tampering | CLI --from/--to paths | mitigate | `load_snapshot` validates JSON structure and required keys; invalid files raise `ValueError` (`snapshot.py:128-137`) | closed |
| T-06-12 | Information Disclosure | CLI --name | mitigate | Name sanitized in `save_snapshot` via `re.sub` pattern — same as T-06-03 | closed |
| T-06-13 | Denial of Service | CLI --cap 0 | accept | `cap=0` would delete all snapshots; user explicitly chose this value; documented behavior | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-05 | Snapshots confined to `graphify-out/snapshots/` (gitignored); no user-controlled base path | phase plan | 2026-04-12 |
| AR-06-02 | T-06-06 | Staleness is advisory metadata only — no pipeline decisions depend on it | phase plan | 2026-04-12 |
| AR-06-03 | T-06-07 | Delta report exposes no information beyond what `graph.json` already contains | phase plan | 2026-04-12 |
| AR-06-04 | T-06-09 | SHA256 cost proportional to file size; mtime gate eliminates most calls | phase plan | 2026-04-12 |
| AR-06-05 | T-06-13 | `--cap 0` is an explicit user choice; behavior is deterministic and predictable | phase plan | 2026-04-12 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-12 | 13 | 13 | 0 | gsd-secure-phase orchestrator |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-12
