# Phase 34: Mapping, Cluster Quality & Note Classes - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 11 new/modified files
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/mapping.py` | service | transform | `graphify/mapping.py` | exact |
| `graphify/export.py` | service | file-I/O | `graphify/export.py` | exact |
| `graphify/templates.py` | service | transform | `graphify/templates.py` | exact |
| `graphify/profile.py` | config | request-response | `graphify/profile.py` | exact |
| `graphify/naming.py` | utility | transform | `graphify/naming.py` | exact |
| `graphify/builtin_templates/code.md` | config | transform | `graphify/builtin_templates/thing.md` | role-match |
| `tests/test_mapping.py` | test | transform | `tests/test_mapping.py` | exact |
| `tests/test_export.py` | test | file-I/O | `tests/test_export.py` | exact |
| `tests/test_templates.py` | test | transform | `tests/test_templates.py` | exact |
| `tests/test_profile.py` | test | request-response | `tests/test_profile.py` | exact |
| `tests/test_naming.py` | test | transform | `tests/test_naming.py` | exact |

## Pattern Assignments

### `graphify/mapping.py` (service, transform)

**Analog:** `graphify/mapping.py`

**Imports pattern** (lines 1-17):
```python
"""Mapping engine: pure classification of graph nodes into note types and folders."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TypedDict

import networkx as nx

from graphify.analyze import (
    _is_concept_node,
    _is_file_node,
    _node_community_map,
    god_nodes,
)
from graphify.templates import ClassificationContext, _NOTE_TYPES
```

**Classification pipeline pattern** (lines 277-408):
```python
def classify(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    *,
    cohesion: dict[int, float] | None = None,
) -> MappingResult:
    """Classify every real node into a ClassificationContext.

    Precedence pipeline (D-47):
        1. Explicit mapping_rules — first-match-wins
        2. Built-in topology fallback — god node → thing
        3. Default — statement
    """
    from graphify.cluster import score_all

    folder_mapping = _effective_folder_mapping(profile)
    top_n = (
        profile.get("topology", {})
        .get("god_node", {})
        .get("top_n", 10)
    )
    raw_rules = profile.get("mapping_rules") or []
    compiled_rules = compile_rules(raw_rules)
```

**Synthetic-node exclusion pattern** (lines 340-391):
```python
    for _cid, node_id in ordered_nodes:
        # (1) Unconditional concept skip (D-50/D-51).
        if _is_concept_node(G, node_id):
            skipped.add(node_id)
            continue

        is_file_hub = _is_file_node(G, node_id)
        matched_rule: tuple[int, dict, dict] | None = None
        for idx, rule in enumerate(compiled_rules):
            when = rule.get("when") or {}
            then = rule.get("then") or {}
            if _match_when(when, node_id, G, ctx=ctx):
                matched_rule = (idx, when, then)
                break

        # (2) File-hub opt-in: only surfaces when the matching rule was
        #     {topology: is_source_file} (D-51). Otherwise skip the hub.
        if is_file_hub:
            if matched_rule is None or matched_rule[1].get("topology") != "is_source_file":
                skipped.add(node_id)
                continue
```

**Community routing pattern** (lines 560-643):
```python
    raw_threshold = profile.get("mapping", {}).get("min_community_size", 3)
    if isinstance(raw_threshold, bool) or not isinstance(raw_threshold, int):
        threshold = 3
    else:
        threshold = raw_threshold

    above_cids = sorted(
        cid for cid, members in communities.items() if len(members) >= threshold
    )
    below_cids = sorted(
        cid for cid, members in communities.items() if len(members) < threshold
    )

    # --- Below-threshold: resolve hosts or route to bucket ------------------
    hostless_below: list[int] = []
    below_to_host: dict[int, int] = {}
    for below_cid in below_cids:
        host = _nearest_host(below_cid, above_cids, inter_edges, community_sizes)
        if host is None:
            hostless_below.append(below_cid)
        else:
            below_to_host[below_cid] = host
```

**Apply to Phase 34:** keep CODE classification in `classify()`/`_assemble_communities()` by enriching `ClassificationContext`; do not add a parallel manifest. Change the fallback god-node note type from `thing` to `code` only when the node is a real code node with a non-empty `source_file`, excluding concept nodes and file hubs with the same filters shown above. Add routing metadata alongside existing `per_community` contexts where host/bucket decisions are made.

---

### `graphify/export.py` (service, file-I/O)

**Analog:** `graphify/export.py`

**Imports pattern** (lines 1-17):
```python
# write graph to HTML, JSON, SVG, GraphML, Obsidian vault, and Neo4j Cypher
from __future__ import annotations
import html as _html
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Callable
import networkx as nx
from networkx.readwrite import json_graph
from graphify.security import sanitize_label
from graphify.analyze import _node_community_map, _fmt_source_file
from graphify.profile import safe_filename, safe_frontmatter_value, safe_tag
```

**Repo/concept resolution pre-render pattern** (lines 612-640):
```python
    if profile is None:
        profile = load_profile(out)
    artifacts_dir = out.resolve().parent
    from graphify.naming import resolve_concept_names, resolve_repo_identity
    resolved_repo_identity = resolve_repo_identity(
        Path.cwd(),
        cli_identity=repo_identity,
        profile=profile,
    )
    if not dry_run:
        _write_repo_identity_sidecar(artifacts_dir, resolved_repo_identity)
    concept_names = resolve_concept_names(
        G,
        communities,
        profile,
        artifacts_dir,
        llm_namer=concept_namer,
        dry_run=dry_run,
    )
    resolved_labels = {
        cid: concept.title
        for cid, concept in concept_names.items()
    }

    mapping_result = classify(G, communities, profile, cohesion=cohesion)
```

**Render loop and graceful skip pattern** (lines 656-691):
```python
    # ---- Per-node notes (thing / statement / person / source) ----
    for node_id, ctx in per_node.items():
        if node_id in skipped:
            continue
        note_type = ctx.get("note_type", "statement")
        if note_type in ("moc", "community"):
            # MOC-shaped classification belongs in per_community, not per_node —
            # defensive skip to avoid double-rendering.
            continue
        try:
            filename, rendered_text = render_note(
                node_id, G, profile, note_type, ctx, vault_dir=out,
            )
        except (ValueError, FileNotFoundError) as exc:
            print(
                f"[graphify] to_obsidian: skipping node {node_id!r} "
                f"({note_type}): {exc}",
                file=sys.stderr,
            )
            continue
```

**Community rendering pattern** (lines 693-727):
```python
    # ---- Per-community MOC notes ----
    for cid, ctx in per_community.items():
        note_type = ctx.get("note_type", "moc")
        render_fn = render_moc if note_type == "moc" else None
        if render_fn is None:
            # community-overview shape: Phase 2's render_community_overview
            from graphify.templates import render_community_overview
            render_fn = render_community_overview
        try:
            filename, rendered_text = render_fn(
                cid, G, communities, profile, ctx, vault_dir=out,
            )
```

**Apply to Phase 34:** compute CODE filename stems after `resolve_repo_identity()` and after `classify()` produces code contexts. Inject `filename_stem`, collision fields, and any final concept MOC labels into node contexts before `render_note()`. Coerce `community` to `moc` in this boundary or lower in templates so normal `to_obsidian()` never writes `_COMMUNITY_*` outputs.

---

### `graphify/templates.py` (service, transform)

**Analog:** `graphify/templates.py`

**Note-type whitelist pattern** (lines 50-52):
```python
_NOTE_TYPES: frozenset[str] = frozenset({
    "moc", "community", "thing", "statement", "person", "source",
})
```

**Template required-fields pattern** (lines 542-549):
```python
_REQUIRED_PER_TYPE: dict[str, set[str]] = {
    "moc": {"frontmatter", "label", "members_section", "dataview_block"},
    "community": {"frontmatter", "label", "members_section", "dataview_block"},
    "thing": {"frontmatter", "label"},
    "statement": {"frontmatter", "label"},
    "person": {"frontmatter", "label"},
    "source": {"frontmatter", "label"},
}
```

**Wikilink safety pattern** (lines 649-667):
```python
def _sanitize_wikilink_alias(label: str) -> str:
    """Replace characters that would break wikilink alias syntax."""
    out = label
    for bad, repl in _WIKILINK_ALIAS_FORBIDDEN.items():
        out = out.replace(bad, repl)
    out = _WIKILINK_ALIAS_CONTROL_RE.sub(" ", out)
    return out


def _emit_wikilink(label: str, convention: str) -> str:
    """Return `[[filename|label]]` auto-aliased to display label."""
    fname = resolve_filename(label, convention)
    alias = _sanitize_wikilink_alias(label)
    return f"[[{fname}|{alias}]]"
```

**Frontmatter construction pattern** (lines 688-733):
```python
def _build_frontmatter_fields(
    *,
    up: list[str],
    related: list[str],
    collections: list[str],
    tags: list[str],
    note_type: str,
    file_type: str | None,
    source_file: str | None,
    source_location: str | None,
    community: str | None,
    created: datetime.date,
    cohesion: float | None = None,
) -> dict:
    fields: dict = {}
    if up:
        fields["up"] = up
    if related:
        fields["related"] = related
    if collections:
        fields["collections"] = collections
    fields["created"] = created
```

**Non-MOC `up:` and related-link pattern** (lines 1017-1034):
```python
    ctx = classification_context
    parent_moc_label = ctx.get("parent_moc_label") if isinstance(ctx, dict) else None
    community_tag = ctx.get("community_tag") if isinstance(ctx, dict) else None
    community_name = (
        ctx.get("community_name") or ctx.get("parent_moc_label")
    ) if isinstance(ctx, dict) else None
    sibling_labels = ctx.get("sibling_labels", []) if isinstance(ctx, dict) else []

    # Build each section as a pre-rendered scalar (D-18)
    up_list: list[str] = []
    if parent_moc_label:
        up_list.append(_emit_wikilink(parent_moc_label, convention))

    related_list: list[str] = [
        _emit_wikilink(lab, convention) for lab in sibling_labels if lab
    ]
```

**MOC render-from-context pattern** (lines 1234-1256):
```python
def _render_moc_like(
    community_id: int,
    G,
    communities: dict,
    profile: dict,
    classification_context,
    template_key: str,  # "moc" or "community"
    vault_dir,
    created: "datetime.date | None" = None,
    *,
    note_type: str | None = None,
) -> tuple[str, str]:
    """Shared rendering body for MOC and Community Overview notes.

    If you find yourself reaching for G here, the right answer is almost always
    "add the derived data to ClassificationContext in Phase 3 and consume it here."
    """
```

**Apply to Phase 34:** add `code` everywhere `_NOTE_TYPES`, `_REQUIRED_PER_TYPE`, render-time non-MOC allowed types, built-in template loading, and dataview lookup expect note types. Preserve `_emit_wikilink()`, `_build_frontmatter_fields()`, and `_dump_frontmatter()` as the only link/frontmatter sinks. Add CODE member rendering to MOC context rather than graph-walking inside `_render_moc_like()`.

---

### `graphify/profile.py` (config, request-response)

**Analog:** `graphify/profile.py`

**Default profile pattern** (lines 64-120):
```python
_DEFAULT_PROFILE: dict = {
    "taxonomy": {
        "version": "v1.8",
        "root": "Atlas/Sources/Graphify",
        "folders": {
            "moc": "MOCs",
            "thing": "Things",
            "statement": "Statements",
            "person": "People",
            "source": "Sources",
            "default": "Things",
            "unclassified": "MOCs",
        },
    },
    "folder_mapping": {
        "moc": "Atlas/Sources/Graphify/MOCs/",
        "thing": "Atlas/Sources/Graphify/Things/",
        "statement": "Atlas/Sources/Graphify/Statements/",
        "person": "Atlas/Sources/Graphify/People/",
        "source": "Atlas/Sources/Graphify/Sources/",
        "default": "Atlas/Sources/Graphify/Things/",
    },
    ...
    "mapping": {"min_community_size": 3},
}
```

**Known note-type validation pattern** (lines 167-173):
```python
# Phase 31 (TMPL-03, D-12): per-note-type keys allowed under `dataview_queries:`.
# Frozen to exactly six members. Defined in profile.py (not templates.py) to
# avoid the templates.py ↔ profile.py import cycle — same precedent as
# `_REQUIRED_PER_TYPE` (see validate_profile_preflight Layer 2 below).
_KNOWN_NOTE_TYPES: frozenset[str] = frozenset(
    {"moc", "community", "thing", "statement", "person", "source"}
)
```

**Validation accumulator pattern** (lines 553-567):
```python
def validate_profile(profile: dict) -> list[str]:
    """Validate a profile dict. Returns a list of error strings — empty means valid."""
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]

    errors: list[str] = []

    # Unknown top-level keys
    for key in profile:
        if key not in _VALID_TOP_LEVEL_KEYS:
            errors.append(f"Unknown profile key '{key}' — valid keys are: {sorted(_VALID_TOP_LEVEL_KEYS)}")
```

**Literal min-community-size validation pattern** (lines 871-892):
```python
    mapping = profile.get("mapping")
    if mapping is not None:
        if not isinstance(mapping, dict):
            errors.append("'mapping' must be a mapping (dict)")
        else:
            if "moc_threshold" in mapping:
                errors.append(
                    "mapping.moc_threshold is no longer supported; "
                    "use mapping.min_community_size"
                )
            threshold = mapping.get("min_community_size")
            if threshold is not None:
                if isinstance(threshold, bool) or not isinstance(threshold, int):
                    errors.append(
                        f"mapping.min_community_size must be an integer "
                        f"(got {type(threshold).__name__})"
                    )
                elif threshold < 1:
                    errors.append(
                        f"mapping.min_community_size must be ≥ 1 (got {threshold})"
                    )
```

**Safety helpers pattern** (lines 1133-1164):
```python
def safe_tag(name: str) -> str:
    """Slugify a community name into a valid Obsidian tag component."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if slug and slug[0].isdigit():
        slug = "x" + slug
    return slug or "community"


