# Phase 4: Merge Engine - Context

**Gathered:** 2026-04-11
**Status:** Ready for planning

<domain>
## Phase Boundary

A **reader-diff-writer layer** that reconciles a vault-on-disk against freshly rendered notes from Phase 2/3 and decides, per-file, whether to create, update (field-surgically), skip, replace, or leave orphaned. Produces a pure `MergePlan` data structure plus an idempotent `apply_merge_plan()` writer.

The engine owns: note identity detection (path + fingerprint), frontmatter per-key merge semantics, body sentinel parsing and refresh, field-ordering preservation, orphan reporting, atomic on-disk writes. It does NOT classify nodes (Phase 3), render templates (Phase 2), or wire the CLI (Phase 5). `--dry-run` and `--validate-profile` land in Phase 5 and reuse `compute_merge_plan()` directly — merge exposes the decision surface they need.

</domain>

<decisions>
## Implementation Decisions

### Note identity / ownership (D-61..D-63)

- **D-61:** **Ownership = path + fingerprint.** Path-based by default: any file at a Phase-3-classified target path is a candidate for merge. Before update, merge MUST confirm the file carries a graphify fingerprint; if it doesn't, merge backs off. Files outside classified paths are invisible to graphify — moving a note out of `Atlas/Dots/Things/` is the user's opt-out.

- **D-62:** **Fingerprint = dual signal — frontmatter field AND body sentinel.** Every managed note carries `graphify_managed: true` in the graphify-owned frontmatter region AND at least one `<!-- graphify:<block>:start -->` / `...:end -->` sentinel pair in its body. Presence of EITHER signal is sufficient to claim ownership; requiring both would lock out notes where a user stripped one by accident. On a fresh CREATE, both signals are written. On UPDATE, merge re-verifies at least one is still present.

- **D-63:** **First-touch collision = skip + warn + continue.** When merge wants to write to a path that already has a file with NO fingerprint, it logs `[graphify] refusing to overwrite unmanaged file at {path}` to stderr, records a `SKIP_CONFLICT` action in the plan, and continues with the rest of the vault. One stray file never blocks the run. Users resolve by deleting/renaming the conflicting file, or by running with `--force` (deferred — see Deferred Ideas).

### Frontmatter per-key merge model (D-64..D-65)

- **D-64:** **Per-key merge policy with three modes:**
  - `replace` — graphify overwrites the scalar value on every UPDATE run. Used for identity-bearing graphify-owned scalars: `type`, `file_type`, `source_file`, `source_location`, `community`, `cohesion`, `graphify_managed`.
  - `union` — graphify's list items are unioned with the user's list items, deduped, order-stable. Used for graphify-owned lists that users legitimately extend: `up`, `related`, `collections`, `tags`. Preserves both sides' contributions.
  - `preserve` — graphify never touches the key under UPDATE. Used for every key in `profile.merge.preserve_fields` (default `rank`, `mapState`, `created`). `created:` is in the preserve list because it's set ONCE at first CREATE (Phase 2, D-27) and must survive re-runs.
  - Unknown keys — keys present in the user's file that graphify doesn't emit at all are untouched regardless of policy. This is the "user wrote `priority: high` in their note" case.

- **D-65:** **Policy table lives in merge module + profile override.** A built-in `_DEFAULT_FIELD_POLICIES: dict[str, str]` ships with the merge module, keyed by field name → policy mode. Users override per-field via `profile.merge.field_policies: {<key>: <mode>}` — e.g., `{tags: replace, collections: preserve}`. Deep-merges over built-ins like every other profile section (Phase 1 D-02). Unknown fields default to `preserve` — conservative default so adding a new field never accidentally clobbers user data.

### Field ordering on update (D-66)

