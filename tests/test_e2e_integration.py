"""E2E subprocess integration tests (Phase 60). Closes v1.11 audit Flow 2/3 gaps."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml
import pytest


# Module-level constants for repeated literals.
_OUTPUT_PATH = "Atlas/Sources/Graphify"
_OVERRIDE_SENTINEL = "OVERRIDE_NTT_THING_MARKER"


def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess.

    Prepends the worktree root to PYTHONPATH so subprocesses pick up the
    in-worktree graphify/ package rather than the editable install. Pops
    GRAPHIFY_ELICIT_LLM defensively to keep maybe_deepen_session deterministic.
    """
    full_env = os.environ.copy()
    worktree_root = Path(__file__).resolve().parent.parent  # tests/ -> repo root
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
    full_env.pop("GRAPHIFY_ELICIT_LLM", None)
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _read_frontmatter(p: Path) -> dict:
    """Parse YAML frontmatter from a markdown file. Returns {} if no frontmatter."""
    text = p.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    _, fm, _ = text.split("---\n", 2)
    return yaml.safe_load(fm) or {}


def _write_vault(
    tmp_path: Path,
    profile_yaml: str,
    *,
    templates: dict[str, str] | None = None,
) -> Path:
    """Create a tmp_path/vault directory with .obsidian/, .graphify/profile.yaml, and optional templates.

    The .obsidian directory MUST be created before profile.yaml is written so the
    update-vault precondition (`target vault must contain .obsidian`) is satisfied.
    """
    vault = tmp_path / "vault"
    # Pitfall 1: .obsidian must exist as a directory BEFORE profile.yaml.
    (vault / ".obsidian").mkdir(parents=True, exist_ok=True)
    graphify_dir = vault / ".graphify"
    graphify_dir.mkdir(parents=True, exist_ok=True)
    (graphify_dir / "profile.yaml").write_text(profile_yaml, encoding="utf-8")
    if templates:
        for rel_path, content in templates.items():
            target = graphify_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    return vault


def _write_corpus(tmp_path: Path) -> Path:
    """Write a fixed 2-class Python corpus as a sibling of the vault."""
    corpus = tmp_path / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / "sample.py").write_text(
        textwrap.dedent(
            """
            class TransformerLayer:
                def __init__(self, dim):
                    self.dim = dim
                def forward(self, x):
                    return x

            class AttentionHead:
                def attend(self, x):
                    return x
            """
        ).lstrip(),
        encoding="utf-8",
    )
    return corpus


def _run_update_vault_preview_then_apply(corpus: Path, vault: Path) -> Path:
    """Run `graphify update-vault` twice (preview, then --apply --plan-id <id>).

    Returns the resolved output root inside the vault (where notes are materialized).
    """
    # Call 1: preview only — writes migration plan JSON.
    preview_result = _graphify(
        ["update-vault", "--input", str(corpus), "--vault", str(vault)],
        cwd=vault.parent,
    )
    assert preview_result.returncode == 0, (
        f"preview failed: stderr={preview_result.stderr!r} stdout={preview_result.stdout!r}"
    )

    # artifacts_dir for a vault run = <vault>.parent / graphify-out (D-11).
    migrations_dir = vault.parent / "graphify-out" / "migrations"
    plan_files = sorted(migrations_dir.glob("migration-plan-*.json"))
    assert len(plan_files) == 1, (
        f"expected exactly one migration plan json, found {len(plan_files)}: {plan_files}"
    )
    plan_data = json.loads(plan_files[0].read_text(encoding="utf-8"))
    plan_id = plan_data["plan_id"]

    # Call 2: apply with the harvested plan_id.
    apply_result = _graphify(
        [
            "update-vault",
            "--input", str(corpus),
            "--vault", str(vault),
            "--apply",
            "--plan-id", plan_id,
        ],
        cwd=vault.parent,
    )
    assert apply_result.returncode == 0, (
        f"apply failed: stderr={apply_result.stderr!r} stdout={apply_result.stdout!r}"
    )

    return vault / "Atlas" / "Sources" / "Graphify"


# -- E2E-01 ---------------------------------------------------------------