def safe_filename(label: str, max_len: int = 200) -> str:
    """Sanitize a label for use as a filename."""
    name = unicodedata.normalize("NFC", label)
    name = re.sub(
        r'[\\/*?:"<>|#^[\]\x00-\x1f\x7f\u0085\u2028\u2029]', "", name
    ).strip() or "unnamed"
    if len(name) > max_len:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = name[:max_len - 9] + "_" + suffix
    return name
```

**Apply to Phase 34:** update default `mapping.min_community_size` to `6`, add `code` to taxonomy/folder mappings only if it needs a distinct folder, and update `_KNOWN_NOTE_TYPES`/`dataview_queries` validation for `code`. Keep `community` as recognized legacy input with warnings rather than a normal output target.

---

### `graphify/naming.py` (utility, transform)

**Analog:** `graphify/naming.py`

**Repo identity pattern** (lines 52-64):
```python
def normalize_repo_identity(value: str) -> str:
    """Normalize a repo identity into a short path-safe slug."""
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("repo identity must not contain path segments or '..'")

    raw = value.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        return "repo"
    if len(slug) > _REPO_IDENTITY_MAX_LEN:
        suffix = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:_REPO_IDENTITY_MAX_LEN - 9]}-{suffix}"
    return slug
```

**Deterministic signature pattern** (lines 182-195):
```python
def _community_signature(G: nx.Graph, members: list[str]) -> str:
    """Hash sorted member IDs, labels, and source files into a stable signature."""
    payload = []
    for node_id in sorted(str(member) for member in members):
        data = G.nodes.get(node_id, {})
        payload.append(
            {
                "id": node_id,
                "label": str(data.get("label", node_id)),
                "source_file": _stringify_source_file(data.get("source_file", "")),
            }
        )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

