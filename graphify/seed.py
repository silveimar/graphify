"""Diagram seed engine: ego-graph extraction, layout heuristic, atomic seed file output.

Consumes Plan 20-01 detection primitives (god_nodes, detect_user_seeds) from
graphify.analyze — never reimplements either (D-18 invariant).

Writes per-seed JSON files + `seeds-manifest.json` under `graphify-out/seeds/`
using the atomic-write + manifest-last pattern lifted from Phase 19's
`vault_promote.py`.

Tag write-back for `gen-diagram-seed` is opt-in via the --vault flag in the
CLI wrapper (__main__.py); when invoked, it routes exclusively through
graphify.merge.compute_merge_plan with tags: 'union' policy (SEED-03, D-08).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

import networkx as nx

from graphify.analyze import god_nodes, detect_user_seeds


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_AUTO_SEEDS = 20
_OVERLAP_THRESHOLD = 0.60

_VALID_LAYOUT_TYPES = {
    "cuadro-sinoptico",
    "workflow",
    "architecture",
    "mind-map",
    "repository-components",
    "glossary-graph",
}

_TEMPLATE_MAP = {k: f"{k}.excalidraw.md" for k in _VALID_LAYOUT_TYPES}

_CONCEPT_FILE_TYPES = {"document", "concept", "paper"}


# ---------------------------------------------------------------------------
# Hashing helpers (SEED-08)
# ---------------------------------------------------------------------------


def _element_id(node_id: str) -> str:
    """Deterministic 16-char element ID: `sha256(node_id)[:16]`.

    SEED-08 invariant: label is NEVER an input.
    """
    return hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:16]


def _version_nonce(node_id: str, x: float, y: float) -> int:
    """Deterministic versionNonce int derived from node_id + position."""
    h = hashlib.sha256(f"{node_id}{x}{y}".encode("utf-8")).hexdigest()[:8]
    return int(h, 16)


# ---------------------------------------------------------------------------
# Atomic write + manifest helpers (lifted from graphify.vault_promote)
# ---------------------------------------------------------------------------


def _write_atomic(target: Path, content: str) -> None:
    """Write *content* to *target* atomically via .tmp + os.replace (with fsync).

    Lifted verbatim from vault_promote._write_atomic. Raises OSError on failure;
    best-effort unlinks the .tmp file if the sequence aborts mid-flight.
    """
    tmp = target.with_suffix(target.suffix + ".tmp")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


def _load_seeds_manifest(graphify_out: Path) -> list[dict]:
    """Load seeds-manifest.json from graphify_out/seeds/, returning [] if missing or corrupt."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    if not manifest_path.exists():
        return []
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("manifest is not a list")
        return data
    except (json.JSONDecodeError, OSError, ValueError):
        print(
            "[graphify] seeds-manifest.json corrupted or unreadable — treating all seeds as new",
            file=sys.stderr,
        )
        return []


def _save_seeds_manifest(entries: list[dict], graphify_out: Path) -> None:
    """Write seeds-manifest.json atomically as the FINAL step of build_all_seeds."""
    manifest_path = graphify_out / "seeds" / "seeds-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(entries, indent=2, ensure_ascii=False))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, manifest_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise


# ---------------------------------------------------------------------------
# Layout heuristic (D-05 priority order, SEED-07)
# ---------------------------------------------------------------------------


