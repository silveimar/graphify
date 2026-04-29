# Milestone v1.8 — Project Summary

**Generated:** 2026-04-29  
**Purpose:** Team onboarding and project review  
**Milestone name:** Output Taxonomy & Cluster Quality  
**Canonical archives:** `.planning/milestones/v1.8-ROADMAP.md`, `v1.8-REQUIREMENTS.md`, `v1.8-MILESTONE-AUDIT.md`

---

## 1. Project Overview

**What this is (from `.planning/PROJECT.md`):** Graphify’s configurable vault adapter injects knowledge-graph output (nodes, edges, communities, analysis) into Obsidian vaults using a declarative `.graphify/profile.yaml` plus templates. Without a profile, graphify falls back to a built-in Ideaverse-compatible ACE-shaped layout.

**Core value:** Any Obsidian vault framework can receive structured graph output **without code forks**—behavior is driven by the vault-side profile.

**Who benefits:** Developers and knowledge workers using graphify as a library or CLI; Obsidian users who want migration-safe, preview-first vault updates and readable default taxonomy.

**What v1.8 delivered:** Default Graphify-owned taxonomy under `Atlas/Sources/Graphify/`, **MOC-only** community output (no new `_COMMUNITY_*` overviews), `mapping.min_community_size` as the canonical cluster-quality floor, cached LLM concept naming with deterministic fallbacks, **CODE** vs concept note classes, **repo identity** resolution (CLI → profile → git → directory), preview-first **`update-vault`** migration with reviewed `--apply --plan-id`, platform skill text aligned to the v1.8 contract, Nyquist **validation metadata** ratification (Phase 37), and Phase **38** docs-only reconciliation of dormant seeds and quick-task lifecycle before the next milestone.

---

## 2. Architecture & Technical Decisions

High-level technical choices made during v1.8 (see `.planning/STATE.md` “Decisions” and phase summaries for detail):

- **Decision:** Resolve **taxonomy + mapping contract** at profile load so downstream mapping/export consume a single `folder_mapping` truth (`taxonomy:` overrides; invalid legacy keys fail validation).
  - **Why:** Keeps mapping.py and export paths stable while centralizing v1.8 taxonomy rules (Phase 32).
  - **Phase:** 32–34.

- **Decision:** **MOC-only** default community output; legacy `_COMMUNITY_*` paths are migration/review surfaces, not silently ignored.
  - **Why:** Legible vaults and safe migration from older layouts (Phases 32, 34, 35).
  - **Phase:** 32, 34, 35.

- **Decision:** **`mapping.min_community_size`** is the only standalone cluster floor key; **`mapping.moc_threshold`** is a hard validation error.
  - **Why:** Prevents silent legacy precedence; tiny/hostless communities route deterministically (e.g. `_Unclassified`) (Phases 32, 34).
  - **Phase:** 32, 34.

- **Decision:** **Repo identity** resolved in `graphify.naming` with precedence **CLI > profile > git remote > cwd**; **`repo.identity`** is the profile field (reject duplicate `naming.repo`).
  - **Why:** Stable CODE filenames, manifests, and tags (Phase 33–35).

- **Decision:** **Concept naming** uses cache + sidecar provenance under the artifacts directory; unsafe LLM titles rejected before persistence.
  - **Why:** Stable filenames across reruns and sanitization for wikilinks/frontmatter (Phase 33).

- **Decision:** **CODE notes** for code-derived god nodes with collision-safe stems and bidirectional links to concept MOCs; export dispatches community rendering to MOC templates only.
  - **Why:** Separates code hubs from concept MOCs while preserving navigation (Phase 34).

- **Decision:** **Migration** uses deterministic **plan IDs** (hash of normalized preview payload), review-first **CREATE/UPDATE/SKIP/ORPHAN** rows, **non-destructive** apply (archive + rollback metadata under `graphify-out/migrations/archive/`).
  - **Why:** Real `work-vault` → target vault path without silent deletes (Phases 35–36).

- **Decision:** **Doctor** calls the same **`validate_profile_preflight()`** path as `--validate-profile` so diagnostics match direct validation (Phase 32).

- **Decision:** Phase **37** was **metadata-only**—normalize Nyquist frontmatter in validation artifacts without changing runtime behavior; Phase **38** was **docs-only**—no runtime code changes.

**Stack (unchanged core):** Python 3.10+, NetworkX, tree-sitter extractors, optional graspologic/MCP/Neo4j per `pyproject.toml`. Tests remain **pure unit tests** with `tmp_path` (no network) per VER-01.

---

## 3. Phases Delivered

| Phase | Name | Status | One-liner (rollup) |
|-------|------|--------|---------------------|
| 32 | Profile Contract & Defaults | Complete | Doctor diagnostics now surface the same v1.8 profile preflight errors and warnings as direct profile validation, with warning-only community overview guidance kept nonfatal. |
| 33 | Naming & Repo Identity Helpers | Complete | Repo identity and concept naming flow through CLI and Obsidian export, with durable sidecar provenance and sanitized generated MOC titles. |
| 34 | Mapping, Cluster Quality & Note Classes | Complete | Concept MOCs link to generated CODE notes using exact collision-safe filename stems while preserving sanitized display aliases. |
| 35 | Templates, Export Plumbing & Dry-Run/Migration Visibility | Complete | Preview-first raw corpus to Obsidian vault updates with reviewed plan-id apply gates and repo-drift conflict visibility. |
| 36 | Migration Guide, Skill Alignment & Regression Sweep | Complete | Install-time Claude/AGENTS guidance matches the v1.8 Obsidian navigation contract and is covered by regression tests. |
| 37 | Validation Metadata Ratification | Complete | v1.8 milestone audit metadata debt was closed and Phase 37 planning/validation tracking was ratified for deterministic closeout automation. |
| 38 | Dormant seeds & quick-task reconciliation | Complete | Planning-only reconciliation of dormant seed posture and quick-task lifecycle with command-backed verification artifacts (no runtime code changes). |