**Filename-stem pattern** (lines 235-243):
```python
def _filename_stem(title: str) -> str:
    name = unicodedata.normalize("NFC", title.replace(" ", "_"))
    name = re.sub(
        r'[\\/*?:"<>|#^[\]\x00-\x1f\x7f\u0085\u2028\u2029]', "", name
    ).strip() or "unnamed"
    if len(name) > 200:
        suffix = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        name = name[:191] + "_" + suffix
    return name
```

**Apply to Phase 34:** put CODE filename helper here if it can stay pure and graph-agnostic. Use grouped collision handling: base stem `CODE_<repo>_<node>` from existing safe filename logic, then suffix all members of a colliding group with `sha256(node_id + "\0" + source_file)[:8]` so output is stable independent of graph insertion order.

---

### `graphify/builtin_templates/code.md` (config, transform)

**Analog:** `graphify/builtin_templates/thing.md`

**Default non-MOC template pattern** (lines 1-10):
```markdown
${frontmatter}
# ${label}

${wayfinder_callout}

${body}

${connections_callout}

${metadata_callout}
```

**Apply to Phase 34:** start `code.md` as a thing-like template to prove note class identity and CODE<->concept navigation. Keep CODE-specific polish minimal in this phase; Phase 35 owns broader template presentation.

