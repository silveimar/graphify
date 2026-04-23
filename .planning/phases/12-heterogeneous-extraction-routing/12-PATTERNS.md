# Phase 12 — Pattern Map

## PATTERN MAPPING COMPLETE

| New / changed artifact | Closest analog | Notes |
|------------------------|----------------|-------|
| `graphify-out/routing.json` | `dedup.py` + `write_dedup_reports` | `version`, atomic `.tmp` + `os.replace`, optional `.md` sibling |
| YAML model routing | `harness_schemas/` / `.graphify/*.yaml` | Safe load, repo-relative paths, no implicit env |
| Per-file sidecar audit | Phase 10 `dedup_report.json` | Human summary optional (`routing_report.md` vs GRAPH_REPORT section) |
| Optional kwarg on hot function | `dedup(..., encoder=)` | Backward compatible defaults |
| Batch max tier | `batch.cluster_files` output + CONTEXT D-01 | `max(tier(file) for file in cluster["files"])` with deterministic ordering |

## Code excerpts (reference)

**Atomic write** — follow `write_dedup_reports` / cache `save_cached` temp-file pattern.

**Import graph for clustering** — `batch._build_import_graph` + `cluster_files(paths, ast_results)`.

**Cache directory** — `cache.cache_dir(root)` layout; extend filename or hash input for `model_id`.