---

## 4. Requirements Coverage

Source: `.planning/milestones/v1.8-REQUIREMENTS.md` (archived). All **in-scope** v1.8 requirement IDs are marked satisfied.

| Group | IDs | Status |
|-------|-----|--------|
| Default output taxonomy | TAX-01 — TAX-04 | ✅ Satisfied |
| Community output semantics | COMM-01 — COMM-03 | ✅ Satisfied |
| Cluster quality floor | CLUST-01 — CLUST-04 | ✅ Satisfied |
| Concept naming | NAME-01 — NAME-05 | ✅ Satisfied |
| God-node taxonomy (CODE notes) | GOD-01 — GOD-04 | ✅ Satisfied |
| Repo identity | REPO-01 — REPO-04 | ✅ Satisfied |
| Migration and rollout | MIG-01 — MIG-06 | ✅ Satisfied |
| Verification and compatibility | VER-01 — VER-03 | ✅ Satisfied |

**Explicitly future / out of scope for v1.8:** ONB-01 (elicitation engine), HAR-01/02 (harness memory / inverse import), VAULT-01/02 (explicit multi-vault UX)—listed under Future Requirements in the archive.

**Milestone audit:** `.planning/milestones/v1.8-MILESTONE-AUDIT.md` — **passed**; **33/33** requirements satisfied; integration checker **18/18** links and **5/5** E2E flows passed (per audit document; Phase 37 closed Nyquist metadata debt; Phase 38 is planning hygiene only).

---

## 5. Key Decisions Log

Aggregated themes (full enumerate with phase tags in `.planning/STATE.md`):

| Theme | Decision | Rationale |
|-------|-----------|-----------|
| Layout | Default concept MOCs under `Atlas/Sources/Graphify/MOCs/` | Graphify-owned subtree for legible defaults |
| Community output | MOC-only by default; deprecate `_COMMUNITY_*` generation | Cleaner vault + migration visibility |
| Cluster floor | `mapping.min_community_size` canonical; reject `mapping.moc_threshold` | Deterministic routing + validation |
| Naming | Cached LLM naming + deterministic fallback + sanitization | Stable filenames and safe display |
| Identity | Centralized `resolve_repo_identity()` precedence rules | Consistent CODE filenames and manifests |
| Migration | Preview-first, plan-id apply, archive path, no auto-delete | Safe existing-vault upgrades |
| Verification | Nyquist metadata ratified for automated discovery (Phase 37) | Audit automation without behavior change |
| Governance | Phase 38 docs-only seed/quick-task reconciliation | Clean handoff before next milestone |

---

## 6. Tech Debt & Deferred Items

**From milestone audit (YAML):** `tech_debt: []` — no audit-tracked tech debt rows at close.

**From `.planning/STATE.md` — deferred / future:**

- **SEED-001** (tacit-to-explicit elicitation), **SEED-002** (multi-harness / inverse import): **dormant** until product demand and prerequisites.
- **Vault selection:** explicit `--vault` and multi-vault selector — **future milestone**.
- **Baseline tests:** `test_detect_skips_dotfiles`, `test_collect_files_from_dir` — tracked for a dedicated **`/gsd-debug`** session (pre-existing scope).
- **Quick task** `260427-rc7-fix-detect-self-ingestion`: acknowledged at ship as **missing** — backlog or debug session (per STATE milestone close table).

**RETROSPECTIVE:** `.planning/milestones/RETROSPECTIVE.md` does not yet contain a dedicated **v1.8** section; lessons from earlier milestones remain general guidance (verification timing, SUMMARY frontmatter consistency, etc.).

---

## 7. Getting Started

**Install & test (from `CLAUDE.md`):**

```bash
pip install -e ".[mcp,pdf,watch]"   # CI-parity optional set
pytest tests/ -q
graphify --help
```

**Key code locations:**

| Area | Module(s) |
|------|-----------|
| Profile load / validation | `graphify/profile.py` |
| Mapping & note classes | `graphify/mapping.py` |
| Templates / block engine | `graphify/templates.py` |
| Obsidian export orchestration | `graphify/export.py` (`to_obsidian`) |
| Naming / repo identity / CODE stems | `graphify/naming.py` |
| Vault migration / merge plans | `graphify/migration.py`, `graphify/merge.py` |
| Doctor | `graphify/doctor.py` |
| CLI entry | `graphify/__main__.py` |

**Where to read first:** `.planning/PROJECT.md` (product intent), `.planning/milestones/v1.8-ROADMAP.md` (phase goals), `CLAUDE.md` (build/test and pipeline map).

**Planning / GSD:** Next orchestrated step is **`/gsd-new-milestone`** when you are ready to define v1.9 (or the next label).

---

## Stats

- **Timeline:** 2026-04-28 → 2026-04-29 (v1.7 tag → v1.8 ship window; dense execution culminating in archive on 2026-04-29)
- **Phases:** 7 / 7 complete (Phases 32–38)
- **Plans:** 25 / 25 complete (per `.planning/STATE.md` progress block)
- **Commits (range):** 129 commits (`git log v1.7..v1.8`)
- **Files changed (range):** 216 files (`git diff --stat v1.7..v1.8`: +26594 / −17241 lines)
- **Contributors:** silveimar

---

*End of milestone summary v1.8.*
