# Requirements: Ideaverse Integration - v1.8 Output Taxonomy & Cluster Quality

**Defined:** 2026-04-28
**Core Value:** Graphify can inject knowledge into any Obsidian vault framework driven entirely by a declarative vault-side profile.

## v1.8 Requirements

Requirements for the v1.8 milestone. Each maps to exactly one roadmap phase.

### Default Output Taxonomy

- [x] **TAX-01**: User can run graphify with no vault profile and receive generated notes under a Graphify-owned default subtree.
- [x] **TAX-02**: User can find default concept MOCs under `Atlas/Sources/Graphify/MOCs/`.
- [x] **TAX-03**: User-authored v1.8 vault profiles can override default folder placement through `taxonomy:`, while profiles missing `taxonomy:` or `mapping.min_community_size` fail validation.
- [x] **TAX-04**: User can validate a v1.8 profile and see actionable errors for unsupported taxonomy keys or invalid folder mappings.

### Community Output Semantics

- [ ] **COMM-01**: User receives MOC-only community output by default, with no generated `_COMMUNITY_*` overview notes.
- [ ] **COMM-02**: User sees legacy `_COMMUNITY_*` files surfaced as migration candidates or orphans instead of silently ignored.
- [x] **COMM-03**: User receives targeted guidance when an existing custom profile or template requests hard-deprecated community overview output.

### Cluster Quality Floor

- [x] **CLUST-01**: User can set `mapping.min_community_size` in the vault profile to control the minimum size for standalone MOC generation.
- [ ] **CLUST-02**: User sees isolate communities omitted from standalone MOC generation while their nodes remain available in graph data and non-community exports.
- [ ] **CLUST-03**: User sees tiny connected communities below the configured floor routed deterministically into an `_Unclassified` MOC.
- [x] **CLUST-04**: User receives a deterministic validation failure when legacy `mapping.moc_threshold` is present, including when `mapping.min_community_size` is also present.

### Concept Naming

- [x] **NAME-01**: User receives human-readable concept MOC titles from cached LLM naming when concept naming is enabled.
- [x] **NAME-02**: User receives stable deterministic fallback concept names when LLM naming is unavailable, disabled by budget, or rejected by validation.
- [ ] **NAME-03**: User can rerun graphify on an unchanged community and keep the same concept MOC filename across runs.
- [ ] **NAME-04**: User can inspect concept naming provenance in generated MOC metadata or dry-run output.
- [ ] **NAME-05**: User is protected from unsafe LLM-generated labels through filename, tag, wikilink, Dataview, and frontmatter sanitization.

### God-Node Taxonomy

- [ ] **GOD-01**: User sees code-derived god nodes exported as `CODE_<repo>_<node>` notes rather than generic Things.
- [ ] **GOD-02**: User sees CODE notes linked to their related concept MOC through frontmatter or body wikilinks.
- [ ] **GOD-03**: User sees concept MOCs list their important CODE member notes, preserving bidirectional navigation.
- [ ] **GOD-04**: User is protected from filename collisions between CODE notes and concept MOCs.

### Repo Identity

- [x] **REPO-01**: User can provide repo identity through a CLI flag with highest precedence.
- [x] **REPO-02**: User can provide repo identity through `profile.yaml` when no CLI override is supplied.
- [x] **REPO-03**: User gets a deterministic auto-derived repo identity from git remote or current working directory when no explicit identity exists.
- [ ] **REPO-04**: User sees the resolved repo identity recorded consistently in CODE note filenames, frontmatter, tags, and output manifests.

### Migration and Rollout

- [ ] **MIG-01**: User can run an automated migration command for the real `work-vault` to `ls-vault` update path.
- [ ] **MIG-02**: User can preview migration effects in dry-run mode before any vault writes occur.
- [ ] **MIG-03**: User sees old managed paths mapped to new Graphify-owned paths when note identity can be matched.
- [ ] **MIG-04**: User can review CREATE, UPDATE, SKIP_PRESERVE, SKIP_CONFLICT, REPLACE, and ORPHAN outcomes before committing to the migration.
- [ ] **MIG-05**: User receives a Markdown migration guide with backup, validation, dry-run, migration command, review, cleanup, rollback, and rerun steps.
- [ ] **MIG-06**: User never has legacy vault notes automatically deleted during migration.

