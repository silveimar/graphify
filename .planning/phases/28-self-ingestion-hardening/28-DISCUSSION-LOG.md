# Phase 28: Self-Ingestion Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 28-self-ingestion-hardening
**Areas discussed:** Exclusion-glob schema, Nesting guard semantics, Manifest design, Renamed-output recovery

---

## Exclusion-glob schema (VAULT-11)

### Q1: Where should user-declared exclusion globs live in profile.yaml?
| Option | Description | Selected |
|--------|-------------|----------|
| Nested under `output:` (Recommended) | `output: { mode, path, exclude: [...] }`. Co-located. ResolvedOutput grows `exclude_globs`. | ✓ |
| New top-level `exclusions:` list | Sibling to `output:`. Cleaner cross-context but adds top-level key. | |
| Extend `.graphifyignore` discovery | Reuse existing parser. Two ignore mechanisms layered. | |

### Q2: When does `output.exclude` apply?
| Option | Description | Selected |
|--------|-------------|----------|
| Always when profile is loaded (Recommended) | Globs apply even if `--output` overrides destination. | ✓ |
| Auto-adopt only | Globs apply only when D-09 auto-adopt fires. | |
| Profile loaded OR explicit `--exclude` flag | Adds parallel CLI flag. | |

### Q3: Glob syntax for `output.exclude`?
| Option | Description | Selected |
|--------|-------------|----------|
| fnmatch (current `.graphifyignore` style) (Recommended) | Reuse `_is_ignored()` at detect.py:307. Stdlib only. | ✓ |
| pathspec (gitignore-compatible) | New optional dep; conflicts with no-new-deps constraint. | |
| Plain prefix-match strings | No globs, inflexible. | |

### Q4: Validation behavior for malformed entries?
| Option | Description | Selected |
|--------|-------------|----------|
| Strict: `validate_profile()` rejects (Recommended) | Loud-fail at profile-load time, matches D-05/D-02. | ✓ |
| Lenient: warn and skip bad entries | Friendlier to typos but masks real errors. | |
| Silent skip | Inconsistent with validate-first pattern. | |

---

## Nesting guard semantics (VAULT-12)

### Q1: What does the nesting guard match?
| Option | Description | Selected |
|--------|-------------|----------|
| Literal name set + ResolvedOutput dir basenames (Recommended) | `{graphify-out, graphify_out}` ∪ basenames of resolved.notes_dir/artifacts_dir. | ✓ |
| Literal name set only (current quick-fix) | Just `{graphify-out, graphify_out}`. Misses renames. | |
| Full path containment check | Resolve every candidate against absolute paths. More expensive. | |

### Q2: Action on detected nesting?
| Option | Description | Selected |
|--------|-------------|----------|
| Warn-and-skip (Recommended) | Single warning, continue scan. Cleanup deferred to Phase 29 doctor. | ✓ |
| Fatal: refuse to run | Blocks recovery; user must clean disk before any graphify command. | |
| Silent skip | User never learns about disk junk. | |

### Q3: Warning frequency?
| Option | Description | Selected |
|--------|-------------|----------|
| One summary line per run (Recommended) | Aggregate during scan, emit at end. | ✓ |
| One line per detected nesting root | More signal, more noise. | |
| Per-file warning | Verbose, debug-only utility. | |

### Q4: Apply guard when no vault detected?
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, always (Recommended) | Universal protection. v1.0 backcompat preserved (default paths unchanged). | ✓ |
| Only when vault detected | Scoped to auto-adopt path. Leaves non-vault users vulnerable. | |

---

## Manifest design (VAULT-13)

### Q1: Where does the written-paths manifest live?
| Option | Description | Selected |
|--------|-------------|----------|
| New `<artifacts_dir>/output-manifest.json` (Recommended) | Separate concerns from existing `manifest.json`. Stable across notes_dir renames. | ✓ |
| Extend existing `graphify-out/manifest.json` with `outputs:` field | Single file but bumps schema for incremental detection readers. | |
| Two files at notes_dir AND artifacts_dir | Redundant, write-amplified. | |

