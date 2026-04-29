# Phase 33: Naming & Repo Identity Helpers - Research

**Researched:** 2026-04-28  
**Domain:** Python CLI/export identity helpers for Obsidian note naming  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The resolved repo identity should be a short stable slug such as `graphify` or `work-vault`, optimized for readability in filenames, tags, and manifests.
- **D-02:** Source precedence is CLI flag first, profile second, deterministic fallback third. The winning source must be printed to stderr during runs and recorded durably in the manifest.
- **D-03:** Profile-supplied identity belongs in a top-level `repo:` block, with a key such as `repo.identity`. Do not hide repo identity under `naming:`.
- **D-04:** Fallback should derive from the git remote slug first, then the current directory name when no remote-derived identity exists. Offline/local projects must still produce deterministic output.
- **D-05:** LLM concept naming should be default-on for the built-in/default v1.8 profile, with deterministic fallback so offline, budget-limited, or no-key runs still produce valid output.
- **D-06:** Vault profiles may control concept naming with enable/disable plus budget/style hints. Avoid exposing full prompt templates in Phase 33.
- **D-07:** Unsafe, empty, duplicate, or overly generic LLM-generated titles must be rejected. Graphify should use the deterministic fallback and record/warn the provenance rather than failing the run.
- **D-08:** Deterministic fallback names should use top meaningful terms plus a community id/hash suffix, e.g. `Auth Session Flow c12`, rather than plain `Community 12` or a single top-node label.
- **D-09:** Concept naming cache keys should be based on a community signature from sorted member node IDs plus labels/source files, not the raw community ID alone.
- **D-10:** Cache reuse should tolerate small member changes when the top terms/signature remain close enough, to avoid filename churn from tiny graph drift.
- **D-11:** Concept naming cache/provenance should live in a `graphify-out/` sidecar cache or manifest, matching existing generated-artifact conventions and avoiding writes to vault-owned `.graphify/` configuration.
- **D-12:** Manual concept-name override behavior is not in Phase 33. Design the cache/schema so future profile overrides can win later, but do not add an approval UI or frontmatter round-trip override in this phase.
- **D-13:** Explicit cache refresh UI is deferred. Keep the cache format ready for a future clear/force naming cache command without adding a new Phase 33 CLI flag solely for refresh.

### Claude's Discretion
No selected decision was delegated to Claude. Planner may choose implementation details that preserve the decisions above and the repo's existing helper style.

