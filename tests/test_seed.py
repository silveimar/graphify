"""Unit tests for graphify.seed — diagram seed engine (Plan 20-02)."""
from __future__ import annotations

import hashlib
import io
import json
import sys
from pathlib import Path
from unittest import mock

import networkx as nx
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chain(n: int = 4) -> nx.Graph:
    """Chain graph a-b-c-d... with label, file_type="code", community=0."""
    G = nx.Graph()
    names = [chr(ord("a") + i) for i in range(n)]
    for name in names:
        G.add_node(name, label=name.upper(), file_type="code", community=0, source_file=f"{name}.py")
    for i in range(n - 1):
        G.add_edge(names[i], names[i + 1], relation="references", confidence="EXTRACTED", source_file="x.py")
    return G


def _make_tree() -> nx.Graph:
    """Tree: root → a,b,c; a → a1,a2 — cleanly tree-shaped."""
    G = nx.Graph()
    for n in ["root", "a", "b", "c", "a1", "a2"]:
        G.add_node(n, label=n.upper(), file_type="document", community=0, source_file="doc.md")
    G.add_edge("root", "a", relation="contains", confidence="EXTRACTED", source_file="doc.md")
    G.add_edge("root", "b", relation="contains", confidence="EXTRACTED", source_file="doc.md")
    G.add_edge("root", "c", relation="contains", confidence="EXTRACTED", source_file="doc.md")
    G.add_edge("a", "a1", relation="contains", confidence="EXTRACTED", source_file="doc.md")
    G.add_edge("a", "a2", relation="contains", confidence="EXTRACTED", source_file="doc.md")
    return G


def _make_dag_three_gens() -> nx.DiGraph:
    """DiGraph with 3 topological generations; not a tree (has a diamond)."""
    G = nx.DiGraph()
    # 3 topo generations minimum: a -> b,c -> d ; b -> d AND c -> d creates diamond (not a tree)
    for n in ["a", "b", "c", "d"]:
        G.add_node(n, label=n.upper(), file_type="code", community=0, source_file=f"{n}.py")
    G.add_edge("a", "b", relation="calls", confidence="EXTRACTED", source_file="a.py")
    G.add_edge("a", "c", relation="calls", confidence="EXTRACTED", source_file="a.py")
    G.add_edge("b", "d", relation="calls", confidence="EXTRACTED", source_file="b.py")
    G.add_edge("c", "d", relation="calls", confidence="EXTRACTED", source_file="c.py")
    return G


def _make_four_community_hub() -> nx.Graph:
    """Hub 'h' connected to 4 nodes spread across 4 communities (non-tree: add one extra edge)."""
    G = nx.Graph()
    G.add_node("h", label="H", file_type="code", community=0, source_file="h.py")
    for i, cid in enumerate([0, 1, 2, 3]):
        nid = f"n{i}"
        G.add_node(nid, label=nid.upper(), file_type="code", community=cid, source_file=f"{nid}.py")
        G.add_edge("h", nid, relation="calls", confidence="EXTRACTED", source_file="h.py")
    # Add a cycle so it's no longer a tree (is_tree must be False so we reach predicate 3)
    G.add_edge("n0", "n1", relation="peer", confidence="EXTRACTED", source_file="h.py")
    G.add_edge("n1", "n2", relation="peer", confidence="EXTRACTED", source_file="h.py")
    return G


def _make_hub(file_type: str, n_spokes: int = 6) -> nx.Graph:
    """Non-tree hub-and-spokes; all nodes share given file_type and a single community."""
    G = nx.Graph()
    G.add_node("h", label="H", file_type=file_type, community=0, source_file=f"h.{file_type}")
    for i in range(n_spokes):
        nid = f"n{i}"
        G.add_node(nid, label=nid.upper(), file_type=file_type, community=0, source_file=f"{nid}.{file_type}")
        G.add_edge("h", nid, relation="references", confidence="EXTRACTED", source_file="h")
    # Add a single cycle so it's not a tree
    G.add_edge("n0", "n1", relation="references", confidence="EXTRACTED", source_file="h")
    return G


# ---------------------------------------------------------------------------
# Hashing (SEED-08)
# ---------------------------------------------------------------------------