### Q2: Granularity?
| Option | Description | Selected |
|--------|-------------|----------|
| Both: root output dirs + every written file (Recommended) | Roots for prefix-prune, files for precise rename-recovery. | ✓ |
| Root output dirs only | Compact but misses individual-file rename cases. | |
| Every written file only | Loses fast prefix-prune. | |

### Q3: History depth?
| Option | Description | Selected |
|--------|-------------|----------|
| Rolling N=5 most recent runs (Recommended) | Bounded; covers rename-once-or-twice case. | ✓ |
| Single previous run only | Misses double-rename scenarios. | |
| Unbounded history | Eventually a problem; needs separate prune. | |
| Configurable in profile.yaml | Schema knob most users won't tune. | |

### Q4: Behavior when manifest is missing/malformed?
| Option | Description | Selected |
|--------|-------------|----------|
| Treat as empty, warn once on malformed (Recommended) | Silent on missing (first-run); warn-once on corruption. | ✓ |
| Fatal on malformed, silent on missing | Refuses to run on corruption; least forgiving. | |
| Always silent fallback | Masks signals; inconsistent with `[graphify]` warning convention. | |

---

## Renamed-output recovery (VAULT-13 #4)

### Q1: How does detect.py find the manifest after a profile rename?
| Option | Description | Selected |
|--------|-------------|----------|
| Always look at `resolved.artifacts_dir` (Recommended) | sibling-of-vault, stable across `notes_dir` renames. | ✓ |
| Discover via filesystem walk | Survives more rename scenarios but expensive and fragile. | |
| Store path in `profile.yaml` under `output.manifest_path:` | Schema knob most users won't set. | |

### Q2: What happens to OLD path's content per manifest?
| Option | Description | Selected |
|--------|-------------|----------|
| Skip from scan (no warning) (Recommended) | Rename is normal user action. | ✓ |
| Skip + emit one informational line | Surfaces what happened; slightly noisier. | |
| Skip + suggest cleanup via doctor | Hooks Phase 29 explicitly. | |

### Q3: Stale manifest entries (file no longer exists on disk)?
| Option | Description | Selected |
|--------|-------------|----------|
| Garbage-collect on next manifest write (Recommended) | Mirrors `deleted_files` cleanup at detect.py:503. | ✓ |
| Keep forever as historical record | Conflicts with rolling N=5 cap. | |
| Refuse to run, ask user to clean up | Too strict for normal user actions. | |

### Q4: When does the run write to output-manifest.json?
| Option | Description | Selected |
|--------|-------------|----------|
| After successful export, before exit (Recommended) | Atomic tmp+rename. Failed runs leave manifest unchanged. | ✓ |
| Incremental: append after each writer | More resilient to crashes but partial-state risk. | |
| Pre-write (before export) | Worst correctness profile. | |

---

## Claude's Discretion

- Exact `run_id` hash construction (UUID4 vs. SHA-256 of `notes_dir + timestamp`).
- Module location of nesting-detection function (extend `_is_noise_dir` vs. new `_is_nested_output` predicate).
- Exact `__main__.py` wire-point for post-export manifest write.
- Test fixture strategy for nesting scenarios (`tmp_path`-based per CLAUDE.md).
- Whether `output-manifest.json` is exposed via MCP `serve.py` (out of scope unless trivially free).

## Deferred Ideas

- `--exclude` CLI flag mirroring `--output`.
- Configurable `output.manifest_history_depth:` profile field.
- Configurable `output.manifest_path:` profile field.
- MCP query surface for `output-manifest.json`.
- Dual manifest files at notes_dir AND artifacts_dir for redundancy.
- Per-file warning on nesting detection.
- Fatal-on-malformed-manifest behavior.
- `graphify init-profile` scaffolding command (Phase 29 stretch / v1.8).
- Discoverable manifest via filesystem walk.
- Pre-write manifest (record intended outputs before writing).
