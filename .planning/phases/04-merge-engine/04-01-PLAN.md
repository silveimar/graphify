---
phase: 04-merge-engine
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - graphify/templates.py
  - tests/test_templates.py
autonomous: true
requirements:
  - MRG-01
tags:
  - templates
  - sentinels
  - merge-coupling

must_haves:
  truths:
    - "Every non-empty wayfinder_callout emitted by render_note is wrapped in <!-- graphify:wayfinder:start --> / :end --> sentinel comments"
    - "Every non-empty connections_callout emitted by render_note is wrapped in <!-- graphify:connections:start --> / :end --> sentinel comments"
    - "Every non-empty metadata_callout emitted by render_note or render_moc is wrapped in <!-- graphify:metadata:start --> / :end --> sentinel comments"
    - "Every non-empty members_section emitted by render_moc is wrapped in <!-- graphify:members:start --> / :end --> sentinel comments"
    - "Every non-empty sub_communities_callout emitted by render_moc is wrapped in <!-- graphify:sub_communities:start --> / :end --> sentinel comments"
    - "Every non-empty dataview_block emitted by render_moc is wrapped in <!-- graphify:dataview:start --> / :end --> sentinel comments"
    - "Empty sections (returning '') do NOT emit stray sentinel markers"
  artifacts:
    - path: "graphify/templates.py"
      provides: "Section builders that return strings pre-wrapped in sentinel HTML comments"
    - path: "tests/test_templates.py"
      provides: "New assertions that confirm sentinel pairs appear in rendered notes"
  key_links:
    - from: "graphify/templates.py::_build_wayfinder_callout"
      to: "Rendered note body"
      via: "sentinel wrap applied before return"
      pattern: "graphify:wayfinder:start"
    - from: "graphify/templates.py::render_note substitution_ctx"
      to: "Outer template ${wayfinder_callout} placeholder"
      via: "pre-wrapped string passed through string.Template.safe_substitute"
      pattern: "<!-- graphify:.*:start -->"
---

<objective>
Back-patch Phase 2's section builders in `graphify/templates.py` to wrap every graphify-owned body block in paired HTML-comment sentinel markers per D-67. This unblocks Phase 4 merge: the sentinel parser in `merge.py` (Plan 03) needs real sentinel output to test against. Without this patch, fingerprint detection (D-62) and body-block refresh (D-67, D-68) cannot work.

Purpose: Satisfy D-62 (body-signal half of the dual fingerprint) and D-67 (sentinel grammar) prerequisite for all downstream merge work.

Output: Every built-in-template note rendered via `render_note` / `render_moc` / `render_community_overview` carries matched start/end sentinel comments around graphify-owned body regions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/04-merge-engine/04-CONTEXT.md
@.planning/phases/02-template-engine/02-CONTEXT.md
@graphify/templates.py
@graphify/profile.py
@tests/test_templates.py

<interfaces>
<!-- Section builders live in templates.py. Each returns a single string (possibly empty). -->
<!-- Merge will later parse these sentinels to detect fingerprints and refresh-vs-preserve regions. -->

From graphify/templates.py (existing):
```python
def _build_wayfinder_callout(note_type, parent_moc_label, profile, convention) -> str
def _build_connections_callout(G, node_id, convention) -> str
def _build_metadata_callout(*, source_file, source_location, community) -> str
def _build_members_section(members_by_type, convention) -> str
def _build_sub_communities_callout(sub_communities, convention) -> str
def _build_dataview_block(profile, community_tag, folder) -> str
```

Locked sentinel grammar (from CONTEXT.md D-67):
```
<!-- graphify:wayfinder:start -->
...content...
<!-- graphify:wayfinder:end -->
```

Sentinel block names (locked):
- Non-MOC notes: wayfinder, connections, metadata
- MOC / Community Overview: wayfinder, members, sub_communities, dataview, metadata