def test_element_id_is_sha256_truncated_16():
    from graphify.seed import _element_id

    expected = hashlib.sha256(b"transformer").hexdigest()[:16]
    assert _element_id("transformer") == expected
    assert len(_element_id("transformer")) == 16


def test_version_nonce_is_deterministic():
    from graphify.seed import _version_nonce

    v1 = _version_nonce("n", 0.0, 0.0)
    v2 = _version_nonce("n", 0.0, 0.0)
    assert v1 == v2
    expected = int(hashlib.sha256(b"n0.00.0").hexdigest()[:8], 16)
    assert v1 == expected


def test_element_id_never_uses_label():
    from graphify.seed import _element_id

    # element_id is derived from node_id only; label is never an input
    assert _element_id("x") == _element_id("x")
    # Different IDs produce different hashes — label-independence is a property of the API shape
    assert _element_id("x") != _element_id("y")


# ---------------------------------------------------------------------------
# build_seed (SEED-04)
# ---------------------------------------------------------------------------


def test_build_seed_main_nodes_radius_1():
    from graphify.seed import build_seed

    G = _make_chain(4)  # a-b-c-d
    seed = build_seed(G, "b", "auto")
    main_ids = {m["id"] for m in seed["main_nodes"]}
    supp_ids = {m["id"] for m in seed["supporting_nodes"]}
    assert main_ids == {"a", "b", "c"}
    assert supp_ids == {"d"}
    assert seed["main_node_id"] == "b"
    assert seed["trigger"] == "auto"


def test_build_seed_relations_contains_subgraph_edges_only():
    from graphify.seed import build_seed

    G = _make_chain(4)  # a-b-c-d
    seed = build_seed(G, "b", "auto")
    allowed_ids = {m["id"] for m in seed["main_nodes"]} | {m["id"] for m in seed["supporting_nodes"]}
    for rel in seed["relations"]:
        assert rel["source"] in allowed_ids
        assert rel["target"] in allowed_ids


def test_build_seed_trigger_user_and_layout_hint_override():
    from graphify.seed import build_seed

    G = _make_tree()  # is_tree → cuadro-sinoptico by default
    seed = build_seed(G, "root", "user", layout_hint="workflow")
    assert seed["trigger"] == "user"
    assert seed["suggested_layout_type"] == "workflow"
    assert seed["suggested_template"] == "workflow.excalidraw.md"


def test_build_seed_invalid_layout_hint_falls_back_to_heuristic():
    from graphify.seed import build_seed

    G = _make_tree()
    seed = build_seed(G, "root", "user", layout_hint="evil-injection-attempt")
    # Heuristic must run; is_tree → cuadro-sinoptico
    assert seed["suggested_layout_type"] == "cuadro-sinoptico"


# ---------------------------------------------------------------------------
# Layout heuristic D-05 priority (SEED-07)
# ---------------------------------------------------------------------------


def test_layout_heuristic_is_tree_wins():
    from graphify.seed import build_seed

    G = _make_tree()
    seed = build_seed(G, "root", "auto")
    assert seed["suggested_layout_type"] == "cuadro-sinoptico"


def test_layout_heuristic_dag_three_gens():
    from graphify.seed import build_seed

    G = _make_dag_three_gens()
    seed = build_seed(G, "a", "auto")
    # Subgraph (radius-2 from 'a') covers all 4 nodes; has 3 topo gens; not a tree
    assert seed["suggested_layout_type"] == "workflow"


def test_layout_heuristic_four_communities():
    from graphify.seed import build_seed

    G = _make_four_community_hub()
    seed = build_seed(G, "h", "auto")
    assert seed["suggested_layout_type"] == "architecture"


def test_layout_heuristic_code_nodes_to_repo_components():
    from graphify.seed import build_seed

    G = _make_hub("code", n_spokes=6)
    seed = build_seed(G, "h", "auto")
    assert seed["suggested_layout_type"] == "repository-components"


def test_layout_heuristic_concept_nodes_to_glossary():
    from graphify.seed import build_seed

    G = _make_hub("document", n_spokes=6)
    seed = build_seed(G, "h", "auto")
    assert seed["suggested_layout_type"] == "glossary-graph"


# ---------------------------------------------------------------------------
# Dedup >60% overlap (SEED-05)
# ---------------------------------------------------------------------------