### Deferred Ideas (OUT OF SCOPE)
None - discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NAME-01 | User receives human-readable concept MOC titles from cached LLM naming when concept naming is enabled. | Add a helper that computes candidate MOC titles before `to_obsidian()` injects `community_labels`, and persist accepted LLM titles in a graphify-out sidecar. [VERIFIED: `.planning/REQUIREMENTS.md`, `graphify/export.py`] |
| NAME-02 | User receives stable deterministic fallback concept names when LLM naming is unavailable, disabled by budget, or rejected by validation. | Replace/augment `_derive_community_label()` with a deterministic top-terms-plus-suffix helper that never requires network/LLM availability. [VERIFIED: `graphify/mapping.py`] |
| NAME-03 | User can rerun graphify on an unchanged community and keep the same concept MOC filename across runs. | Key the naming cache by a sorted community signature rather than raw community ID; `render_moc()` already converts `community_name` into the final filename via `resolve_filename()`. [VERIFIED: `graphify/templates.py`] |
| NAME-04 | User can inspect concept naming provenance in generated MOC metadata or dry-run output. | Provenance should be stored in the sidecar and threaded into `ClassificationContext`/frontmatter later; dry-run can surface the same data without writes. [VERIFIED: `graphify/export.py`, `graphify/templates.py`] |
| NAME-05 | User is protected from unsafe LLM-generated labels through filename, tag, wikilink, Dataview, and frontmatter sanitization. | Reuse `safe_filename`, `safe_tag`, `safe_frontmatter_value`, `_sanitize_wikilink_alias`, and existing Dataview/template substitution flow. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`] |
| REPO-01 | User can provide repo identity through a CLI flag with highest precedence. | Add a flag near existing `--output` parsing paths, then resolve identity before export naming depends on it. [VERIFIED: `graphify/__main__.py`] |
| REPO-02 | User can provide repo identity through `profile.yaml` when no CLI override is supplied. | Extend `_VALID_TOP_LEVEL_KEYS` and `validate_profile()` for a top-level `repo:` block. [VERIFIED: `graphify/profile.py`] |
| REPO-03 | User gets a deterministic auto-derived repo identity from git remote or current working directory when no explicit identity exists. | Implement fallback with stdlib parsing of `.git/config` where possible, falling back to `Path.cwd().name`; do not require the `git` CLI. [VERIFIED: `pyproject.toml`, `graphify/output.py`] |
</phase_requirements>

## Summary

Phase 33 should be planned as a helper-layer phase, not an export rewrite. The existing pipeline already has the main insertion points: `profile.load_profile()` merges and validates vault configuration, `__main__.py` handles CLI precedence for output options, `mapping.classify()` assembles per-community contexts, `export.to_obsidian()` can inject `community_labels`, and `templates.render_moc()` turns `community_name` into filenames, tags, wikilinks, Dataview input, and frontmatter. [VERIFIED: `graphify/profile.py`, `graphify/__main__.py`, `graphify/mapping.py`, `graphify/export.py`, `graphify/templates.py`]

The primary planning move is to add a small identity/naming module that produces plain dicts/NamedTuples and is consumed by these existing seams. Repo identity resolution should mirror `output.resolve_output()` precedence and stderr reporting. Concept naming should feed the existing `community_labels` and `ClassificationContext.community_name` contract, with a graphify-out sidecar cache/provenance file using the same atomic write and malformed-cache fallback style as cache and manifest code. [VERIFIED: `graphify/output.py`, `graphify/cache.py`, `graphify/detect.py`, `graphify/merge.py`]

**Primary recommendation:** Create `graphify/naming.py` with `resolve_repo_identity()`, `resolve_concept_names()`, deterministic fallback/signature helpers, validation/provenance dataclasses, and sidecar JSON load/save; wire it through profile validation, CLI flags, and `to_obsidian()` without adding required dependencies. [VERIFIED: codebase structure and `pyproject.toml`]

## Project Constraints (from .cursor/rules/)

| Rule Source | Actionable Directive |
|-------------|----------------------|
| `.cursor/rules/graphify.mdc` | No additional actionable directive beyond `alwaysApply: true`. [VERIFIED: `.cursor/rules/graphify.mdc`] |
| `CLAUDE.md` | Preserve Python 3.10+ compatibility, no new required dependencies, pure unit tests, no network calls, no filesystem side effects outside `tmp_path`. [VERIFIED: `CLAUDE.md`] |
| `CLAUDE.md` | Use existing profile, security, cache, export, and test patterns; no formatter/linter is configured, CI runs pytest on Python 3.10 and 3.12. [VERIFIED: `CLAUDE.md`] |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CLI repo identity override | CLI / Entrypoint | Profile layer | CLI parsing owns user flags and already applies precedence for `--output`; profile validation owns schema. [VERIFIED: `graphify/__main__.py`, `graphify/profile.py`] |
| Profile repo identity | Profile layer | Export layer | Profile schema should accept `repo.identity`; export consumes only the resolved result. [VERIFIED: `graphify/profile.py`, `graphify/export.py`] |
| Deterministic repo fallback | Helper library | CLI / Export | A pure helper can inspect git config/cwd deterministically without tying behavior to a command path. [VERIFIED: `pyproject.toml`] |
| Concept MOC naming | Helper library | Mapping / Export / Templates | Mapping has current community labels, export already accepts injected labels, and templates already render the final filename and metadata. [VERIFIED: `graphify/mapping.py`, `graphify/export.py`, `graphify/templates.py`] |
| Concept naming cache/provenance | Generated artifact sidecar | Merge manifest | Sidecar belongs under `graphify-out/`, not vault-owned `.graphify/`; existing cache/manifests provide the persistence pattern. [VERIFIED: `graphify/cache.py`, `graphify/detect.py`, `graphify/merge.py`] |
| Sanitization | Profile/template helpers | Security module | The exact output surfaces already route through `safe_filename`, `safe_tag`, frontmatter dumping, wikilink alias scrubbing, and Dataview block generation. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`pathlib`, `json`, `hashlib`, `re`, `configparser`, `os`) | Python 3.10+ | Repo identity fallback, JSON sidecars, deterministic signatures, atomic writes. | Project core already favors stdlib helpers and has a no-new-required-dependencies constraint. [VERIFIED: `CLAUDE.md`, `pyproject.toml`] |
| NetworkX | 3.4.2 installed locally | Read graph/community members and node attributes for naming signatures and top terms. | Existing graph abstraction for all pipeline stages. [VERIFIED: local package metadata, `CLAUDE.md`] |
| PyYAML | 6.0.3 installed locally, optional dependency | Parse `profile.yaml` when vault profiles are used. | Already optional via `obsidian`/`routing` extras and guarded at import time. [VERIFIED: local package metadata, `pyproject.toml`, `graphify/profile.py`] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git` CLI | 2.50.1 available locally | Test fixture setup or manual verification only. | Implementation should parse `.git/config` or use cwd fallback so local/offline projects do not require a subprocess. [VERIFIED: local command, `pyproject.toml`] |
| Existing `graphify.enrich` LLM shim | Internal | Optional reference for budget accounting and monkeypatched LLM calls. | Use the budget/dry-run pattern, but avoid coupling naming to enrichment overlays. [VERIFIED: `graphify/enrich.py`] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stdlib `.git/config` parsing | Shell out to `git config --get remote.origin.url` | Shelling out is simpler but makes fallback depend on an external command and complicates tests; stdlib parsing is deterministic and pure. [VERIFIED: `pyproject.toml`, local `git` availability] |
| Sidecar naming cache | Store names in vault `.graphify/profile.yaml` | `.graphify/` is user-owned configuration; Phase 33 explicitly requires generated cache/provenance in `graphify-out/`. [VERIFIED: `33-CONTEXT.md`] |
| Exposing full prompt templates | Profile prompt customization | Phase 33 explicitly defers full prompt templates; use enable/disable, budget, and style hints only. [VERIFIED: `33-CONTEXT.md`] |

