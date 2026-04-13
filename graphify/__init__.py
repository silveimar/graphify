"""graphify - extract · build · cluster · analyze · report."""


def __getattr__(name):
    # Lazy imports so `graphify install` works before heavy deps are in place.
    _map = {
        "extract": ("graphify.extract", "extract"),
        "collect_files": ("graphify.extract", "collect_files"),
        "build_from_json": ("graphify.build", "build_from_json"),
        "cluster": ("graphify.cluster", "cluster"),
        "score_all": ("graphify.cluster", "score_all"),
        "cohesion_score": ("graphify.cluster", "cohesion_score"),
        "god_nodes": ("graphify.analyze", "god_nodes"),
        "surprising_connections": ("graphify.analyze", "surprising_connections"),
        "suggest_questions": ("graphify.analyze", "suggest_questions"),
        "generate": ("graphify.report", "generate"),
        "to_json": ("graphify.export", "to_json"),
        "to_html": ("graphify.export", "to_html"),
        "to_svg": ("graphify.export", "to_svg"),
        "to_canvas": ("graphify.export", "to_canvas"),
        "to_obsidian": ("graphify.export", "to_obsidian"),
        "to_wiki": ("graphify.wiki", "to_wiki"),
        "load_profile": ("graphify.profile", "load_profile"),
        "validate_profile": ("graphify.profile", "validate_profile"),
        "resolve_filename": ("graphify.templates", "resolve_filename"),
        "validate_template": ("graphify.templates", "validate_template"),
        "load_templates": ("graphify.templates", "load_templates"),
        "render_note": ("graphify.templates", "render_note"),
        "render_moc": ("graphify.templates", "render_moc"),
        "render_community_overview": ("graphify.templates", "render_community_overview"),
        "classify": ("graphify.mapping", "classify"),
        "MappingResult": ("graphify.mapping", "MappingResult"),
        "validate_rules": ("graphify.mapping", "validate_rules"),
        "apply_merge_plan": ("graphify.merge", "apply_merge_plan"),
        "compute_merge_plan": ("graphify.merge", "compute_merge_plan"),
        "format_merge_plan": ("graphify.merge", "format_merge_plan"),
        "split_rendered_note": ("graphify.merge", "split_rendered_note"),
        "MergeAction": ("graphify.merge", "MergeAction"),
        "MergePlan": ("graphify.merge", "MergePlan"),
        "MergeResult": ("graphify.merge", "MergeResult"),
        "RenderedNote": ("graphify.merge", "RenderedNote"),
        "validate_profile_preflight": ("graphify.profile", "validate_profile_preflight"),
        "PreflightResult": ("graphify.profile", "PreflightResult"),
        "compute_delta": ("graphify.delta", "compute_delta"),
        "classify_staleness": ("graphify.delta", "classify_staleness"),
        "render_delta_md": ("graphify.delta", "render_delta_md"),
        "save_snapshot": ("graphify.snapshot", "save_snapshot"),
        "load_snapshot": ("graphify.snapshot", "load_snapshot"),
        "list_snapshots": ("graphify.snapshot", "list_snapshots"),
        "snapshots_dir": ("graphify.snapshot", "snapshots_dir"),
    }
    if name in _map:
        import importlib
        mod_name, attr = _map[name]
        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'graphify' has no attribute {name!r}")
