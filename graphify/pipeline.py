"""Thin pipeline wrapper for `graphify run` (Phase 12)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from graphify.output import ResolvedOutput


def run_corpus(
    target: Path,
    *,
    use_router: bool,
    out_dir: Path | None = None,
    resolved: "ResolvedOutput | None" = None,
    profile: dict | None = None,
    detection_meta: dict | None = None,
) -> dict:
    """detect → extract (optional Router + audit flush). AST-only structural pass.

    When out_dir is None, use :func:`graphify.output.default_graphify_artifacts_dir`
    (HYG-05: non-vault default output is cwd-relative, not nested under *target*).
    """
    from graphify.detect import detect
    from graphify.extract import extract
    from graphify.output import default_graphify_artifacts_dir
    from graphify.routing import default_router
    from graphify.routing_audit import RoutingAudit

    if out_dir is None:
        out_dir = default_graphify_artifacts_dir(target, resolved=resolved)

    if target.is_file():
        paths = [target.resolve()]
    else:
        det = detect(target, resolved=resolved, profile=profile)
        if detection_meta is not None:
            detection_meta.clear()
            detection_meta["dot_graphify_discovered"] = list(
                det.get("dot_graphify_discovered", [])
            )
        paths = [Path(p) for p in det["files"].get("code", [])]

    router = default_router() if use_router else None
    audit = RoutingAudit() if use_router else None
    result = extract(paths, router=router, audit=audit)
    if audit is not None:
        dest = audit.flush(out_dir)
        print(f"routing audit -> {dest}")
    return result