**Installation:** No new package installation is recommended. [VERIFIED: `CLAUDE.md`, `pyproject.toml`]

## Architecture Patterns

### System Architecture Diagram

```text
CLI flags / profile.yaml / cwd
        |
        v
resolve_repo_identity()
  |-- CLI identity wins
  |-- profile repo.identity wins
  |-- git remote slug fallback
  `-- cwd name fallback
        |
        v
RepoIdentity(slug, source, raw, warnings)
        |
        +--> stderr source report
        +--> graphify-out sidecar/manifest metadata

Graph + communities + profile
        |
        v
resolve_concept_names()
  |-- compute stable community signatures
  |-- load graphify-out naming cache
  |-- optional LLM title candidate
  |-- validate generated title
  `-- deterministic fallback
        |
        v
community_labels + provenance
        |
        v
export.to_obsidian() -> mapping contexts -> templates.render_moc()
        |
        v
safe filenames, tags, wikilinks, Dataview queries, frontmatter
```

### Recommended Project Structure

```text
graphify/
├── naming.py        # repo identity + concept naming helpers and sidecar IO
├── profile.py       # schema/defaults for repo + naming controls
├── __main__.py      # CLI identity flag parsing and stderr source reporting
├── export.py        # invokes naming helpers before MOC render
└── templates.py     # unchanged final filename/frontmatter/wikilink sink
tests/
├── test_naming.py   # pure helper tests for identity, signatures, cache, fallback
├── test_profile.py  # repo/naming schema validation additions
├── test_export.py   # to_obsidian community_labels/provenance integration
└── test_main.py or test_cli.py # CLI flag parsing/source reporting if existing pattern supports it
```