---

### `tests/test_mapping.py` (test, transform)

**Analog:** `tests/test_mapping.py`

**Fixture/profile pattern** (lines 91-126):
```python
def _profile(**overrides) -> dict:
    base = {
        "taxonomy": {
            "version": "v1.8",
            "root": "Atlas/Sources/Graphify",
            "folders": {
                "moc": "MOCs",
                "thing": "Things",
                "statement": "Statements",
                "person": "People",
                "source": "Sources",
                "default": "Things",
                "unclassified": "MOCs",
            },
        },
        ...
        "topology": {"god_node": {"top_n": 1}},
        "mapping": {"min_community_size": 3},
    }
    base.update(overrides)
    return base
```

**Host-first routing test pattern** (lines 516-528):
```python
def test_community_below_threshold_collapses_to_host():
    """VALIDATION row 3-01-10."""
    from graphify.mapping import classify

    G, communities = make_classification_fixture()
    result = classify(G, communities, _profile())
    # cid 1 should collapse into cid 0 via the n_transformer—n_auth edge.
    subs = result["per_community"][0]["sub_communities"]
    labels_in_subs = {s["label"] for s in subs}
    assert "AuthService" in labels_in_subs
    # n_auth's per_node ctx points parent_moc_label at "Transformer"
    assert result["per_node"]["n_auth"]["parent_moc_label"] == "Transformer"
```