_PROFILE_YAML_E2E_01 = textwrap.dedent(
    f"""\
    output:
      mode: vault-relative
      path: {_OUTPUT_PATH}
    taxonomy:
      version: v1.8
      root: {_OUTPUT_PATH}
      folders:
        moc: MOCs
        thing: Things
        statement: Statements
        person: People
        source: Sources
        default: Things
        unclassified: MOCs
    mapping:
      min_community_size: 1
    naming:
      convention: kebab-case
    mapping_rule_templates:
      - match: rule_id
        pattern: e2e-test-rule
        template: templates/mrt-rule.md
    note_type_templates:
      - match: note_type
        pattern: thing
        template: templates/ntt-thing.md
    """
)

_NTT_THING_TEMPLATE = textwrap.dedent(
    """\
    ${frontmatter}
    # OVERRIDE_NTT_THING_MARKER: ${label}

    {{#if_note_type_thing}}NTT_BLOCK_RAN{{/if}}

    {{#connections}}
    - ${conn.label} via ${conn.relation}
    {{/connections}}
    """
)

_MRT_RULE_TEMPLATE = textwrap.dedent(
    """\
    ${frontmatter}
    # MRT_RULE_MATCHED: ${label}
    """
)


def test_e2e_compose_override_ladder(tmp_path: Path) -> None:
    """E2E-01: profile composing note_type_templates + mapping_rule_templates produces
    correctly-classified notes through the real CLI subprocess pipeline.

    Asserts:
      - update-vault preview + apply both exit 0
      - note materialized under <vault>/Atlas/Sources/Graphify/
      - body contains override sentinel (proves ntt selected over base)
      - body shows expanded {{#…}} block AND substituted ${} placeholders
        (proves D-16 ordering: block expansion BEFORE substitution)
      - mapping_rule_templates does NOT shadow ntt when its pattern doesn't match
      - frontmatter has type=thing, community/* tag, non-empty community,
        and cohesion is absent (cohesion is moc/community-only)
    """
    vault = _write_vault(
        tmp_path,
        _PROFILE_YAML_E2E_01,
        templates={
            "templates/ntt-thing.md": _NTT_THING_TEMPLATE,
            "templates/mrt-rule.md": _MRT_RULE_TEMPLATE,
        },
    )
    corpus = _write_corpus(tmp_path)

    output_root = _run_update_vault_preview_then_apply(corpus, vault)
    assert output_root.exists(), f"output root not materialized: {output_root}"

    # Find all rendered notes whose frontmatter parses with type=thing.
    md_files = list(output_root.rglob("*.md"))
    assert md_files, f"no markdown files found under {output_root}"
    thing_notes = [p for p in md_files if _read_frontmatter(p).get("type") == "thing"]
    assert len(thing_notes) >= 1, (
        f"expected >=1 note with type=thing, found {len(thing_notes)}; "
        f"all notes: {[(p.relative_to(output_root), _read_frontmatter(p).get('type')) for p in md_files]}"
    )

    note = thing_notes[0]
    body = note.read_text(encoding="utf-8")

    # Body assertions: ntt template was selected and D-16 ordering held.
    assert _OVERRIDE_SENTINEL in body, (
        f"sentinel {_OVERRIDE_SENTINEL!r} missing from body of {note}; body={body!r}"
    )
    assert "NTT_BLOCK_RAN" in body, f"block expansion did not run; body={body!r}"
    assert " via " in body, f"connections block did not expand with relation; body={body!r}"
    assert "${label}" not in body, f"raw ${{label}} placeholder remains in body; body={body!r}"
    assert "${conn.label}" not in body, (
        f"raw ${{conn.label}} placeholder remains in body; body={body!r}"
    )
    assert "MRT_RULE_MATCHED" not in body, (
        f"mapping_rule_templates incorrectly shadowed ntt; body={body!r}"
    )

    # Frontmatter assertions: contract surface for ladder resolution.
    fm = _read_frontmatter(note)
    assert fm.get("type") == "thing", f"frontmatter type != thing: {fm!r}"
    tags = fm.get("tags") or []
    assert any(isinstance(t, str) and t.startswith("community/") for t in tags), (
        f"no community/* tag in {tags!r}"
    )
    community = fm.get("community")
    assert isinstance(community, str) and community, (
        f"community must be a non-empty string, got {community!r}"
    )
    assert "cohesion" not in fm, (
        f"cohesion must be absent for type=thing notes; got {fm!r}"
    )
