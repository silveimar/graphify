---
status: complete
phase: 06-graph-delta-analysis-staleness
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md]
started: 2026-04-12T00:00:00Z
updated: 2026-04-12T23:46:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Snapshot Save and Round-Trip
expected: Running save_snapshot then load_snapshot round-trips correctly — nodes, edges, and community assignments are preserved. Metadata contains timestamp, node_count, edge_count.
result: pass

### 2. Provenance Metadata on Extracted Nodes
expected: Extracted nodes contain 'extracted_at', 'source_hash', and 'source_mtime' keys alongside the standard id, label, file_type, source_file, source_location.
result: pass

### 3. Delta Computation — Added/Removed Detection
expected: Creating two graphs where G_new has an extra node, running compute_delta shows that node in added_nodes. Removing a node shows it in removed_nodes. Same for edges.
result: pass

### 4. Staleness Classification (FRESH/STALE/GHOST)
expected: classify_staleness returns "FRESH" for a node whose source_hash matches the file on disk, "STALE" for one whose hash mismatches (file was edited), and "GHOST" for one whose source_file no longer exists.
result: pass

### 5. GRAPH_DELTA.md Report Rendering
expected: render_delta_md produces markdown with summary section (counts of changes, notable changes) and archive content (Added Nodes, Removed Nodes, Community Migrations). Empty delta says "No changes detected". First run says "First run — no previous snapshot to compare."
result: pass

### 6. CLI — graphify snapshot Command
expected: Running `graphify --help` shows "snapshot" in the command list. Running `graphify snapshot --graph <path>` creates a .json file in graphify-out/snapshots/. Running with `--name my-label` includes "my-label" in the filename.
result: pass

### 7. Auto-Snapshot + Auto-Delta Pipeline Helper
expected: Calling auto_snapshot_and_delta(G, communities) saves a snapshot AND writes graphify-out/GRAPH_DELTA.md. On first call, delta says "First run — no previous snapshot to compare." On second call with a modified graph, delta shows actual changes.
result: pass

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