- **D-66:** **Preserve existing order + slot-near-neighbor insertion.** Keys already present in the user's file keep their observed position on re-emission (zero churn). Newly-added graphify keys are inserted immediately after their canonical D-24 neighbor (e.g., if graphify is adding `cohesion` for the first time, merge finds `community` in the existing file and inserts `cohesion` on the next line). If the canonical neighbor is absent, fall back to inserting at the bottom of the graphify-owned region, just before any unknown user keys. This satisfies MRG-06 with the minimum git diff: existing fields never move, new fields land near their logical home.

### Body content merge (D-67..D-69)

- **D-67:** **Body region markers are paired HTML comments.** Phase 2's non-MOC templates (Thing/Statement/Person/Source, D-32) and MOC template (D-31) emit graphify-owned body blocks wrapped in sentinels:
  ```markdown
  <!-- graphify:wayfinder:start -->
  > [!note] Wayfinder
  > Up: [[Parent|Parent]]
  > Map: [[Atlas|Atlas]]
  <!-- graphify:wayfinder:end -->

  [user's ${body} region — untouched by merge]

  <!-- graphify:connections:start -->
  > [!info] Connections
  > - [[Target|Target]] — relation [CONFIDENCE]
  <!-- graphify:connections:end -->

  <!-- graphify:metadata:start -->
  > [!abstract] Metadata
  > source_file: ...
  <!-- graphify:metadata:end -->
  ```
  Sentinel names: `wayfinder`, `connections`, `metadata` for non-MOC; `wayfinder`, `members`, `sub_communities`, `dataview`, `metadata` for MOC. Everything between matched start/end markers is graphify-owned and refreshed on update. Everything OUTSIDE any sentinel pair is the user's body and NEVER touched.

- **D-68:** **Deleted sentinel blocks are respected — no re-insertion.** If a user removes the entire `graphify:connections` pair from a note, merge does NOT re-insert it on subsequent runs. Merge only refreshes blocks still present. This is a state-free rule (see Phase 4 insight): merge makes the decision on each run from the file alone, without needing a manifest of what graphify wrote last time. A user's "I don't want Connections in this note" intent survives forever.

- **D-69:** **Malformed sentinels = skip + warn.** If a sentinel pair is unpaired (start without end, or vice versa), nested improperly, or the contents can't be parsed, merge logs `[graphify] malformed sentinel block in {path}, skipping note` to stderr, emits a `SKIP_CONFLICT` action in the plan, and leaves the file entirely untouched. Never self-heal — swallowing user prose between a good start-marker and an algorithmic guess at "end" is the worst failure mode we can design in.

### Public API / phase boundary (D-70..D-72)

- **D-70:** **Two-layer API: compute + apply.** Module is `graphify/merge.py` with:
  ```python
  def compute_merge_plan(
      vault_dir: Path,
      rendered_notes: dict[str, RenderedNote],
      profile: dict,
  ) -> MergePlan: ...

  def apply_merge_plan(plan: MergePlan) -> MergeResult: ...
  ```
  `compute_merge_plan` is a pure function over (vault state, rendered notes, profile) — reads existing files, diffs, emits the plan, no writes. `apply_merge_plan` consumes the plan and performs atomic writes. Phase 5's `--dry-run` (MRG-03) calls only `compute_merge_plan` and prints the plan; normal runs call both in sequence. Mirrors Phase 3's `MappingResult` precedent.

- **D-71:** **`MergePlan` is a dataclass (or TypedDict) carrying per-file `MergeAction`:**
  ```python
  @dataclass(frozen=True)
  class MergeAction:
      path: Path
      action: Literal["CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"]
      reason: str  # human-readable explanation for the log / dry-run / GRAPH_REPORT
      # UPDATE-only details:
      changed_fields: list[str] = field(default_factory=list)       # frontmatter keys that differ
      changed_blocks: list[str] = field(default_factory=list)       # body sentinel block names that differ
      # SKIP_CONFLICT-only:
      conflict_kind: str | None = None   # "unmanaged_file" | "malformed_sentinel"

  @dataclass(frozen=True)
  class MergePlan:
      actions: list[MergeAction]
      orphans: list[Path]      # convenience view of ORPHAN entries
      summary: dict[str, int]  # action -> count, for reports
  ```
  `MergeResult` mirrors `MergePlan` but records per-file write success/failure after `apply_merge_plan` runs. Both structures are JSON-serializable so Phase 5 can render them in `GRAPH_REPORT.md` and dry-run output.