Frontmatter field `graphify_managed: true` is part of the dual-signal fingerprint (D-62)
but lives in `_build_frontmatter_fields` and is owned by Plan 03/04, NOT this plan.
This plan handles the BODY signal only.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wrap section builders in sentinel markers</name>
  <files>graphify/templates.py</files>
  <read_first>
    - graphify/templates.py (must read to see current section-builder return values and understand empty-string contract)
    - graphify/profile.py L359-394 (_dump_frontmatter — canonical writer; do NOT touch, but read to understand the emission grammar the merge reader will mirror)
    - .planning/phases/04-merge-engine/04-CONTEXT.md D-67, D-68, D-69 (sentinel grammar, deleted-block rule, malformed-sentinel rule — the grammar you emit here must be unambiguous to parse later)
    - graphify/builtin_templates/thing.md + moc.md (confirm ${wayfinder_callout}, ${connections_callout}, ${metadata_callout}, ${members_section}, ${sub_communities_callout}, ${dataview_block} placeholders exist exactly as listed)
  </read_first>
  <behavior>
    - Test 1: `_build_wayfinder_callout("thing", "Parent", {}, "title_case")` return value starts with `<!-- graphify:wayfinder:start -->\n` and ends with `\n<!-- graphify:wayfinder:end -->`.
    - Test 2: `_build_connections_callout(G, "n_iso", "title_case")` where `n_iso` has no edges returns exactly `""` — NO sentinel markers on empty output.
    - Test 3: `_build_metadata_callout(source_file=None, source_location=None, community=None)` returns exactly `""` — NO sentinel markers on empty output.
    - Test 4: `_build_members_section({"thing": []}, "title_case")` returns exactly `""` — no markers.
    - Test 5: `_build_members_section({"thing": [{"label": "T1"}]}, "title_case")` is wrapped in `<!-- graphify:members:start -->` / `:end -->`.
    - Test 6: `_build_sub_communities_callout([], "title_case")` returns exactly `""`.
    - Test 7: `_build_dataview_block({}, "community-x", "Atlas/Maps/")` (always returns a non-empty dataview fence) is wrapped in `<!-- graphify:dataview:start -->` / `:end -->`.
    - Test 8: A full `render_note` call produces output where `grep -c "graphify:wayfinder:start"` == 1 AND `grep -c "graphify:wayfinder:end"` == 1.
    - Test 9: A full `render_moc` call produces matched `members`, `sub_communities` (when sub_communities non-empty), `dataview`, `wayfinder`, `metadata` sentinel pairs.
  </behavior>
  <action>
Modify each of the six section-builder private functions in `graphify/templates.py` to wrap their final return string in sentinel HTML comments. Follow the exact grammar below.

**Module-level constant (add near the other constants around line 48):**
```python
# Sentinel grammar (D-67). Any change here MUST be mirrored in merge.py's
# sentinel parser — these strings are the source of truth for the body-signal
# half of the dual fingerprint (D-62).
_SENTINEL_START_FMT: str = "<!-- graphify:{name}:start -->"
_SENTINEL_END_FMT: str = "<!-- graphify:{name}:end -->"

def _wrap_sentinel(name: str, content: str) -> str:
    """Wrap a non-empty section in paired HTML-comment sentinel markers.

    Returns the original (empty) string when *content* is empty — empty
    sections never emit stray markers per the empty-string contract (D-18)
    and the D-68 deleted-block-respect rule.
    """
    if not content:
        return ""
    start = _SENTINEL_START_FMT.format(name=name)
    end = _SENTINEL_END_FMT.format(name=name)
    return f"{start}\n{content}\n{end}"
```

**Then update each of the six section builders:**

1. `_build_wayfinder_callout` — at the bottom, replace the final `return (...)` with:
   ```python
   body = (
       "> [!note] Wayfinder\n"
       f"> Up: {up_link}\n"
       f"> Map: {atlas_link}"
   )
   return _wrap_sentinel("wayfinder", body)
   ```
   Note: wayfinder is ALWAYS non-empty (there is always at least an Atlas link fallback), so it will always be wrapped.

2. `_build_connections_callout` — the existing `if not lines: return ""` stays. Replace the final `return "> [!info] Connections\n" + "\n".join(lines)` with:
   ```python
   body = "> [!info] Connections\n" + "\n".join(lines)
   return _wrap_sentinel("connections", body)
   ```

3. `_build_metadata_callout` — the existing `if len(lines) == 1: return ""` stays. Replace the final `return "\n".join(lines)` with:
   ```python
   body = "\n".join(lines)
   return _wrap_sentinel("metadata", body)
   ```

4. `_build_members_section` — the final `return "\n\n".join(blocks)` returns `""` when blocks is empty. Replace with:
   ```python
   body = "\n\n".join(blocks)
   return _wrap_sentinel("members", body)
   ```
   (`_wrap_sentinel` handles the empty case internally.)

5. `_build_sub_communities_callout` — the existing `if not sub_communities: return ""` stays. Replace the final `return "\n".join(lines)` with:
   ```python
   body = "\n".join(lines)
   return _wrap_sentinel("sub_communities", body)
   ```

6. `_build_dataview_block` — dataview is always non-empty (fallback query applies). Replace the final `return f"```dataview\n{query}\n```"` with:
   ```python
   body = f"```dataview\n{query}\n```"
   return _wrap_sentinel("dataview", body)
   ```

