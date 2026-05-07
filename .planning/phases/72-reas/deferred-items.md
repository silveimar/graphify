# Deferred items — Phase 72

## Pre-existing failures observed during 72-01 execution

Discovered via `pytest tests/ -q` during 72-01 final regression run on 2026-05-07.

**47 failures** — all in:
- `tests/test_vault_cwd.py` (multiple tests)
- `tests/test_vault_parity.py` (multiple tests)

These are unrelated to Phase 72 (REAS) scope (validate.py reasoning relations).
Out of scope per executor SCOPE BOUNDARY rule. No vault paths or vault-discovery
code touched in 72-01.

`pytest tests/test_validate.py -q` passes 31/31 — Phase 72 scope is clean.