**Bucket MOC test pattern** (lines 530-560):
```python
def test_bucket_moc_absorbs_hostless_below_threshold():
    """VALIDATION row 3-01-13: all-below-threshold corpus → bucket MOC."""
    import networkx as nx

    from graphify.mapping import classify

    G = nx.Graph()
    # Two below-threshold isolated communities, no inter-community edges
    G.add_node("a", label="A", file_type="code", source_file="a.py", source_location="L1")
    G.add_node("b", label="B", file_type="code", source_file="b.py", source_location="L1")
    communities = {0: ["a"], 1: ["b"]}
    result = classify(G, communities, _profile())
    assert -1 in result["per_community"]
    assert result["per_community"][-1]["community_name"] == "_Unclassified"
    assert len(result["per_community"][-1]["sub_communities"]) == 2
```

**Apply to Phase 34:** add focused tests for default floor `6`, literal floor override `1`, routing metadata values, CODE eligibility for code-backed god nodes, and negative cases for concept/file hub/document nodes.

---

### `tests/test_export.py` (test, file-I/O)

**Analog:** `tests/test_export.py`

**Dry-run path assertion pattern** (lines 191-230):
```python
def test_to_obsidian_no_profile_dry_run_uses_graphify_default_paths(tmp_path):
    from graphify.export import to_obsidian
    import networkx as nx

    G = nx.Graph()
    G.add_node(
        "transformer",
        label="Transformer",
        file_type="code",
        source_file="model.py",
        source_location="L1",
        community=0,
    )
    ...
    plan = to_obsidian(
        G,
        communities={0: ["transformer", "softmax"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
    )

    relative_paths = [
        action.path.relative_to(obsidian_dir).as_posix()
        for action in plan.actions
        if action.action == "CREATE"
    ]
    assert relative_paths
    assert all(path.startswith("Atlas/Sources/Graphify/") for path in relative_paths)
```

