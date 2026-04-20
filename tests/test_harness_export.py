"""Phase 13 — SEED-002 harness export (HARNESS-01..08)."""
from __future__ import annotations

import importlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from graphify.harness_export import (
    ANNOTATION_ALLOW_LIST,
    SECRET_PATTERNS,
    _filter_annotations_allowlist,
    _normalize_placeholders,
    _redact_secrets,
    _sha256_file,
    export_claude_harness,
    scan_annotations_for_secrets,
    set_clock,
)

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "harness"


def _copy_fixtures(dest: Path) -> None:
    """Copy all harness fixture files into ``dest`` (flat)."""
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ("graph.json", "annotations.jsonl", "agent-edges.json", "telemetry.json"):
        shutil.copy(_FIXTURE_DIR / fname, dest / fname)


class _FrozenDatetime:
    """Test shim: deterministic datetime for byte-equality assertions."""

    _frozen = datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)

    @classmethod
    def now(cls, tz: timezone | None = None) -> datetime:  # pragma: no cover - trivial
        return cls._frozen


def _frozen_clock() -> datetime:
    return datetime(2026, 4, 17, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# HARNESS-01 / HARNESS-05: writes three files with canonical filenames
# ---------------------------------------------------------------------------


def test_export_writes_three_files(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    written = export_claude_harness(out_dir)

    # HARNESS-08 (Plan 04) appends ``fidelity.json`` to the returned paths.
    assert len(written) == 4
    assert [p.name for p in written] == [
        "claude-SOUL.md",
        "claude-HEARTBEAT.md",
        "claude-USER.md",
        "fidelity.json",
    ]
    for p in written:
        assert p.exists(), f"expected {p} to exist"
        assert p.parent == out_dir / "harness"
    # Content sanity: SOUL file mentions god nodes heading from the schema.
    soul = (out_dir / "harness" / "claude-SOUL.md").read_text(encoding="utf-8")
    assert "God Nodes" in soul
    assert "Transformer" in soul  # label for the top-degree node in fixture


# ---------------------------------------------------------------------------
# T-13-05: output confined to graphify-out/ (path escape fails cleanly)
# ---------------------------------------------------------------------------


def test_output_confined_to_graphify_out(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    def _raise_escape(*_a, **_kw):
        raise ValueError(
            "Path '/escape' escapes the allowed directory. Only paths inside "
            "graphify-out/ are permitted."
        )

    monkeypatch.setattr(
        "graphify.harness_export.validate_graph_path", _raise_escape
    )

    with pytest.raises(ValueError, match="escapes the allowed directory"):
        export_claude_harness(out_dir)

    # Nothing was written under the harness dir (beyond the mkdir itself).
    harness_dir = out_dir / "harness"
    if harness_dir.exists():
        assert list(harness_dir.iterdir()) == []


# ---------------------------------------------------------------------------
# HARNESS-06 / T-13-04: annotations allow-list filters secrets by default
# ---------------------------------------------------------------------------


def test_annotations_allow_list_default() -> None:
    annotations = [
        {
            "id": "n1",
            "label": "Node1",
            "peer_id": "SECRET_PEER",
            "body": "free-text leak with api_key=sk-LEAK",
        }
    ]
    filtered = _filter_annotations_allowlist(annotations)
    assert filtered == [{"id": "n1", "label": "Node1"}]
    payload = json.dumps(filtered)
    assert "SECRET_PEER" not in payload
    assert "free-text leak" not in payload
    assert "sk-LEAK" not in payload
    assert ANNOTATION_ALLOW_LIST == frozenset(
        {"id", "label", "source_file", "relation", "confidence"}
    )


# ---------------------------------------------------------------------------
# HARNESS-03: placeholder token regex normalization
# ---------------------------------------------------------------------------


def test_placeholder_token_regex_normalization() -> None:
    assert _normalize_placeholders("{{ god_nodes }}") == "${god_nodes}"
    assert _normalize_placeholders("{{god_nodes}}") == "${god_nodes}"
    assert _normalize_placeholders("{{  spaced  }}") == "${spaced}"
    assert _normalize_placeholders("no tokens here") == "no tokens here"
    # Single $ sigil is untouched — regex only matches double-brace tokens.
    assert _normalize_placeholders("$already_dollar") == "$already_dollar"


# ---------------------------------------------------------------------------
# T-13-06: deterministic output across runs with a pinned clock
# ---------------------------------------------------------------------------


def test_deterministic_output_across_runs(tmp_path: Path) -> None:
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"
    _copy_fixtures(out1)
    _copy_fixtures(out2)

    export_claude_harness(out1, _clock=_frozen_clock)
    export_claude_harness(out2, _clock=_frozen_clock)

    for fname in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md"):
        a = (out1 / "harness" / fname).read_bytes()
        b = (out2 / "harness" / fname).read_bytes()
        assert a == b, f"byte-equality broken for {fname}"


# ---------------------------------------------------------------------------
# Locked decision: no Jinja2 touched during harness export module import
# ---------------------------------------------------------------------------


def test_no_jinja2_import() -> None:
    # Jinja2 may already be imported transitively by other tests in the
    # session; the contract is that *our* module never imports it.
    removed = sys.modules.pop("graphify.harness_export", None)
    jinja_was_present = "jinja2" in sys.modules
    importlib.import_module("graphify.harness_export")
    if not jinja_was_present:
        assert "jinja2" not in sys.modules, (
            "graphify.harness_export must not import jinja2"
        )
    # Hard guard regardless of prior state — the module text must not import it.
    source = (
        Path(__file__).resolve().parent.parent
        / "graphify"
        / "harness_export.py"
    ).read_text(encoding="utf-8")
    assert "import jinja2" not in source
    assert "from jinja2" not in source
    # Restore original module so no test state leaks.
    if removed is not None:
        sys.modules["graphify.harness_export"] = removed


# ---------------------------------------------------------------------------
# HARNESS-04: CLI subcommand dispatcher invokes the exporter
# ---------------------------------------------------------------------------


def test_cli_harness_export_invokes_exporter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    monkeypatch.setattr(
        sys, "argv", ["graphify", "harness", "export", "--out", str(out_dir)]
    )

    from graphify import __main__ as g_main

    with pytest.raises(SystemExit) as exc:
        g_main.main()
    assert exc.value.code == 0

    captured = capsys.readouterr()
    out_lines = [ln for ln in captured.out.splitlines() if ln.strip()]
    # SOUL/HEARTBEAT/USER + fidelity.json (HARNESS-08, Plan 04) in order.
    assert len(out_lines) == 4
    assert out_lines[0].endswith("claude-SOUL.md")
    assert out_lines[1].endswith("claude-HEARTBEAT.md")
    assert out_lines[2].endswith("claude-USER.md")
    assert out_lines[3].endswith("fidelity.json")

    for fname in (
        "claude-SOUL.md",
        "claude-HEARTBEAT.md",
        "claude-USER.md",
        "fidelity.json",
    ):
        assert (out_dir / "harness" / fname).exists()


# ---------------------------------------------------------------------------
# HARNESS-07 / T-13-07: secret scanner (Plan 04)
# ---------------------------------------------------------------------------


def test_secret_patterns_coverage() -> None:
    names = [n for n, _ in SECRET_PATTERNS]
    required = {
        "aws_access_key",
        "github_pat",
        "openai_api_key",
        "slack_token",
        "bearer_token",
        "pem_private_key",
        "email_credential",
    }
    assert required.issubset(set(names))
    assert len(SECRET_PATTERNS) >= 7


def test_scanner_detects_aws_key() -> None:
    cleaned, matched = _redact_secrets("AWS creds: AKIAIOSFODNN7EXAMPLE")
    assert "[REDACTED]" in cleaned
    assert "AKIAIOSFODNN7EXAMPLE" not in cleaned
    assert "aws_access_key" in matched


def test_scanner_detects_aws_temporary_credentials() -> None:
    """WR-01 (Phase 13 review): STS/SSO/role credentials use ASIA, AGPA,
    AIDA, AROA, ANPA, ANVA, AIPA prefixes — all must be redacted in
    addition to long-term AKIA keys.
    """
    for prefix in ("ASIA", "AGPA", "AIDA", "AROA", "ANPA", "ANVA", "AIPA"):
        token = prefix + "IOSFODNN7EXAMPLE"
        cleaned, matched = _redact_secrets(f"creds: {token}")
        assert "[REDACTED]" in cleaned, f"missed {prefix} prefix"
        assert token not in cleaned, f"failed to redact {token}"
        assert "aws_access_key" in matched, f"no aws_access_key tag for {prefix}"


def test_scanner_detects_github_pat() -> None:
    token = "ghp_" + "a" * 36
    cleaned, matched = _redact_secrets(f"leaked token: {token}")
    assert "[REDACTED]" in cleaned
    assert token not in cleaned
    assert "github_pat" in matched


def test_scanner_detects_openai_key() -> None:
    # 48 alphanumeric chars after the ``sk-`` prefix — matches the
    # tightened CR-02 pattern that targets the documented OpenAI shape.
    real_shape = "sk-" + ("A" * 48)
    cleaned, matched = _redact_secrets(f"leak: {real_shape}")
    assert "[REDACTED]" in cleaned
    assert real_shape not in cleaned
    assert "openai_api_key" in matched


def test_scanner_detects_openai_proj_key() -> None:
    """CR-02: ``sk-proj-`` prefix with 64+ chars must also be redacted."""
    proj = "sk-proj-" + ("a" * 64)
    cleaned, matched = _redact_secrets(f"leak: {proj}")
    assert "[REDACTED]" in cleaned
    assert proj not in cleaned
    assert "openai_api_key" in matched


def test_scanner_does_not_match_sk_learn_or_short_sk_tokens() -> None:
    """CR-02 false-positive guard: legitimate ``sk-`` prefixed identifiers
    (e.g. ``sk-learn-...``) and short tokens must NOT be redacted under the
    tightened OpenAI pattern.
    """
    benign_inputs = [
        "package: sk-learn-20240101abcdefghij",  # sk-learn package id
        "short token: sk-abc123def456",  # 12 chars after sk-
        "sk-foo-bar",  # too short, hyphenated
        "sk-" + ("X" * 47),  # one char short of the 48-char threshold
    ]
    for line in benign_inputs:
        cleaned, matched = _redact_secrets(line)
        assert "openai_api_key" not in matched, f"false positive on {line!r}"
        assert "[REDACTED]" not in cleaned, f"unexpected redaction on {line!r}"


def test_scanner_redacts_full_pem_private_key_body() -> None:
    """CR-01 (Phase 13 review): the PEM detector must redact the entire
    block (header + base64 body + footer), not just the BEGIN line.
    """
    pem = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEAvR8L0pK7nC9VgN4xZ1JwGd9bP+UQ0sGmBcYbE5sL3oXg+0nF\n"
        "abCDefGHijKLmnOPqrSTuvWXyz0123456789ABCDEFGHIJKLmnopqrstuvwxyzAB\n"
        "-----END RSA PRIVATE KEY-----"
    )
    cleaned, matched = _redact_secrets(f"key dump:\n{pem}\n")
    assert "pem_private_key" in matched
    assert "[REDACTED]" in cleaned
    # Body and footer must be gone — not only the BEGIN header line.
    assert "-----END" not in cleaned
    assert "MIIEowIBAAKCAQEAvR8L0pK7nC9VgN4xZ1JwGd9bP" not in cleaned
    assert "abCDefGHijKLmnOPqrSTuvWXyz" not in cleaned


def test_scanner_redact_mode() -> None:
    annotations = [
        {
            "id": "a1",
            "notes": "GitHub token ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        }
    ]
    cleaned, findings = scan_annotations_for_secrets(
        annotations, mode="redact"
    )
    assert "[REDACTED]" in cleaned[0]["notes"]
    assert "ghp_" not in cleaned[0]["notes"]
    assert len(findings) == 1
    assert findings[0]["id"] == "a1"
    assert findings[0]["field"] == "notes"
    assert findings[0]["patterns"] == ["github_pat"]


def test_scanner_error_mode_exits_nonzero() -> None:
    annotations = [
        {
            "id": "a1",
            "notes": "GitHub token ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        }
    ]
    with pytest.raises(ValueError) as exc:
        scan_annotations_for_secrets(annotations, mode="error")
    assert "a1" in str(exc.value)
    assert "secret patterns detected" in str(exc.value)


def test_scanner_skips_allowlist_fields() -> None:
    # Allow-list fields are never scanned — changing them would break
    # downstream consumers. sk-* in ``label`` survives untouched.
    dangerous = "sk-SHOULDNOTBESCANNEDBECAUSEALLOWLIST12345"
    annotations = [{"id": "a2", "label": dangerous}]
    cleaned, findings = scan_annotations_for_secrets(
        annotations, mode="redact"
    )
    assert cleaned[0]["label"] == dangerous
    assert findings == []


def test_scanner_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="unknown secrets_mode"):
        scan_annotations_for_secrets([], mode="bogus")


def test_include_annotations_flag_invokes_scanner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End-to-end: ``include_annotations=True`` runs the scanner; the
    ``[graphify] harness export: redacted ...`` stderr line is the
    observable side-channel (annotation text is not rendered into the
    current claude.yaml schema bodies by default)."""
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)
    # Overwrite the default fixture with a scanner-matching GitHub PAT so
    # the scanner actually fires (the default fixture's ``sk-LEAK`` is too
    # short to match the 20+ char OpenAI pattern — intentional: the default
    # allow-list path is tested separately).
    (out_dir / "annotations.jsonl").write_text(
        json.dumps(
            {
                "id": "transformer",
                "label": "Transformer",
                "notes": "leaked: ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    export_claude_harness(
        out_dir, include_annotations=True, secrets_mode="redact"
    )
    captured = capsys.readouterr()
    assert "redacted" in captured.err
    # Even though the scanner runs, the schema bodies never embed annotation
    # text, so the MD files should not contain the original secret either.
    for fname in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md"):
        md = (out_dir / "harness" / fname).read_text(encoding="utf-8")
        assert "ghp_abcdefghijklmnopqrstuvwxyz0123456789" not in md


def test_cli_include_annotations_error_mode_exits_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--secrets-mode error`` with a GitHub PAT annotation exits code 3
    and emits a ``[graphify]``-prefixed stderr line."""
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)
    # Overwrite the annotations file with a known-bad GitHub PAT.
    (out_dir / "annotations.jsonl").write_text(
        json.dumps(
            {
                "id": "a1",
                "label": "N",
                "notes": "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "graphify",
            "harness",
            "export",
            "--out",
            str(out_dir),
            "--include-annotations",
            "--secrets-mode",
            "error",
        ],
    )
    from graphify import __main__ as g_main

    with pytest.raises(SystemExit) as exc:
        g_main.main()
    assert exc.value.code == 3


# ---------------------------------------------------------------------------
# HARNESS-08 / T-13-08: round-trip fidelity manifest (Plan 04)
# ---------------------------------------------------------------------------


def test_fidelity_manifest_written(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)
    export_claude_harness(out_dir, _clock=_frozen_clock)

    fidelity_path = out_dir / "harness" / "fidelity.json"
    assert fidelity_path.exists()
    data = json.loads(fidelity_path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"version", "target", "round_trip", "files"}
    assert data["version"] == 1
    assert data["target"] == "claude"
    assert data["round_trip"] == "first-export"
    assert set(data["files"].keys()) == {
        "claude-SOUL.md",
        "claude-HEARTBEAT.md",
        "claude-USER.md",
    }
    # Each entry records a 64-char hex SHA-256 + positive byte count.
    for meta in data["files"].values():
        assert isinstance(meta["sha256"], str) and len(meta["sha256"]) == 64
        assert isinstance(meta["bytes"], int) and meta["bytes"] > 0


def test_round_trip_byte_equal_with_frozen_clock(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    export_claude_harness(out_dir, _clock=_frozen_clock)
    first_bytes = {
        name: (out_dir / "harness" / name).read_bytes()
        for name in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md")
    }

    export_claude_harness(out_dir, _clock=_frozen_clock)

    fidelity = json.loads(
        (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
    )
    assert fidelity["round_trip"] == "byte-equal"

    second_bytes = {
        name: (out_dir / "harness" / name).read_bytes()
        for name in ("claude-SOUL.md", "claude-HEARTBEAT.md", "claude-USER.md")
    }
    for name in first_bytes:
        assert first_bytes[name] == second_bytes[name], (
            f"byte-equality broken for {name}"
        )
        # SHA-256 recorded in fidelity matches a fresh hash of on-disk bytes.
        fresh = _sha256_file(out_dir / "harness" / name)
        assert fidelity["files"][name]["sha256"] == fresh


def test_round_trip_drift_detected_when_schema_changes(
    tmp_path: Path,
) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)
    export_claude_harness(out_dir, _clock=_frozen_clock)

    # Simulate drift: the second export uses a different pinned clock, which
    # flows into ``generated_at`` and changes the rendered output bytes.
    # HARNESS-08's job is to catch this — the per-file SHA-256 will not
    # match the prior manifest, flipping ``round_trip`` to ``"drift"``.
    other_clock = lambda: datetime(
        2030, 6, 15, 12, 0, 0, tzinfo=timezone.utc
    )
    export_claude_harness(out_dir, _clock=other_clock)

    fidelity = json.loads(
        (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
    )
    assert fidelity["round_trip"] == "drift"


def test_clock_seam_overridable(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    # The rendered SOUL template currently references ${generated_at} — we
    # don't assert a specific string in the body (schema may evolve), but we
    # do assert that the fidelity manifest's sha256 for SOUL changes when the
    # clock output changes (proving the seam wires through).
    export_claude_harness(
        out_dir,
        _clock=lambda: datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    fidelity_a = json.loads(
        (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
    )
    sha_a = fidelity_a["files"]["claude-SOUL.md"]["sha256"]

    # Use a different pinned clock; wipe the prior fidelity so the second run
    # treats itself as a fresh export.
    (out_dir / "harness" / "fidelity.json").unlink()
    export_claude_harness(
        out_dir,
        _clock=lambda: datetime(2030, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    fidelity_b = json.loads(
        (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
    )
    sha_b = fidelity_b["files"]["claude-SOUL.md"]["sha256"]
    assert sha_a != sha_b, "clock seam did not flow through to rendered output"


def test_set_clock_module_override(tmp_path: Path) -> None:
    """Module-level ``set_clock`` overrides the default when no kwarg given."""
    out_dir = tmp_path / "out"
    _copy_fixtures(out_dir)

    fixed = datetime(2026, 4, 17, 22, 30, 0, tzinfo=timezone.utc)
    import graphify.harness_export as he

    prior = he._default_clock
    try:
        set_clock(lambda: fixed)
        export_claude_harness(out_dir)  # no _clock kwarg — uses module override
        fidelity_a = json.loads(
            (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
        )
        sha_a = fidelity_a["files"]["claude-SOUL.md"]["sha256"]

        # Wipe fidelity + rerun with the same override — must be byte-equal.
        (out_dir / "harness" / "fidelity.json").unlink()
        export_claude_harness(out_dir)
        fidelity_b = json.loads(
            (out_dir / "harness" / "fidelity.json").read_text(encoding="utf-8")
        )
        assert fidelity_b["round_trip"] in {"first-export"}  # fidelity wiped
        assert fidelity_b["files"]["claude-SOUL.md"]["sha256"] == sha_a
    finally:
        # Restore the default clock so later tests / session state is clean.
        set_clock(prior)