- **D-72:** **Orphan notes are reported, never deleted.** When a previously-managed note corresponds to a node that no longer exists in the new graph, merge emits an `ORPHAN` action with a reason (`"node {id} no longer in graph"`). `apply_merge_plan` does NOT delete orphan files under any strategy — not even `replace`. Orphans surface in dry-run output and the Phase 5 `GRAPH_REPORT.md` "classification" section. User decides. Any future auto-delete or auto-archive behavior lives behind an explicit profile flag (see Deferred Ideas).

### Merge strategies — concrete behaviors

The three profile strategies (Phase 1 D-01, `_VALID_MERGE_STRATEGIES` at `profile.py:49`) are realized in `compute_merge_plan` as follows:

- **`update` (default):** All field-level policies (D-64) and block-level semantics (D-68) apply. CREATE for new notes, UPDATE for fingerprinted existing notes, SKIP_CONFLICT for unmanaged or malformed, ORPHAN for disappeared nodes.
- **`skip`:** compute_merge_plan emits CREATE for new notes, `SKIP_PRESERVE` for every existing file (managed or not), ORPHAN for disappeared nodes. apply_merge_plan only writes CREATE entries. Used for "once-only injection" workflows.
- **`replace`:** compute_merge_plan emits CREATE for new notes and `REPLACE` for existing managed notes (NOT unmanaged ones — D-63 still applies; unmanaged still becomes SKIP_CONFLICT). A REPLACE action means the note is rewritten from scratch, losing user-edited `preserve_fields` and any user body content. Orphans still reported, never deleted.

### Claude's Discretion

- **YAML reading.** `compute_merge_plan` must parse existing frontmatter to diff it. Matches D-23's hand-rolled-dumper posture: **symmetric hand-rolled reader** in `merge.py` (or extracted to `profile.py` if `templates.py` also needs it later). No PyYAML dependency on the read path — tolerance for user edits comes from following `_dump_frontmatter`'s emission grammar precisely. Edge cases to test: block-form lists, quoted wikilinks, date strings, bool/null coercion, Templater `<% %>` tokens as literal strings. If a frontmatter block fails to parse cleanly, the action is `SKIP_CONFLICT` with `conflict_kind="malformed_frontmatter"`.
- **Atomic writes.** `apply_merge_plan` writes to `<target>.tmp`, `fsync`, then `os.replace(<target>.tmp, <target>)` for crash safety. BEFORE writing, hash-compare the new content to the existing content; if identical, skip the write entirely (no mtime churn, no git diff noise). This turns re-runs with no graph changes into a no-op at the filesystem level.
- **Rule-trace-style merge log.** Phase 3 shipped `rule_traces` as a debugging aid. Consider an analogous `MergeAction.diff` field carrying a structured per-field / per-block diff for UPDATE actions, gated by a `verbose: bool` kwarg. Decide at plan time.
- **Test fixture strategy.** Reuse Phase 2/3's `make_classification_fixture()` helper for graph inputs; add a `tests/fixtures/vaults/` directory with real vault states (empty vault, pristine graphify vault, user-edited vault with preserve_fields set, vault with stripped fingerprint, vault with malformed sentinel) that tests can copy into `tmp_path`.
- **Public vs private helpers.** `compute_merge_plan`, `apply_merge_plan`, `MergePlan`, `MergeAction`, `MergeResult` — public. Everything else (sentinel parser, frontmatter diff, policy dispatcher) — leading underscore, private.
- **Module-level imports.** `merge.py` imports from `profile.py` (`safe_frontmatter_value`, `_dump_frontmatter`, `_VALID_MERGE_STRATEGIES`, `_deep_merge`) and stdlib only. No imports from `export.py`, `templates.py`, `mapping.py` — merge operates over the data contracts those modules define, not their internals.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 foundations (MUST import, MUST extend)
- `graphify/profile.py` L16-40 — `_DEFAULT_PROFILE`. Phase 4 **extends** `merge` section with optional `field_policies` dict (default empty — built-in table wins). `preserve_fields` default is already `["rank", "mapState", "tags"]`; this phase ADDS `created` to the default list to satisfy D-27.
- `graphify/profile.py` L49 — `_VALID_MERGE_STRATEGIES = {"update", "skip", "replace"}`. All three behaviors are implemented in this phase (see "Merge strategies" section above).
- `graphify/profile.py` L159-175 — existing `merge` validation stub. Extend to also validate the optional `field_policies` map: keys must be strings, values must be in `{"replace", "union", "preserve"}`.
- `graphify/profile.py` L186 — `safe_frontmatter_value(value)` — reuse for any new scalars merge emits.
- `graphify/profile.py` L359-394 — `_dump_frontmatter(fields: dict) -> str` — CANONICAL WRITER. The hand-rolled reader merge needs must be a strict inverse of this function's emission grammar.
- `graphify/validate.py` — validation returns `list[str]` pattern. `validate_merge_config()` in merge.py (or profile.py) follows it.