### Verification and Compatibility

- [ ] **VER-01**: Maintainer can verify v1.8 behavior with pure unit tests that use `tmp_path` and perform no network calls.
- [ ] **VER-02**: Maintainer can confirm skill files and CLI docs use the same v1.8 Obsidian export behavior.
- [ ] **VER-03**: Maintainer can confirm all new path, template, profile, LLM-label, and repo-identity inputs pass through existing security/sanitization helpers.

## Future Requirements

Deferred to future releases.

### Onboarding

- **ONB-01**: User can use a Tacit-to-Explicit Elicitation Engine to discover vault/profile intent.

### Harness Memory

- **HAR-01**: User can export memory for additional agent harnesses beyond the current Claude target.
- **HAR-02**: User can safely inverse-import harness memory with prompt-injection defenses.

### Vault Selection

- **VAULT-01**: User can pass an explicit `--vault` flag for multi-vault workflows.
- **VAULT-02**: User can choose among multiple detected vaults through a selector.

## Out of Scope

Explicitly excluded from v1.8 to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Replacing the clustering algorithm | v1.8 changes output semantics, not graph topology. |
| Automatic deletion of legacy vault notes | Destructive cleanup risks user data loss; migration must be review-first. |
| Obsidian plugin behavior or `.obsidian/graph.json` management | The adapter outputs Markdown/frontmatter, not plugin configuration. |
| Manual LLM naming approval queues | Cached LLM naming is in scope; approval workflows are separate product surface. |
| New required runtime dependencies | Research found the existing stdlib, NetworkX, profile, merge, template, and cache patterns sufficient. |
| Fixing the two baseline test failures | Pre-existing failures remain a separate `/gsd-debug` session. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TAX-01 | Phase 32 | Complete |
| TAX-02 | Phase 32 | Complete |
| TAX-03 | Phase 32 | Complete |
| TAX-04 | Phase 32 | Complete |
| COMM-01 | Phase 34 | Pending |
| COMM-02 | Phase 35 | Pending |
| COMM-03 | Phase 32 | Complete |
| CLUST-01 | Phase 32 | Complete |
| CLUST-02 | Phase 34 | Pending |
| CLUST-03 | Phase 34 | Pending |
| CLUST-04 | Phase 32 | Complete |
| NAME-01 | Phase 33 | Complete |
| NAME-02 | Phase 33 | Complete |
| NAME-03 | Phase 33 | Pending |
| NAME-04 | Phase 33 | Pending |
| NAME-05 | Phase 33 | Pending |
| GOD-01 | Phase 34 | Pending |
| GOD-02 | Phase 34 | Pending |
| GOD-03 | Phase 34 | Pending |
| GOD-04 | Phase 34 | Pending |
| REPO-01 | Phase 33 | Complete |
| REPO-02 | Phase 33 | Complete |
| REPO-03 | Phase 33 | Complete |
| REPO-04 | Phase 35 | Pending |
| MIG-01 | Phase 35 | Pending |
| MIG-02 | Phase 35 | Pending |
| MIG-03 | Phase 35 | Pending |
| MIG-04 | Phase 35 | Pending |
| MIG-05 | Phase 36 | Pending |
| MIG-06 | Phase 35 | Pending |
| VER-01 | Phase 36 | Pending |
| VER-02 | Phase 36 | Pending |
| VER-03 | Phase 36 | Pending |

**Coverage:**
- v1.8 requirements: 33 total
- Mapped to phases: 33
- Unmapped: 0

---
*Requirements defined: 2026-04-28*
*Last updated: 2026-04-28 after v1.8 roadmap creation*
