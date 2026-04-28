"""Thin pipeline wrapper for `graphify run` (Phase 12)."""
from __future__ import annotations

from pathlib import Path


def run_corpus(target: Path, *, use_router: bool, out_dir: Path | None = None) -> dict:
    """detect → extract (optional Router + audit flush). AST-only structural pass.

    When out_dir is None, preserve the v1.0 default: target/'graphify-out' for
    directory targets, target.parent/'graphify-out' for file targets (D-12).
    """
    from graphify.detect import detect
    from graphify.extract import extract
    from graphify.routing import default_router
    from graphify.routing_audit import RoutingAudit

    if out_dir is None:
        out_dir = target / "graphify-out" if target.is_dir() else target.parent / "graphify-out"

    if target.is_file():
        paths = [target.resolve()]
    else:
        det = detect(target)
        paths = [Path(p) for p in det["files"].get("code", [])]

    router = default_router() if use_router else None
    audit = RoutingAudit() if use_router else None
    result = extract(paths, router=router, audit=audit)
    if audit is not None:
        dest = audit.flush(out_dir)
        print(f"routing audit -> {dest}")
    return result
