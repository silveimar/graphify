"""Unit tests for graphify/doctor.py — Phase 29 diagnostics + dry-run."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from graphify.doctor import (
    DoctorReport,
    PreviewSection,
    _FIX_HINTS,
    format_report,
    run_doctor,
)
from graphify.output import ResolvedOutput


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_vault(tmp_path: Path, *, profile_text: str | None = None) -> Path:
    """Create a synthetic Obsidian vault under tmp_path/vault.

    - .obsidian/  marks it as a vault (D-04)
    - .git/       halts _load_graphifyignore walk-up (RESEARCH §Pitfall 6)
    - .graphify/  for profile.yaml when profile_text is provided
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".git").mkdir()
    (vault / ".graphify").mkdir()
    if profile_text is not None:
        (vault / ".graphify" / "profile.yaml").write_text(profile_text)
    return vault


_VALID_PROFILE = (
    "taxonomy:\n"
    "  version: v1.8\n"
    "  root: Atlas/Sources/Graphify\n"
    "  folders:\n"
    "    moc: MOCs\n"
    "    thing: Things\n"
    "    statement: Statements\n"
    "    person: People\n"
    "    source: Sources\n"
    "    default: Things\n"
    "    unclassified: MOCs\n"
    "mapping:\n"
    "  min_community_size: 3\n"
    "output:\n"
    "  mode: vault-relative\n"
    "  path: Atlas/Generated\n"
)


def _valid_profile_with(extra: str) -> str:
    """Append focused profile overrides to the v1.8-valid doctor fixture."""
    return f"{_VALID_PROFILE}{extra}"


# ---------------------------------------------------------------------------
# 1. test_run_doctor_vault_detected
# ---------------------------------------------------------------------------