### Phase 2 foundations (MUST produce output mergeable into Phase 2's rendered notes)
- `graphify/templates.py` — Phase 2 renders note *strings*. Phase 4 consumes `(filename, rendered_text)` tuples from `render_note` / `render_moc` and decides what to write where.
- **Phase 2 output must be extended to emit sentinel markers.** This is a coupled change: Phase 4 won't work until Phase 2's built-in templates have `<!-- graphify:<block>:start -->` / `end -->` comments around wayfinder, connections, and metadata callouts. Plan this as a shared first plan of Phase 4 OR a retroactive Phase 2 patch — decide at plan time.
- `graphify/templates.py` L24-26 — `_dump_frontmatter`, `safe_frontmatter_value` imports. Merge imports from the same source of truth.

### Phase 3 foundations (READ ONLY — merge consumes its output)
- `graphify/mapping.py` (Phase 3 output) — `MergePlan` is computed over `MappingResult.per_node` / `per_community`. Merge does NOT re-classify anything; it trusts Phase 3's classification and target path assignments.
- `.planning/phases/03-mapping-engine/03-CONTEXT.md` D-72 — Phase 3's `skipped_node_ids` set. Merge must treat any node in this set as producing NO file — no create, no update, no orphan. A node being in `skipped_node_ids` is not the same as a node being deleted (which would produce an ORPHAN action for its prior file).

### Security patterns (MUST follow)
- `graphify/security.py` — path confinement. Every `MergeAction.path` MUST be validated to stay inside `vault_dir` before `apply_merge_plan` writes. No symlink traversal, no `..` escapes. Matches Phase 1 MRG-04.
- `graphify/profile.py` — `validate_vault_path` (if exists) or equivalent — called from `compute_merge_plan` before a path ever lands in the plan.

