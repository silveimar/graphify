# Phase 5: Integration & CLI - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

The **wire-up phase**: connect `profile.py` + `templates.py` + `mapping.py` + `merge.py` into a refactored `to_obsidian()` that orchestrates the full pipeline and exposes `--dry-run` / `--validate-profile` surfaces. This phase is thin by design — the hard decisions (public APIs, schemas, return shapes) were locked upstream in Phases 1–4. Phase 5's job is plumbing.

The engine owns: the orchestration sequence inside `to_obsidian()` (`load_profile → classify → render → compute_merge_plan → apply_merge_plan`), a library helper that formats `MergePlan` for human-readable dry-run output, and a library helper that runs a four-layer preflight validation of a vault's `.graphify/` directory. It does NOT: add any new `__main__.py` subcommand (CLI stays install/query/hook/benchmark/save-result only), re-implement any Phase 1–4 logic, or preserve the pre-profile flat-vault output shape.

Requirements delivered: **PROF-05** (validate-profile preflight), **MRG-03** (dry-run), **MRG-05** (default-profile path, not legacy code preservation).

</domain>

<decisions>
## Implementation Decisions

### CLI surface — library + skill only (D-73)

- **D-73:** **No new `__main__.py` subcommand.** `to_obsidian()` and a new `validate_profile_preflight()` are exposed as library-level APIs. The skill (`graphify/skill.md`) remains the pipeline driver and is updated to pass the new flags through its inline Python block. `__main__.py` stays install/query/hook/benchmark/save-result only. Rationale: graphify's existing architecture already splits pipeline-in-skill vs utilities-in-CLI. Adding a `graphify run` subcommand would require porting the whole extract→build→cluster orchestration into `__main__.py`, ballooning Phase 5 scope without user benefit — every existing entry point is already a skill invocation. Non-skill users call `from graphify.export import to_obsidian` directly from Python, as the tests already do.

### Legacy code path — deleted, not branched (D-74)

- **D-74:** **Delete the legacy 240-line flat-vault body of `to_obsidian()` (export.py L444–679).** The refactored function always runs the new pipeline: `profile = profile or _DEFAULT_PROFILE; classify → render → compute_merge_plan → apply_merge_plan`. No `if profile is None` branches inside the function body. This means MRG-05 ("backward compatible with current `to_obsidian()` behavior") is re-interpreted: backward compatibility is the **built-in default profile producing Ideaverse ACE structure**, not byte-for-byte preservation of the old flat output. Users of pre-profile graphify who re-run against an existing vault will see a completely different folder shape (`Atlas/Dots/Things/` instead of root-level `.md` files) — this is accepted migration cost. The cleaner single code path is worth it; two parallel exporters would bit-rot quickly given how often `export.py` is touched.

- **D-74a:** **Existing tests get rewritten.** `test_export.py::test_to_obsidian_*` assertions on flat output shape are obsolete. They move to `test_integration.py` (new file) and assert against `MergeResult.summary` action counts and specific files emitted under the profile's `folder_mapping` paths. FIX-01 (frontmatter injection), FIX-02 (deterministic dedup), FIX-03 (tag sanitization) regression tests **transfer** — their invariants apply to the new pipeline too, just against different target paths. `test_pipeline.py::test_pipeline_end_to_end` gets updated in place to assert on the new `MergeResult` shape instead of an integer count.

### Return type — `MergeResult | MergePlan` (D-75)

- **D-75:** **`to_obsidian()` returns `MergeResult` on normal runs, `MergePlan` on dry-run.** Union return type. No `__int__` magic, no `return_plan` kwarg, no side-channel plan stashing. Signature:
  ```python
  def to_obsidian(
      G: nx.Graph,
      communities: dict[int, list[str]],
      output_dir: str,
      *,
      profile: dict | None = None,
      community_labels: dict[int, str] | None = None,
      cohesion: dict[int, float] | None = None,
      dry_run: bool = False,
  ) -> MergeResult | MergePlan: ...
  ```
  Existing positional parameters (`G`, `communities`, `output_dir`) stay positional to protect library callers. Everything new is keyword-only. Dry-run returns `MergePlan` directly from `compute_merge_plan` — no writes ran, so `MergeResult` (which records write outcomes) would be structurally wrong. Callers branch on `dry_run` or on `isinstance(result, MergePlan)`.