**Repo identity sidecar pattern** (lines 316-338):
```python
def test_to_obsidian_profile_repo_identity_records_sidecar(tmp_path):
    from graphify.export import to_obsidian

    G, communities = _phase33_graph()
    out_root = tmp_path / "graphify-out"
    obsidian_dir = out_root / "obsidian"
    profile = {
        "repo": {"identity": "profile-repo"},
        "naming": {"concept_names": {"enabled": False}},
    }

    to_obsidian(
        G,
        communities,
        output_dir=str(obsidian_dir),
        profile=profile,
    )

    payload = json.loads((out_root / "repo-identity.json").read_text(encoding="utf-8"))
    assert payload["identity"] == "profile-repo"
```

**Apply to Phase 34:** add dry-run assertions that CODE notes produce `CODE_<repo>_<node>.md`, concept MOCs still produce normal concept filenames, CODE filename collisions hash deterministically in both graph insertion orders, and no generated path contains `_COMMUNITY_`.

---

### `tests/test_templates.py` (test, transform)

**Analog:** `tests/test_templates.py`

**Known-vars and context shape pattern** (lines 53-80):
```python
def test_known_vars_frozen():
    from graphify.templates import KNOWN_VARS

    assert isinstance(KNOWN_VARS, frozenset)
    assert KNOWN_VARS == {
        "label",
        "frontmatter",
        "wayfinder_callout",
        "connections_callout",
        "members_section",
        "sub_communities_callout",
        "dataview_block",
        "metadata_callout",
        "body",
    }


def test_classification_context_declares_community_name():
    from graphify.templates import ClassificationContext

    assert "community_name" in typing.get_type_hints(ClassificationContext)
```

**Non-MOC note type test pattern** (lines 929-940):
```python
def test_render_note_all_four_non_moc_types_work():
    from tests.fixtures.template_context import make_min_graph, make_classification_context
    from graphify.templates import render_note

    G = make_min_graph()
    ctx = make_classification_context()
    profile = {"naming": {"convention": "title_case"}, "obsidian": {"atlas_root": "Atlas"}}
    for note_type in ("thing", "statement", "person", "source"):
        fname, text = render_note("n_transformer", G, profile, note_type, ctx)
        assert fname.endswith(".md"), f"{note_type}: fname missing .md"
        assert len(text) > 0, f"{note_type}: text is empty"
        assert f"type: {note_type}" in text, f"{note_type}: type not in frontmatter"
```

**MOC context-only render pattern** (lines 1716-1736):
```python
def test_render_moc_does_not_consult_graph():
    from tests.fixtures.template_context import make_min_graph, make_moc_context
    from graphify.templates import render_moc

    G = make_min_graph()
    # Add extra nodes NOT in classification_context members_by_type
    G.add_node("n_ghost_1", label="GhostNodeOne", file_type="code", source_file="src/ghost.py")
    ...
    ctx = make_moc_context(members_by_type={
        "thing": [{"id": "n_transformer", "label": "Transformer"}],
        "statement": [], "person": [], "source": [],
    })
    _, text = render_moc(0, G, communities, profile, ctx)
    assert "GhostNodeOne" not in text
```

