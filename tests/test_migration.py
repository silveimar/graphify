"""Unit tests for migration preview helpers (Phase 35 Plan 01)."""
from __future__ import annotations

import json
from pathlib import Path


def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "ls-vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / "Atlas" / "Sources" / "Graphify" / "MOCs").mkdir(parents=True)
    return vault


def _write_legacy_community(vault: Path, community_id: int = 12) -> Path:
    legacy = vault / "Atlas" / "Sources" / "Graphify" / "MOCs" / f"_COMMUNITY_{community_id}.md"
    legacy.write_text(
        "---\n"
        "graphify_managed: true\n"
        "type: community\n"
        f"community: {community_id}\n"
        "---\n"
        f"# Legacy Community {community_id}\n"
        "<!-- graphify:metadata:start -->\n"
        "legacy graphify fingerprint\n"
        "<!-- graphify:metadata:end -->\n",
        encoding="utf-8",
    )
    return legacy


def _plan_with_actions(vault: Path):
    from graphify.merge import MergeAction, MergePlan

    actions = [
        MergeAction(
            path=vault / "Atlas" / "Sources" / "Graphify" / "MOCs" / "Community_12.md",
            action="UPDATE",
            reason="canonical v1.8 MOC target",
            changed_fields=["tags"],
        ),
        MergeAction(
            path=vault / "Atlas" / "Sources" / "Graphify" / "MOCs" / "New.md",
            action="CREATE",
            reason="new file",
        ),
    ]
    return MergePlan(
        actions=actions,
        orphans=[],
        summary={"UPDATE": 1, "CREATE": 1},
    )


def _manifest_for_community(legacy: Path, vault: Path) -> dict[str, dict]:
    rel = legacy.relative_to(vault).as_posix()
    return {
        rel: {
            "content_hash": "legacy-hash",
            "target_path": rel,
            "node_id": "_moc_12",
            "note_type": "community",
            "community_id": 12,
            "has_user_blocks": False,
        }
    }


def test_legacy_community_files_surface_as_orphans(tmp_path):
    """D-06/D-08/COMM-02: unmatched _COMMUNITY_* files surface as review-only ORPHAN rows."""
    from graphify.merge import MergePlan
    from graphify.migration import build_migration_preview

    vault = _make_vault(tmp_path)
    legacy = _write_legacy_community(vault)
    plan = MergePlan(actions=[], orphans=[], summary={})

    preview = build_migration_preview(
        plan,
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=tmp_path / "graphify-out",
        repo_identity="graphify",
    )

    orphan_rows = [
        row for row in preview["actions"]
        if row["action"] == "ORPHAN" and row["path"] == legacy.relative_to(vault).as_posix()
    ]
    assert len(orphan_rows) == 1, "D-06/D-08/COMM-02 legacy community file must not be ignored"
    assert orphan_rows[0]["review_only"] is True, "D-08 ORPHAN rows must be review-only"


def test_preview_writes_artifacts_but_no_vault_notes(tmp_path):
    """D-11/MIG-02: preview persists JSON/Markdown artifacts without touching vault notes."""
    from graphify.migration import build_migration_preview, write_migration_artifacts

    vault = _make_vault(tmp_path)
    artifacts_dir = tmp_path / "graphify-out"
    manifest_path = artifacts_dir / "vault-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps({"before": {"content_hash": "unchanged"}}), encoding="utf-8")
    before_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    before_manifest = manifest_path.read_text(encoding="utf-8")

    preview = build_migration_preview(
        _plan_with_actions(vault),
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=artifacts_dir,
        repo_identity="graphify",
    )
    json_path, md_path = write_migration_artifacts(preview, artifacts_dir)

    assert json_path == artifacts_dir / "migrations" / f"migration-plan-{preview['plan_id']}.json"
    assert md_path == artifacts_dir / "migrations" / f"migration-plan-{preview['plan_id']}.md"
    assert json_path.exists()
    assert md_path.exists()
    after_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    assert after_vault_files == before_vault_files, "MIG-02 preview must not create vault Markdown notes"
    assert manifest_path.read_text(encoding="utf-8") == before_manifest, "MIG-02 preview must not mutate vault-manifest.json"


