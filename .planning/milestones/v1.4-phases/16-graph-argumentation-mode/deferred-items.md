# Deferred Items — Phase 16

## Pre-existing Test Failure (out of scope)

**test:** `tests/test_capability.py::test_validate_cli_zero`
**Status:** Failing before Phase 16 started (confirmed by git stash check)
**Failure:** `assert 1 == 0` — validate_cli returns exit code 1 instead of 0
**Root cause:** server.json manifest hash drift (likely from Phase 17 adding `chat` tool); needs manifest regeneration
**Action:** Deferred — not caused by Phase 16 changes; requires Phase 13 Wave B manifest regen