**Apply to Phase 34:** extend the non-MOC type loop to include `code`; add assertions for CODE `up:` frontmatter and body Wayfinder links; add MOC tests for CODE member links in `related:` and/or a CODE member section driven entirely by `ClassificationContext`.

---

### `tests/test_profile.py` (test, request-response)

**Analog:** `tests/test_profile.py`

**Default profile floor test pattern** (lines 728-732):
```python
def test_default_profile_includes_topology_and_mapping_keys():
    from graphify.profile import _DEFAULT_PROFILE
    assert _DEFAULT_PROFILE["topology"]["god_node"]["top_n"] == 10
    assert _DEFAULT_PROFILE["mapping"]["min_community_size"] == 3
    assert "moc_threshold" not in _DEFAULT_PROFILE["mapping"]
```

**Dataview note-type validation pattern** (lines 1614-1637):
```python
def test_dataview_queries_validates_against_known_types():
    """Every member of _KNOWN_NOTE_TYPES is accepted as a key."""
    from graphify.profile import _KNOWN_NOTE_TYPES
    assert _KNOWN_NOTE_TYPES == frozenset(
        {"moc", "community", "thing", "statement", "person", "source"}
    )
    profile = {
        "dataview_queries": {
            note_type: f"TABLE q FROM #t/{note_type}"
            for note_type in _KNOWN_NOTE_TYPES
        }
    }
    assert validate_profile(profile) == []
```

**Deprecation warning pattern** (lines 1022-1033):
```python
def test_profile_v18_community_template_deprecation_warning(tmp_path):
    community_template = "---\n${frontmatter}---\n# ${label}\n${members_section}\n"
    vault = _mk_vault(
        tmp_path,
        profile_yaml=_V18_REQUIRED_YAML,
        templates={"community.md": community_template},
    )
    result = validate_profile_preflight(vault)
    assert any(
        "community.md" in w and "MOC-only output" in w
        for w in result.warnings
    ), result.warnings
```

**Apply to Phase 34:** change default min-community-size assertions to `6`; add `code` to `_KNOWN_NOTE_TYPES` tests; add tests for `dataview_queries.code`; keep legacy `community` accepted with warning/coercion behavior instead of removing it outright.

---

### `tests/test_naming.py` (test, transform)

**Analog:** `tests/test_naming.py`

**Graph fixture pattern** (lines 21-51):
```python
def _community_graph() -> tuple[nx.Graph, dict[int, list[str]]]:
    G = nx.Graph()
    G.add_node(
        "n_auth_session",
        label="Auth Session",
        file_type="code",
        source_file="auth/session.py",
        source_location="L10",
        community=12,
    )
    ...
    G.add_edges_from([
        ("n_auth_session", "n_refresh_token"),
        ("n_auth_session", "n_login_flow"),
    ])
    return G, {12: ["n_auth_session", "n_refresh_token", "n_login_flow"]}
```

**Repo identity precedence pattern** (lines 175-188):
```python
def test_repo_identity_cli_wins(tmp_path, capsys, monkeypatch):
    _, ResolvedRepoIdentity, _, resolve_repo_identity = _naming_api()
    result = resolve_repo_identity(
        tmp_path,
        cli_identity="cli-repo",
        profile={"repo": {"identity": "profile-repo"}},
    )

    assert result == ResolvedRepoIdentity(
        identity="cli-repo",
        source="cli-flag",
        raw_value="cli-repo",
        warnings=(),
    )
```

**Apply to Phase 34:** if CODE filename logic lands in `naming.py`, add helper tests for repo normalization, base filename construction, no hash for unique stems, hash for every colliding stem member, path-unsafe labels/source files, and reversed input order.

