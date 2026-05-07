import json
from pathlib import Path

import pytest
from graphify.validate import (
    assert_valid,
    validate_extraction,
    validate_extraction_for_read,
    validate_extraction_for_write,
)

FIXTURES = Path(__file__).parent / "fixtures"

VALID = {
    "nodes": [
        {"id": "n1", "label": "Foo", "file_type": "code", "source_file": "foo.py"},
        {"id": "n2", "label": "Bar", "file_type": "document", "source_file": "bar.md"},
    ],
    "edges": [
        {"source": "n1", "target": "n2", "relation": "references",
         "confidence": "EXTRACTED", "source_file": "foo.py", "weight": 1.0},
    ],
}

def test_valid_passes():
    assert validate_extraction(VALID) == []

def test_missing_nodes_key():
    errors = validate_extraction({"edges": []})
    assert any("nodes" in e for e in errors)

def test_missing_edges_key():
    errors = validate_extraction({"nodes": []})
    assert any("edges" in e for e in errors)

def test_not_a_dict():
    errors = validate_extraction([])
    assert len(errors) == 1

def test_invalid_file_type():
    data = {
        "nodes": [{"id": "n1", "label": "X", "file_type": "video", "source_file": "x.mp4"}],
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("file_type" in e for e in errors)

def test_invalid_confidence():
    data = {
        "nodes": [
            {"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "B", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "relation": "calls",
             "confidence": "CERTAIN", "source_file": "a.py"},
        ],
    }
    errors = validate_extraction(data)
    assert any("confidence" in e for e in errors)

def test_dangling_edge_source():
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
        "edges": [
            {"source": "missing_id", "target": "n1", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py"},
        ],
    }
    errors = validate_extraction(data)
    assert any("source" in e and "missing_id" in e for e in errors)

def test_dangling_edge_target():
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code", "source_file": "a.py"}],
        "edges": [
            {"source": "n1", "target": "ghost", "relation": "calls",
             "confidence": "EXTRACTED", "source_file": "a.py"},
        ],
    }
    errors = validate_extraction(data)
    assert any("target" in e and "ghost" in e for e in errors)

def test_missing_node_field():
    data = {
        "nodes": [{"id": "n1", "label": "A", "source_file": "a.py"}],  # missing file_type
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("file_type" in e for e in errors)

def test_assert_valid_raises_on_errors():
    with pytest.raises(ValueError, match="error"):
        assert_valid({"nodes": [], "edges": [], "oops": True, **{"nodes": "bad"}})

def test_assert_valid_passes_silently():
    assert_valid(VALID)  # should not raise


def test_source_file_as_list():
    """D-12: source_file list[str] is valid after dedup."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": ["a.py", "b.py"], "merged_from": ["n2"]}],
        "edges": [],
    }
    assert validate_extraction(data) == []

def test_merged_from_accepted():
    """D-11: merged_from list[str] is optional; when present must be list[str]."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": "a.py", "merged_from": ["n2", "n3"]}],
        "edges": [],
    }
    assert validate_extraction(data) == []

def test_source_file_invalid_type():
    """D-12: source_file that is neither str nor list[str] must fail validation."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": 42}],
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("source_file" in e for e in errors)

def test_source_file_list_with_non_string():
    """D-12: source_file list with a non-string element must fail."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": ["a.py", 7]}],
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("source_file list must contain only strings" in e for e in errors)

def test_merged_from_not_list():
    """D-11: merged_from must be list[str], not a string."""
    data = {
        "nodes": [{"id": "n1", "label": "A", "file_type": "code",
                   "source_file": "a.py", "merged_from": "n2"}],
        "edges": [],
    }
    errors = validate_extraction(data)
    assert any("merged_from" in e for e in errors)


# ---- Phase 65-01: schema_version read/write split (CCONF-05) ----

def _load_legacy_v1_12() -> dict:
    return json.loads((FIXTURES / "legacy_v1_12_graph.json").read_text())


def test_legacy_v1_12_passes_read():
    """Pre-1.13 graphs (no schema_version key) must pass read validation."""
    data = _load_legacy_v1_12()
    assert "schema_version" not in data, "fixture must NOT carry schema_version"
    assert validate_extraction_for_read(data) == []


