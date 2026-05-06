"""RED tests for graphify.federate (Phase 66 CFED Plan 01).

Locks D-66.3 (namespacing), D-66.4 (AND-gate + tiebreaker), D-66.5 (manifest schema),
D-66.7 (canonical lex-min id, determinism) before any pipeline wiring lands.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from graphify.federate import FederationCollisionError, build_manifest, federate


FIXTURES = Path(__file__).parent / "fixtures"
PEER_MATCH = FIXTURES / "peer_match" / "graph.json"
PEER_NOMERGE = FIXTURES / "peer_nomerge" / "graph.json"
PEER_COLLISION_A = FIXTURES / "peer_collision_a" / "repo" / "graph.json"
PEER_COLLISION_B = FIXTURES / "peer_collision_b" / "repo" / "graph.json"


def _local_extraction() -> dict:
    """Local fixture: TokenValidator concept w/ neighbors {AuthService, TokenStore} in auth.py."""
    return {
        "nodes": [
            {"id": "l_token_validator", "label": "TokenValidator", "file_type": "document",
             "source_file": "auth.py", "source_location": "L1"},
            {"id": "l_auth_service", "label": "AuthService", "file_type": "code",
             "source_file": "auth.py", "source_location": "L10"},
            {"id": "l_token_store", "label": "TokenStore", "file_type": "code",
             "source_file": "auth.py", "source_location": "L30"},
        ],
        "edges": [
            {"source": "l_token_validator", "target": "l_auth_service", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.6, "weight": 1.0},
            {"source": "l_token_validator", "target": "l_token_store", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.6, "weight": 1.0},
        ],
    }


def test_namespace():
    """All node ids in result are prefixed with `{repo}::` for both local and peer contributors."""
    merged, _ = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    for n in merged["nodes"]:
        assert "::" in n["id"], f"node id {n['id']!r} not namespaced"
        prefix = n["id"].split("::", 1)[0]
        assert prefix in {"local", "peer_match"}, f"unexpected repo prefix {prefix!r}"
    for e in merged["edges"]:
        assert "::" in e["source"] and "::" in e["target"]


def test_gate_all_pass():
    """peer_match passes all three signals → exactly 1 merge; merged_id = lex-min of contributors."""
    merged, merges = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    assert len(merges) == 1
    entry = merges[0]
    contributing_ids = sorted(c["original_id"] for c in entry["contributing"])
    namespaced = sorted(
        f"{c['repo']}::{c['original_id']}" for c in entry["contributing"]
    )
    assert entry["merged_id"] == min(namespaced)
    # Merged_id should have replaced both contributors in the node list.
    ids = {n["id"] for n in merged["nodes"]}
    assert entry["merged_id"] in ids


def test_gate_label_fail():
    """Label-mismatch peer → 0 merges (engineer a peer w/ same neighbors but different label)."""
    local = _local_extraction()
    # Patch peer in-memory to simulate label-fail w/ neighborhood + basename overlap intact.
    peer_dict = {
        "nodes": [
            {"id": "p_other_label", "label": "DifferentName", "file_type": "document",
             "source_file": "auth.py", "source_location": "L1"},
            {"id": "p_auth_service", "label": "AuthService", "file_type": "code",
             "source_file": "auth.py", "source_location": "L10"},
            {"id": "p_token_store", "label": "TokenStore", "file_type": "code",
             "source_file": "auth.py", "source_location": "L30"},
        ],
        "edges": [
            {"source": "p_other_label", "target": "p_auth_service", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.8, "weight": 1.0},
            {"source": "p_other_label", "target": "p_token_store", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.8, "weight": 1.0},
        ],
    }
    peer_path = FIXTURES / "peer_match" / "_synth_label_fail.json"
    peer_path.write_text(json.dumps(peer_dict))
    try:
        _, merges = federate(local, [peer_path], local_repo="local")
        assert merges == []
    finally:
        peer_path.unlink()


def test_gate_jaccard_fail():
    """peer_nomerge has same label but disjoint neighborhood (Jaccard < 0.5) → 0 merges."""
    _, merges = federate(_local_extraction(), [PEER_NOMERGE], local_repo="local")
    assert merges == []


def test_gate_basename_fail():
    """Same label + neighborhood, but no shared source_file basename → 0 merges."""
    peer_dict = {
        "nodes": [
            {"id": "p_token_validator", "label": "TokenValidator", "file_type": "document",
             "source_file": "different.py", "source_location": "L1"},
            {"id": "p_auth_service", "label": "AuthService", "file_type": "code",
             "source_file": "different.py", "source_location": "L10"},
            {"id": "p_token_store", "label": "TokenStore", "file_type": "code",
             "source_file": "different.py", "source_location": "L30"},
        ],
        "edges": [
            {"source": "p_token_validator", "target": "p_auth_service", "relation": "uses",
             "confidence": "INFERRED", "source_file": "different.py", "confidence_score": 0.8, "weight": 1.0},
            {"source": "p_token_validator", "target": "p_token_store", "relation": "uses",
             "confidence": "INFERRED", "source_file": "different.py", "confidence_score": 0.8, "weight": 1.0},
        ],
    }
    peer_path = FIXTURES / "peer_match" / "_synth_basename_fail.json"
    peer_path.write_text(json.dumps(peer_dict))
    try:
        _, merges = federate(_local_extraction(), [peer_path], local_repo="local")
        assert merges == []
    finally:
        peer_path.unlink()


def test_tiebreaker():
    """Two peers compete for same local target → winner has higher mean INFERRED confidence_score.

    Manifest entry contains `tiebreaker_score`.
    """
    # Lower-score competing peer (mean = 0.30).
    peer_low = {
        "nodes": [
            {"id": "p_token_validator", "label": "TokenValidator", "file_type": "document",
             "source_file": "auth.py", "source_location": "L1"},
            {"id": "p_auth_service", "label": "AuthService", "file_type": "code",
             "source_file": "auth.py", "source_location": "L10"},
            {"id": "p_token_store", "label": "TokenStore", "file_type": "code",
             "source_file": "auth.py", "source_location": "L30"},
        ],
        "edges": [
            {"source": "p_token_validator", "target": "p_auth_service", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.30, "weight": 1.0},
            {"source": "p_token_validator", "target": "p_token_store", "relation": "uses",
             "confidence": "INFERRED", "source_file": "auth.py", "confidence_score": 0.30, "weight": 1.0},
        ],
    }
    low_dir = FIXTURES / "peer_lowscore"
    low_dir.mkdir(exist_ok=True)
    low_path = low_dir / "graph.json"
    low_path.write_text(json.dumps(peer_low))
    try:
        _, merges = federate(
            _local_extraction(),
            [PEER_MATCH, low_path],  # peer_match has 0.85 mean, peer_lowscore has 0.30
            local_repo="local",
        )
        assert len(merges) == 1
        entry = merges[0]
        # Winner must be peer_match (higher mean confidence_score).
        repos = {c["repo"] for c in entry["contributing"]}
        assert "peer_match" in repos
        assert "peer_lowscore" not in repos
        assert "tiebreaker_score" in entry
        assert entry["tiebreaker_score"] == pytest.approx(0.85)
    finally:
        low_path.unlink()
        low_dir.rmdir()


def test_canonical_id():
    """merged_id = lex-min of contributing namespaced ids — deterministic across runs."""
    merged_a, merges_a = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    merged_b, merges_b = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    assert merges_a[0]["merged_id"] == merges_b[0]["merged_id"]
    namespaced = [
        f"{c['repo']}::{c['original_id']}" for c in merges_a[0]["contributing"]
    ]
    assert merges_a[0]["merged_id"] == min(namespaced)


def test_collision_error():
    """Two peers whose parent.name collides → FederationCollisionError w/ Phase 64 two-line msg."""
    with pytest.raises(FederationCollisionError) as excinfo:
        federate(_local_extraction(), [PEER_COLLISION_A, PEER_COLLISION_B], local_repo="local")
    msg = str(excinfo.value)
    assert msg == (
        "[graphify] error: --federate-with paths share repo basename 'repo'\n"
        "  hint: rename a peer directory or pass distinct parents"
    )


def test_manifest_deterministic():
    """build_manifest twice on same merges → byte-identical JSON (sorted keys, fixed separators)."""
    _, merges = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    manifest1 = build_manifest(merges)
    manifest2 = build_manifest(merges)
    s1 = json.dumps(manifest1, sort_keys=True, separators=(",", ": "))
    s2 = json.dumps(manifest2, sort_keys=True, separators=(",", ": "))
    assert s1 == s2


def test_manifest_schema():
    """Manifest entry has exactly D-66.5 keys; tiebreaker_score absent when tiebreaker did not fire."""
    _, merges = federate(_local_extraction(), [PEER_MATCH], local_repo="local")
    manifest = build_manifest(merges)
    assert len(manifest) == 1
    entry = manifest[0]
    expected_keys = {"merged_id", "contributing", "signals"}
    # tiebreaker_score MUST be absent on a single-candidate merge.
    assert set(entry.keys()) == expected_keys, (
        f"expected {expected_keys}, got {set(entry.keys())}"
    )
    # contributing entries
    for c in entry["contributing"]:
        assert set(c.keys()) == {"repo", "original_id", "label", "source_files"}
    # signals subkeys
    assert set(entry["signals"].keys()) == {
        "label_match", "neighborhood_jaccard", "shared_basenames"
    }


def test_no_new_deps():
    """AST-scan graphify/federate.py — imports must be subset of allow-list (CLAUDE.md no-new-deps)."""
    src = Path(__file__).resolve().parent.parent / "graphify" / "federate.py"
    tree = ast.parse(src.read_text())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
    allowed = {
        "__future__", "json", "pathlib", "hashlib", "os", "tempfile", "typing",
        "graphify.validate", "graphify.security",
    }
    bad = imports - allowed
    assert not bad, f"federate.py imports unexpected modules: {bad}"