## Shared Patterns

### Classification Context Is The Contract
**Source:** `graphify/mapping.py`, `graphify/templates.py`
**Apply to:** `mapping.py`, `export.py`, `templates.py`, CODE member rendering
```python
per_node[node_id] = ClassificationContext(
    note_type=note_type,
    folder=folder,
    members_by_type={},
    sub_communities=[],
    sibling_labels=[],
)
```

Planner should require new Phase 34 data to flow through `ClassificationContext`, not ad hoc graph reads in templates or a second export manifest.

### Host-First Then Bucket Routing
**Source:** `graphify/mapping.py`
**Apply to:** cluster-quality floor, isolate behavior, routing metadata
```python
for below_cid in below_cids:
    host = _nearest_host(below_cid, above_cids, inter_edges, community_sizes)
    if host is None:
        hostless_below.append(below_cid)
    else:
        below_to_host[below_cid] = host
```

Planner should preserve this order and add explicit metadata such as `routing: standalone|hosted|bucketed`, `host_community_id`, or equivalent deterministic fields.

### MOC-Only Community Output
**Source:** `graphify/export.py`, `graphify/templates.py`, `graphify/profile.py`
**Apply to:** `community` note-type coercion, default export, profile warnings
```python
render_fn = render_moc if note_type == "moc" else None
if render_fn is None:
    # community-overview shape: Phase 2's render_community_overview
    from graphify.templates import render_community_overview
    render_fn = render_community_overview
```

Planner should replace this normal-output fallback with MOC coercion for Phase 34 while preserving legacy renderer support only as an explicit migration/diagnostic path.

### Frontmatter And Wikilink Sinks
**Source:** `graphify/templates.py`, `graphify/profile.py`
**Apply to:** CODE notes, concept MOC CODE links, collision metadata
```python
frontmatter_fields = _build_frontmatter_fields(
    up=up_list,
    related=related_list,
    collections=[],
    tags=tag_list,
    note_type=note_type,
    file_type=file_type,
    source_file=source_file,
    source_location=source_location,
    community=community_name,
    created=created if created is not None else datetime.date.today(),
)
```

Planner should avoid hand-written YAML and raw wikilinks; any CODE-related `up`, `related`, or metadata field should pass through existing helpers.

### Deterministic Hashing
**Source:** `graphify/naming.py`, `graphify/profile.py`
**Apply to:** CODE collision suffixes
```python
encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
return hashlib.sha256(encoded).hexdigest()
```

Planner should require grouping CODE candidates by base stem and suffixing every member of a colliding group, not only the second item seen.

### Test Fixtures Stay Small And In-Memory
**Source:** `tests/test_mapping.py`, `tests/test_export.py`, `tests/test_templates.py`
**Apply to:** all Phase 34 tests
```python
G = nx.Graph()
G.add_node(
    "transformer",
    label="Transformer",
    file_type="code",
    source_file="model.py",
    source_location="L1",
    community=0,
)
G.add_edge("transformer", "softmax", relation="calls", confidence="EXTRACTED")
```

Planner should use pure NetworkX fixtures and `tmp_path` dry-run/output assertions; no network calls or repo-wide filesystem effects.

## No Analog Found

All planned Phase 34 files have close analogs in the current codebase. The only new file, `graphify/builtin_templates/code.md`, should copy the existing non-MOC built-in template pattern from `thing.md` / `source.md`.

## Metadata

**Analog search scope:** `graphify/mapping.py`, `graphify/export.py`, `graphify/templates.py`, `graphify/profile.py`, `graphify/naming.py`, `graphify/builtin_templates/*.md`, `tests/test_mapping.py`, `tests/test_export.py`, `tests/test_templates.py`, `tests/test_profile.py`, `tests/test_naming.py`
**Files scanned:** 13
**Pattern extraction date:** 2026-04-28