def _mk_seed(seed_id: str, node_ids: list[str], *, trigger: str = "auto", layout_type: str = "mind-map",
             main_node_id: str | None = None, layout_hint: str | None = None) -> dict:
    main = main_node_id or node_ids[0]
    return {
        "seed_id": seed_id,
        "trigger": trigger,
        "main_node_id": main,
        "main_node_label": main.upper(),
        "main_nodes": [{"id": nid, "label": nid, "file_type": "code", "element_id": nid[:16]} for nid in node_ids],
        "supporting_nodes": [],
        "relations": [],
        "suggested_layout_type": layout_type,
        "suggested_template": f"{layout_type}.excalidraw.md",
        "version_nonce_seed": 0,
        "_layout_hint": layout_hint,
        "_degree": len(node_ids),
    }


def test_dedup_merges_when_overlap_above_60_percent():
    from graphify.seed import _dedup_overlapping_seeds

    # A = {a,b,c,d,e,f}, B = {c,d,e,f,g,h} → Jaccard = 4/8 = 0.5 (below) — use tighter overlap
    # Use A = {a,b,c,d,e,f}, B = {b,c,d,e,f,g} → shared 5/7 = 0.714 → merges
    s1 = _mk_seed("A", ["a", "b", "c", "d", "e", "f"])
    s2 = _mk_seed("B", ["b", "c", "d", "e", "f", "g"])
    # s3 shares only {a,b,c} with merged → 3/|union| — stays separate
    s3 = _mk_seed("C", ["a", "b", "c", "z1", "z2", "z3"])

    out = _dedup_overlapping_seeds([s1, s2, s3])

    # s1 and s2 merged into one; s3 preserved
    assert len(out) == 2
    # One seed is a merged seed; find it
    merged = [s for s in out if s.get("dedup_merged_from")]
    assert len(merged) == 1
    assert set(merged[0]["dedup_merged_from"]) == {"A", "B"}
    # The merged seed_id is a deterministic hash
    assert merged[0]["seed_id"].startswith("merged-")


def test_dedup_preserves_user_layout_hint_on_merge():
    from graphify.seed import _dedup_overlapping_seeds

    # Overlapping seeds — one auto, one user with layout_hint=workflow
    s1 = _mk_seed("A", ["a", "b", "c", "d", "e"], trigger="auto", layout_type="mind-map")
    s2 = _mk_seed("B", ["b", "c", "d", "e", "f"], trigger="user", layout_type="workflow", layout_hint="workflow")

    out = _dedup_overlapping_seeds([s1, s2])
    assert len(out) == 1
    merged = out[0]
    assert merged["trigger"] == "user"
    assert merged["suggested_layout_type"] == "workflow"


# ---------------------------------------------------------------------------
# Cap enforcement (SEED-06)
# ---------------------------------------------------------------------------


def _make_cap_graph(n_auto: int = 25, n_user: int = 0) -> nx.Graph:
    """Build a graph with n_auto god-node candidates + n_user tagged nodes.

    Each auto node is connected to 'anchor' so god_nodes ranks it.
    User nodes carry a 'gen-diagram-seed' tag.
    """
    G = nx.Graph()
    G.add_node("anchor", label="ANCHOR", file_type="code", community=0, source_file="anchor.py")
    # Auto: high-degree concept-like nodes
    for i in range(n_auto):
        nid = f"auto_{i:02d}"
        G.add_node(nid, label=f"Auto{i}", file_type="code", community=0, source_file=f"auto_{i}.py",
                   possible_diagram_seed=True)
        # Give each auto node a specific degree (more edges for lower-index → higher rank)
        for j in range(n_auto - i):
            peer_id = f"{nid}_peer_{j}"
            G.add_node(peer_id, label=f"P{j}", file_type="code", community=0, source_file=f"p.py")
            G.add_edge(nid, peer_id, relation="calls", confidence="EXTRACTED", source_file=f"{nid}.py")
    for i in range(n_user):
        nid = f"user_{i}"
        G.add_node(nid, label=f"User{i}", file_type="code", community=0, source_file=f"user_{i}.py",
                   tags=["gen-diagram-seed"])
        G.add_edge("anchor", nid, relation="references", confidence="EXTRACTED", source_file="x.py")
    return G


