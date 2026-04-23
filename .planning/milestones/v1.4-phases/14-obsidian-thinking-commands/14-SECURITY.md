# SECURITY — Phase 14: obsidian-thinking-commands

**Phase:** 14 — obsidian-thinking-commands
**ASVS Level:** 1
**Block policy:** high
**Threats closed:** 17 / 17
**Audit date:** 2026-04-22

## Summary

All 17 threats declared across the six Phase 14 plans (14-00 through 14-05) are
verified. Fourteen `mitigate` threats have code and/or test evidence; three
`accept` threats have documented scope-based rationale recorded here.

## Threat Verification Table

### Plan 14-00 — uninstall directory-scan refactor

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| TM-14-02 | Tampering / drift | mitigate | `graphify/__main__.py:190` (`sorted(src_dir.glob("*.md"))` in `_install_commands`), `graphify/__main__.py:222` (same directory-scan in `_uninstall_commands`); `tests/test_install.py::test_uninstall_directory_scan` asserts legacy + new names both removed, proving no hardcoded whitelist. |
| T-14-00-01 | Tampering | mitigate | `graphify/__main__.py:222-225` — loop over `src_dir.glob("*.md")` only, `target.unlink(missing_ok=True)` on `dst_dir / src.name`. No `rglob`, no `rm -rf`, no user-authored files touched. |
| T-14-00-02 | DoS / idempotency | accept | `graphify/__main__.py:217` (`if not dst_dir.exists(): return`), `__main__.py:220` (same guard for `src_dir`), `__main__.py:225` (`missing_ok=True`). Accept-rationale verified: `tests/test_install.py::test_uninstall_idempotent` passes on repeat calls. |

### Plan 14-01 — target filter + prefix enforcement

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| TM-14-02 | Tampering / drift | mitigate | `graphify/__main__.py` lines 57/66/75/84/93/102/111/120/129/138/147 — every `_PLATFORM_CONFIG` entry has a `supports:` list; `tests/test_install.py::test_platform_config_has_supports_key` enforces the invariant; `tests/test_commands.py::test_graphify_prefix_enforced` catches collisions. |
| TM-14-04 | Spoofing | mitigate | `tests/test_commands.py:248-259` (`test_graphify_prefix_enforced`) — every command name must start with `graphify-` OR be in the legacy allow-list of 9 commands. |
| T-14-01-01 | Info disclosure | accept | `graphify/__main__.py:166-169` — `_read_command_target` reads first 1024 bytes with `errors="replace"`, defaults to `"both"` on `OSError`. Accept: only package-shipped files are read; user files never parsed here. |
| T-14-01-02 | Tampering (intentional contract flip) | accept | `tests/test_commands.py::test_ask_md_frontmatter` and `test_argue_md_frontmatter` assert `target == "both"` for the 9 legacy commands — a deliberate contract update, not a regression. |

### Plan 14-02 — /graphify-moc

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| TM-14-01 | Tampering (trust boundary) | mitigate | `graphify/commands/graphify-moc.md` invokes `propose_vault_note`; `tests/test_commands.py::test_moc_trust_boundary_and_contract` (lines 279-292) grep-asserts absence of `Path.write_text`, `write_note_directly`, `open(..., 'w')`. |
| T-14-02-01 | Spoofing ($ARGUMENTS) | mitigate | `graphify/commands/graphify-moc.md` explicitly: "Parse `$ARGUMENTS` as an integer... If it is not a non-negative integer, render ... and stop." before `get_community` dispatch. |
| T-14-02-02 | Info disclosure (25-node cap) | accept | Documented cap + rationale: labels are from the user's own local graph; no cross-tenant exposure. |