def _select_layout_type(
    subG: nx.Graph,
    main_nodes: list[dict],
    layout_hint: str | None,
) -> str:
    """D-05 precedence. Returns one of _VALID_LAYOUT_TYPES.

    User slash-type-hint (when in the allowlist) bypasses all predicates.
    Unknown hint → fall through to heuristic (T-20-01-02 defense).
    """
    if layout_hint is not None and layout_hint in _VALID_LAYOUT_TYPES:
        return layout_hint

    n_nodes = subG.number_of_nodes()
    if n_nodes == 0:
        return "mind-map"

    # Coerce to undirected view for is_tree (networkx requires undirected).
    try:
        undirected = subG.to_undirected() if subG.is_directed() else subG
    except AttributeError:
        undirected = subG

    # Predicate 1: is_tree → cuadro-sinoptico
    try:
        if n_nodes >= 2 and nx.is_tree(undirected):
            return "cuadro-sinoptico"
    except Exception:
        pass

    # Predicate 2: DAG with ≥3 topological generations → workflow
    try:
        if subG.is_directed() and nx.is_directed_acyclic_graph(subG):
            gens = list(nx.topological_generations(subG))
            if len(gens) >= 3:
                return "workflow"
    except (AttributeError, Exception):
        pass

    # Predicate 3: ≥4 distinct communities (from 'community' node attr) → architecture
    communities = set()
    for n in subG.nodes():
        cid = subG.nodes[n].get("community")
        if cid is not None:
            communities.add(cid)
    if len(communities) >= 4:
        return "architecture"

    # Predicate 4: single community + degree-concentrated hub → mind-map
    # Metric: max-degree / sum-of-degrees ≥ 0.5.
    degrees = dict(undirected.degree()) if hasattr(undirected, "degree") else {}
    if degrees:
        total = sum(degrees.values())
        max_deg = max(degrees.values())
        if total > 0 and (max_deg / total) >= 0.5:
            return "mind-map"

    # Predicates 5/6: file_type dominance across main_nodes
    if main_nodes:
        code_count = sum(1 for m in main_nodes if m.get("file_type") == "code")
        concept_count = sum(
            1 for m in main_nodes if m.get("file_type") in _CONCEPT_FILE_TYPES
        )
        total = len(main_nodes)
        if code_count / total > 0.5:
            return "repository-components"
        if concept_count / total > 0.5:
            return "glossary-graph"

    # Default: single-hub assumption
    return "mind-map"


# ---------------------------------------------------------------------------
# build_seed (SEED-04)
# ---------------------------------------------------------------------------


def build_seed(
    G: nx.Graph,
    node_id: str,
    trigger: str,
    layout_hint: str | None = None,
) -> dict:
    """Produce a SeedDict for *node_id* from its radius-1/radius-2 ego graph.

    *trigger* must be "auto" or "user". *layout_hint* (if valid) bypasses
    the heuristic; invalid hints are silently ignored (T-20-02-01).
    """
    assert trigger in ("auto", "user"), f"invalid trigger: {trigger!r}"

    r1 = nx.ego_graph(G, node_id, radius=1)
    r2 = nx.ego_graph(G, node_id, radius=2)

    main_node_ids = set(r1.nodes())
    supporting_node_ids = set(r2.nodes()) - main_node_ids

    def _pack(nid: str) -> dict:
        data = G.nodes[nid]
        return {
            "id": nid,
            "label": data.get("label", nid),
            "file_type": data.get("file_type", ""),
            "element_id": _element_id(nid),
        }

    main_nodes = [_pack(n) for n in sorted(main_node_ids)]
    supporting_nodes = [_pack(n) for n in sorted(supporting_node_ids)]

    subG = r2
    relations = [
        {
            "source": u,
            "target": v,
            "relation": d.get("relation", ""),
            "confidence": d.get("confidence", ""),
        }
        for u, v, d in subG.edges(data=True)
    ]

    layout_type = _select_layout_type(subG, main_nodes, layout_hint)

    # Phase 21 PROF-04 + D-06/D-07: profile.diagram_types recommender
    # D-06: match iff (trigger_tags ∩ node_tags OR node_type ∈ trigger_node_types)
    #       AND len(main_nodes) >= min_main_nodes
    # D-07: tiebreak = highest min_main_nodes wins; ties fall back to
    #       declaration order (stable max).
    suggested_template = _TEMPLATE_MAP[layout_type]
    try:
        from graphify.profile import load_profile
        _profile = load_profile(vault_dir=None)
        _node_data = G.nodes[node_id]
        node_tags = set(_node_data.get("tags", []) or [])
        node_type = _node_data.get("file_type") or _node_data.get("node_type")
        candidates = [
            dt for dt in (_profile.get("diagram_types") or [])
            if (
                (set(dt.get("trigger_tags") or []) & node_tags)
                or (node_type is not None and node_type in set(dt.get("trigger_node_types") or []))
            )
            and len(main_nodes) >= int(dt.get("min_main_nodes", 2))
        ]
        if candidates:
            # max() is stable — ties fall back to declaration order (D-07)
            chosen = max(candidates, key=lambda dt: int(dt.get("min_main_nodes", 2)))
            if chosen.get("template_path"):
                suggested_template = chosen["template_path"]
    except Exception:
        pass  # Never break seed build on profile errors

    return {
        "seed_id": node_id,
        "trigger": trigger,
        "main_node_id": node_id,
        "main_node_label": G.nodes[node_id].get("label", node_id),
        "main_nodes": main_nodes,
        "supporting_nodes": supporting_nodes,
        "relations": relations,
        "suggested_layout_type": layout_type,
        "suggested_template": suggested_template,
        "version_nonce_seed": _version_nonce(node_id, 0.0, 0.0),
    }