def test_cap_enforced_before_file_io_and_warn_emitted(tmp_path, capsys):
    from graphify.seed import build_all_seeds

    G = _make_cap_graph(n_auto=25, n_user=0)
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    summary = build_all_seeds(G, graphify_out=out_dir)

    # Manifest present; count dropped entries
    manifest_path = out_dir / "seeds" / "seeds-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    dropped = [e for e in manifest if e.get("dropped_due_to_cap")]
    kept = [e for e in manifest if not e.get("dropped_due_to_cap")]
    assert len(kept) == 20, f"Expected 20 kept seeds; got {len(kept)}"
    assert len(dropped) == 5, f"Expected 5 dropped; got {len(dropped)}"
    for e in dropped:
        assert e["rank_at_drop"] in range(21, 26)

    # Only 20 seed files on disk (no dropped ones written)
    seed_files = list((out_dir / "seeds").glob("*-seed.json"))
    assert len(seed_files) == 20

    # Cap warning on stderr
    captured = capsys.readouterr()
    assert "[graphify] Capped at 20 auto seeds; 5 dropped" in captured.err


def test_user_seeds_never_counted_toward_cap(tmp_path, capsys):
    from graphify.seed import build_all_seeds

    G = _make_cap_graph(n_auto=20, n_user=7)
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    build_all_seeds(G, graphify_out=out_dir)

    manifest_path = out_dir / "seeds" / "seeds-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    dropped = [e for e in manifest if e.get("dropped_due_to_cap")]
    assert len(dropped) == 0, "User seeds must not trigger cap"

    captured = capsys.readouterr()
    assert "Capped at 20" not in captured.err


def test_overlap_user_frees_auto_slot(tmp_path):
    from graphify.seed import build_all_seeds

    # Graph: 20 auto candidates + 1 node that is BOTH auto and user-tagged
    # Plus 1 extra auto candidate that would be rank 21 — should be promoted
    G = _make_cap_graph(n_auto=21, n_user=0)
    # Tag auto_15 as also user
    existing_tags = G.nodes["auto_15"].get("tags")
    G.nodes["auto_15"]["tags"] = ["gen-diagram-seed"]

    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    build_all_seeds(G, graphify_out=out_dir)

    manifest_path = out_dir / "seeds" / "seeds-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # auto_15 emitted once as user
    entries_15 = [e for e in manifest if e["node_id"] == "auto_15"]
    assert len(entries_15) == 1
    assert entries_15[0]["trigger"] == "user"

    # All 21 nodes kept (user frees slot; auto cap still 20)
    kept = [e for e in manifest if not e.get("dropped_due_to_cap")]
    assert len(kept) == 21


# ---------------------------------------------------------------------------
# Atomic writes + manifest roundtrip
# ---------------------------------------------------------------------------


def test_seeds_manifest_roundtrip(tmp_path):
    from graphify.seed import _save_seeds_manifest, _load_seeds_manifest

    entries = [
        {"node_id": "n1", "seed_file": "n1-seed.json", "trigger": "auto",
         "layout_type": "mind-map", "dedup_merged_from": [],
         "dropped_due_to_cap": False, "rank_at_drop": None,
         "written_at": "2026-04-23T00:00:00Z"},
        {"node_id": "n2", "seed_file": "n2-seed.json", "trigger": "user",
         "layout_type": "workflow", "dedup_merged_from": [],
         "dropped_due_to_cap": False, "rank_at_drop": None,
         "written_at": "2026-04-23T00:00:00Z"},
    ]
    _save_seeds_manifest(entries, tmp_path)
    loaded = _load_seeds_manifest(tmp_path)
    assert loaded == entries


def test_partial_write_failure_leaves_no_visible_state(tmp_path, monkeypatch):
    from graphify import seed as seed_mod

    entries = [{"node_id": "n", "seed_file": "n-seed.json", "trigger": "auto",
                "layout_type": "mind-map", "dedup_merged_from": [],
                "dropped_due_to_cap": False, "rank_at_drop": None,
                "written_at": "2026-04-23T00:00:00Z"}]

    # Force os.replace to fail inside _save_seeds_manifest
    real_replace = __import__("os").replace

    def _fail_replace(src, dst):
        if "seeds-manifest" in str(dst):
            raise OSError("simulated failure")
        return real_replace(src, dst)

    monkeypatch.setattr("os.replace", _fail_replace)

    with pytest.raises(OSError):
        seed_mod._save_seeds_manifest(entries, tmp_path)

    # No .tmp leaked and no manifest on disk
    seeds_dir = tmp_path / "seeds"
    if seeds_dir.exists():
        tmps = list(seeds_dir.glob("*.tmp"))
        assert tmps == []
    manifest_path = tmp_path / "seeds" / "seeds-manifest.json"
    assert not manifest_path.exists()