### Dry-run output — grouped summary + per-action list (D-76)

- **D-76:** **Library-level formatter, human-scannable default.** `format_merge_plan(plan: MergePlan) -> str` ships in `graphify/merge.py` as a public helper. It produces:
  ```
  Merge Plan — 52 actions
  ========================
    CREATE:         42
    UPDATE:          7
    SKIP_PRESERVE:   0
    SKIP_CONFLICT:   1
    REPLACE:         0
    ORPHAN:          2

  CREATE (42)
    CREATE  Atlas/Dots/Things/Transformer.md
    CREATE  Atlas/Dots/Things/Attention.md
    ...
  UPDATE (7)
    UPDATE  Atlas/Maps/Community_0.md  (3 fields, 2 blocks)
    ...
  SKIP_CONFLICT (1)
    SKIP_CONFLICT  Atlas/Dots/Things/Stale_Note.md  [unmanaged_file]
  ORPHAN (2)
    ORPHAN  Atlas/Dots/Things/Deleted_Node.md  (node transformer_old no longer in graph)
  ```
  Header first, then per-action groups, each group listing one line per file. UPDATE rows append `(N fields, M blocks)` via `len(action.changed_fields)` / `len(action.changed_blocks)`. SKIP_CONFLICT rows append `[conflict_kind]`. ORPHAN rows append the action `reason`. The skill calls `format_merge_plan(plan)` and prints the result; any future CLI reuses the same formatter. No JSON mode in v1 (deferred).

### Validate-profile — four-layer preflight (D-77)