# ---------------------------------------------------------------------------
# Dedup (SEED-05) — single-pass, degree-sorted, no recursive re-merge
# ---------------------------------------------------------------------------


def _seed_node_ids(seed: dict) -> set[str]:
    """Union of main + supporting node ids."""
    ids = {m["id"] for m in seed.get("main_nodes", [])}
    ids |= {m["id"] for m in seed.get("supporting_nodes", [])}
    return ids


def _seed_size(seed: dict) -> int:
    """Used as a degree-proxy for sort ordering: total node count in the seed."""
    # Prefer an injected _degree hint (test seeds carry it); else use node count.
    if "_degree" in seed:
        return int(seed["_degree"])
    return len(_seed_node_ids(seed))


def _dedup_overlapping_seeds(seeds: list[dict]) -> list[dict]:
    """Merge seeds whose Jaccard overlap > _OVERLAP_THRESHOLD.

    Single-pass algorithm:
      1. Sort by size (degree proxy) DESC — larger seeds win as merge anchors.
      2. For each unmerged seed *i*, scan later seeds *j*; if Jaccard(A,B) > 0.60,
         merge j into i and mark j as consumed.
      3. No recursive re-merge — merged output is not reconsidered.

    When merging, the user trigger wins over auto; user layout_hint wins over
    auto heuristic (D-04). `seed_id` becomes `merged-<sha12>`. Source node_ids
    are recorded in `dedup_merged_from`.
    """
    ordered = sorted(enumerate(seeds), key=lambda t: _seed_size(t[1]), reverse=True)
    consumed: set[int] = set()
    result: list[tuple[int, dict]] = []

    for pos_i, (idx_i, seed_i) in enumerate(ordered):
        if idx_i in consumed:
            continue
        a_ids = _seed_node_ids(seed_i)
        merged_from: list[str] = []
        # Tracking for merged output
        current = dict(seed_i)

        for pos_j in range(pos_i + 1, len(ordered)):
            idx_j, seed_j = ordered[pos_j]
            if idx_j in consumed:
                continue
            b_ids = _seed_node_ids(seed_j)
            union = a_ids | b_ids
            intersection = a_ids & b_ids
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard > _OVERLAP_THRESHOLD:
                # Merge j into i
                # Extend main_nodes with any nodes from j not already in i
                existing_main_ids = {m["id"] for m in current["main_nodes"]}
                existing_supp_ids = {m["id"] for m in current["supporting_nodes"]}
                for m in seed_j.get("main_nodes", []):
                    if m["id"] not in existing_main_ids and m["id"] not in existing_supp_ids:
                        current["main_nodes"].append(m)
                        existing_main_ids.add(m["id"])
                for m in seed_j.get("supporting_nodes", []):
                    if m["id"] not in existing_main_ids and m["id"] not in existing_supp_ids:
                        current["supporting_nodes"].append(m)
                        existing_supp_ids.add(m["id"])

                # Record merged source seed_ids
                if not merged_from:
                    merged_from.append(current.get("seed_id", seed_i.get("seed_id")))
                merged_from.append(seed_j.get("seed_id"))

                # D-04: user trigger wins; user layout_hint wins
                if seed_j.get("trigger") == "user":
                    current["trigger"] = "user"
                    hint_j = seed_j.get("_layout_hint") or (
                        seed_j.get("suggested_layout_type")
                        if seed_j.get("suggested_layout_type") in _VALID_LAYOUT_TYPES
                        else None
                    )
                    if hint_j:
                        current["suggested_layout_type"] = seed_j["suggested_layout_type"]
                        current["suggested_template"] = _TEMPLATE_MAP.get(
                            current["suggested_layout_type"], current["suggested_template"]
                        )

                consumed.add(idx_j)
                # Update union set for next iteration
                a_ids = a_ids | b_ids

        if merged_from:
            # Produce deterministic merged seed_id
            all_ids = sorted(a_ids)
            h12 = hashlib.sha256("|".join(all_ids).encode("utf-8")).hexdigest()[:12]
            current["seed_id"] = f"merged-{h12}"
            current["dedup_merged_from"] = merged_from

        result.append((idx_i, current))

    # Return in original positional order
    result.sort(key=lambda t: t[0])
    return [s for _, s in result]