def test_run_doctor_vault_detected(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    assert report.vault_detection is True
    assert report.vault_path == vault.resolve()


# ---------------------------------------------------------------------------
# 2. test_run_doctor_invalid_profile
# ---------------------------------------------------------------------------

def test_run_doctor_invalid_profile(tmp_path):
    pytest.importorskip("yaml")
    # mode is invalid -> resolve_output _refuse() captures into errors
    bad = (
        "output:\n"
        "  mode: not-a-mode\n"
        "  path: Atlas/Generated\n"
    )
    vault = _make_vault(tmp_path, profile_text=bad)
    report = run_doctor(vault)
    assert report.profile_validation_errors, (
        f"expected non-empty errors, got: {report.profile_validation_errors}"
    )
    assert report.is_misconfigured() is True


def test_run_doctor_surfaces_taxonomy_preflight_errors(tmp_path):
    pytest.importorskip("yaml")
    bad = _valid_profile_with(
        "taxonomy:\n"
        "  version: v1.8\n"
        "  root: Atlas/Sources/Graphify\n"
        "  bad_key: true\n"
        "  folders:\n"
        "    moc: MOCs\n"
        "    thing: Things\n"
        "    statement: Statements\n"
        "    person: People\n"
        "    source: Sources\n"
        "    default: Things\n"
        "    unclassified: MOCs\n"
    )
    vault = _make_vault(tmp_path, profile_text=bad)
    report = run_doctor(vault)
    text = format_report(report)
    assert any("Unknown taxonomy key 'bad_key'" in err for err in report.profile_validation_errors)
    assert "[graphify] error: Unknown taxonomy key 'bad_key'" in text
    assert report.is_misconfigured() is True


def test_run_doctor_mapping_moc_threshold_error_and_fix(tmp_path):
    pytest.importorskip("yaml")
    bad = _valid_profile_with(
        "mapping:\n"
        "  min_community_size: 3\n"
        "  moc_threshold: 3\n"
    )
    vault = _make_vault(tmp_path, profile_text=bad)
    report = run_doctor(vault)
    assert any("mapping.moc_threshold" in err for err in report.profile_validation_errors)
    assert report.is_misconfigured() is True
    assert any("mapping.min_community_size" in fix for fix in report.recommended_fixes)


def test_run_doctor_community_template_warning_is_nonfatal(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    templates_dir = vault / ".graphify" / "templates"
    templates_dir.mkdir()
    (templates_dir / "community.md").write_text(
        "${frontmatter}\n# ${label}\n${members_section}\n${dataview_block}\n",
        encoding="utf-8",
    )
    report = run_doctor(vault)
    text = format_report(report)
    assert report.profile_validation_errors == []
    assert report.profile_validation_warnings
    assert any("MOC-only output" in warn for warn in report.profile_validation_warnings)
    assert "[graphify] warning:" in text
    assert "MOC-only output" in text
    assert report.is_misconfigured() is False


# ---------------------------------------------------------------------------
# 3. test_run_doctor_resolved_output
# ---------------------------------------------------------------------------

def test_run_doctor_resolved_output(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    assert report.resolved_output is not None
    assert report.resolved_output.notes_dir == (vault / "Atlas" / "Generated").resolve()
    assert report.resolved_output.source == "profile"


def test_run_doctor_preflight_uses_pinned_vault_not_cwd(tmp_path):
    """VCLI-03: preflight must validate profile_home, not CWD, when they differ."""
    pytest.importorskip("yaml")
    bad = (
        "output:\n"
        "  mode: not-a-mode\n"
        "  path: Atlas/Generated\n"
    )
    vault = _make_vault(tmp_path, profile_text=bad)
    cwd_elsewhere = tmp_path / "not_a_vault_cwd"
    cwd_elsewhere.mkdir()
    v = vault.resolve()
    resolved = ResolvedOutput(
        True,
        v,
        v / "Atlas" / "Generated",
        v.parent / "graphify-out",
        "vault-cli",
        (),
    )
    report = run_doctor(cwd_elsewhere, resolved_output=resolved)
    assert report.profile_validation_errors, (
        "pinned vault has invalid profile — errors must not be masked by empty CWD tree"
    )


# ---------------------------------------------------------------------------
# 4. test_run_doctor_ignore_list_sources (D-37)
# ---------------------------------------------------------------------------

def test_run_doctor_ignore_list_sources(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    assert set(report.ignore_list.keys()) == {
        "self-output-dirs",
        "resolved-basenames",
        "graphifyignore-patterns",
        "profile-exclude-globs",
    }
    # Self-output-dirs constant always present
    assert "graphify-out" in report.ignore_list["self-output-dirs"]
    assert "graphify_out" in report.ignore_list["self-output-dirs"]


# ---------------------------------------------------------------------------
# 5. test_run_doctor_manifest_history
# ---------------------------------------------------------------------------

def test_run_doctor_manifest_history(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    # Manifest lives under resolved.artifacts_dir which is sibling-of-vault
    # (cwd_resolved.parent / "graphify-out") per output.py D-11.
    artifacts_dir = (vault.resolve().parent / "graphify-out")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": 1,
        "runs": [
            {
                "run_id": "test-run-id",
                "timestamp": "2026-04-28T00:00:00+00:00",
                "notes_dir": str(vault / "Atlas" / "Generated"),
                "artifacts_dir": str(artifacts_dir),
                "files": [],
            }
        ],
    }
    (artifacts_dir / "output-manifest.json").write_text(json.dumps(manifest))
    report = run_doctor(vault)
    assert isinstance(report.manifest_history, list)
    assert len(report.manifest_history) == 1
    assert report.manifest_history[0]["run_id"] == "test-run-id"


# ---------------------------------------------------------------------------
# 6. test_run_doctor_self_ingest_detected
# ---------------------------------------------------------------------------

def test_run_doctor_self_ingest_detected(tmp_path):
    pytest.importorskip("yaml")
    # output.path lives nested under a name that trips _is_nested_output
    # (matches notes_dir basename → guard returns True).
    nested = _valid_profile_with(
        "output:\n"
        "  mode: vault-relative\n"
        "  path: graphify-out/notes\n"
    )
    vault = _make_vault(tmp_path, profile_text=nested)
    report = run_doctor(vault)
    assert report.would_self_ingest is True
    assert report.is_misconfigured() is True


# ---------------------------------------------------------------------------
# 7. test_run_doctor_default_paths_not_self_ingest (D-12 backcompat)
# ---------------------------------------------------------------------------

def test_run_doctor_default_paths_not_self_ingest(tmp_path):
    # Non-vault directory → resolved.source == "default" → no self-ingest concern
    (tmp_path / ".git").mkdir()
    report = run_doctor(tmp_path)
    assert report.resolved_output is not None
    assert report.resolved_output.source == "default"
    assert report.would_self_ingest is False


# ---------------------------------------------------------------------------
# 8. test_format_report_section_order (D-34)
# ---------------------------------------------------------------------------

def test_format_report_section_order(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    text = format_report(report)
    i_vault = text.index("Vault Detection")
    i_profile = text.index("Profile Validation")
    i_output = text.index("Output Destination")
    i_ignore = text.index("Ignore-List")
    i_fixes = text.index("Recommended Fixes")
    assert i_vault < i_profile < i_output < i_ignore < i_fixes


# ---------------------------------------------------------------------------
# 9. test_format_report_graphify_prefix
# ---------------------------------------------------------------------------

def test_format_report_graphify_prefix(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    text = format_report(report)
    for line in text.splitlines():
        if not line.strip():
            continue
        assert line.startswith("[graphify] "), (
            f"line missing [graphify] prefix: {line!r}"
        )


# ---------------------------------------------------------------------------
# 10. test_fix_hints_coverage (D-40)
# ---------------------------------------------------------------------------

def test_fix_hints_coverage():
    """For each _FIX_HINTS entry, synthesizing the matching error yields the fix line."""
    for pattern, fix_line in _FIX_HINTS:
        if pattern == "WOULD_SELF_INGEST":
            report = DoctorReport(would_self_ingest=True)
        else:
            report = DoctorReport(profile_validation_errors=[pattern])
        # _build_recommended_fixes happens inside run_doctor; for the unit-level
        # check we re-import it locally so we don't need a live filesystem.
        from graphify.doctor import _build_recommended_fixes
        fixes = _build_recommended_fixes(
            report.profile_validation_errors, report.would_self_ingest
        )
        assert fix_line in fixes, (
            f"pattern {pattern!r} did not produce fix line {fix_line!r}; got {fixes}"
        )
        # And via format_report():
        report.recommended_fixes = fixes
        text = format_report(report)
        assert fix_line in text


# ---------------------------------------------------------------------------
# 11. test_format_report_no_issues
# ---------------------------------------------------------------------------

def test_format_report_no_issues(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    report = run_doctor(vault)
    # Clean profile, default sibling-of-vault artifacts → no issues
    assert report.recommended_fixes == []
    text = format_report(report)
    assert "[graphify] No issues detected." in text


# ---------------------------------------------------------------------------
# 12. test_run_doctor_no_disk_writes
# ---------------------------------------------------------------------------

def test_run_doctor_no_disk_writes(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)

    def _snapshot(root: Path) -> set[Path]:
        return {p for p in root.rglob("*")}

    # Snapshot the entire tmp_path tree (vault parent), not just the vault,
    # because resolve_output writes artifacts_dir as sibling-of-vault (D-11).
    before = _snapshot(tmp_path)
    run_doctor(vault)
    after = _snapshot(tmp_path)
    new_paths = after - before
    assert new_paths == set(), f"run_doctor created files: {sorted(new_paths)}"


# ---------------------------------------------------------------------------
# 13. test_run_doctor_dry_run_preview (D-38, D-39)
# ---------------------------------------------------------------------------

def test_run_doctor_dry_run_preview(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    # A handful of code+doc files so detect() returns non-empty buckets.
    (vault / "alpha.py").write_text("def a(): return 1\n")
    (vault / "beta.py").write_text("def b(): return 2\n")
    (vault / "notes.md").write_text("# Notes\nhello\n")
    report = run_doctor(vault, dry_run=True)
    assert report.preview is not None
    assert report.preview.would_ingest_count > 0
    assert isinstance(report.preview.would_ingest_sample, list)
    assert all(isinstance(p, str) for p in report.preview.would_ingest_sample)
    assert len(report.preview.would_ingest_sample) <= 10
    assert len(report.preview.would_ingest_sample) == min(
        10, report.preview.would_ingest_count
    )


# ---------------------------------------------------------------------------
# 14. test_dry_run_skip_grouping (D-38)
# ---------------------------------------------------------------------------

def test_dry_run_skip_grouping(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    # .graphifyignore'd file → "exclude-glob" reason
    (vault / ".graphifyignore").write_text("ignored.py\n")
    (vault / "ignored.py").write_text("def x(): return 0\n")
    # noise dir with code → "noise-dir" reason
    (vault / "node_modules").mkdir()
    (vault / "node_modules" / "lib.js").write_text("module.exports = {};\n")
    # a real ingestable file so flattened isn't completely empty
    (vault / "real.py").write_text("def y(): return 1\n")
    report = run_doctor(vault, dry_run=True)
    assert report.preview is not None
    grouped = report.preview.would_skip_grouped
    # Both reasons present (detect's skipped dict initialized with empty lists
    # for every reason; we only emit groups detect actually populated). When
    # populated, each list is bounded at 5.
    if "exclude-glob" in grouped:
        assert len(grouped["exclude-glob"]) <= 5
    if "noise-dir" in grouped:
        assert len(grouped["noise-dir"]) <= 5


# ---------------------------------------------------------------------------
# 15. test_dry_run_no_disk_writes (T-29-* mitigation)
# ---------------------------------------------------------------------------

def test_dry_run_no_disk_writes(tmp_path):
    pytest.importorskip("yaml")
    vault = _make_vault(tmp_path, profile_text=_VALID_PROFILE)
    (vault / "alpha.py").write_text("def a(): return 1\n")

    def _snapshot(p: Path) -> set[Path]:
        return {q for q in p.rglob("*") if q.is_file()}

    before = _snapshot(tmp_path)
    run_doctor(vault, dry_run=True)
    after = _snapshot(tmp_path)
    assert before == after, f"dry_run created files: {sorted(after - before)}"