- **D-77:** **Library API `validate_profile_preflight(vault_dir: Path) -> tuple[list[str], list[str]]`** returns `(errors, warnings)`. Four layers:
  1. **Schema (errors):** existing Phase 1 `validate_profile()` — loads `.graphify/profile.yaml`, checks structure, `folder_mapping` keys, `merge.strategy` enum, `mapping_rules` shape. All failures are errors.
  2. **Templates (errors):** for every `.graphify/templates/<type>.md` override present, call Phase 2 `validate_template(text, required_vars)`. Unknown `${placeholder}`, missing required placeholders, or path-confinement failures are errors.
  3. **Dead mapping rules (warnings):** invoke Phase 3 D-45 dead-rule detection (a later rule is provably unreachable because an earlier rule is strictly more general for the same `note_type`). Dead rules don't break the run but waste user intent.
  4. **Path safety (warnings):** walk `folder_mapping` entries and every `mapping_rules[*].then.folder` value. For each folder, compute `len(str(vault_dir / folder / "X" * 200))` — if it exceeds 240 chars, flag as warning (leaves headroom under Windows MAX_PATH 260 with a 200-char filename, as capped by Phase 1 D-06). Also flag `folder_mapping` entries with > 4 path segments (UX warning, Obsidian's file tree gets cluttered past 4 levels; Ideaverse ACE itself nests 3 deep).
- **D-77a:** **Skill contract:** skill's `--validate-profile` code path calls `validate_profile_preflight(vault_dir)`, prints errors and warnings (each prefixed `error:` / `warning:`), exits 1 if errors are non-empty, exits 0 otherwise. Warnings never block exit 0. Empty errors + empty warnings prints `profile ok — N rules, M templates validated` and exits 0.

### Claude's Discretion

- **Module organization.** Refactored `to_obsidian()` stays in `graphify/export.py` alongside the other exporters (`to_canvas`, `to_html`, `to_json`, `to_graphml`, `to_cypher`, `push_to_neo4j`, `to_wiki`). Deleting the 240-line legacy block and replacing it with ~30 lines of orchestration shrinks `export.py` net. No new `graphify/integration.py` module for v1 — revisit if orchestration grows beyond ~100 lines.
- **`apply_merge_plan` partial failure policy.** Continue-on-failure. If action 17 of 50 fails to write (disk full, permission denied, stale `.tmp`), `apply_merge_plan` logs the failure to stderr with the path and `OSError` message, records it in a new `MergeResult.failures: list[tuple[Path, str]]` field, and continues with the remaining actions. Never abort mid-run. Matches Phase 4 D-63 ("one stray file never blocks the run") and Phase 1's "validate, report, don't crash" ethos. `MergeResult.summary` reflects successful writes only; `failures` is the complementary view.
- **`format_merge_plan` lives in `merge.py`.** Same module as `MergePlan` / `MergeResult` / `MergeAction` — the formatter is tightly coupled to those dataclasses. Also exported via `graphify/__init__.py` lazy imports for skill/test access.
- **`_DEFAULT_PROFILE` is good enough as-is.** No Phase 5 edits to Phase 1's default. The Atlas-shaped defaults are the legacy-replacement output.
- **Skill update scope.** `graphify/skill.md` L485–509 (the current inline `to_obsidian()` call block) gets one edit: add `profile=load_profile(obsidian_dir)` and `dry_run=args.dry_run` arguments, wrap the return in `print(format_merge_plan(result)) if isinstance(result, MergePlan) else summary_line(result)`. Platform variants (`skill-codex.md`, `skill-opencode.md`, `skill-droid.md`, etc.) get the same edit. This is a handful of mechanical edits, not a rewrite.
- **Test fixture strategy.** New `tests/test_integration.py` constructs a minimal `nx.Graph` (3–5 nodes, 1–2 communities) + a minimal profile dict, calls `to_obsidian(G, communities, tmp_path, profile=profile)`, and asserts on `MergeResult.summary` counts and specific `Atlas/…/*.md` file existence. Bring across FIX-01/02/03 invariants by constructing graphs with special-char labels, duplicate labels, special-char community names — same assertions, new target paths. Purely `tmp_path`-scoped, no network, matches existing test conventions.
- **`profile.load_profile(vault_dir)` signature gap.** Phase 1 ships a `load_profile()` function; Phase 5 is its first caller inside `to_obsidian()`. If the function doesn't already handle "no `.graphify/profile.yaml` → return `_DEFAULT_PROFILE`", Phase 5 adds that fallback either in `profile.py` (cleaner) or inline in `to_obsidian()` (less invasive). Decide at plan time after reading `profile.py`'s current signature.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 foundations (MUST import)
- `graphify/profile.py` — `load_profile(vault_dir)`, `validate_profile(profile)`, `_DEFAULT_PROFILE`, `safe_filename`, `safe_frontmatter_value`, `safe_tag`, `_VALID_MERGE_STRATEGIES`, `_dump_frontmatter`. The refactored `to_obsidian()` calls `load_profile` as its first line and passes the result through to classify/render/merge.
- `graphify/profile.py` `_DEFAULT_PROFILE` — this is THE MRG-05 backward-compat answer. Phase 5 does not write a new default; it trusts Phase 1's.

### Phase 2 foundations (MUST import)
- `graphify/templates.py` — `render_note(node_id, G, profile, note_type, classification_context) -> tuple[str, str]`, `render_moc(community_id, ...)`, `render_community_overview(...)`, `resolve_filename(label, convention)`, `load_templates(vault_dir)`, `validate_template(text, required)`. Phase 5 calls `render_note` / `render_moc` for every real node and above-threshold community, respectively, to produce the `rendered_notes: dict[str, RenderedNote]` that `compute_merge_plan` consumes.
- `graphify/templates.py` D-42 `ClassificationContext` shape — Phase 5 does not construct this directly; it gets per-node / per-community `ClassificationContext` instances from `mapping.classify()`.

### Phase 3 foundations (MUST import)
- `graphify/mapping.py` — `classify(G, communities, profile) -> MappingResult` and the `ClassificationContext` TypedDict. Phase 5 passes the mapping result through to Phase 2 rendering (each node's `ClassificationContext` becomes `render_note`'s context parameter).
- `graphify/mapping.py` `MappingResult.skipped_node_ids` — nodes in this set produce NO file (Phase 3 D-50). Phase 5 must skip them before calling `render_note` and before `compute_merge_plan` receives them, to avoid spurious ORPHAN actions on re-run.
- `graphify/mapping.py` — dead-rule detection helper used by `validate_profile_preflight` layer 3 (Phase 3 D-45).

### Phase 4 foundations (MUST import — the whole module)
- `graphify/merge.py` — `compute_merge_plan(vault_dir, rendered_notes, profile)`, `apply_merge_plan(plan)`, `MergePlan`, `MergeAction`, `MergeResult`. These are the two function calls that bookend `to_obsidian()`'s pipeline. Dry-run calls only `compute_merge_plan`; normal runs call both.
- `graphify/merge.py` `RenderedNote` TypedDict — the input contract for `compute_merge_plan`. Phase 5 assembles `dict[str, RenderedNote]` from Phase 2 `render_note` / `render_moc` return tuples.
- `graphify/merge.py` — Phase 5 ADDS `format_merge_plan(plan: MergePlan) -> str` as a new public helper in this module. Signature and grouping format locked in D-76 above.
- `graphify/merge.py` — Phase 5 ADDS `MergeResult.failures: list[tuple[Path, str]]` field per the Claude's Discretion policy. `apply_merge_plan` populates it on per-action `OSError`.

### Existing code (MODIFY)
- `graphify/export.py` L440–679 — current legacy `to_obsidian()` body. **Delete** the flat-vault implementation. Replace with ~30-line orchestration (`load_profile → classify → render_all → compute_merge_plan → apply_merge_plan`). Keep the function name and positional parameters for backward compat; add keyword-only `profile`, `dry_run`.
- `graphify/skill.md` L485–509 — current `to_obsidian()` call site. Update to pass `profile=` and `dry_run=` and to call `format_merge_plan()` on dry-run return.
- `graphify/skill-codex.md`, `graphify/skill-opencode.md`, `graphify/skill-aider.md`, `graphify/skill-droid.md`, `graphify/skill-claw.md`, `graphify/skill-trae.md`, `graphify/skill-trae-cn.md` — same skill update as above (mechanical per-platform edits).
- `graphify/__init__.py` — lazy import map gains `format_merge_plan`, `validate_profile_preflight`. Existing lazy exports (`to_obsidian`, `compute_merge_plan`, `apply_merge_plan`, `MergePlan`, `MergeResult`, `load_profile`, `validate_profile`, `classify`, `render_note`, `render_moc`) are already registered from prior phases.

### Tests (REWRITE)
- `tests/test_export.py::test_to_obsidian_frontmatter_special_chars` (L155) — migrate to `tests/test_integration.py`, assert FIX-01 invariant against new target paths.
- `tests/test_export.py::test_to_obsidian_dedup_deterministic` (L188) — migrate, assert FIX-02 invariant.
- `tests/test_export.py::test_to_obsidian_tag_sanitization` (L216) — migrate, assert FIX-03 invariant.
- `tests/test_export.py` L251, L285 — remaining flat-output assertions: rewrite against `MergeResult.summary` counts and Atlas/ path existence.
- `tests/test_pipeline.py::test_pipeline_end_to_end` L88 — update in place: the int return becomes `MergeResult`, assertion becomes `result.summary["CREATE"] == expected`.
- `tests/test_integration.py` (NEW) — full profile-driven test suite. Fixtures: minimal graph + minimal profile + `tmp_path` vault. Exercises `to_obsidian()` normal and dry-run paths, `validate_profile_preflight()` all four layers, `format_merge_plan()` output stability.

### Prior phase context (MUST read — decisions cascade)
- `.planning/phases/01-foundation/01-CONTEXT.md` D-01, D-02, D-14, D-15, D-16 — profile schema, deep merge, module boundary. D-16 explicitly reserves the `to_obsidian(..., profile=None)` signature slot Phase 5 now fills.
- `.planning/phases/02-template-engine/02-CONTEXT.md` D-17 through D-42 — especially D-40 (module boundary: templates.py ← profile.py only), D-41 (public API signatures Phase 5 calls), D-42 (`ClassificationContext` shape).
- `.planning/phases/03-mapping-engine/03-CONTEXT.md` D-43 through D-47 (mapping rule DSL), D-50 (`skipped_node_ids`), D-45 (dead-rule detection — consumed by validate-profile preflight layer 3).
- `.planning/phases/04-merge-engine/04-CONTEXT.md` D-63 (collision policy), D-70 (compute/apply surface, dry-run), D-71 (`MergePlan`/`MergeAction` dataclass shapes), D-72 (orphan reporting, never delete). **D-70's public API is the entire Phase 5 pipeline contract.**

### Requirements
- `.planning/REQUIREMENTS.md` PROF-05 — `validate-profile` preflight (D-77 realizes this, extended to four layers)
- `.planning/REQUIREMENTS.md` MRG-03 — `--dry-run` (D-75 + D-76 realize this: union return type + formatter helper)
- `.planning/REQUIREMENTS.md` MRG-05 — backward compatibility (D-74 **re-interprets** this: backward compat = the Atlas-shaped default profile, NOT byte-for-byte flat output preservation)

### Security patterns (MUST follow)
- `graphify/security.py` — path confinement applies to every `MergeAction.path` before `apply_merge_plan` writes, already enforced by `compute_merge_plan` per Phase 4. Phase 5 does not add new path-touching code outside the pipeline call chain.
- `graphify/profile.py` — `safe_filename`, `safe_frontmatter_value`, `safe_tag` are the sanitization front line; Phase 5 relies on Phase 2's `render_note` to have already called them.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **All four prior phases.** Phase 5 imports but adds almost no new logic. The entire orchestration body is ~30 lines of function calls plus error handling.
- `graphify/merge.py:format_merge_plan` (NEW) — the one non-trivial new function. Pure formatter over `MergePlan` dataclass.
- `graphify/profile.py:validate_profile_preflight` (NEW) — composes existing `validate_profile()` (Phase 1) + `validate_template()` (Phase 2) + dead-rule detector (Phase 3) + new path-safety walker. Glue code, not algorithm.
- `graphify/__init__.py` lazy import pattern — extend with new exports.

### Established Patterns
- **Pure functions over plain data** — `to_obsidian()` becomes a thin orchestration over the four pure pipeline stages. Only `apply_merge_plan` writes.
- **Validation returns error lists** — `validate_profile_preflight(vault) -> (errors, warnings)` follows the pattern but extends to warning tier.
- **Lazy imports** — new public exports added to `graphify/__init__.py` lazy-load map.
- **`from __future__ import annotations`** + single-line module docstring — standard for any new module (none planned here).
- **Skill-driven pipeline** — the existing split (skill orchestrates, CLI is utilities) is what D-73 preserves.

### Integration Points
- `graphify/export.py:to_obsidian` — signature grows `profile`, `dry_run` kwargs; body is rewritten end-to-end.
- `graphify/__init__.py` — `format_merge_plan`, `validate_profile_preflight` added to lazy imports.
- `graphify/skill.md` (+ 7 platform variants) — inline Python block updated with new kwargs and dry-run print path.
- `graphify/merge.py` — gains `format_merge_plan(plan)` and `MergeResult.failures` field.
- `tests/test_integration.py` (NEW file) — replaces `test_export.py::test_to_obsidian_*`.

### Creative Options the Architecture Enables
- **Dry-run is a 3-line wrapper.** Because `compute_merge_plan` is pure (Phase 4 D-70), `dry_run=True` is just `plan = compute_merge_plan(...); return plan` — no duplicate logic, no dry-run branches inside merge or anywhere else.
- **`format_merge_plan` is reusable.** The same formatter the skill uses for dry-run today is what a future `graphify run --obsidian --dry-run` CLI subcommand would call tomorrow. No rework when/if we add a CLI pipeline runner.
- **`validate_profile_preflight` is four independent passes.** Each layer (schema, templates, dead rules, path safety) can be tested in isolation; the composite function is glue over four well-tested components.
- **Non-skill Python callers already work.** Anyone doing `from graphify.export import to_obsidian` gets the new pipeline automatically. No new surface to document beyond the function signature change.

</code_context>

<specifics>
## Specific Ideas

- **"Library + skill only" matches graphify's existing split.** `__main__.py` hosts utilities (install, hook, query, benchmark, save-result); pipeline orchestration lives in the skill. D-73 preserves this split — adding a `graphify run` subcommand would be a precedent-breaking move that Phase 5 doesn't need to make.
- **The legacy path deletion is the single biggest simplification of this phase.** 240 lines out, ~30 lines of orchestration in. `export.py` shrinks net despite gaining a whole pipeline. Existing `to_obsidian()` bugs (already fixed in Phase 1) disappear along with the code that contained them.
- **MRG-05 is re-interpreted, not relaxed.** "Backward compatible" now means "the default profile is Ideaverse-ACE-shaped and produces a sensible vault without user config," not "byte-for-byte identical output to pre-profile graphify." Users upgrading see a different folder shape — that's the migration cost of the adapter.
- **`format_merge_plan` is a library export, not a skill implementation detail.** Shipping it in `merge.py` means the skill's Python block is one function call, and any future CLI subcommand inherits the same formatter. Preserves optionality.
- **Preflight returns `(errors, warnings)` not just `list[str]`.** Dead rules and long-path entries aren't blocking errors — they're advisories. Separating them lets users distinguish "fix this or nothing runs" from "this looks suspicious but will work." Matches Python linter idioms (pyflakes errors vs warnings).
- **Path safety uses 240 chars, not 260.** 260 is Windows MAX_PATH; 240 leaves 20 chars of headroom for growth (filename extension edge cases, temp-file suffixes during atomic write). Phase 1 D-06 already caps filenames at 200 chars, so the preflight walker simulates the worst case.
- **`apply_merge_plan` continue-on-failure is consistent with Phase 4 D-63.** One permission-denied note never blocks 49 good writes. The `MergeResult.failures` field records what broke; the summary records what succeeded. Users read both.
- **Test migration is regression-preserving, not regression-risking.** The three FIX invariants (frontmatter injection, deterministic dedup, tag sanitization) carry to the new pipeline because Phase 2/3 already call `safe_frontmatter_value`, `safe_filename`, `safe_tag`. We're not losing test coverage, we're relocating assertions to new target paths.
- **No new Python dependencies.** Everything Phase 5 needs is already imported by prior phases. PyYAML stays optional (already the case).

</specifics>

<deferred>
## Deferred Ideas

- **`graphify run` pipeline CLI subcommand.** A real `__main__.py` entry that drives extract → build → cluster → export without going through the skill. Would open the door to non-Claude-Code users running graphify as a plain CLI tool. Deferred because it's a separate feature (CLI UX, argparse-based orchestration, LLM-free extraction path decisions) that doesn't belong in a four-module wire-up phase. Capture as a roadmap backlog item.
- **`graphify validate-profile` standalone CLI subcommand.** Would invoke `validate_profile_preflight(Path(sys.argv[2]))` from `__main__.py` directly, letting non-skill users run it. Small scope, but breaks D-73's "CLI stays utilities-only" line. Defer until there's a real non-skill user asking for it.
- **`--verbose` dry-run mode with full field/block diffs.** `format_merge_plan` could take a `verbose: bool = False` kwarg and emit per-UPDATE diff blocks (`  - tags: [a, b] → [a, b, c]`). Deferred; the current grouped summary is enough for daily use. Revisit if users report debugging pain.
- **JSON dry-run output mode.** `format_merge_plan_json(plan) -> str` (or just `json.dumps(dataclasses.asdict(plan))`). Useful for CI pipelines and diff-tool integrations. Deferred to v2 — no current consumer.
- **`MergeAction.diff` structured diff field.** Inherited from Phase 4's Claude's Discretion note. Cheap to compute, inflates `MergePlan` size. Not needed for v1's default formatter output.
- **Windows long-path opt-in (`\\?\` prefix).** Phase 5's path-safety walker only warns on paths > 240 chars; it never bypasses the limit via Windows's extended-length prefix. Deferred until a Windows user reports real breakage.
- **Validator check for overly-slow regex matchers.** Phase 3 D-44 already caps regex pattern length at 512 chars and candidate string length at 2048 chars. A preflight walker could also reject catastrophic-backtracking patterns via static analysis — significant complexity for low real-world incidence.
- **Platform-variant skill sync automation.** The 7 `skill-*.md` variants all get the same Phase 5 edit. A preprocessor that stamps them from a single source would prevent drift. Deferred — orthogonal to the wire-up work.
- **`MergeResult.failures` aggregation into `GRAPH_REPORT.md`.** Phase 5 stops at logging failures to stderr + `MergeResult.failures`. Surfacing them in the audit report (`report.py`) would close the loop. Deferred until a Phase 6 or follow-up phase touches `report.py`.

</deferred>

---

*Phase: 05-integration-cli*
*Context gathered: 2026-04-11*
