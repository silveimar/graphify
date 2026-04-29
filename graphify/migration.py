"""Migration preview helpers for review-first Obsidian vault updates."""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

from graphify.merge import MergeAction, MergePlan, split_rendered_note
from graphify.profile import validate_vault_path


MIGRATION_ARTIFACT_DIR = "migrations"
RISKY_ACTIONS = frozenset({"SKIP_CONFLICT", "SKIP_PRESERVE", "ORPHAN", "REPLACE"})
ACTION_ORDER = ("CREATE", "UPDATE", "SKIP_PRESERVE", "SKIP_CONFLICT", "REPLACE", "ORPHAN")

_LEGACY_COMMUNITY_RE = re.compile(r"^_COMMUNITY_(\d+)\.md$", re.IGNORECASE)
_COMMUNITY_ID_RE = re.compile(r"(?:^|[_\-\s])(?:COMMUNITY[_\-\s]?)?(\d+)(?:\.md)?$", re.IGNORECASE)
_PLAN_ID_RE = re.compile(r"^[a-f0-9]{16,64}$")
_NOISE_DIRS = {
    ".git",
    ".obsidian",
    ".graphify",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "graphify-out",
    "graphify_out",
}


def scan_legacy_notes(vault_dir: Path, manifest: dict[str, dict] | None = None) -> list[dict]:
    """Find legacy graphify-managed notes in *vault_dir* without following links."""
    vault = Path(vault_dir).resolve()
    entries: list[dict] = []
    manifest = manifest or {}

    for dirpath, dirnames, filenames in os.walk(vault, followlinks=False):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in _NOISE_DIRS
        ]
        root = Path(dirpath)
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            candidate = root / filename
            try:
                rel_path = candidate.resolve().relative_to(vault)
                safe_path = validate_vault_path(rel_path, vault)
            except (OSError, ValueError):
                continue
            try:
                text = safe_path.read_text(encoding="utf-8")
            except OSError:
                continue
            is_legacy_name = _LEGACY_COMMUNITY_RE.match(filename) is not None
            has_fingerprint = _has_graphify_fingerprint(text)
            if not is_legacy_name and not has_fingerprint:
                continue
            rel = rel_path.as_posix()
            identity, identity_source = _legacy_identity(rel, text, manifest.get(rel))
            entries.append({
                "path": rel,
                "absolute_path": str(safe_path),
                "review_only": True,
                "identity": identity,
                "identity_source": identity_source,
                "legacy_name": is_legacy_name,
            })

    return sorted(entries, key=lambda row: row["path"])


