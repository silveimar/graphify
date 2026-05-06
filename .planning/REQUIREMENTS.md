# graphify v1.13 — Concept Intelligence & Audit Closure: Requirements

**Milestone:** v1.13
**Goal:** Promote concept↔code edges from a structural feature to a knowledge-reasoning tool (cross-repo identity, semantic confidence, drift detection, parameterized queries), close the remaining vault-CWD seed bullet, and resolve all v1.12 audit-deferred items.
**Phase numbering:** continues from v1.12 (last phase 62.1) → starts at **Phase 63**.
**Source seeds:** SEED-bidirectional-concept-code-links (35% remaining), SEED-vault-root-aware-cli (20% remaining — Option B).

---

## v1.13 Requirements

### CCONF — Per-Edge Concept Confidence
- [ ] **CCONF-01**: Concept↔code edges emit per-edge `confidence_score ∈ [0.0, 1.0]` from LLM scoring (replaces uniform `1.0` baseline shipped in v1.10–v1.12).
- [ ] **CCONF-02**: INFERRED edges include an `evidence` field carrying the textual basis for the assigned score.
- [ ] **CCONF-03**: Confidence cache lives in a separate namespace keyed on `prompt_version + model + edge_signature` (independent from the existing `extract.py` file-hash cache); bumping `prompt_version` invalidates only confidence entries.
- [ ] **CCONF-04**: GRAPH_REPORT.md gains a calibration self-check section that flags suspicious score distributions (e.g., >70% of scores clustered in 0.85±0.05).
- [ ] **CCONF-05**: `validate.py` enforces "optional on read, required on write" with a new `schema_version` field; a frozen v1.10–v1.12 legacy fixture must pass read validation in `tests/`.

### CFED — Cross-Repo Concept Federation
- [ ] **CFED-01**: User can opt into cross-repo federation via an explicit CLI flag; default behaviour is off (federation never runs without consent).
- [ ] **CFED-02**: Federation is deterministic — namespaces all node IDs as `{repo}::{id}`; merges only when multi-signal evidence (label + shared neighborhood + source-path overlap) all agree. No embeddings, no LLM arbitration.
- [ ] **CFED-03**: A federation manifest records per-repo provenance for every merged concept (which repos contributed, which signals matched).
- [ ] **CFED-04**: `graphify/federate.py` runs as a build-time merge step after `_normalize_concept_code_edges` in `build.py` and before `cluster.py`.
- [ ] **CFED-05**: GRAPH_REPORT.md gains a Federation section listing merged concepts with their provenance entries.

### CDRIFT — Edge-Level Concept Drift
- [ ] **CDRIFT-01**: Drift detection compares snapshots via community-membership **Jaccard similarity**, never via community names or IDs (which rename for benign reasons even with stable membership).
- [ ] **CDRIFT-02**: Each `implements` / `documents` / `tests` edge is classified across snapshots as one of: `stable` / `community-renamed` / `community-resharded` / `orphaned`.
- [ ] **CDRIFT-03**: GRAPH_REPORT.md gains a Drift section when a prior snapshot exists; absent snapshot ⇒ section omitted (no spurious output).
- [ ] **CDRIFT-04**: Drift snapshots persist under `graphify-out/cache/snapshots/` with a count- or age-based retention policy decided at planning time.

### CQUERY — Parameterized Concept Queries
- [ ] **CQUERY-01**: MCP `concept_code_hops` accepts `min_confidence`, `relations`, and `confidence_band` parameters and applies them as filters on the BFS traversal.
- [ ] **CQUERY-02**: Backward compatibility — callers that omit the new parameters receive results identical to the v1.12 implementation.

### VOPT — Vault Option B Silent Reroute
- [x] **VOPT-01**: When CWD is an Obsidian vault (`.obsidian/` present) but no `.graphify/profile.yaml` exists, output reroutes silently to a hidden `.graphify-out/` inside the vault.
- [x] **VOPT-02**: An unconditional one-line `[graphify]` stderr breadcrumb explains the reroute on every run that uses Option B.
- [ ] **VOPT-03**: A new `--explain-paths` flag dumps the resolved output paths (and active vault profile, if any) without running the pipeline.