**DO NOT modify:**
- `_dump_frontmatter` (frontmatter-level fingerprint is Plan 03/04's concern)
- `_build_frontmatter_fields` (field emission order stays identical)
- The built-in template .md files under `graphify/builtin_templates/` — placeholders already flow through
- `render_note` / `render_moc` / `_render_moc_like` orchestration bodies
- Empty-string contract (D-18): empty sections MUST still return exactly `""`
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && pytest tests/test_templates.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - grep returns count 1: `grep -c "_SENTINEL_START_FMT" graphify/templates.py` == 1 (constant defined once)
    - grep returns count 1: `grep -c "def _wrap_sentinel" graphify/templates.py` == 1
    - grep returns count 6: `grep -c "_wrap_sentinel(" graphify/templates.py` >= 6 (used in each of six section builders)
    - `python -c "from graphify.templates import _build_wayfinder_callout; s = _build_wayfinder_callout('thing', 'Parent', {}, 'title_case'); assert s.startswith('<!-- graphify:wayfinder:start -->\n'); assert s.endswith('\n<!-- graphify:wayfinder:end -->')"` exits 0
    - `python -c "from graphify.templates import _build_connections_callout; import networkx as nx; G = nx.Graph(); G.add_node('n_iso', label='Iso'); assert _build_connections_callout(G, 'n_iso', 'title_case') == ''"` exits 0
    - `python -c "from graphify.templates import _build_metadata_callout; assert _build_metadata_callout(source_file=None, source_location=None, community=None) == ''"` exits 0
    - pytest tests/test_templates.py passes (existing tests unmodified must still pass — the empty-string contract and substitution flow are unchanged for empty sections)
  </acceptance_criteria>
  <done>All six section builders emit paired sentinel markers around non-empty output; empty output is untouched; existing test_templates.py tests still pass; the sentinel grammar constant is declared exactly once as the single source of truth.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add sentinel round-trip assertions to test_templates.py</name>
  <files>tests/test_templates.py</files>
  <read_first>
    - tests/test_templates.py (read the existing test patterns — fixture style, helper functions, assertion style)
    - tests/fixtures/template_context.py (if it exists — reusable ClassificationContext fixture)
    - graphify/templates.py (the now-updated section builders and render functions)
  </read_first>
  <behavior>
    - Test `test_render_note_emits_matched_wayfinder_sentinels`: render a Thing note and assert body contains exactly one `<!-- graphify:wayfinder:start -->` AND exactly one `<!-- graphify:wayfinder:end -->`.
    - Test `test_render_note_emits_matched_connections_sentinels`: render a Thing with outgoing edges, assert matched `connections` sentinels exist.
    - Test `test_render_note_omits_connections_sentinel_when_no_edges`: render an isolated Thing, assert neither `<!-- graphify:connections:start -->` nor `<!-- graphify:connections:end -->` appears.
    - Test `test_render_moc_emits_all_moc_sentinels`: render a MOC with members and sub_communities, assert matched pairs for `wayfinder`, `members`, `sub_communities`, `dataview`, `metadata`.
    - Test `test_render_moc_omits_members_sentinel_when_empty`: render a MOC with empty members_by_type, assert neither `members:start` nor `members:end` appears.
    - Test `test_sentinel_start_end_are_paired_in_render_output`: for every `<!-- graphify:<name>:start -->` in the rendered output, a matching `<!-- graphify:<name>:end -->` MUST appear exactly once, and in order.
  </behavior>
  <action>
Append a new `class TestSentinelMarkers:` test group (or a top-level section marked `# --- Phase 4 sentinel round-trip (D-67) ---`) to `tests/test_templates.py`. All tests must:

- Use the existing ClassificationContext / graph fixture style (look at how `test_render_note_builtin_template_scaffold` or equivalent tests construct inputs).
- Build a minimal `networkx.Graph` with 1-3 nodes for non-MOC cases.
- For MOC cases, build a `classification_context` dict with `members_by_type={"thing": [{"label": "T1"}]}` and `sub_communities=[{"label": "mini", "members": [{"label": "m1"}]}]`.
- Use `_emit_wikilink`-free assertions — check ONLY for presence/absence of the sentinel comment strings, not the content between them.

**Exact assertions:**

```python
import re

_START_PATTERN = re.compile(r"<!-- graphify:(\w+):start -->")
_END_PATTERN = re.compile(r"<!-- graphify:(\w+):end -->")

def _collect_sentinels(text: str) -> tuple[list[str], list[str]]:
    starts = [m.group(1) for m in _START_PATTERN.finditer(text)]
    ends = [m.group(1) for m in _END_PATTERN.finditer(text)]
    return starts, ends

def test_render_note_emits_matched_wayfinder_sentinels():
    # ... build G, ctx ...
    _, text = render_note("n1", G, {}, "thing", ctx)
    starts, ends = _collect_sentinels(text)
    assert starts.count("wayfinder") == 1
    assert ends.count("wayfinder") == 1

def test_sentinel_start_end_are_paired_in_render_output():
    # ... render a MOC with all sections populated ...
    starts, ends = _collect_sentinels(text)
    # Every start has a matching end in the SAME ORDER and SAME COUNT
    assert starts == ends, f"unmatched sentinels: starts={starts} ends={ends}"
```

Cover all six test cases in the behavior block. Use `tmp_path` only if a test actually needs filesystem (most won't — pass `vault_dir=None` to use built-in templates).
  </action>
  <verify>
    <automated>cd /Users/silveimar/Documents/silogia-repos/companion-util_repos/graphify && pytest tests/test_templates.py -k "sentinel" -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_render_note_emits_matched_wayfinder_sentinels" tests/test_templates.py` == 1
    - `grep -c "def test_render_note_omits_connections_sentinel_when_no_edges" tests/test_templates.py` == 1
    - `grep -c "def test_render_moc_emits_all_moc_sentinels" tests/test_templates.py` == 1
    - `grep -c "def test_render_moc_omits_members_sentinel_when_empty" tests/test_templates.py` == 1
    - `grep -c "def test_sentinel_start_end_are_paired_in_render_output" tests/test_templates.py` == 1
    - `pytest tests/test_templates.py -k sentinel -q` exits 0 with at least 5 tests collected and passing
    - `pytest tests/test_templates.py -q` exits 0 (no regression in existing template tests)
  </acceptance_criteria>
  <done>Five-plus sentinel round-trip tests added and passing; full test_templates.py still green; assertions check pair-matching, presence on non-empty sections, and absence on empty sections.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| rendered-note → vault file (future, Phase 4 downstream) | Sentinel content emitted here will later be parsed by `merge.py`; malformed grammar here becomes a correctness bug there |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01 | Tampering | `_build_connections_callout` via node labels containing `<!-- graphify:*:end -->` in the label string | mitigate | Node labels are sanitized upstream by `_sanitize_wikilink_alias` (strips `]]`, `|`, newlines) and by `safe_frontmatter_value` for scalar emission. The sentinel comment is emitted as a fixed literal from `_wrap_sentinel`, NOT interpolated from user data; an adversarial label cannot inject a premature end marker because the label only appears inside the wikilink body, not between sentinel-literal brackets. Plan 06 adds a test asserting that a label containing `graphify:connections:end` does not break sentinel pairing. |
| T-04-02 | Information Disclosure | Empty section builder inadvertently emits a start marker with no content | accept | `_wrap_sentinel` short-circuits on empty content — no marker emitted. The empty-string contract (D-18) is preserved and tested in Task 2. |
| T-04-03 | Denial of Service | Extremely long section content (e.g., 10,000-edge connections) produces massive sentinel block | accept | Sentinel markers add only ~60 bytes per block; orthogonal to section size. Size caps on upstream node/edge counts are existing concerns (Phase 1 `safe_frontmatter_value`). |
</threat_model>

<verification>
- `pytest tests/test_templates.py -q` passes with zero regressions
- Manual inspection: render a minimal Thing note and confirm sentinel pairs are visually present and well-formed
- grep audit: `grep -c "_wrap_sentinel" graphify/templates.py` equals exactly 6 call sites (one per section builder) + 1 definition = 7
</verification>

<success_criteria>
- All six section builders wrap non-empty output in paired `<!-- graphify:<name>:start --> / :end -->` markers
- Empty sections produce exactly `""` (no stray markers)
- `_wrap_sentinel` helper and `_SENTINEL_START_FMT` / `_SENTINEL_END_FMT` constants are the single source of truth for sentinel grammar — Plan 03's sentinel parser will reference this file as its canonical writer
- Sentinel round-trip tests assert presence, absence, and pair-matching behavior
- Full `pytest tests/test_templates.py` suite remains green
</success_criteria>

<output>
After completion, create `.planning/phases/04-merge-engine/04-01-SUMMARY.md` capturing: the sentinel grammar committed, the file mutations made to templates.py (line numbers of the six call sites + the helper definition), and any surprises encountered while rendering.
</output>
