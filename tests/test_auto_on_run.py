"""Integration tests for the auto_on_run hook (Phase 70 / VRSYNC-01, Plan 05).

Covers Success Criterion 4 and D-11 (warn-and-continue) and Pitfall 5
(no recursion). The hook fires at the start of `graphify run` and
`graphify update-vault` when profile.reverse_sync.auto_on_run=true.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _write_profile_yaml(
    vault: Path,
    *,
    auto_on_run: bool,
    mode: str = "always_copy",
    folders=("Atlas",),
) -> None:
    """Write a minimal valid v1.8 profile with reverse_sync.auto_on_run set.

    Mirrors tests/test_reverse_sync.py::_write_profile_yaml so the schema
    validates and run_reverse_sync can read mode/auto_on_run.
    """
    pdir = vault / ".graphify"
    pdir.mkdir(parents=True, exist_ok=True)
    folders_yaml = "\n".join(f"  - {f}" for f in folders)
    (pdir / "profile.yaml").write_text(
        "taxonomy: {}\n"
        "mapping:\n"
        "  min_community_size: 1\n"
        "output:\n"
        "  mode: vault-relative\n"
        "  path: graphify-out\n"
        "user_only_folders:\n" + folders_yaml + "\n"
        "reverse_sync:\n"
        f"  mode: {mode}\n"
        f"  auto_on_run: {'true' if auto_on_run else 'false'}\n",
        encoding="utf-8",
    )


def _setup_vault_input(tmp_path: Path) -> tuple[Path, Path]:
    vault = tmp_path / "vault"
    inp = tmp_path / "input"
    (vault / "Atlas").mkdir(parents=True)
    (vault / ".obsidian").mkdir(parents=True)
    (inp / "Atlas").mkdir(parents=True)
    return vault, inp


def _stub_run_corpus(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Stub graphify.pipeline.run_corpus to record calls without doing work."""
    calls: list[dict] = []

    def _fake_run_corpus(target, **kwargs):
        calls.append({"target": target, "kwargs": kwargs})

    monkeypatch.setattr("graphify.pipeline.run_corpus", _fake_run_corpus)
    return calls


def _stub_update_vault(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Stub graphify.migration.run_update_vault to record calls."""
    calls: list[dict] = []

    def _fake(**kwargs):
        calls.append(kwargs)
        return {"preview": {}, "applied": False}

    monkeypatch.setattr("graphify.migration.run_update_vault", _fake)
    monkeypatch.setattr(
        "graphify.migration.format_migration_preview", lambda *a, **kw: ""
    )
    return calls


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_with_auto_on_run_true_fires_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """auto_on_run=true: `graphify run` triggers reverse-sync before pipeline."""
    vault, inp = _setup_vault_input(tmp_path)
    (vault / "Atlas" / "new.md").write_text("hello\n")
    _write_profile_yaml(vault, auto_on_run=True, mode="always_copy")

    _stub_run_corpus(monkeypatch)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        ["graphify", "run", "--vault", str(vault), str(inp)],
    )

    import graphify.__main__ as m

    m.main()

    # Reverse-sync mirrored vault → input
    assert (inp / "Atlas" / "new.md").read_text() == "hello\n"
    log_path = vault / ".graphify" / "reverse-sync-log.jsonl"
    assert log_path.exists()
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1


def test_run_with_auto_on_run_false_skips_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auto_on_run=false (default): no reverse-sync, no log file written."""
    vault, inp = _setup_vault_input(tmp_path)
    (vault / "Atlas" / "new.md").write_text("hello\n")
    _write_profile_yaml(vault, auto_on_run=False, mode="always_copy")

    _stub_run_corpus(monkeypatch)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        ["graphify", "run", "--vault", str(vault), str(inp)],
    )

    import graphify.__main__ as m

    m.main()

    # Hook did NOT fire — file was not mirrored, no log written
    assert not (inp / "Atlas" / "new.md").exists()
    assert not (vault / ".graphify" / "reverse-sync-log.jsonl").exists()


def test_update_vault_with_auto_on_run_true_fires_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """auto_on_run=true: `graphify update-vault` triggers reverse-sync."""
    vault, inp = _setup_vault_input(tmp_path)
    (vault / "Atlas" / "new.md").write_text("hello\n")
    _write_profile_yaml(vault, auto_on_run=True, mode="always_copy")

    _stub_update_vault(monkeypatch)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graphify",
            "update-vault",
            "--input",
            str(inp),
            "--vault",
            str(vault),
        ],
    )

    import graphify.__main__ as m

    try:
        m.main()
    except SystemExit as e:
        assert e.code == 0

    assert (inp / "Atlas" / "new.md").read_text() == "hello\n"
    assert (vault / ".graphify" / "reverse-sync-log.jsonl").exists()


def test_auto_on_run_failure_warn_continue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-11: reverse_sync errors must NOT block the parent command."""
    vault, inp = _setup_vault_input(tmp_path)
    _write_profile_yaml(vault, auto_on_run=True, mode="always_copy")

    calls = _stub_run_corpus(monkeypatch)

    def _boom(*a, **kw):
        raise RuntimeError("simulated reverse-sync failure")

    monkeypatch.setattr("graphify.reverse_sync.run_reverse_sync", _boom)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        ["graphify", "run", "--vault", str(vault), str(inp)],
    )

    import graphify.__main__ as m

    # Must not raise — parent command continues
    m.main()

    err = capsys.readouterr().err
    assert "reverse-sync" in err
    assert "skipped" in err.lower() or "error" in err.lower()
    # Pipeline still ran
    assert len(calls) == 1


def test_auto_on_run_conflicts_skipped_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """D-11: when conflicts_skipped > 0, stderr prints the resolve hint."""
    vault, inp = _setup_vault_input(tmp_path)
    _write_profile_yaml(vault, auto_on_run=True, mode="always_copy")

    _stub_run_corpus(monkeypatch)

    def _fake_rs(*a, **kw):
        return {
            "copied": 0,
            "skipped_user": 0,
            "skipped_conflict": 3,
            "skipped_never_copy": 0,
            "vault_deleted": 0,
            "conflicts_skipped": 3,
            "failed": False,
            "log_path": str(vault / ".graphify" / "reverse-sync-log.jsonl"),
        }

    monkeypatch.setattr("graphify.reverse_sync.run_reverse_sync", _fake_rs)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        ["graphify", "run", "--vault", str(vault), str(inp)],
    )

    import graphify.__main__ as m

    m.main()
    err = capsys.readouterr().err
    assert "3 conflicts skipped" in err
    assert "graphify reverse-sync" in err
    assert "resolve" in err


def test_no_recursion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pitfall 5: hook must not cause reverse-sync to re-invoke run."""
    vault, inp = _setup_vault_input(tmp_path)
    (vault / "Atlas" / "a.md").write_text("a\n")
    (vault / "Atlas" / "b.md").write_text("b\n")
    _write_profile_yaml(vault, auto_on_run=True, mode="always_copy")

    _stub_run_corpus(monkeypatch)
    monkeypatch.chdir(vault)
    monkeypatch.setattr(
        sys,
        "argv",
        ["graphify", "run", "--vault", str(vault), str(inp)],
    )

    import graphify.__main__ as m

    m.main()

    log_path = vault / ".graphify" / "reverse-sync-log.jsonl"
    lines = log_path.read_text().strip().splitlines()
    # Exactly N entries for N changes — not 2N
    assert len(lines) == 2
    for ln in lines:
        rec = json.loads(ln)
        assert rec["action"] == "copied"