### VPROF — Vault Profile Schema v2 & Profile-Driven Writes
- [x] **VPROF-01**: Profile schema v2 — `.graphify/profile.yaml` adds `input_path`, `vault_path`, `graphify_folder_mapping` (renamed from `folder_mapping`), `user_only_folders`, `augment.allow_community` (default `false`), `reverse_sync.{mode, memory_path, auto_on_run}`. A one-shot migrator renames `folder_mapping` → `graphify_folder_mapping` on first read so existing vault profiles upgrade silently.
- [x] **VPROF-02**: Vault writes MUST resolve target folder via `profile.graphify_folder_mapping[<record_type>]`. Default ALWAYS `Atlas/Sources/Graphify/<type>/`. Legacy hardcoded literals in `graphify/vault_promote.py:206-299` and `_DEFAULT_LAYERS` at `vault_promote.py:873-879` are removed (no fallback to `Atlas/Maps/`, `Atlas/Dots/*`).
- [x] **VPROF-03**: Hard non-overwrite invariant — graphify MUST NOT create, delete, or overwrite any file under `profile.user_only_folders` (default includes `Atlas/`, `Calendar/`, `Efforts/`, `+/`, `x/`, and vault root). User files MAY be **augmented** via frontmatter merge only, limited to: `related_to`, `up`, `tags`, `comments`, `analysis`, `references`, `type` (and `community` only when `augment.allow_community: true`). Body content is never modified. Pre-flight refusal with actionable error when a write would land outside the profile-pinned graphify subtree. The existing manifest-hash overwrite guard at `vault_promote.py:702-732` is preserved.
- [x] **VPROF-04**: Legacy artifact migration — `graphify doctor` gains a section that detects prior graphify-shaped notes outside `graphify_folder_mapping` (e.g. `_COMM*.md` at vault root, `Community*.md` under `Atlas/Maps/`). `graphify update-vault --migrate-legacy` relocates them into the profile-pinned subtree. Detection is read-only without the flag.

### VRSYNC — Vault → Input Reverse-Sync
- [x] **VRSYNC-01**: New explicit `graphify reverse-sync` command copies new/changed files from `profile.vault_path` user folders back into `profile.input_path` (raw corpus). Modes: `always_ask` (default, prompts with diff before each copy), `never_copy` (detect-and-log only), `always_copy` (mirror without prompting). `--yes` flag overrides `always_ask` for scripted runs. SHA256-based change detection reuses the `cache.py` hashing primitive. JSONL diff memory at `profile.reverse_sync.memory_path` (default `.graphify/reverse-sync-log.jsonl`) records `{ts, vault_path, input_path, action: new|update|skip, diff_summary, hash_before, hash_after}` per event. `profile.reverse_sync.auto_on_run: false` (default) opts into running reverse-sync implicitly at the start of `graphify run` / `update-vault`.


### VFIX — Vault Output Path Resolution Fixes (Phase 70.1, gap-closure for Phase 70 UAT)
- [x] **VFIX-01**: Path resolution from `cwd` × `--obsidian-dir` × profile `output:` produces a single, consistent absolute notes-directory regardless of invocation form. Specifically: (a) when CWD is the vault root and `profile.output.path == "."`, notes are written under `<vault>/<folder_mapping[type]>/...` with NO nested vault-name folder; (b) when CWD is the vault's parent and the user passes `--obsidian-dir <vault-name>` (no `--vault`), the resolved write path is identical to (a); (c) when CWD is the vault's parent and `--vault <vault>` is passed (with profile loaded), the resolved write path is identical to (a); (d) `--output <abs>` continues to override profile/--obsidian-dir per D-08. Regression matrix is covered by pure-unit tests in `tests/test_output_path_matrix.py` (no fs side-effects outside `tmp_path`). No regression in existing `tests/test_output.py`.
- [x] **VFIX-02**: Documentation accurately describes the precedence chain (`--output > profile.output > --obsidian-dir > legacy default`) and the `output.path: .` convention. README, CLI `--help` text for `--obsidian-dir` and `--output`, and the seven `graphify/skill*.md` variants include a "common pitfalls — nested vault folder" note. The bundled `profile-example.yaml` and `profile-example-complete.yaml` carry inline comments explaining when to set `output.path: .` (vault-root taxonomy) vs. when to set a subdirectory.

