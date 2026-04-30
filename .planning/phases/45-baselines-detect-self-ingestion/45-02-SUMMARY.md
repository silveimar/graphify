# Plan 45-02 Summary

- Extended `_DEFAULT_PROFILE` with `corpus.dot_graphify` + `validate_profile` / top-level `corpus` key.
- `detect(..., profile=)` applies `.graphify/` include/exclude + hard YAML/profile deny; returns `dot_graphify_discovered`; threads profile through `run_corpus`, vault auto-track, and `doctor --dot-graphify-track` / `--apply-dot-graphify-track`.