def test_write_requires_schema_version():
    """Write validation must reject graphs missing schema_version."""
    data = _load_legacy_v1_12()
    errors = validate_extraction_for_write(data)
    assert errors, "expected non-empty error list when schema_version is absent"
    assert any("schema_version" in e for e in errors)


def test_write_accepts_with_schema_version():
    """Write validation must accept graphs that carry schema_version='1.13'."""
    data = _load_legacy_v1_12()
    data["schema_version"] = "1.13"
    assert validate_extraction_for_write(data) == []


# ---- Phase 71 (TEMP) — schema 2.0 + temporal field validators --------------

import json as _json71
from pathlib import Path as _Path71

from graphify.validate import (
    validate_extraction_for_read as _v_read_71,
    validate_extraction_for_write as _v_write_71,
)

_FIX71 = _Path71(__file__).parent / "fixtures"


def _load_fixture_71(name: str) -> dict:
    return _json71.loads((_FIX71 / name).read_text(encoding="utf-8"))


def _temporal_data_71(**edge_overrides) -> dict:
    """Build a minimal write-mode-valid extraction dict, with edge overrides."""
    edge = {
        "source": "n1", "target": "n2", "relation": "calls",
        "confidence": "EXTRACTED", "source_file": "a.py",
        "valid_from": "2026-05-07T12:00:00+00:00",
        "valid_until": None,
        "decay_weight": 1.0,
    }
    edge.update(edge_overrides)
    return {
        "schema_version": "2.0",
        "nodes": [
            {"id": "n1", "label": "n1", "file_type": "code", "source_file": "a.py"},
            {"id": "n2", "label": "n2", "file_type": "code", "source_file": "b.py"},
        ],
        "edges": [edge],
    }


def test_legacy_graph_loads_71():
    """Read-mode tolerates pre-temporal v1.13 fixture (no valid_from/decay_weight)."""
    data = _load_fixture_71("graph_legacy_v113.json")
    # node_link fixtures use "links"; validate_extraction handles either.
    if "links" in data and "edges" not in data:
        data["edges"] = data["links"]
    assert _v_read_71(data) == []


def test_temporal_v20_fixture_passes_read_71():
    data = _load_fixture_71("graph_temporal_v20.json")
    if "links" in data and "edges" not in data:
        data["edges"] = data["links"]
    assert _v_read_71(data) == []


def test_write_requires_valid_from_71():
    data = _temporal_data_71()
    del data["edges"][0]["valid_from"]
    errors = _v_write_71(data)
    assert "Edge 0 missing required field 'valid_from' (write-mode)" in errors


def test_write_rejects_invalid_decay_weight_71():
    # 1.5 is out of range
    data = _temporal_data_71(decay_weight=1.5)
    errors = _v_write_71(data)
    assert "Edge 0 'decay_weight' must be float in [0.0, 1.0] (write-mode)" in errors

    # -0.1 is out of range
    data = _temporal_data_71(decay_weight=-0.1)
    errors = _v_write_71(data)
    assert "Edge 0 'decay_weight' must be float in [0.0, 1.0] (write-mode)" in errors

    # non-numeric
    data = _temporal_data_71(decay_weight="not-a-number")
    errors = _v_write_71(data)
    assert "Edge 0 'decay_weight' must be float in [0.0, 1.0] (write-mode)" in errors

    # missing
    data = _temporal_data_71()
    del data["edges"][0]["decay_weight"]
    errors = _v_write_71(data)
    assert "Edge 0 'decay_weight' must be float in [0.0, 1.0] (write-mode)" in errors


def test_write_accepts_null_valid_until_71():
    data = _temporal_data_71(valid_until=None)
    assert _v_write_71(data) == []
    data = _temporal_data_71(valid_until="2026-05-07T12:00:00+00:00")
    assert _v_write_71(data) == []


def test_schema_version_2_0_constant_71():
    from graphify.build import SCHEMA_VERSION
    assert SCHEMA_VERSION == "2.0"


def test_base_validate_does_not_require_temporal_71():
    """validate_extraction (base) must remain tolerant — no temporal field requirements."""
    from graphify.validate import validate_extraction
    data = _temporal_data_71()
    # strip ALL temporal fields
    for k in ("valid_from", "valid_until", "decay_weight"):
        data["edges"][0].pop(k, None)
    assert validate_extraction(data) == []