### Pattern 1: Resolver Returns Plain Data and Source

**What:** Follow `ResolvedOutput`: a small `NamedTuple` that contains the resolved value and the source that won. [VERIFIED: `graphify/output.py`]

**When to use:** Repo identity resolution should expose `identity`, `source`, `raw_value`, and warnings without mutating global state. [VERIFIED: `33-CONTEXT.md`]

**Example:**

```python
class ResolvedRepoIdentity(NamedTuple):
    identity: str
    source: Literal["cli-flag", "profile", "fallback-git-remote", "fallback-directory"]
    raw_value: str
    warnings: tuple[str, ...] = ()
```

### Pattern 2: Cache Sidecar Uses Stable JSON and Atomic Replace

**What:** Existing cache/manifest writers load malformed files defensively and write via temp file plus `os.replace()`. [VERIFIED: `graphify/cache.py`, `graphify/detect.py`, `graphify/merge.py`]

**When to use:** Concept naming cache/provenance should use `graphify-out/concept-names.json` or `graphify-out/naming-cache.json`, not vault `.graphify/`. [VERIFIED: `33-CONTEXT.md`]

**Example:**

```python
def _community_signature(G, members: list[str]) -> str:
    payload = [
        {
            "id": node_id,
            "label": str(G.nodes[node_id].get("label", node_id)),
            "source_file": str(G.nodes[node_id].get("source_file", "")),
        }
        for node_id in sorted(members)
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
```

### Pattern 3: Existing MOC Render Path Should Stay the Final Sanitization Sink

**What:** `render_moc()` reads `ctx["community_name"]`, derives `community_tag = safe_tag(community_name)`, emits frontmatter through `_dump_frontmatter()`, uses `_emit_wikilink()`, and resolves the filename through `resolve_filename()`. [VERIFIED: `graphify/templates.py`]

**When to use:** The naming helper should provide a validated display label, then let the template layer apply final sink-specific sanitization. [VERIFIED: `graphify/templates.py`]

### Anti-Patterns to Avoid

- **Putting repo identity under `naming:`:** The locked decision requires a top-level `repo:` block. [VERIFIED: `33-CONTEXT.md`]
- **Raw community ID cache keys:** Community IDs can drift; use sorted member IDs plus labels/source files. [VERIFIED: `33-CONTEXT.md`, `graphify/mapping.py`]
- **Failing export because LLM naming failed:** The requirement is fallback plus provenance/warning, not a hard failure. [VERIFIED: `.planning/REQUIREMENTS.md`, `33-CONTEXT.md`]
- **Writing generated naming state into `.graphify/`:** `.graphify/` is configuration; generated state belongs under `graphify-out/`. [VERIFIED: `33-CONTEXT.md`]
- **Trusting sanitized filename as sanitized YAML/Dataview/tag text:** Each sink needs its existing sanitizer: filename, tag, wikilink alias, frontmatter, and Dataview strings are not interchangeable. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`] 

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML frontmatter emitting | A new YAML serializer | `_dump_frontmatter()` and `safe_frontmatter_value()` | Existing dumper is intentionally symmetric with merge parsing and avoids new dependencies. [VERIFIED: `graphify/profile.py`, `graphify/merge.py`] |
| Filename sanitization | New regex per caller | `resolve_filename()` / `safe_filename()` | Existing helper handles Unicode normalization, illegal characters, control chars, max length, and hash suffix. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`] |
| Tags | Ad hoc lowercasing | `safe_tag()` | Existing helper normalizes to lowercase hyphenated tag-safe strings and handles empty/digit-leading cases. [VERIFIED: `graphify/profile.py`] |
| Wikilinks | Raw `[[{label}]]` strings | `_emit_wikilink()` flow via templates | Existing helper separates filename target from display alias and scrubs alias-breaking characters. [VERIFIED: `graphify/templates.py`] |
| Manifest/cache IO | Bare writes | Existing temp + `os.replace()` style | Existing generated artifacts degrade gracefully on corrupt JSON and write atomically. [VERIFIED: `graphify/cache.py`, `graphify/detect.py`, `graphify/merge.py`] |
| Git URL parsing via dependency | GitPython or dulwich | Stdlib parsing of `.git/config` plus regex/urllib parsing | No new required dependencies; fallback must work offline/local. [VERIFIED: `CLAUDE.md`, `pyproject.toml`, `33-CONTEXT.md`] |

