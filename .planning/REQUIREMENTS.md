# Requirements: Milestone v1.7 Vault Adapter UX & Template Polish

**Goal:** Make graphify safe and ergonomic to run from inside an Obsidian vault — profile-driven output placement, vault-CWD detection with auto-adopt (SEED-vault-root-aware-cli Option C), hardened self-ingestion defenses, onboarding diagnostics — and close out the long-deferred template/profile composition backlog from v1.0.

**Scope:** 13 requirements, 3 categories.

---

## v1.7 Requirements

### Vault Adapter UX & Self-Ingestion Hardening

- [ ] **VAULT-08**: graphify detects when CWD is itself an Obsidian vault (presence of `.obsidian/` at CWD)
- [ ] **VAULT-09**: When CWD is a vault with `.graphify/profile.yaml`, graphify auto-adopts profile-driven placement (SEED-vault-root-aware-cli Option C) — CWD is both input corpus and output target
- [ ] **VAULT-10**: `.graphify/profile.yaml` declares output destination (vault-relative path, absolute path, or sibling-of-vault) via a profile field; CLI `--output` flag overrides
- [x] **VAULT-11**: Profile-aware self-ingestion exclusions — `detect.py` reads profile output destination + declared exclusion globs and prunes them from input scan
- [x] **VAULT-12**: Recursive nesting guard — `detect.py` refuses to ingest paths matching `**/graphify-out/**` at any depth and warns the user about prior nesting if found
- [ ] **VAULT-13**: Manifest-based ignore — current run's manifest records output paths so subsequent runs skip them even if profile changes
- [ ] **VAULT-14**: `graphify doctor` command — prints vault detection, profile validation status, resolved output destination, ignore-list, recommended fixes; non-zero exit on misconfiguration
- [ ] **VAULT-15**: Dry-run preview for vault-root-aware behavior — `graphify --dry-run` (or `graphify doctor --dry-run`) shows what files would land where, which profile is detected, and which ingestion targets would be skipped, without writing

### Template Engine Extensions (deferred from v1.0)

- [ ] **TMPL-01**: Conditional template sections — `{{#if_god_node}}...{{/if}}` guards in markdown templates, evaluated against node attributes
- [ ] **TMPL-02**: Loop blocks for connections — `{{#connections}}...{{/connections}}` iteration in templates, with per-iteration variable scope
- [ ] **TMPL-03**: Custom Dataview query templates per note type — profile field allowing per-note-type Dataview query strings injected at render time

### Profile Composition (deferred from v1.0)

- [ ] **CFG-02**: Profile includes/extends mechanism — compose profiles from fragments via `extends:` or `includes:` field; deterministic merge order; cycle detection
- [ ] **CFG-03**: Per-community template overrides — profile field mapping community ID/label patterns to custom templates; first-match-wins precedence consistent with the v1.0 mapping engine

---

## Future Requirements (deferred beyond v1.7)

- **SEED-001 territory** (v1.8 candidate): Tacit-to-Explicit Elicitation Engine — onboarding/discovery as a primary theme
- **SEED-002 territory** (v1.9 candidate): Multi-harness memory expansion (codex.yaml, letta.yaml, honcho.yaml, AGENTS.md), inverse-import (CLAUDE.md → graph) — gated on prompt-injection defenses
- **2 baseline test failures** (`test_detect_skips_dotfiles`, `test_collect_files_from_dir`) — deferred to a dedicated `/gsd-debug` session, not absorbed into v1.7

---

## Out of Scope (v1.7)

- **CFG-01** (custom color palettes for graph.json) — dead via D-74 (`.obsidian/graph.json` management de-scoped from `to_obsidian()` in v1.0)
- **Jinja2 / template engine swap** — constraint preserved from v1.0: template features stay on `string.Template` with custom block syntax; no new required deps
- **CLI pipeline driver verb** — D-73 still holds; `graphify --obsidian` and new `graphify doctor` are utilities, the skill remains the orchestrator
- **Multi-harness expansion** (codex/letta/honcho/AGENTS.md) — deferred to v1.9
- **Onboarding/Elicitation Engine** — deferred to v1.8

---

## Constraints (carried from PROJECT.md)

- Python 3.10+ on CI targets (3.10 and 3.12)
- No new required dependencies; PyYAML stays optional under the `obsidian` extra
- Backward compatibility: existing `graphify --obsidian` invocations without profile-yaml changes must still produce v1.0-equivalent output
- All file paths confined to output directory per `security.py` patterns
- Template placeholders sanitized — no injection via node labels (HTML-escape, control char strip, length cap)
- Pure unit tests only — no network, no filesystem side effects outside `tmp_path`

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VAULT-08    | Phase 27   | Planned |
| VAULT-09    | Phase 27   | Planned |
| VAULT-10    | Phase 27   | Planned |
| VAULT-11    | Phase 28   | Planned |
| VAULT-12    | Phase 28   | Planned |
| VAULT-13    | Phase 28   | Planned |
| VAULT-14    | Phase 29   | Planned |
| VAULT-15    | Phase 29   | Planned |
| TMPL-01     | Phase 31   | Planned |
| TMPL-02     | Phase 31   | Planned |
| TMPL-03     | Phase 31   | Planned |
| CFG-02      | Phase 30   | Planned |
| CFG-03      | Phase 30   | Planned |

(Phase column populated by `gsd-roadmapper` during `/gsd-new-milestone` roadmap step.)

---
*Created: 2026-04-27 — v1.7 Vault Adapter UX & Template Polish*