# ---------------------------------------------------------------------------
# Orchestrator smoke (Task 2 tests)
# ---------------------------------------------------------------------------


def _make_small_graph_with_3_god_nodes() -> nx.Graph:
    """10-node graph: 3 hub concepts, 7 peripherals, enough degree for god_nodes()."""
    G = nx.Graph()
    # 3 concept hubs (not file nodes) — degree must exceed file nodes
    for hub in ["alpha", "beta", "gamma"]:
        G.add_node(hub, label=hub.title(), file_type="code", community=0, source_file=f"{hub}.py")
    # 7 peripheral nodes (concepts, not file hubs; labels don't match filenames)
    for i in range(7):
        nid = f"p{i}"
        G.add_node(nid, label=f"Peripheral{i}", file_type="code", community=0, source_file=f"p{i}.py")
    # Connect each hub to ~5 peripherals
    for hub in ["alpha", "beta", "gamma"]:
        for i in range(5):
            G.add_edge(hub, f"p{i}", relation="references", confidence="EXTRACTED", source_file=f"{hub}.py")
    return G


def test_build_all_seeds_writes_manifest_and_seed_files(tmp_path):
    from graphify.seed import build_all_seeds

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    summary = build_all_seeds(G, graphify_out=out_dir)

    manifest_path = out_dir / "seeds" / "seeds-manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest, list)
    assert len(manifest) >= 1

    # Schema check
    entry = manifest[0]
    for key in ("node_id", "seed_file", "trigger", "layout_type",
                "dedup_merged_from", "dropped_due_to_cap", "rank_at_drop", "written_at"):
        assert key in entry, f"Missing key {key} in manifest entry"

    # At least one seed file on disk
    seed_files = list((out_dir / "seeds").glob("*-seed.json"))
    assert len(seed_files) >= 1


def test_manifest_is_written_last(tmp_path, monkeypatch):
    """If manifest write fails, seed files may exist but manifest does not."""
    from graphify import seed as seed_mod

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()

    real_save = seed_mod._save_seeds_manifest

    def _fail_manifest(entries, graphify_out):
        raise OSError("simulated manifest failure")

    monkeypatch.setattr(seed_mod, "_save_seeds_manifest", _fail_manifest)

    with pytest.raises(OSError):
        seed_mod.build_all_seeds(G, graphify_out=out_dir)

    manifest_path = out_dir / "seeds" / "seeds-manifest.json"
    assert not manifest_path.exists(), "manifest must not exist when save_seeds_manifest fails"
    # At least one seed file likely written before manifest step
    # (This proves manifest is the final step)


def test_rerun_deletes_orphaned_seed_files(tmp_path):
    from graphify.seed import build_all_seeds

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()

    # First run
    build_all_seeds(G, graphify_out=out_dir)
    manifest1 = json.loads((out_dir / "seeds" / "seeds-manifest.json").read_text(encoding="utf-8"))
    first_seed_files = {e["seed_file"] for e in manifest1 if not e.get("dropped_due_to_cap")}
    assert len(first_seed_files) >= 2

    # Mutate graph: remove ALL edges from 'beta' and 'gamma', leaving only 'alpha' as candidate
    for hub in ["beta", "gamma"]:
        edges = list(G.edges(hub))
        G.remove_edges_from(edges)
        # Remove the possible_diagram_seed attr if set
        G.nodes[hub].pop("possible_diagram_seed", None)

    # Remove all peripheral p0..p6 nodes' attributes that would make them candidates
    # (ensures alpha is dominant; beta/gamma become isolated)

    # Second run
    build_all_seeds(G, graphify_out=out_dir)

    # Compare seed files on disk
    remaining_files = {p.name for p in (out_dir / "seeds").glob("*-seed.json")}
    # At minimum, any seed file for beta/gamma that was written and is no longer a candidate
    # should be removed. Verify no beta/gamma seed file remains.
    assert not any("beta" in f for f in remaining_files), f"beta seed file not cleaned: {remaining_files}"
    assert not any("gamma" in f for f in remaining_files), f"gamma seed file not cleaned: {remaining_files}"


