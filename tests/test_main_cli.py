"""Phase 5 gap-closure (plan 06) — CLI integration tests for the new top-level
flags added to graphify/__main__.py: --validate-profile and --obsidian.

These tests exercise the real entrypoint via `python -m graphify ...` so they
catch regressions in argv parsing, exit codes, stdout/stderr routing, and the
thin wiring over validate_profile_preflight / to_obsidian / format_merge_plan.

Conventions (matching tests/test_integration.py + tests/test_install.py):
  - Pure, tmp_path only, no network
  - subprocess.run with check=False so we can assert on exit codes
  - Assertions use substring matching, not exact equality, so the em-dash
    formatter (U+2014) stays out of the test source
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke `python -m graphify <args...>` and return the completed process.

    Uses check=False so the caller owns exit-code assertions.
    """
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_fixture_graph_json(path: Path) -> None:
    """Build a minimal 4-node / 2-community graph and write it to `path`
    via the real graphify.export.to_json so the community attribute shape
    matches production.
    """
    from graphify.export import to_json

    G = nx.Graph()
    G.add_node("n1", label="Transformer", file_type="code", source_file="model.py")
    G.add_node("n2", label="Attention", file_type="code", source_file="model.py")
    G.add_node("n3", label="LayerNorm", file_type="code", source_file="model.py")
    G.add_node("n4", label="SGD Optimizer", file_type="code", source_file="train.py")
    G.add_edge("n1", "n2", relation="contains", confidence="EXTRACTED", source_file="model.py", weight=1.0)
    G.add_edge("n1", "n3", relation="contains", confidence="EXTRACTED", source_file="model.py", weight=1.0)
    G.add_edge("n2", "n3", relation="uses", confidence="EXTRACTED", source_file="model.py", weight=1.0)
    communities = {0: ["n1", "n2", "n3"], 1: ["n4"]}
    path.parent.mkdir(parents=True, exist_ok=True)
    to_json(G, communities, str(path))


# ---------------------------------------------------------------------------
# --validate-profile branch (PROF-05)
# ---------------------------------------------------------------------------

def test_validate_profile_missing_path_exits_1(tmp_path):
    missing = tmp_path / "does_not_exist"
    result = _run_cli("--validate-profile", str(missing))
    assert result.returncode == 1, f"stderr={result.stderr}"
    assert "vault_dir does not exist" in result.stderr


def test_validate_profile_empty_vault_exits_0(tmp_path):
    # tmp_path is an empty directory with no .graphify/ subdir —
    # validate_profile_preflight short-circuits to (errors=[], warnings=[], 0, 0)
    result = _run_cli("--validate-profile", str(tmp_path))
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "profile ok" in result.stdout
    assert "0 rules" in result.stdout
    assert "0 templates validated" in result.stdout


def test_validate_profile_no_arg_exits_2(tmp_path):
    result = _run_cli("--validate-profile")
    assert result.returncode == 2
    assert "Usage" in result.stderr
    assert "--validate-profile" in result.stderr


def test_validate_profile_file_not_dir_exits_1(tmp_path):
    f = tmp_path / "not_a_dir.txt"
    f.write_text("hello", encoding="utf-8")
    result = _run_cli("--validate-profile", str(f))
    assert result.returncode == 1
    assert "vault_dir is not a directory" in result.stderr


# ---------------------------------------------------------------------------
# --obsidian branch (MRG-03 dry-run + MRG-05 default-profile full-run)
# ---------------------------------------------------------------------------

