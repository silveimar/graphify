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


def _make_update_vault_fixture(
    tmp_path: Path,
    *,
    raw_name: str = "raw",
    output_mode: str = "vault-relative",
    output_path: str = "Atlas/Sources/Graphify",
) -> tuple[Path, Path]:
    raw = tmp_path / "work-vault" / raw_name
    raw.mkdir(parents=True)
    (raw / "alpha.py").write_text(
        "class Alpha:\n"
        "    def compute(self):\n"
        "        return 1\n",
        encoding="utf-8",
    )

    vault = _make_vault(tmp_path)
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
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
        "  min_community_size: 1\n"
        "repo:\n"
        "  identity: graphify\n"
        "output:\n"
        f"  mode: {output_mode}\n"
        f"  path: {output_path}\n",
        encoding="utf-8",
    )
    return raw, vault


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


def test_update_vault_rejects_stale_plan_id(tmp_path):
    """D-14/MIG-01/MIG-04: apply validates the reviewed plan against the current preview before writes."""
    from graphify.migration import run_update_vault

    raw, vault = _make_update_vault_fixture(tmp_path)
    preview_result = run_update_vault(input_dir=raw, vault_dir=vault)
    plan_id = preview_result["preview"]["plan_id"]
    stale_raw = tmp_path / "work-vault" / "stale-raw"
    stale_raw.mkdir(parents=True)
    (stale_raw / "beta.py").write_text("def beta():\n    return 2\n", encoding="utf-8")

    before_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    try:
        run_update_vault(
            input_dir=stale_raw,
            vault_dir=vault,
            apply=True,
            plan_id=plan_id,
        )
    except ValueError as exc:
        assert "stale or mismatched migration plan" in str(exc)
    else:
        raise AssertionError("stale migration plan should be rejected")
    after_vault_files = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    assert after_vault_files == before_vault_files


def test_update_vault_profile_output_outside_vault_previews_and_applies(tmp_path):
    """MIG-01/MIG-04: update-vault honors profile-routed notes outside the vault root."""
    from graphify.migration import run_update_vault

    for mode in ("absolute", "sibling-of-vault"):
        case_root = tmp_path / mode
        case_root.mkdir()
        notes_dir = case_root / f"{mode}-notes"
        raw, vault = _make_update_vault_fixture(
            case_root,
            raw_name=f"raw-{mode}",
            output_mode=mode,
            output_path=str(notes_dir) if mode == "absolute" else notes_dir.name,
        )

        preview_result = run_update_vault(input_dir=raw, vault_dir=vault)
        preview = preview_result["preview"]
        plan_id = preview["plan_id"]

        assert preview_result["applied"] is False
        assert preview["vault"] == str(vault.resolve())
        assert all(not Path(row["path"]).is_absolute() for row in preview["actions"])
        assert not list(notes_dir.rglob("*.md"))

        apply_result = run_update_vault(
            input_dir=raw,
            vault_dir=vault,
            apply=True,
            plan_id=plan_id,
        )

        assert apply_result["applied"] is True
        assert apply_result["result"].failed == []
        assert list(notes_dir.rglob("*.md"))


def test_repo_identity_drift_becomes_skip_conflict(tmp_path):
    """D-18/REPO-04: concrete existing repo drift is visible as SKIP_CONFLICT evidence."""
    from graphify.merge import MergeAction, MergePlan
    from graphify.migration import build_migration_preview

    vault = _make_vault(tmp_path)
    target = vault / "Atlas" / "Sources" / "Graphify" / "CODE_graphify_alpha.md"
    target.write_text(
        "---\n"
        "graphify_managed: true\n"
        "type: code\n"
        "repo: other-repo\n"
        "---\n"
        "# Alpha\n",
        encoding="utf-8",
    )
    rel = target.relative_to(vault).as_posix()
    manifest = {
        rel: {
            "content_hash": "stale",
            "target_path": rel,
            "node_id": "alpha",
            "note_type": "code",
            "repo_identity": "other-repo",
        }
    }
    plan = MergePlan(
        actions=[MergeAction(path=target, action="UPDATE", reason="update")],
        orphans=[],
        summary={"UPDATE": 1},
    )

    preview = build_migration_preview(
        plan,
        input_dir=tmp_path / "work-vault" / "raw",
        vault_dir=vault,
        artifacts_dir=tmp_path / "graphify-out",
        repo_identity="graphify",
        manifest=manifest,
    )

    drift_rows = [
        row for row in preview["actions"]
        if row["path"] == rel and row["action"] == "SKIP_CONFLICT"
    ]
    assert len(drift_rows) == 1
    assert drift_rows[0]["conflict_kind"] == "repo_identity_drift"
    assert drift_rows[0]["existing_repo_identity"] == "other-repo"
    assert drift_rows[0]["repo_identity"] == "graphify"
    assert "repo_identity_drift" in json.dumps(preview, sort_keys=True)