**Key insight:** Phase 33 is about stable identity surfaces; custom one-off sanitation or cache logic would create filename/frontmatter drift exactly where downstream phases need trust. [VERIFIED: phase success criteria]

## Common Pitfalls

### Pitfall 1: Community ID Drift Causes Filename Churn

**What goes wrong:** A cached name keyed only by `cid` is reused for the wrong cluster or missed after clustering shifts. [VERIFIED: `33-CONTEXT.md`]  
**Why it happens:** Community IDs are assigned after graph clustering and can change with graph topology. [VERIFIED: `CLAUDE.md`, `graphify/mapping.py`]  
**How to avoid:** Key exact cache entries by a sorted member signature and store top-term summaries for small-change tolerant lookup. [VERIFIED: `33-CONTEXT.md`]  
**Warning signs:** Tests only assert `Community 0` output on one fixture; no test changes member order or cid. [VERIFIED: existing tests inspected]

### Pitfall 2: LLM Title Accepted Before Sink Validation

**What goes wrong:** A title with `]]`, `|`, YAML-reserved values, control chars, or Dataview-sensitive text looks fine in one surface but breaks another. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`]  
**Why it happens:** Filename, tag, wikilink alias, YAML, and Dataview contexts have different escaping rules. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`]  
**How to avoid:** Validate the raw LLM candidate for emptiness, generic names, duplicates, length, and unsafe structural tokens; then still route accepted/fallback names through existing sink-specific helpers. [VERIFIED: `33-CONTEXT.md`]  
**Warning signs:** Tests check `safe_filename()` but not generated LLM labels across all sinks. [VERIFIED: `tests/test_profile.py`, `tests/test_templates.py`]

### Pitfall 3: CLI and Profile Precedence Diverge Between Commands

**What goes wrong:** `graphify run` and `graphify --obsidian` disagree about which repo identity won. [VERIFIED: `graphify/__main__.py`]  
**Why it happens:** CLI parsing is currently duplicated in command-specific branches for options such as `--output`. [VERIFIED: `graphify/__main__.py`]  
**How to avoid:** Centralize repo identity resolution in one helper and call it from both command paths; assert source strings and stderr messages in tests. [VERIFIED: `graphify/output.py`]

### Pitfall 4: Fallback Repo Identity Depends on Installed Git

**What goes wrong:** Offline/local projects without a working git executable get unstable or failing identity resolution. [VERIFIED: `33-CONTEXT.md`]  
**Why it happens:** Subprocess-based git discovery can fail for bare repos, missing git, restricted PATH, or non-git directories. [ASSUMED]  
**How to avoid:** Parse `.git/config` with stdlib when present and fall back to cwd name; use the git CLI only in optional manual checks. [VERIFIED: `pyproject.toml`, local environment]

### Pitfall 5: Cache Tolerance Reuses a Stale Bad Name

**What goes wrong:** Small-change tolerance preserves a name after the community meaning actually changes. [VERIFIED: `33-CONTEXT.md`]  
**Why it happens:** A fuzzy match on top terms can be too permissive. [ASSUMED]  
**How to avoid:** Prefer exact signature matches; allow tolerant reuse only when top terms overlap strongly and record `provenance.source="cache-tolerant"` with previous/current signatures. [VERIFIED: `33-CONTEXT.md`]  
**Warning signs:** Provenance lacks the signature used to accept a cached title. [ASSUMED]

## Code Examples

### Repo Identity Resolution Shape