### Existing code (REFERENCE ONLY — Phase 5 rewires)
- `graphify/export.py` L444-679 — current `to_obsidian()`. Baseline for understanding the default-profile output shape Phase 4 must be backward-compatible with (MRG-05, Phase 5's concern but informs test fixtures).
- `graphify/export.py` L520-533 — current flat frontmatter emission. Illustrates the minimum field set Phase 4 must handle in legacy-file parsing (for users upgrading from a pre-profile graphify vault).

### Prior phase context (MUST read — decisions cascade)
- `.planning/phases/01-foundation/01-CONTEXT.md` — D-01 through D-16: profile schema, merge section, safety helpers, validation pattern.
- `.planning/phases/02-template-engine/02-CONTEXT.md` — **especially D-23, D-24, D-25, D-26, D-27 for the frontmatter model Phase 4 must parse symmetrically, and D-31, D-32, D-33, D-34, D-35 for the body block structure the sentinels must wrap.**
- `.planning/phases/03-mapping-engine/03-CONTEXT.md` — D-50 skipped_node_ids semantics; classification → file path contract.

### Requirements
- `.planning/REQUIREMENTS.md` MRG-01 — graphify-owned fields refresh, user-edited fields preserve (D-64 realizes this)
- `.planning/REQUIREMENTS.md` MRG-02 — `preserve_fields` list with defaults `rank`, `mapState`, `tags` (extended to include `created` — see D-65)
- `.planning/REQUIREMENTS.md` MRG-06 — frontmatter field ordering preservation (D-66 realizes this)
- `.planning/REQUIREMENTS.md` MRG-07 — three merge strategies (update, skip, replace) — realized in the "Merge strategies" subsection
- `.planning/REQUIREMENTS.md` MRG-03 — `--dry-run` lands in Phase 5; merge EXPOSES the decision surface (`compute_merge_plan`) Phase 5 needs (D-70)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `profile.py:_dump_frontmatter` — the canonical hand-rolled YAML writer. Merge's hand-rolled reader is literally the inverse grammar of this function. If you're ever unsure how to parse something, look at how `_dump_frontmatter` wrote it.
- `profile.py:safe_frontmatter_value` — quote-on-demand YAML scalar emitter; used for any value merge re-emits after an update.
- `profile.py:_deep_merge` — merges user's `field_policies` overrides with the built-in default policy table.
- `profile.py:_VALID_MERGE_STRATEGIES` — single source of truth for the three valid strategies.
- `validate.py` pattern — `validate_merge_config(config) -> list[str]` signature.
- `security.py` path-confinement helpers — gate every `MergeAction.path` before emission.

### Established Patterns
- **Pure functions over plain data** — `compute_merge_plan` is a pure function of `(vault_dir, rendered_notes, profile)`. Reads the filesystem, emits a dataclass, no writes. Apply is the only side-effectful function in this module.
- **Validation returns error lists** — `validate_merge_config(config) -> list[str]` never raises.
- **Lazy imports** — new public exports (`compute_merge_plan`, `apply_merge_plan`, `MergePlan`, `MergeAction`, `MergeResult`) added to `graphify/__init__.py` lazy-load map.
- **`from __future__ import annotations`** + single-line module docstring pattern.
- **TypedDict / frozen dataclass for structured returns** — Phase 2 uses TypedDict for `ClassificationContext`, Phase 3 uses dataclass for `MappingResult`. Phase 4 follows the latter for `MergePlan` / `MergeAction` / `MergeResult` — immutable, hashable, JSON-serializable via `dataclasses.asdict`.
- **Optional dependencies guarded at import time** — merge MUST NOT add any new required dependencies. PyYAML is NOT used for the read path either (see Claude's Discretion).

### Integration Points
- `graphify/__init__.py` — lazy import map gains `compute_merge_plan`, `apply_merge_plan`, `MergePlan`, `MergeAction`, `MergeResult`, `validate_merge_config`.
- `profile.py::_DEFAULT_PROFILE` — `merge.preserve_fields` default extended to include `created`; `merge.field_policies` added as optional dict (default empty).
- `profile.py::validate_profile` — gains a call into `validate_merge_config` (or keeps that logic inline — Claude's pick at plan time).
- **Phase 2 templates** — built-in templates under `graphify/builtin_templates/*.md` gain sentinel comments around wayfinder, connections, metadata, members, sub_communities, dataview blocks. Coordinate with any Phase 2 back-patching.
- **Phase 5 callsite** — `to_obsidian()` eventually calls:
  ```python
  plan = compute_merge_plan(vault_dir, rendered_notes, profile)
  if args.dry_run:
      print_plan(plan)
      return
  result = apply_merge_plan(plan)
  ```

### Creative Options the Architecture Enables
- **Dry-run is free.** Because `compute_merge_plan` is pure and returns a structured plan, `graphify --obsidian --dry-run` is a 3-line wrapper in Phase 5 that calls compute and prints. No duplicate logic, no dry-run-mode branches inside merge.
- **Pure-function testability.** `compute_merge_plan` tests are over `tmp_path` for vault inputs but produce deterministic `MergePlan` dataclasses that can be asserted cleanly without mocking filesystem writes. `apply_merge_plan` tests exercise the write path against a pristine plan.
- **Fingerprint = two independent signals.** If a future feature wants to detect "user stripped all fingerprints" (e.g., for a `graphify migrate` subcommand), the dual-signal design lets us distinguish "this note was never ours" from "this note was ours but the user opted out."
- **Deleted-block respect is state-free (D-68).** We don't need a manifest. The rule "refresh blocks that exist, don't re-insert missing ones" is checkable from the file alone. This is the single decision that let us say no to a sidecar manifest in Area A.
- **Content-hash compare = zero churn.** Re-running graphify on a vault with no graph changes should produce zero filesystem writes. `apply_merge_plan` compares `sha256(new_content) == sha256(old_content)` before `os.replace` and skips the write entirely when identical. Git diff stays clean, mtime stays stable, Obsidian doesn't re-index the vault unnecessarily.

</code_context>

<specifics>
## Specific Ideas

- **Path + fingerprint is the trust model.** Graphify trusts the path (you classified this note into `Atlas/Dots/Things/` → it's a thing) AND trusts the fingerprint (we wrote this note last run, or at least stamped it with our markers). Removing one of the two signals isn't enough to fool merge; removing both is how a user explicitly takes ownership of a note ("graphify, this is mine now").
- **`created:` must be in `preserve_fields`.** Phase 2 D-27 set `created:` on first render to today's ISO date. If merge ever rewrote that field on update, every re-run would reset `created:` to today. It's in the preserve list by default. Users who want to force-reset creation dates can run with `strategy: replace` and lose the preservation.
- **Per-key union semantics let users actually extend graphify's output.** The `collections` field is the motivating example: a user adds `[[Research Log]]` to a transformer note's collections, then re-runs graphify. Without union, their `[[Research Log]]` gets wiped. With union, graphify's canonical `[[Atlas]]` is guaranteed present, the user's `[[Research Log]]` stays, and both show up in Obsidian's Properties UI.
- **Unknown keys are conservatively preserved.** If a user adds `priority: high` to a note, graphify has no built-in policy for `priority:` and the fallback is `preserve`. This means adding new user frontmatter is never silently destroyed. The cost is: if graphify ships a new version with a new field called `priority:`, the first merge after upgrade won't overwrite an existing user's `priority:` value until the user adds it to the default policy table.
- **Sentinel deletion is state-free, by design.** We consciously rejected a sidecar manifest in Area A. That decision is consistent with D-68 only because "refresh blocks that currently exist, don't re-insert missing ones" is checkable from the file in front of us. No "what did graphify write last time?" history needed. This is the most important architectural insight of this phase.
- **Malformed sentinels fail loud, not self-heal.** D-69's "skip + warn, never auto-repair" rule is the same fail-loudly-continue-when-safe pattern as Phase 1 profile validation. Self-healing would mean trusting an algorithm's guess at block boundaries against potentially-mangled user content. Not a trade we're willing to make.
- **Orphans are visible but immortal.** D-72's "report but never delete" matches every other graphify guarantee: we never destroy files. Users who want auto-delete of orphans can opt in via a future profile flag (deferred). The default posture is ultra-conservative.
- **Content-hash skip = re-runs are cheap.** A user running graphify on a vault where nothing has changed should see zero filesystem writes, zero mtime bumps, zero git diffs. This is the combination of (a) `compute_merge_plan` emitting an UPDATE action whose `changed_fields` and `changed_blocks` are empty, plus (b) `apply_merge_plan` hash-comparing before the `os.replace` and skipping identical writes. Implement as two separate optimizations so empty UPDATE actions still appear in the plan for visibility.
- **Atomic writes via `.tmp + os.replace`.** `os.replace` is atomic on POSIX and Windows (Python docs guarantee). `.tmp` files live next to the target in the same directory to ensure they're on the same filesystem (otherwise `os.replace` degrades to copy+delete). Clean up stale `.tmp` files at the top of `apply_merge_plan` as a defensive pass.
- **Test vault fixtures are a corpus, not unit mocks.** `tests/fixtures/vaults/` directory: `empty/`, `pristine_graphify/`, `user_extended/`, `fingerprint_stripped/`, `malformed_sentinel/`, `preserve_fields_edited/`. Each is a real directory tree the test copies into `tmp_path` and runs `compute_merge_plan` against. This gives us test coverage over real-world vault states instead of constructed dicts.

</specifics>

<deferred>
## Deferred Ideas

- **`--force` flag to overwrite unmanaged files.** D-63 says first-touch collision skips. A future `--force` flag would bypass the fingerprint check and update anyway. Not in v1 — the skip-with-warning behavior is the safe default and users who want force-overwrite can delete the conflicting file manually. Revisit if the warning becomes a common pain point.
- **Auto-delete or auto-archive orphans.** D-72 says orphans are reported, never deleted. A future profile flag `merge.orphan_action: leave|delete|archive` would let power users opt in to tidy vaults. Out of scope for v1 because the data-loss risk of an incorrect action is very high.
- **Sidecar manifest for forensic merge.** Rejected in Area A. Would let merge know exactly what graphify wrote last run (per-field provenance, precise orphan detection even after renames). Would also introduce a state-sync problem with Obsidian's silent file renames. Not worth the complexity for v1. If users report real pain around orphans or rename drift, revisit.
- **Per-field provenance tracking.** "Was this specific frontmatter value last written by graphify or by a human?" Requires a sidecar or a hash-on-write scheme. Interesting for audit but not required for MRG-01 to work correctly.
- **Conflict resolution prompts.** Interactive "this field was edited by both sides, which wins?" behavior. Graphify is a batch tool (PROJECT.md constraint) — no interactive loops. Merge's deterministic per-key policy is the correct posture for batch runs. Defer any interactive behavior to a hypothetical future `graphify merge-interactive` subcommand.
- **Structured diff in `MergeAction` for UPDATE actions.** Noted in Claude's Discretion. The data is cheap to produce but inflates `MergePlan` size. Gated by a `verbose: bool` kwarg at plan time would be ideal; otherwise leave it as a `changed_fields: list[str]` / `changed_blocks: list[str]` summary.
- **Three-way merge with git ancestor.** "What was the version at the last commit" as a third data point beyond (user's current file, graphify's new output). Would give true git-style merge semantics. Out of scope — requires git integration and raises the question of "which commit is the ancestor?" None of the existing phases depend on git, so staying git-agnostic is valuable.
- **LLM-assisted merge of user prose.** If a user edits the `${body}` and graphify's sentinel blocks reference content the user has contradicted (e.g., user's prose now says "this node is deprecated" but graphify's Metadata callout still says `status: active`), an LLM could flag the conflict. Out of scope — graphify's mandate is structural, not content.
- **Merge preview in the HTML export.** A future `--merge-preview` mode could render the `MergePlan` as a diff viewer in the existing HTML output. Phase 5 concern at earliest.

</deferred>

---

*Phase: 04-merge-engine*
*Context gathered: 2026-04-11*
