"""Tests for the graphify approve CLI helper functions."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers for creating fixture proposals
# ---------------------------------------------------------------------------

def _make_proposal(tmp_path: Path, title: str, status: str = "pending", timestamp: str = "2026-04-13T00:00:00Z") -> dict:
    """Write a proposal JSON file to tmp_path/proposals/ and return the record."""
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    record_id = str(uuid.uuid4())
    record = {
        "record_id": record_id,
        "title": title,
        "note_type": "note",
        "body_markdown": f"# {title}\n\nBody content.",
        "suggested_folder": "Atlas/Dots/Things",
        "tags": ["graphify"],
        "rationale": "test rationale",
        "peer_id": "anonymous",
        "session_id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "status": status,
    }
    (proposals_dir / f"{record_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# _list_pending_proposals tests
# ---------------------------------------------------------------------------

def test_list_pending_proposals_empty(tmp_path):
    """Returns [] when proposals/ directory does not exist."""
    from graphify.__main__ import _list_pending_proposals
    result = _list_pending_proposals(tmp_path)
    assert result == []


def test_list_pending_proposals_filters_status(tmp_path):
    """Returns only proposals with status 'pending'."""
    from graphify.__main__ import _list_pending_proposals
    p1 = _make_proposal(tmp_path, "Pending One", status="pending")
    p2 = _make_proposal(tmp_path, "Pending Two", status="pending")
    _make_proposal(tmp_path, "Rejected One", status="rejected")
    result = _list_pending_proposals(tmp_path)
    assert len(result) == 2
    ids = {r["record_id"] for r in result}
    assert p1["record_id"] in ids
    assert p2["record_id"] in ids


def test_list_pending_proposals_sorted_by_timestamp(tmp_path):
    """Returns proposals sorted by timestamp ascending."""
    from graphify.__main__ import _list_pending_proposals
    p_later = _make_proposal(tmp_path, "Later", timestamp="2026-04-13T10:00:00Z")
    p_earlier = _make_proposal(tmp_path, "Earlier", timestamp="2026-04-13T01:00:00Z")
    result = _list_pending_proposals(tmp_path)
    assert len(result) == 2
    assert result[0]["record_id"] == p_earlier["record_id"]
    assert result[1]["record_id"] == p_later["record_id"]


# ---------------------------------------------------------------------------
# _reject_proposal tests
# ---------------------------------------------------------------------------

def test_reject_proposal(tmp_path):
    """Rejects a pending proposal and updates status to 'rejected' on disk."""
    from graphify.__main__ import _reject_proposal
    record = _make_proposal(tmp_path, "Test Proposal")
    proposals_dir = tmp_path / "proposals"
    result = _reject_proposal(proposals_dir, record["record_id"])
    assert result["status"] == "rejected"
    # Verify the file was updated on disk
    on_disk = json.loads((proposals_dir / f"{record['record_id']}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "rejected"


def test_reject_proposal_missing(tmp_path):
    """Raises FileNotFoundError when rejecting a non-existent proposal."""
    from graphify.__main__ import _reject_proposal
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError, match="Proposal not found"):
        _reject_proposal(proposals_dir, "nonexistent-id")


# ---------------------------------------------------------------------------
# _format_proposal_summary tests
# ---------------------------------------------------------------------------

def test_format_proposal_summary():
    """Output contains the record_id prefix and title."""
    from graphify.__main__ import _format_proposal_summary
    record = {
        "record_id": "abcdef12-0000-0000-0000-000000000000",
        "title": "My Interesting Note",
        "note_type": "note",
        "peer_id": "anonymous",
        "timestamp": "2026-04-13T00:00:00Z",
    }
    summary = _format_proposal_summary(record)
    assert "abcdef12" in summary
    assert "My Interesting Note" in summary


# ---------------------------------------------------------------------------
# _approve_and_write_proposal test (mocked merge engine)
# ---------------------------------------------------------------------------

def test_approve_and_write_proposal_calls_merge(tmp_path, monkeypatch):
    """Calls compute_merge_plan and apply_merge_plan; sets proposal status to 'approved'."""
    from graphify.__main__ import _approve_and_write_proposal
    record = _make_proposal(tmp_path, "Vault Note Title")
    proposals_dir = tmp_path / "proposals"

    # Create a vault dir (empty, but exists)
    vault_dir = tmp_path / "my-vault"
    vault_dir.mkdir()

    called = {"compute": False, "apply": False}

    def fake_load_profile(vault_path):
        return {}

    def fake_validate_vault_path(candidate, vault_dir):
        # Return a simple path without raising
        return vault_dir / "Atlas" / "Dots" / "Things" / "Vault Note Title.md"

    def fake_compute_merge_plan(vault_dir, rendered_notes, profile, **kwargs):
        called["compute"] = True
        # Return a simple MergePlan-like object
        from graphify.merge import MergePlan
        return MergePlan(actions=[], orphans=[], summary={})

    def fake_apply_merge_plan(plan, vault_dir, rendered_notes, profile):
        called["apply"] = True
        from graphify.merge import MergeResult
        return MergeResult(plan=plan, succeeded=[], failed=[], skipped_identical=[])

    monkeypatch.setattr("graphify.__main__._load_profile_for_approve", fake_load_profile)
    monkeypatch.setattr("graphify.__main__._validate_vault_path_for_approve", fake_validate_vault_path)
    monkeypatch.setattr("graphify.__main__._compute_merge_plan_for_approve", fake_compute_merge_plan)
    monkeypatch.setattr("graphify.__main__._apply_merge_plan_for_approve", fake_apply_merge_plan)

    result = _approve_and_write_proposal(proposals_dir, record["record_id"], vault_dir)

    assert result["status"] == "approved"
    on_disk = json.loads((proposals_dir / f"{record['record_id']}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "approved"
    assert called["compute"]
    assert called["apply"]


# ---------------------------------------------------------------------------
# CLI integration tests (Task 2)
# ---------------------------------------------------------------------------

def test_cli_approve_list(tmp_path, monkeypatch, capsys):
    """graphify approve --out-dir <dir> lists pending proposals."""
    from graphify.__main__ import main
    p1 = _make_proposal(tmp_path, "First Note")
    p2 = _make_proposal(tmp_path, "Second Note")
    monkeypatch.setattr("sys.argv", ["graphify", "approve", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    # Both proposal IDs should appear in output (at least the first 8 chars)
    assert p1["record_id"][:8] in out
    assert p2["record_id"][:8] in out


def test_cli_approve_no_vault_exits_2(tmp_path, monkeypatch):
    """graphify approve <id> without --vault exits with code 2."""
    from graphify.__main__ import main
    _make_proposal(tmp_path, "Some Note")
    monkeypatch.setattr("sys.argv", ["graphify", "approve", "some-id", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2


def test_cli_approve_reject(tmp_path, monkeypatch, capsys):
    """graphify approve --reject <id> sets proposal status to rejected."""
    from graphify.__main__ import main
    record = _make_proposal(tmp_path, "To Reject")
    monkeypatch.setattr(
        "sys.argv",
        ["graphify", "approve", "--reject", record["record_id"], "--out-dir", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    proposals_dir = tmp_path / "proposals"
    on_disk = json.loads((proposals_dir / f"{record['record_id']}.json").read_text(encoding="utf-8"))
    assert on_disk["status"] == "rejected"


def test_cli_approve_reject_all(tmp_path, monkeypatch, capsys):
    """graphify approve --reject-all rejects all pending proposals."""
    from graphify.__main__ import main
    r1 = _make_proposal(tmp_path, "Note One")
    r2 = _make_proposal(tmp_path, "Note Two")
    monkeypatch.setattr(
        "sys.argv",
        ["graphify", "approve", "--reject-all", "--out-dir", str(tmp_path)],
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 0
    proposals_dir = tmp_path / "proposals"
    for r in (r1, r2):
        on_disk = json.loads((proposals_dir / f"{r['record_id']}.json").read_text(encoding="utf-8"))
        assert on_disk["status"] == "rejected"