```python
# Source: existing ResolvedOutput pattern in graphify/output.py
class ResolvedRepoIdentity(NamedTuple):
    identity: str
    source: Literal["cli-flag", "profile", "fallback-git-remote", "fallback-directory"]
    raw_value: str
    warnings: tuple[str, ...] = ()
```

### Concept Naming Output Shape

```python
# Source: existing plain-dict / NamedTuple project style in graphify/profile.py and graphify/output.py
class ConceptName(NamedTuple):
    community_id: int
    title: str
    filename_stem: str
    source: Literal["llm-cache", "llm-fresh", "fallback", "cache-tolerant"]
    signature: str
    reason: str
```

### Export Integration

```python
# Source: graphify/export.py already injects community_labels into per_community context
concept_names = resolve_concept_names(G, communities, profile, artifacts_dir=out.parent)
community_labels = {cid: name.title for cid, name in concept_names.items()}
result = to_obsidian(G, communities, output_dir, community_labels=community_labels)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Community MOC label from the top real node only | Stable naming helper with LLM/cache/fallback/provenance | Phase 33 planned | Prevents filenames from depending on a single top node or raw cid. [VERIFIED: `graphify/mapping.py`, `33-CONTEXT.md`] |
| Output destination precedence only | Separate repo identity precedence CLI > profile > fallback | Phase 33 planned | Mirrors existing source-reporting UX while serving CODE note filenames in later phases. [VERIFIED: `graphify/output.py`, `33-CONTEXT.md`] |
| Per-file extraction cache | Community naming cache keyed by semantic community signature | Phase 33 planned | Supports unchanged-community reruns and small graph drift. [VERIFIED: `graphify/cache.py`, `33-CONTEXT.md`] |

**Deprecated/outdated:**
- `_derive_community_label()` as the sole concept MOC title source should become fallback/input only, because it uses one top in-community real node and falls back to `Community {cid}`. [VERIFIED: `graphify/mapping.py`]
- Storing generated names in profile configuration is out of scope and contradicts the sidecar decision. [VERIFIED: `33-CONTEXT.md`]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Subprocess-based git discovery can fail in environments where stdlib `.git/config` parsing would still work. | Common Pitfalls | Planner may over-optimize for a failure mode that is unlikely but still harmless if stdlib fallback is used. |
| A2 | Tolerant cache reuse can preserve a stale bad name if overlap thresholds are too permissive. | Common Pitfalls | Planner needs tests around meaning-changing community edits, not just tiny drift. |
| A3 | Provenance without signatures will make cache reuse difficult to debug. | Common Pitfalls | Planner may omit fields that later migration/debug tooling needs. |

## Open Questions (RESOLVED)

1. **What exact CLI flag name should Phase 33 use?**
   - What we know: Requirements say CLI flag with highest precedence; existing CLI has `--output` in both `run` and `--obsidian` branches. [VERIFIED: `.planning/REQUIREMENTS.md`, `graphify/__main__.py`]
   - Resolution: Use `--repo-identity` as the Phase 33 CLI flag for clarity. Do not add a shorter alias in this phase. Route all CLI/profile/fallback identity values through the same resolver.

2. **Where should concept provenance become user-visible in Phase 33?**
   - What we know: NAME-04 allows generated MOC metadata or dry-run output; Phase 35 owns broader export plumbing/manifest consistency. [VERIFIED: `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`]
   - Resolution: Store complete provenance in the `graphify-out/` sidecar now and expose it through dry-run/diagnostic surfaces where Phase 33 touches export. Defer permanent MOC frontmatter schema expansion to Phase 35 unless required by tests to satisfy NAME-04.

3. **What LLM callable should production naming use?**
   - What we know: `graphify.enrich._call_llm()` is intentionally a monkeypatch placeholder, and extraction has model-aware cache patterns. [VERIFIED: `graphify/enrich.py`, `graphify/extract.py`]
   - Resolution: Define an injectable naming callable and test it with monkeypatches. Default production behavior must fall back deterministically when no callable/API key is available; do not introduce a required model router dependency in Phase 33.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Implementation and tests | yes | 3.10.19 | CI also runs 3.12. [VERIFIED: local command, `CLAUDE.md`] |
| pytest | Unit tests | yes | 9.0.3 | None needed locally. [VERIFIED: local command] |
| NetworkX | Graph/community inspection | yes | 3.4.2 | Already required dependency. [VERIFIED: local package metadata, `pyproject.toml`] |
| PyYAML | Profile YAML tests/integration | yes | 6.0.3 | Existing code falls back to default profile when unavailable. [VERIFIED: local package metadata, `graphify/profile.py`] |
| git CLI | Manual repo fallback verification | yes | 2.50.1 | Implementation should not require it; parse `.git/config` and fallback to cwd. [VERIFIED: local command, `33-CONTEXT.md`] |

**Missing dependencies with no fallback:** None. [VERIFIED: local environment checks]

**Missing dependencies with fallback:** None. [VERIFIED: local environment checks]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 locally; CI targets Python 3.10 and 3.12. [VERIFIED: local command, `CLAUDE.md`] |
| Config file | none found in required context; tests follow module-paired files under `tests/`. [VERIFIED: `CLAUDE.md`, tests inspected] |
| Quick run command | `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_mapping.py tests/test_export.py -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| NAME-01 | Cached LLM title is reused when concept naming is enabled. | unit | `python3 -m pytest tests/test_naming.py::test_concept_name_uses_cached_llm_title -q` | no - Wave 0 |
| NAME-02 | Fallback name is deterministic when LLM is disabled/unavailable/rejected. | unit | `python3 -m pytest tests/test_naming.py::test_fallback_name_uses_terms_and_suffix -q` | no - Wave 0 |
| NAME-03 | Same community signature yields same filename across reruns. | unit | `python3 -m pytest tests/test_naming.py::test_same_signature_reuses_filename -q` | no - Wave 0 |
| NAME-04 | Provenance records source, signature, and rejection/fallback reason. | unit | `python3 -m pytest tests/test_naming.py::test_concept_name_provenance_records_source -q` | no - Wave 0 |
| NAME-05 | Unsafe LLM labels are rejected or sanitized across filename/tag/wikilink/frontmatter sinks. | unit/integration | `python3 -m pytest tests/test_naming.py::test_unsafe_llm_title_rejected tests/test_templates.py -q` | partial - Wave 0 |
| REPO-01 | CLI repo identity wins over profile/fallback and reports source. | unit/CLI | `python3 -m pytest tests/test_naming.py::test_repo_identity_cli_wins -q` | no - Wave 0 |
| REPO-02 | `profile.yaml` `repo.identity` wins when CLI flag absent. | unit | `python3 -m pytest tests/test_profile.py::test_validate_profile_accepts_repo_identity tests/test_naming.py::test_repo_identity_profile_wins -q` | partial - Wave 0 |
| REPO-03 | Git remote slug fallback precedes cwd fallback and both are deterministic. | unit | `python3 -m pytest tests/test_naming.py::test_repo_identity_fallback_git_remote_then_cwd -q` | no - Wave 0 |