def test_legacy_manifest_identity_maps_old_path_to_new_path(tmp_path):
    """D-07/D-09/MIG-03: manifest community identity maps old paths to canonical v1.8 targets."""
    from graphify.migration import build_migration_preview, format_migration_preview

    vault = _make_vault(tmp_path)
    legacy = _write_legacy_community(vault)
    manifest = _manifest_for_community(legacy, vault)

    preview = build_migration_preview(
        _plan_with_actions(vault),
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=tmp_path / "graphify-out",
        repo_identity="graphify",
        manifest=manifest,
    )
    mapping = preview["legacy_mappings"][0]

    assert mapping["old_path"] == "Atlas/Sources/Graphify/MOCs/_COMMUNITY_12.md"
    assert mapping["new_path"] == "Atlas/Sources/Graphify/MOCs/Community_12.md"
    assert mapping["identity_source"] == "manifest"
    assert mapping["legacy_action"] == "ORPHAN"
    assert mapping["canonical_action"] == "UPDATE"
    rendered = format_migration_preview(preview)
    assert mapping["old_path"] in json.dumps(preview, sort_keys=True)
    assert mapping["new_path"] in json.dumps(preview, sort_keys=True)
    assert mapping["old_path"] in rendered
    assert mapping["new_path"] in rendered


def test_preview_expands_risky_action_rows(tmp_path):
    """D-10/D-12/D-13/MIG-04: risky rows expand; CREATE/UPDATE summarize by default."""
    from graphify.merge import MergeAction, MergePlan
    from graphify.migration import format_migration_preview, build_migration_preview

    vault = _make_vault(tmp_path)
    actions = []
    for i in range(6):
        actions.append(MergeAction(path=vault / f"Atlas/Sources/Graphify/MOCs/Create_{i}.md", action="CREATE", reason="new"))
        actions.append(MergeAction(path=vault / f"Atlas/Sources/Graphify/MOCs/Update_{i}.md", action="UPDATE", reason="update"))
    actions.extend([
        MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Preserve.md", action="SKIP_PRESERVE", reason="preserve"),
        MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Conflict.md", action="SKIP_CONFLICT", reason="conflict"),
        MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Replace.md", action="REPLACE", reason="replace"),
        MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Orphan.md", action="ORPHAN", reason="orphan"),
    ])
    plan = MergePlan(actions=actions, orphans=[], summary={})
    preview = build_migration_preview(
        plan,
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=tmp_path / "graphify-out",
        repo_identity="graphify",
    )

    compact = format_migration_preview(preview, representative_limit=5)
    verbose = format_migration_preview(preview, verbose=True)

    for action in ("CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN"):
        assert f"{action}:" in compact, f"MIG-04 preview must show {action} count"
    for risky_name in ("Preserve.md", "Conflict.md", "Replace.md", "Orphan.md"):
        assert risky_name in compact, f"D-13 risky row {risky_name} must be expanded"
    assert "Create_5.md" not in compact, "D-12 CREATE rows should summarize to representatives"
    assert "Update_5.md" not in compact, "D-12 UPDATE rows should summarize to representatives"
    assert "Create_5.md" in verbose and "Update_5.md" in verbose


def test_apply_never_deletes_legacy_orphan_files(tmp_path):
    """D-11/MIG-06: apply filtering excludes ORPHAN/SKIP rows and legacy files remain."""
    from graphify.merge import MergeAction, MergePlan, apply_merge_plan
    from graphify.migration import build_migration_preview, filter_applicable_actions

    vault = _make_vault(tmp_path)
    legacy = _write_legacy_community(vault)
    create_target = vault / "Atlas" / "Sources" / "Graphify" / "MOCs" / "Created.md"
    plan = MergePlan(
        actions=[
            MergeAction(path=create_target, action="CREATE", reason="new"),
            MergeAction(path=legacy, action="ORPHAN", reason="legacy review-only"),
            MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Preserve.md", action="SKIP_PRESERVE", reason="preserve"),
            MergeAction(path=vault / "Atlas/Sources/Graphify/MOCs/Conflict.md", action="SKIP_CONFLICT", reason="conflict"),
        ],
        orphans=[legacy],
        summary={"CREATE": 1, "ORPHAN": 1, "SKIP_PRESERVE": 1, "SKIP_CONFLICT": 1},
    )
    preview = build_migration_preview(
        plan,
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=tmp_path / "graphify-out",
        repo_identity="graphify",
    )

    applicable = filter_applicable_actions(preview)
    assert [row["action"] for row in applicable] == ["CREATE"], "MIG-06 apply helpers must exclude ORPHAN and SKIP rows"
    result = apply_merge_plan(
        plan,
        vault,
        {
            "created": {
                "node_id": "created",
                "target_path": create_target,
                "frontmatter_fields": {"type": "moc", "graphify_managed": True},
                "body": "# Created\n",
            }
        },
        {},
    )

    assert create_target in result.succeeded
    assert legacy.exists(), "MIG-06 legacy _COMMUNITY_* files must never be deleted or moved"