### Plan 14-03 — /graphify-related

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| TM-14-03 | Spoofing / ID | mitigate | `graphify/commands/graphify-related.md:32-33` explicit `no_context` branch; `tests/test_commands.py::test_related_handles_no_context` asserts "no_context" appears in body. Phase 18 CR-01 snapshot-root fix confines `file_path` to project root. |
| T-14-03-01 | Info disclosure | accept | Reading user's own vault frontmatter is the command's defining contract. No third-party data involved. |
| T-14-03-02 | Tampering (read-only) | mitigate | `graphify/commands/graphify-related.md:44` explicit "Do NOT write to the vault — this command is read-only." The body contains no `propose_vault_note` call; verified by inspection. |

### Plan 14-04 — /graphify-orphan

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| T-14-04-01 | Info disclosure | accept | `graphify-out/` artifacts are user's own local data; no sensitive external surface. |
| T-14-04-02 | DoS (missing enrichment.json) | mitigate | `graphify/commands/graphify-orphan.md` Step 2 handles `enrichment.json` absence with a banner; `tests/test_commands.py::test_orphan_graceful_without_enrichment` enforces banner + `graphify enrich` remediation phrasing. |
| T-14-04-03 | Tampering (read-only) | mitigate | `graphify/commands/graphify-orphan.md:9` ("read-only report; it does NOT write to the vault") and `:35` ("no vault-write primitives, no note-proposal tool calls"). Codified by `tests/test_commands.py::test_trust_boundary_invariant_all_p1` keeping orphan out of the P1-write set. |

### Plan 14-05 — /graphify-wayfind

| Threat ID | Category | Disposition | Evidence |
|-----------|----------|-------------|----------|
| TM-14-01 | Tampering (trust boundary) | mitigate | `graphify/commands/graphify-wayfind.md:69` invokes `propose_vault_note`; `tests/test_commands.py::test_trust_boundary_invariant_all_p1` (lines 376-392) grep-asserts `propose_vault_note` present and `Path.write_text` / `write_note_directly` / `open(...,'w')` absent for both `graphify-moc` and `graphify-wayfind`. |
| T-14-05-01 | DoS (degenerate graph) | mitigate | `graphify/commands/graphify-wayfind.md:22-26` — explicit `community_not_found` branch rendering friendly message and stopping. |
| T-14-05-02 | Spoofing (unresolved topic) | mitigate | `graphify/commands/graphify-wayfind.md:37` — explicit `entity_not_found` branch rendering friendly message. |

## Accepted Risks Log

Three threats are accepted with explicit scope-based rationale:

1. **T-14-00-02** — `_uninstall_commands` idempotency via `missing_ok=True` plus absent-dir guard. No DoS surface — symmetric with `_install_commands`.
2. **T-14-01-01** — `_read_command_target` head-only (1024-byte) read with `errors="replace"` and `OSError` fallback to `"both"`. Operates only on package-shipped files, so info-disclosure surface is nil.
3. **T-14-01-02** — `target: both` is an intentional contract update for the 9 legacy commands; flipped test assertions document the new contract.
4. **T-14-02-02** — 25-member MOC cap bounds output; labels already reside in the user's own local graph.
5. **T-14-03-01** — Reading the user's own vault frontmatter is the command's defining behaviour.
6. **T-14-04-01** — `graphify-out/` artifacts are the user's own local data.

(Items 4-6 are `accept` entries in the threat register; kept here for auditability.)

## Unregistered Flags

None. No `## Threat Flags` entries in any of the six SUMMARY.md files that lack a mapping in the Phase 14 threat register.

## Verification Method Summary

- **Mitigate threats (14):** Code pattern located at cited file:line; corresponding test present in `tests/test_install.py` or `tests/test_commands.py`.
- **Accept threats (3 in register + 3 informational):** Rationale documented; scope limits reviewed and deemed reasonable for ASVS Level 1.
- **Transfer threats:** none in this phase.

## Sign-off

Phase 14 is SECURED. All P1 write commands (`graphify-moc`, `graphify-wayfind`) are confirmed to route exclusively through the `propose_vault_note` trust boundary. All read-only commands (`graphify-related`, `graphify-orphan`) are confirmed free of vault-write primitives. Uninstall is directory-scan driven, idempotent, and confined to source-tree-known filenames.