### AUDIT — v1.12 Audit Closure
- [ ] **AUDIT-01**: Nyquist VALIDATION.md gap-fill for v1.12 phases 59, 59.1, 60, 60.1, 61 — each retroactive entry cites the implementing SHA and the asserting test path; the closure script re-runs the cited tests to prove they still pass.
- [ ] **AUDIT-02**: Project-wide `[graphify]` stderr two-line format sweep migrates remaining one-line outliers (e.g. `__main__.py:~2745`) to the v1.12 `[graphify] error:` + `  hint:` convention. A stderr-format snapshot test is introduced **before** any reformatting to lock the contract for the 7 platform skill files that regex-parse stderr.
- [ ] **AUDIT-03**: Retroactive seed-SHA traceability — REQUIREMENTS.md and PROJECT.md are annotated with the milestone that consumed each seed (SEED-001 → v1.9, SEED-002 → v1.4, SEED-vault-root-aware-cli → v1.12 + v1.13 closes Option B, SEED-bidirectional-concept-code-links → v1.10 / v1.11 / v1.13 closes remainder).

---

## Future Requirements (deferred past v1.13)

- **D-3 Coverage lens query** — surface "concept coverage" (% of concepts with implements edges above confidence threshold). Depends on CQUERY shipping and being exercised in anger to learn the right shape.
- **D-5 Federated Obsidian frontmatter** — extend MOC↔CODE bidirectional links in the vault to reflect federated identity. Wait for CFED to prove its merge rules are trusted before extending into the vault surface.
- **Federation alias / override file** — manual override list for cases where exact-label + multi-signal heuristics produce false negatives. Only if real-world federation reveals this gap.

---

## Out of Scope (explicit exclusions)

- **Embedding-based similarity matching** for federation or concept identity — anti-feature; violates the deterministic + auditable + zero-new-deps stance. Adds ~800MB of torch weight and breaks the "no system deps" promise.
- **Auto-merge across repos without multi-signal evidence** — false-merges across repos are unrecoverable; deterministic guard rails (CFED-02) are non-negotiable.
- **Drift remediation / auto-fix** — v1.13 surfaces drift as a read-only signal in GRAPH_REPORT.md; auto-rewriting orphaned edges is out of scope and likely belongs to a vault-side workflow rather than graphify itself.
- **LLM-based federation arbitration** — federation decisions are deterministic by design; LLM-as-judge for merging concepts is non-reproducible and not auditable.
- **Cross-vault profile inheritance** — the vault profile system stays per-vault.
- **Real-time drift watcher / watch-mode integration** — drift is a batch-time signal in v1.13. A watch-mode integration is deferred until users hit a clear pain point.
- **Concept-edge schema breaking changes** — already shipped in v1.10/v1.11; CCONF-05 enforces backward-compat.
- **New language extractors** — orthogonal to v1.13's theme.

---

## Traceability

*Filled in by the roadmapper once phases are derived. Each REQ-ID below maps to the phase that delivers it.*

| REQ-ID | Phase | Notes |
|--------|-------|-------|
| CCONF-01 | Phase 65 | |
| CCONF-02 | Phase 65 | |
| CCONF-03 | Phase 65 | |
| CCONF-04 | Phase 65 | |
| CCONF-05 | Phase 65 | |
| CFED-01 | Phase 66 | |
| CFED-02 | Phase 66 | |
| CFED-03 | Phase 66 | |
| CFED-04 | Phase 66 | |
| CFED-05 | Phase 66 | |
| CDRIFT-01 | Phase 67 | |
| CDRIFT-02 | Phase 67 | |
| CDRIFT-03 | Phase 67 | |
| CDRIFT-04 | Phase 67 | |
| CQUERY-01 | Phase 67 | |
| CQUERY-02 | Phase 67 | |
| VOPT-01 | Phase 63 | |
| VOPT-02 | Phase 63 | |
| VOPT-03 | Phase 63 | |
| AUDIT-01 | Phase 68 | |
| AUDIT-02 | Phase 64 | |
| AUDIT-03 | Phase 68 | |
| VPROF-01 | Phase 69 | schema migrator; augment + reverse_sync keys also consumed by Phase 70 |
| VPROF-02 | Phase 69 | |
| VPROF-03 | Phase 69, Phase 70 | refusal half in 69; augmentation half in 70 |
| VPROF-04 | Phase 69 | |
| VRSYNC-01 | Phase 70 | |
| VFIX-01 | Phase 70.1 | gap-closure for Phase 70 UAT path bugs |
| VFIX-02 | Phase 70.1 | docs + profile examples |

---

*Created: 2026-05-05 — graphify v1.13 milestone init.*
