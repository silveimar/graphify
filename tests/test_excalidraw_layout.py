"""Phase 22 SKILL-06: pure-Python Excalidraw fallback layout + write tests.

Wave 0 stubs are marked ``xfail(strict=True)`` so the suite stays green
until Wave 1 implements ``layout_for`` and ``write_diagram`` in
``graphify/excalidraw.py``. Tasks 3 and 4 of plan 22-01 flip these
markers off when the implementation lands.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


def _import_layout():
    from graphify.excalidraw import (  # noqa: F401
        _VALID_LAYOUT_TYPES,
        layout_for,
        write_diagram,
    )
    return layout_for, write_diagram, _VALID_LAYOUT_TYPES


def test_layout_for_all_six_layout_types():
    layout_for, _, _VALID_LAYOUT_TYPES = _import_layout()
    nodes = [
        {"id": f"n{i}", "label": f"N{i}", "element_id": f"elem-{i:04d}"}
        for i in range(5)
    ]
    edges = [{"source": "n0", "target": "n1", "relation": "calls", "confidence": "EXTRACTED"}]
    for lt in _VALID_LAYOUT_TYPES:
        elems = layout_for(lt, nodes, edges)
        assert len(elems) >= len(nodes), f"{lt}: missing node elements"
        ids = [e["id"] for e in elems]
        assert len(ids) == len(set(ids)), f"{lt}: duplicate element ids"


def test_layout_for_is_deterministic():
    layout_for, _, _ = _import_layout()
    nodes = [{"id": "a", "label": "A", "element_id": "elem-0001"}]
    a = layout_for("mind-map", nodes, [])
    b = layout_for("mind-map", nodes, [])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_layout_for_unknown_falls_back_to_mind_map():
    layout_for, _, _ = _import_layout()
    nodes = [{"id": "a", "label": "A", "element_id": "elem-0001"}]
    assert layout_for("not-a-layout", nodes, []) == layout_for("mind-map", nodes, [])


def test_write_diagram_collision_refuses(tmp_path):
    _, write_diagram, _ = _import_layout()
    seed = {
        "seed_id": "x",
        "main_node_label": "X",
        "main_nodes": [],
        "supporting_nodes": [],
        "relations": [],
        "suggested_layout_type": "mind-map",
    }
    profile = {
        "diagram_types": [
            {"name": "mind-map", "layout_type": "mind-map", "output_path": "Excalidraw/Diagrams"}
        ]
    }
    write_diagram(tmp_path, seed, profile)
    with pytest.raises(FileExistsError):
        write_diagram(tmp_path, seed, profile)
    write_diagram(tmp_path, seed, profile, force=True)


def test_write_diagram_path_confined(tmp_path):
    _, write_diagram, _ = _import_layout()
    seed = {
        "seed_id": "x",
        "main_node_label": "X",
        "main_nodes": [],
        "supporting_nodes": [],
        "relations": [],
        "suggested_layout_type": "mind-map",
    }
    profile = {
        "diagram_types": [
            {"name": "mind-map", "layout_type": "mind-map", "output_path": "../../etc"}
        ]
    }
    with pytest.raises(ValueError, match="escape vault directory"):
        write_diagram(tmp_path, seed, profile)


def test_write_diagram_compress_false(tmp_path):
    _, write_diagram, _ = _import_layout()
    seed = {
        "seed_id": "x",
        "main_node_label": "X",
        "main_nodes": [],
        "supporting_nodes": [],
        "relations": [],
        "suggested_layout_type": "mind-map",
    }
    profile = {
        "diagram_types": [
            {"name": "mind-map", "layout_type": "mind-map", "output_path": "Excalidraw/Diagrams"}
        ]
    }
    out = write_diagram(tmp_path, seed, profile)
    body = out.read_text()
    assert "compress: false" in body
    assert "excalidraw-plugin: parsed" in body
    m = re.search(r"```json\n(.+?)\n```", body, re.S)
    assert m is not None, "Drawing block missing in output"
    scene = json.loads(m.group(1))
    assert scene["appState"]["currentItemFontFamily"] == 5
    assert scene["type"] == "excalidraw" and scene["version"] == 2


# Wave 0 → Wave 1 transition: layout_for tests now pass (Task 3).
# write_diagram tests remain xfail until Task 4 implementation lands.
_WD_XFAIL = pytest.mark.xfail(
    reason="Wave 0 stub — write_diagram implementation lands in Task 4",
    strict=True,
)
test_write_diagram_collision_refuses = _WD_XFAIL(test_write_diagram_collision_refuses)
test_write_diagram_path_confined = _WD_XFAIL(test_write_diagram_path_confined)
test_write_diagram_compress_false = _WD_XFAIL(test_write_diagram_compress_false)