def compute_migration_plan_id(payload: dict) -> str:
    """Return a deterministic SHA-256 digest for a non-volatile preview payload."""
    normalized = _digest_payload(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_migration_preview(
    plan: MergePlan,
    *,
    input_dir: Path,
    vault_dir: Path,
    artifacts_dir: Path,
    repo_identity: str,
    manifest: dict[str, dict] | None = None,
    verbose: bool = False,
) -> dict:
    """Build a JSON-serializable migration preview from a MergePlan."""
    vault = Path(vault_dir).resolve()
    manifest = manifest or {}
    actions = [
        _classify_repo_drift(
            _action_to_row(action, vault, review_only=False),
            vault,
            repo_identity,
            manifest,
        )
        for action in plan.actions
    ]
    legacy_notes = scan_legacy_notes(vault, manifest=manifest)
    canonical_by_identity = _canonical_actions_by_identity(actions)
    existing_paths = {row["path"] for row in actions}
    legacy_mappings: list[dict] = []

    for legacy in legacy_notes:
        canonical = _match_canonical_action(legacy, canonical_by_identity)
        if canonical is not None:
            legacy_mappings.append({
                "old_path": legacy["path"],
                "new_path": canonical["path"],
                "identity_source": legacy["identity_source"],
                "legacy_action": "ORPHAN",
                "canonical_action": canonical["action"],
            })
        if legacy["path"] not in existing_paths:
            actions.append({
                "path": legacy["path"],
                "action": "ORPHAN",
                "reason": "legacy graphify-managed note — review only, never deleted",
                "changed_fields": [],
                "changed_blocks": [],
                "conflict_kind": None,
                "user_modified": False,
                "has_user_blocks": False,
                "source": "graphify",
                "review_only": True,
                "legacy": True,
            })
            existing_paths.add(legacy["path"])

    actions = sorted(actions, key=lambda row: (ACTION_ORDER.index(row["action"]), row["path"]))
    summary = _summary_for(actions)
    preview = {
        "input": str(Path(input_dir).resolve()),
        "vault": str(vault),
        "artifacts_dir": str(Path(artifacts_dir).resolve()),
        "repo_identity": repo_identity,
        "summary": summary,
        "actions": actions,
        "legacy_mappings": sorted(legacy_mappings, key=lambda row: row["old_path"]),
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "review_only_paths": sorted(row["path"] for row in actions if row.get("review_only")),
        "verbose": verbose,
    }
    preview["plan_id"] = compute_migration_plan_id(preview)
    return preview


def run_update_vault(
    *,
    input_dir: Path,
    vault_dir: Path,
    repo_identity: str | None = None,
    apply: bool = False,
    plan_id: str | None = None,
    use_router: bool = False,
    verbose: bool = False,
) -> dict:
    """Run the preview-first raw-corpus to Obsidian vault update workflow."""
    raw = Path(input_dir).resolve()
    vault = Path(vault_dir).resolve()
    if not raw.exists():
        raise ValueError(f"input path not found: {raw}")
    if not (vault / ".obsidian").is_dir():
        raise ValueError(f"target vault must contain .obsidian: {vault}")
    if apply and not plan_id:
        raise ValueError("--apply requires --plan-id from a preview artifact")

    from graphify.build import build
    from graphify.cluster import cluster
    from graphify.export import to_obsidian
    from graphify.merge import _load_manifest
    from graphify.naming import resolve_repo_identity
    from graphify.output import resolve_output
    from graphify.pipeline import run_corpus
    from graphify.profile import load_profile

    resolved = resolve_output(vault)
    profile = load_profile(vault)
    resolved_repo = resolve_repo_identity(
        raw,
        cli_identity=repo_identity,
        profile=profile,
    )

    extraction = run_corpus(
        raw,
        use_router=use_router,
        out_dir=resolved.artifacts_dir,
        resolved=None,
    )
    G = build([extraction])
    communities = cluster(G)
    plan = to_obsidian(
        G,
        communities,
        str(resolved.notes_dir),
        profile=profile,
        repo_identity=resolved_repo.identity,
        dry_run=True,
    )
    manifest_path = resolved.artifacts_dir / "vault-manifest.json"
    manifest = _load_manifest(manifest_path)
    preview = build_migration_preview(
        plan,
        input_dir=raw,
        vault_dir=vault,
        artifacts_dir=resolved.artifacts_dir,
        repo_identity=resolved_repo.identity,
        manifest=manifest,
        verbose=verbose,
    )

    if apply:
        loaded = load_migration_plan(resolved.artifacts_dir, str(plan_id))
        validate_plan_matches_request(
            loaded,
            raw,
            vault,
            resolved_repo.identity,
            current_preview=preview,
        )
        return {
            "preview": loaded,
            "json_path": resolved.artifacts_dir / MIGRATION_ARTIFACT_DIR / f"migration-plan-{plan_id}.json",
            "markdown_path": resolved.artifacts_dir / MIGRATION_ARTIFACT_DIR / f"migration-plan-{plan_id}.md",
            "applied": False,
            "repo_identity": resolved_repo.identity,
        }

    json_path, markdown_path = write_migration_artifacts(preview, resolved.artifacts_dir)
    return {
        "preview": preview,
        "json_path": json_path,
        "markdown_path": markdown_path,
        "applied": False,
        "repo_identity": resolved_repo.identity,
    }


def format_migration_preview(
    preview: dict,
    *,
    verbose: bool = False,
    representative_limit: int = 5,
) -> str:
    """Render migration preview rows for terminal or Markdown review."""
    lines = [f"Migration Preview - repo: {preview.get('repo_identity', '')}"]
    lines.append("=" * 48)
    lines.append(f"Plan ID: {preview.get('plan_id', '')}")
    lines.append(f"Input: {preview.get('input', '')}")
    lines.append(f"Vault: {preview.get('vault', '')}")
    lines.append("")

    summary = preview.get("summary") or {}
    for action in ACTION_ORDER:
        lines.append(f"  {action + ':':<15}{summary.get(action, 0):>3}")
    lines.append("")

    actions = list(preview.get("actions") or [])
    for action in ACTION_ORDER:
        rows = [row for row in actions if row.get("action") == action]
        if not rows:
            continue
        show_all = verbose or action in RISKY_ACTIONS
        shown = rows if show_all else rows[:representative_limit]
        lines.append(f"{action} ({len(rows)})")
        for row in shown:
            suffix = " [review-only]" if row.get("review_only") else ""
            reason = row.get("reason") or ""
            lines.append(f"  {action}  {row.get('path', '')}{suffix} — {reason}")
        hidden = len(rows) - len(shown)
        if hidden > 0:
            lines.append(f"  ... {hidden} more {action} rows (use verbose for all)")
        lines.append("")

    mappings = preview.get("legacy_mappings") or []
    if mappings:
        lines.append("Legacy mappings")
        for mapping in mappings:
            lines.append(
                f"  {mapping['old_path']} -> {mapping['new_path']} "
                f"({mapping['identity_source']}, {mapping['legacy_action']} beside "
                f"{mapping['canonical_action']})"
            )
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def write_migration_artifacts(preview: dict, artifacts_dir: Path) -> tuple[Path, Path]:
    """Persist JSON and Markdown migration artifacts atomically."""
    plan_id = str(preview.get("plan_id", ""))
    _validate_plan_id(plan_id)
    directory = Path(artifacts_dir).resolve() / MIGRATION_ARTIFACT_DIR
    json_path = directory / f"migration-plan-{plan_id}.json"
    markdown_path = directory / f"migration-plan-{plan_id}.md"
    _write_atomic_text(
        json_path,
        json.dumps(preview, indent=2, sort_keys=True) + "\n",
    )
    _write_atomic_text(markdown_path, format_migration_preview(preview))
    return json_path, markdown_path


def load_migration_plan(artifacts_dir: Path, plan_id: str) -> dict:
    """Load and verify a migration plan artifact by digest id."""
    _validate_plan_id(plan_id)
    path = (
        Path(artifacts_dir).resolve()
        / MIGRATION_ARTIFACT_DIR
        / f"migration-plan-{plan_id}.json"
    )
    if not path.exists():
        raise ValueError("migration plan not found")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("invalid migration plan") from exc
    if not isinstance(loaded, dict):
        raise ValueError("invalid migration plan")
    stored_plan_id = str(loaded.get("plan_id", ""))
    recomputed = compute_migration_plan_id(loaded)
    if stored_plan_id != plan_id or recomputed != plan_id:
        raise ValueError("invalid migration plan")
    return loaded


def validate_plan_matches_request(
    preview: dict,
    input_dir: Path,
    vault_dir: Path,
    repo_identity: str,
    *,
    current_preview: dict | None = None,
) -> None:
    """Ensure a loaded migration plan matches the current apply request."""
    if preview.get("input") != str(Path(input_dir).resolve()):
        raise ValueError("stale or mismatched migration plan")
    if preview.get("vault") != str(Path(vault_dir).resolve()):
        raise ValueError("stale or mismatched migration plan")
    if preview.get("repo_identity") != repo_identity:
        raise ValueError("stale or mismatched migration plan")
    plan_id = str(preview.get("plan_id", ""))
    if compute_migration_plan_id(preview) != plan_id:
        raise ValueError("stale or mismatched migration plan")
    if current_preview is not None and plan_id != current_preview.get("plan_id"):
        raise ValueError("stale or mismatched migration plan")


def filter_applicable_actions(preview: dict) -> list[dict]:
    """Return only action rows that an apply step may write."""
    return [
        dict(row) for row in preview.get("actions", [])
        if row.get("action") in {"CREATE", "UPDATE", "REPLACE"}
    ]


def _has_graphify_fingerprint(text: str) -> bool:
    frontmatter, body = split_rendered_note(text)
    return bool(frontmatter.get("graphify_managed")) or "<!-- graphify:" in body


def _legacy_identity(
    rel_path: str,
    text: str,
    manifest_entry: dict | None,
) -> tuple[dict, str]:
    if manifest_entry:
        identity = _identity_from_manifest(manifest_entry)
        if identity:
            return identity, "manifest"

    frontmatter, _ = split_rendered_note(text)
    identity = _identity_from_frontmatter(frontmatter)
    if identity:
        return identity, "frontmatter"

    community_id = _community_id_from_path(rel_path)
    if community_id is not None:
        return {"community_id": community_id}, "filename"
    return {}, "unknown"


def _identity_from_manifest(entry: dict) -> dict:
    if not isinstance(entry, dict):
        return {}
    if entry.get("community_id") is not None:
        return {"community_id": entry.get("community_id")}
    if entry.get("node_id"):
        return {"node_id": entry.get("node_id")}
    return {}


def _identity_from_frontmatter(frontmatter: dict) -> dict:
    if not isinstance(frontmatter, dict):
        return {}
    if frontmatter.get("community") is not None:
        return {"community_id": frontmatter.get("community")}
    if frontmatter.get("node_id"):
        return {"node_id": frontmatter.get("node_id")}
    return {}


def _action_to_row(action: MergeAction, vault: Path, *, review_only: bool) -> dict:
    path = _display_path(action.path, vault)
    row = {
        "path": path,
        "action": action.action,
        "reason": action.reason,
        "changed_fields": list(action.changed_fields),
        "changed_blocks": list(action.changed_blocks),
        "conflict_kind": action.conflict_kind,
        "user_modified": action.user_modified,
        "has_user_blocks": action.has_user_blocks,
        "source": action.source,
        "review_only": review_only,
        "legacy": False,
    }
    if Path(path).name.startswith("CODE_"):
        row["repo_identity"] = None
    return row


def _classify_repo_drift(
    row: dict,
    vault: Path,
    repo_identity: str,
    manifest: dict[str, dict],
) -> dict:
    existing_repo = _existing_repo_identity(row["path"], vault, manifest)
    if existing_repo is None:
        if Path(row["path"]).name.startswith("CODE_"):
            updated = dict(row)
            updated["repo_identity"] = repo_identity
            return updated
        return row
    if existing_repo == repo_identity:
        updated = dict(row)
        updated["repo_identity"] = repo_identity
        return updated
    updated = dict(row)
    updated["action"] = "SKIP_CONFLICT"
    updated["reason"] = (
        "existing managed note belongs to a different repo identity "
        f"({existing_repo} != {repo_identity})"
    )
    updated["changed_fields"] = []
    updated["changed_blocks"] = []
    updated["conflict_kind"] = "repo_identity_drift"
    updated["source"] = "both"
    updated["review_only"] = True
    updated["existing_repo_identity"] = existing_repo
    updated["repo_identity"] = repo_identity
    return updated


def _existing_repo_identity(path: str, vault: Path, manifest: dict[str, dict]) -> str | None:
    entry = manifest.get(path)
    if isinstance(entry, dict):
        value = entry.get("repo_identity")
        if isinstance(value, str) and value.strip():
            return value.strip()

    candidate = validate_vault_path(path, vault)
    if not candidate.exists() or candidate.suffix.lower() != ".md":
        return None
    try:
        frontmatter, _ = split_rendered_note(candidate.read_text(encoding="utf-8"))
    except OSError:
        return None
    value = frontmatter.get("repo")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _display_path(path: Path, vault: Path) -> str:
    candidate = Path(path)
    try:
        if candidate.is_absolute():
            return candidate.resolve().relative_to(vault).as_posix()
        return validate_vault_path(candidate, vault).relative_to(vault).as_posix()
    except ValueError:
        return candidate.as_posix()


def _canonical_actions_by_identity(actions: list[dict]) -> dict[tuple[str, object], dict]:
    result: dict[tuple[str, object], dict] = {}
    for row in actions:
        community_id = _community_id_from_path(row["path"])
        if community_id is not None:
            result[("community_id", community_id)] = row
        node_id = _node_id_from_path(row["path"])
        if node_id:
            result[("node_id", node_id)] = row
    return result


def _match_canonical_action(legacy: dict, canonical_by_identity: dict[tuple[str, object], dict]) -> dict | None:
    identity = legacy.get("identity") or {}
    for key in ("community_id", "node_id"):
        if key not in identity:
            continue
        row = canonical_by_identity.get((key, identity[key]))
        if row is not None:
            return row
    return None


def _community_id_from_path(path: str) -> int | None:
    name = Path(path).name
    match = _LEGACY_COMMUNITY_RE.match(name)
    if match:
        return int(match.group(1))
    match = _COMMUNITY_ID_RE.search(name)
    if match:
        return int(match.group(1))
    return None


def _node_id_from_path(path: str) -> str | None:
    stem = Path(path).stem
    if not stem:
        return None
    return stem.lower()


def _summary_for(actions: list[dict]) -> dict[str, int]:
    summary = {action: 0 for action in ACTION_ORDER}
    for row in actions:
        action = row.get("action")
        if action in summary:
            summary[action] += 1
    return summary


def _digest_payload(payload: dict) -> dict:
    return {
        "input": payload.get("input"),
        "vault": payload.get("vault"),
        "repo_identity": payload.get("repo_identity"),
        "summary": payload.get("summary"),
        "actions": _normalize_actions(payload.get("actions") or []),
        "legacy_mappings": _normalize_legacy_mappings(payload.get("legacy_mappings") or []),
        "review_only_paths": sorted(payload.get("review_only_paths") or []),
    }


def _normalize_actions(actions: list[dict]) -> list[dict]:
    normalized = []
    for row in actions:
        normalized.append({
            "path": row.get("path"),
            "action": row.get("action"),
            "reason": row.get("reason"),
            "changed_fields": sorted(row.get("changed_fields") or []),
            "changed_blocks": sorted(row.get("changed_blocks") or []),
            "conflict_kind": row.get("conflict_kind"),
            "user_modified": bool(row.get("user_modified")),
            "has_user_blocks": bool(row.get("has_user_blocks")),
            "source": row.get("source"),
            "review_only": bool(row.get("review_only")),
            "legacy": bool(row.get("legacy")),
        })
    return sorted(normalized, key=lambda row: (row["action"], row["path"]))


def _normalize_legacy_mappings(mappings: list[dict]) -> list[dict]:
    return sorted(
        [dict(row) for row in mappings],
        key=lambda row: (row.get("old_path", ""), row.get("new_path", "")),
    )


def _validate_plan_id(plan_id: str) -> None:
    if (
        not plan_id
        or "/" in plan_id
        or "\\" in plan_id
        or ".." in plan_id
        or _PLAN_ID_RE.match(plan_id) is None
    ):
        raise ValueError("invalid migration plan")


def _write_atomic_text(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, target)