# ---------------------------------------------------------------------------
# Orchestrator: build_all_seeds
# ---------------------------------------------------------------------------


def _iso_utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename_stem(seed_id: str) -> str:
    """Sanitize seed_id for use as a filename stem.

    Node IDs flowing from `_make_id` are lowercase alphanumeric + underscores,
    but as a defense-in-depth step we replace any path-separator or suspicious
    characters. Merged-seed IDs already use `merged-<sha12>` and are safe.
    """
    safe = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in seed_id)
    return safe or "seed"


def build_all_seeds(
    G: nx.Graph,
    graphify_out: Path,
    vault: Path | None = None,
    profile: dict | None = None,
) -> dict:
    """Produce all seeds under *graphify_out/seeds/*.

    Steps (mirrors graphify.vault_promote.promote):
      1. Ensure auto-tags are set by calling god_nodes(G, top_n=30).
      2. Read auto+user seeds via detect_user_seeds(G).
      3. D-04 overlap: if a node is both auto + user, drop from auto (user wins).
      4. Rank auto candidates by degree DESC; apply max_seeds=20 cap BEFORE I/O.
      5. Build seed dicts (build_seed) for all non-dropped candidates.
      6. Apply _dedup_overlapping_seeds across full list.
      7. Load prior manifest → delete any *-seed.json listed there but not in
         the new decision table.
      8. Atomically write each retained seed file.
      9. Atomically write seeds-manifest.json as the FINAL step.
     10. If vault is not None, route tag write-back through
         graphify.merge.compute_merge_plan (tags: 'union' policy).

    Returns a summary dict.
    """
    graphify_out = Path(graphify_out)
    seeds_dir = graphify_out / "seeds"
    seeds_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: clear stale tags from prior runs, then re-run god_nodes to
    # produce a fresh `possible_diagram_seed` set for this snapshot of G.
    for _n, _data in G.nodes(data=True):
        if "possible_diagram_seed" in _data:
            _data.pop("possible_diagram_seed", None)
    god_nodes(G, top_n=30)

    # Step 2: read candidates. Filter zero-degree nodes — they have no ego
    # graph worth visualizing and should never be emitted as seeds.
    raw = detect_user_seeds(G)
    auto_candidates = [
        a for a in raw.get("auto_seeds", []) if G.degree(a["id"]) > 0
    ]
    user_candidates = [
        u for u in raw.get("user_seeds", []) if G.degree(u["id"]) > 0
    ]

    # Step 3: D-04 — if a node is both auto + user, drop from auto.
    user_ids = {u["id"] for u in user_candidates}
    auto_candidates = [a for a in auto_candidates if a["id"] not in user_ids]

    # Step 4: rank auto by degree DESC.
    def _deg(nid: str) -> int:
        try:
            return G.degree(nid)
        except Exception:
            return 0

    auto_candidates.sort(key=lambda a: _deg(a["id"]), reverse=True)

    # Apply cap: first 20 kept; remainder marked as dropped.
    auto_kept = auto_candidates[:_MAX_AUTO_SEEDS]
    auto_dropped = auto_candidates[_MAX_AUTO_SEEDS:]
    if auto_dropped:
        print(
            f"[graphify] Capped at {_MAX_AUTO_SEEDS} auto seeds; {len(auto_dropped)} dropped (see seeds-manifest.json)",
            file=sys.stderr,
        )

    if not auto_kept and not user_candidates and not auto_dropped:
        # Empty-state: still produce empty manifest + info line
        print("[graphify] diagram-seeds: no auto or user candidates found", file=sys.stderr)
        _save_seeds_manifest([], graphify_out)
        return {
            "seeds_written": 0,
            "auto": 0,
            "user": 0,
            "dropped_by_cap": 0,
            "merged": 0,
            "manifest_path": str(seeds_dir / "seeds-manifest.json"),
        }

    # Step 5: build seed dicts.
    built: list[dict] = []
    for cand in auto_kept:
        if cand["id"] not in G.nodes:
            continue
        seed = build_seed(G, cand["id"], "auto")
        built.append(seed)
    for cand in user_candidates:
        if cand["id"] not in G.nodes:
            continue
        hint = cand.get("layout_hint")
        seed = build_seed(G, cand["id"], "user", layout_hint=hint)
        # Preserve layout_hint for dedup's D-04 handling
        if hint and hint in _VALID_LAYOUT_TYPES:
            seed["_layout_hint"] = hint
        built.append(seed)

    # Step 6: dedup across full list.
    deduped = _dedup_overlapping_seeds(built)

    # Compute new decision-table node ids (retained seeds only).
    retained_node_ids = {s["main_node_id"] for s in deduped}

    # Step 7: load prior manifest, delete orphaned files.
    prior_manifest = _load_seeds_manifest(graphify_out)
    prior_files: dict[str, str] = {e["node_id"]: e["seed_file"] for e in prior_manifest if e.get("seed_file")}

    new_files_set = {f"{_safe_filename_stem(s['seed_id'])}-seed.json" for s in deduped}
    for prior_nid, prior_file in prior_files.items():
        if prior_nid not in retained_node_ids and prior_file not in new_files_set:
            orphan = seeds_dir / prior_file
            try:
                if orphan.exists():
                    orphan.unlink()
            except OSError:
                pass

    # Step 8: atomically write each seed.
    now = _iso_utc_now()
    entries: list[dict] = []
    for seed in deduped:
        # Strip internal-only keys
        seed_out = {k: v for k, v in seed.items() if not k.startswith("_")}
        filename = f"{_safe_filename_stem(seed['seed_id'])}-seed.json"
        seed_path = seeds_dir / filename
        content = json.dumps(seed_out, indent=2, ensure_ascii=False)
        _write_atomic(seed_path, content)

        entries.append({
            "node_id": seed["main_node_id"],
            "seed_file": filename,
            "trigger": seed["trigger"],
            "layout_type": seed["suggested_layout_type"],
            "dedup_merged_from": list(seed.get("dedup_merged_from", [])),
            "dropped_due_to_cap": False,
            "rank_at_drop": None,
            "written_at": now,
        })

    # Step 8b: append dropped-by-cap audit entries (no files written).
    for rank_offset, cand in enumerate(auto_dropped, start=_MAX_AUTO_SEEDS + 1):
        entries.append({
            "node_id": cand["id"],
            "seed_file": None,
            "trigger": "auto",
            "layout_type": None,
            "dedup_merged_from": [],
            "dropped_due_to_cap": True,
            "rank_at_drop": rank_offset,
            "written_at": now,
        })

    # Step 9: manifest as the FINAL atomic step.
    _save_seeds_manifest(entries, graphify_out)

    # Step 10: optional --vault tag write-back via compute_merge_plan (D-08).
    if vault is not None:
        from graphify.merge import compute_merge_plan  # noqa: F401

        auto_node_ids = [s["main_node_id"] for s in deduped if s["trigger"] == "auto"]
        rendered_notes = {}
        for nid in auto_node_ids:
            label = G.nodes[nid].get("label", nid)
            rendered_notes[nid] = {
                "node_id": nid,
                "target_path": Path(vault) / f"{label}.md",
                "frontmatter_fields": {"tags": ["gen-diagram-seed"]},
                "body": "",
            }
        if rendered_notes:
            compute_merge_plan(Path(vault), rendered_notes, profile or {})

    auto_written = sum(1 for e in entries if e["trigger"] == "auto" and not e["dropped_due_to_cap"])
    user_written = sum(1 for e in entries if e["trigger"] == "user" and not e["dropped_due_to_cap"])
    merged_count = sum(1 for s in deduped if s.get("dedup_merged_from"))
    return {
        "seeds_written": auto_written + user_written,
        "auto": auto_written,
        "user": user_written,
        "dropped_by_cap": len(auto_dropped),
        "merged": merged_count,
        "manifest_path": str(seeds_dir / "seeds-manifest.json"),
    }