### Sampling Rate

- **Per task commit:** Run focused `tests/test_naming.py` plus any touched module-paired test file.
- **Per wave merge:** Run `python3 -m pytest tests/test_naming.py tests/test_profile.py tests/test_templates.py tests/test_mapping.py tests/test_export.py tests/test_output.py -q`.
- **Phase gate:** Run `python3 -m pytest tests/ -q` before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_naming.py` - new pure unit coverage for repo identity, concept signatures, fallback terms, cache IO, provenance, and LLM rejection.
- [ ] `tests/test_profile.py` - extend schema coverage for `repo:` and `naming.concept_names` or equivalent controls.
- [ ] `tests/test_export.py` - prove `to_obsidian()` receives resolved concept names and keeps MOC filenames stable.
- [ ] `tests/test_templates.py` - add explicit unsafe generated community title coverage across filename/tag/wikilink/frontmatter if existing tests do not cover the combined MOC path.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | No auth surface in this phase. [VERIFIED: phase scope] |
| V3 Session Management | no | No session surface in this phase. [VERIFIED: phase scope] |
| V4 Access Control | no | No authorization surface in this phase. [VERIFIED: phase scope] |
| V5 Input Validation | yes | Validate CLI/profile repo identity and LLM titles; reuse profile/template sanitizers for all output sinks. [VERIFIED: `graphify/profile.py`, `graphify/templates.py`] |
| V6 Cryptography | yes, limited | Use SHA-256 from stdlib for deterministic signatures/cache keys; do not hand-roll hashing. [VERIFIED: `graphify/cache.py`, `graphify/detect.py`] |

### Known Threat Patterns for Naming/Profile Inputs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via repo identity or concept title | Tampering | Slug validation plus `safe_filename()` and existing path confinement at write time. [VERIFIED: `graphify/profile.py`, `graphify/merge.py`] |
| YAML/frontmatter injection via LLM title | Tampering | `_dump_frontmatter()` and `safe_frontmatter_value()` for emitted metadata. [VERIFIED: `graphify/profile.py`] |
| Wikilink injection via `]]` or `|` | Tampering | `_sanitize_wikilink_alias()` and `resolve_filename()` split target/alias. [VERIFIED: `graphify/templates.py`] |
| Dataview query breakage via generated community tag | Tampering | Use `safe_tag()` for `community_tag`; do not interpolate raw title into Dataview query strings except through existing render path. [VERIFIED: `graphify/templates.py`] |
| Cache poisoning with path-like keys | Tampering | Store by SHA signature and fixed sidecar path under artifacts dir; mirror model-id/path sanitization discipline from `cache.py`. [VERIFIED: `graphify/cache.py`] |
| Denial of service via oversized generated labels | Denial of Service | Reject or cap candidate titles before persistence; `safe_filename()` caps filenames with hash suffix. [VERIFIED: `graphify/profile.py`] |

## Sources

### Primary (HIGH confidence)

- `.planning/phases/33-naming-repo-identity-helpers/33-CONTEXT.md` - locked decisions and phase boundary.
- `.planning/REQUIREMENTS.md` - NAME-01..05 and REPO-01..03.
- `.planning/ROADMAP.md` - Phase 33 goal, dependency, and downstream phase boundaries.
- `.planning/STATE.md` - v1.8 carry-forward decisions and known concerns.
- `CLAUDE.md` - architecture, dependency, testing, and security constraints.
- `graphify/profile.py` - profile schema/defaults, sanitizers, frontmatter, preflight.
- `graphify/templates.py` - filename, MOC rendering, wikilink, Dataview, frontmatter sinks.
- `graphify/mapping.py` - current community label derivation and per-community contexts.
- `graphify/export.py` - `to_obsidian()` community label injection and manifest flow.
- `graphify/output.py` - precedence/source reporting pattern.
- `graphify/cache.py`, `graphify/detect.py`, `graphify/merge.py` - generated sidecar and atomic write patterns.
- `pyproject.toml` - Python/dependency constraints.

### Secondary (MEDIUM confidence)

- Local environment probes: Python 3.10.19, pytest 9.0.3, NetworkX 3.4.2, PyYAML 6.0.3, git 2.50.1.
- Planning graph status: graph exists but is stale by about 343 hours; graph queries returned no relevant nodes, so semantic graph context was not used for implementation claims.

### Tertiary (LOW confidence)

- No web-only or unverified third-party sources were used. This phase is codebase-internal.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependency selection; existing stdlib/NetworkX/PyYAML constraints verified in code and local package metadata.
- Architecture: HIGH - all integration points are existing code paths with direct evidence.
- Pitfalls: MEDIUM - codebase pitfalls are verified; two cache/git failure-mode claims are reasoned assumptions and listed in the assumptions log.

**Research date:** 2026-04-28  
**Valid until:** 2026-05-28 for codebase patterns, or sooner if Phase 34/35 changes export/template ownership before implementation.