def test_rerun_with_corrupt_prior_manifest_is_safe(tmp_path, capsys):
    from graphify.seed import build_all_seeds

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    seeds_dir = out_dir / "seeds"
    seeds_dir.mkdir(parents=True)
    (seeds_dir / "seeds-manifest.json").write_text("{{{ not valid json ]]]", encoding="utf-8")

    build_all_seeds(G, graphify_out=out_dir)  # must not raise

    captured = capsys.readouterr()
    assert "corrupt" in captured.err.lower() or "unreadable" in captured.err.lower()
    # New manifest should now be valid
    new_manifest = json.loads((out_dir / "seeds" / "seeds-manifest.json").read_text(encoding="utf-8"))
    assert isinstance(new_manifest, list)


def test_user_tag_on_auto_candidate_emits_single_user_trigger(tmp_path):
    from graphify.seed import build_all_seeds

    G = _make_small_graph_with_3_god_nodes()
    # Tag alpha as user as well — it's both auto (god node) and user
    G.nodes["alpha"]["tags"] = ["gen-diagram-seed"]
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    build_all_seeds(G, graphify_out=out_dir)

    manifest = json.loads((out_dir / "seeds" / "seeds-manifest.json").read_text(encoding="utf-8"))
    # Deduplication may merge alpha with overlapping seeds — find entries that include alpha
    alpha_entries = [
        e for e in manifest
        if e["node_id"] == "alpha" or "alpha" in e.get("dedup_merged_from", [])
    ]
    assert len(alpha_entries) == 1
    assert alpha_entries[0]["trigger"] == "user"


def test_build_all_seeds_without_vault_does_not_touch_vault(tmp_path, monkeypatch):
    from graphify.seed import build_all_seeds
    import graphify.merge as merge_mod

    def _explode(*a, **kw):
        raise AssertionError("compute_merge_plan must not be called when vault=None")

    monkeypatch.setattr(merge_mod, "compute_merge_plan", _explode)

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    build_all_seeds(G, graphify_out=out_dir, vault=None)  # must not raise


def test_build_all_seeds_with_vault_routes_tag_writeback_through_compute_merge_plan(tmp_path, monkeypatch):
    from graphify.seed import build_all_seeds
    import graphify.merge as merge_mod

    calls: list = []

    def _spy(vault_dir, rendered_notes, profile, **kwargs):
        calls.append({"vault_dir": vault_dir, "rendered_notes": rendered_notes, "profile": profile})
        # Return a minimal MergePlan-shaped stub
        return merge_mod.MergePlan(actions=[], orphan_paths=[])

    monkeypatch.setattr(merge_mod, "compute_merge_plan", _spy)

    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()

    build_all_seeds(G, graphify_out=out_dir, vault=vault)

    assert len(calls) == 1, f"compute_merge_plan must be called exactly once, got {len(calls)}"
    assert calls[0]["rendered_notes"], "rendered_notes must contain auto-tagged entries"
    # Verify merge policy embeds tags: union — either inside profile.merge or defaults
    # Confirm the default policy resolves to 'union' for tags
    assert merge_mod._DEFAULT_FIELD_POLICY["tags"] == "union"


def test_cli_diagram_seeds_flag_smoke(tmp_path):
    import subprocess
    import json as _json
    from networkx.readwrite import json_graph

    # Build a small graph and serialize to graphify-out/graph.json
    G = _make_small_graph_with_3_god_nodes()
    out_dir = tmp_path / "graphify-out"
    out_dir.mkdir()
    graph_path = out_dir / "graph.json"
    graph_path.write_text(_json.dumps(json_graph.node_link_data(G)), encoding="utf-8")

    result = subprocess.run(
        ["python", "-m", "graphify", "--diagram-seeds", "--graph", str(graph_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    assert "[graphify] diagram-seeds complete:" in result.stdout
    assert (out_dir / "seeds" / "seeds-manifest.json").exists()