def test_obsidian_dry_run_prints_plan_and_writes_nothing(tmp_path):
    graph_path = tmp_path / "graph.json"
    _write_fixture_graph_json(graph_path)
    vault = tmp_path / "obsidian_out"

    result = _run_cli(
        "--obsidian",
        "--dry-run",
        "--graph", str(graph_path),
        "--obsidian-dir", str(vault),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    # format_merge_plan header + at least one group label
    assert "Merge Plan" in result.stdout
    assert "CREATE" in result.stdout
    # --dry-run MUST NOT write any .md files. vault may be auto-created (exists)
    # by to_obsidian's `out.mkdir(parents=True, exist_ok=True)` at export.py L479,
    # but no file content should be emitted.
    md_files = list(vault.rglob("*.md")) if vault.exists() else []
    assert md_files == [], f"dry-run wrote {len(md_files)} .md files: {md_files}"


def test_obsidian_full_run_writes_atlas_files(tmp_path):
    graph_path = tmp_path / "graph.json"
    _write_fixture_graph_json(graph_path)
    vault = tmp_path / "obsidian_out"

    result = _run_cli(
        "--obsidian",
        "--graph", str(graph_path),
        "--obsidian-dir", str(vault),
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "wrote obsidian vault" in result.stdout

    # Default profile produces Atlas/-shaped output (Ideaverse ACE, per D-15
    # in graphify/profile.py::_DEFAULT_PROFILE). At minimum there should be
    # at least one .md file somewhere under Atlas/.
    atlas_dir = vault / "Atlas"
    assert atlas_dir.exists(), (
        f"no Atlas/ subdir in {vault}; "
        f"contents: {list(vault.iterdir()) if vault.exists() else 'vault missing'}"
    )
    md_files = list(atlas_dir.rglob("*.md"))
    assert len(md_files) >= 1, f"Atlas/ has no .md files; rglob found: {md_files}"


def test_obsidian_missing_graph_file_exits_1(tmp_path):
    missing = tmp_path / "no_such_graph.json"
    result = _run_cli(
        "--obsidian",
        "--graph", str(missing),
    )
    assert result.returncode == 1
    assert "graph file not found" in result.stderr


def test_obsidian_bad_graph_suffix_exits_1(tmp_path):
    bogus = tmp_path / "graph.txt"
    bogus.write_text("{}", encoding="utf-8")
    result = _run_cli(
        "--obsidian",
        "--graph", str(bogus),
    )
    assert result.returncode == 1
    assert "must be a .json file" in result.stderr


def test_obsidian_unknown_option_exits_2(tmp_path):
    result = _run_cli("--obsidian", "--frobnicate")
    assert result.returncode == 2
    assert "unknown --obsidian option" in result.stderr


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

def test_help_mentions_new_flags():
    result = _run_cli()  # no args → help path
    assert result.returncode == 0
    assert "--validate-profile" in result.stdout
    assert "--obsidian" in result.stdout
    assert "--dry-run" in result.stdout


# ---------------------------------------------------------------------------
# --dedup branch (Phase 10, GRAPH-02/03, D-14, D-17, T-10-04)
# ---------------------------------------------------------------------------

def _run_cli_in(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Invoke `python -m graphify <args...>` with a specific working directory.

    Passes the project root on PYTHONPATH so the local graphify package is
    used even when cwd is a tmp_path outside the project tree.
    """
    import os
    env = os.environ.copy()
    # Project root is two levels up from this test file (tests/../)
    project_root = str(Path(__file__).parent.parent.resolve())
    existing_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{project_root}:{existing_path}" if existing_path else project_root
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
        env=env,
    )


def test_help_lists_dedup_flags():
    """--help must list --dedup and its sub-flags (Phase 10 D-14, D-17)."""
    result = _run_cli()  # no args → help path
    assert result.returncode == 0
    out = result.stdout
    assert "--dedup" in out
    assert "--dedup-fuzzy-threshold" in out
    assert "--dedup-embed-threshold" in out
    assert "--dedup-cross-type" in out
    assert "--batch-token-budget" in out


def test_dedup_missing_source_errors_cleanly(tmp_path):
    """`graphify --dedup` with no extraction.json exits 1 with a readable error."""
    (tmp_path / "graphify-out").mkdir()
    result = _run_cli_in("--dedup", cwd=tmp_path)
    assert result.returncode == 1
    assert "no extraction.json or graph.json found" in result.stderr


def test_dedup_unknown_flag_exits_2(tmp_path):
    """Bad flag exits with code 2 per CLI convention."""
    (tmp_path / "graphify-out").mkdir()
    # Seed a minimal extraction.json so arg parsing runs before source lookup
    (tmp_path / "graphify-out" / "extraction.json").write_text(
        json.dumps({"nodes": [], "edges": []}), encoding="utf-8",
    )
    result = _run_cli_in("--dedup", "--nope", cwd=tmp_path)
    assert result.returncode == 2
    assert "unknown --dedup option" in result.stderr


def test_dedup_reads_empty_extraction(tmp_path):
    """`--dedup` on an empty extraction.json succeeds, writes a 0-merge report."""
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "extraction.json").write_text(
        json.dumps({"nodes": [], "edges": []}), encoding="utf-8",
    )
    result = _run_cli_in("--dedup", cwd=tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    report = json.loads((tmp_path / "graphify-out" / "dedup_report.json").read_text())
    assert report["summary"]["merges"] == 0


def test_dedup_yaml_config_respected(tmp_path):
    """D-17: .graphify/dedup.yaml values are loaded; CLI flags override."""
    import textwrap
    pytest.importorskip("yaml", reason="PyYAML required for this test")
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "extraction.json").write_text(
        json.dumps({"nodes": [], "edges": []}), encoding="utf-8",
    )
    (tmp_path / ".graphify").mkdir()
    (tmp_path / ".graphify" / "dedup.yaml").write_text(textwrap.dedent("""\
        fuzzy_threshold: 0.95
        embed_threshold: 0.88
        cross_type: true
    """), encoding="utf-8")
    result = _run_cli_in("--dedup", cwd=tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Stderr line echoes the effective thresholds
    assert "fuzzy>=0.95" in result.stderr
    assert "cos>=0.88" in result.stderr
    assert "cross_type=True" in result.stderr


def test_dedup_yaml_safe_load_only():
    """T-10-04: verify yaml.load (unsafe) is NOT called anywhere in __main__.py.

    Dedup YAML loading must use yaml.safe_load exclusively to prevent
    arbitrary-code-execution via PyYAML tag injection. Only actual call
    sites (followed by '(') are flagged — docstring references are excluded.
    """
    import re
    content = Path("graphify/__main__.py").read_text(encoding="utf-8")
    # Match yaml.load( but NOT yaml.safe_load( and NOT yaml.load_all(
    forbidden = re.findall(r"\byaml\.load\(", content)
    assert not forbidden, "yaml.load( call found in __main__.py — must use yaml.safe_load (T-10-04)"


def test_no_unsafe_yaml_load_in_any_module():
    """T-10-04: graphify/dedup.py and graphify/__main__.py must not call yaml.load (unsafe)."""
    import re
    for mod_path in ["graphify/dedup.py", "graphify/__main__.py"]:
        content = Path(mod_path).read_text(encoding="utf-8")
        # Match yaml.load( but NOT yaml.safe_load( and NOT yaml.load_all(
        forbidden = re.findall(r"\byaml\.load\(", content)
        assert not forbidden, f"yaml.load( call found in {mod_path} — use yaml.safe_load (T-10-04)"
