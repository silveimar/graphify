# Pitfalls Research

**Project:** graphify v1.5 — Diagram Intelligence & Excalidraw Bridge
**Researched:** 2026-04-22
**Focus:** What are the critical failure modes for v1.5 diagram generation, and how do we prevent them?

---

## Critical Pitfalls (Block Shipping)

### P1 — Compression Format is a One-Way Door
**Risk:** If any diagram is generated with LZ-String compression (`compress: true` or default Excalidraw behavior), all downstream tooling (pure-Python readers, agents, git diffs) breaks. Migrating existing compressed files requires JS tooling.

**Prevention:** Explicitly set `compress: false` in every generated scene. Enforce this in `diagram.py` with an assertion in tests. Document as immutable in the profile schema. Phase 1 must lock this before any diagram files are written to disk.

**Phase:** Must be decided and tested in Phase 1 (diagram.py foundation) before any other phase writes `.excalidraw.md` files.

---

### P2 — _VALID_TOP_LEVEL_KEYS / diagram_types Desync
**Risk:** If `diagram_types` config handling is added to `profile.py` without updating `_VALID_TOP_LEVEL_KEYS`, valid user config keys are silently dropped. Users get no error — their config just doesn't apply. This is extremely hard to debug.

**Prevention:** Update both `_VALID_TOP_LEVEL_KEYS` and `diagram_types` handling in the same commit, in the same function. Add a test that loads a profile with all diagram config keys and asserts none are dropped.

**Phase:** profile.py changes (Phase 2 in build order).

---

### P3 — mcp_tool_registry + serve.py Non-Atomic Update
**Risk:** If `serve.py` is updated to call new MCP diagram tools but `mcp_tool_registry` is not updated (or vice versa), the result is either a KeyError at runtime or silently missing tool handlers. Both failure modes are hard to detect in CI.

**Prevention:** Always update both files in the same commit. Add an integration test that instantiates the registry and asserts all expected tool names are present. Mark this pair as "atomic" in the planning docs.

**Phase:** mcp_tool_registry + serve.py (Phase 4 in build order, atomic).

---

### P4 — max_seeds Cap Not Enforced
**Risk:** Without a hard cap, a large graph (500+ nodes) generates hundreds of diagram files, floods the Obsidian vault, and makes Excalidraw unusable (too many elements per canvas).

**Prevention:** Enforce `max_seeds=20` as a hard cap in `seed.py` with a warning when truncation occurs. Make it configurable in vault profile but cap the configurable max at 50 (never unlimited). Test with a 500-node graph to verify truncation behavior.

**Phase:** seed.py (Phase 3 in build order).

---

### P5 — Label-Derived Element IDs Break User Edits
**Risk:** If element IDs are derived from node labels (e.g., `slugify(label)`), any label change during a re-run produces new IDs. Excalidraw treats new IDs as new elements — all user edits (repositioned nodes, resized boxes, custom arrows) are lost on re-run.

**Prevention:** Use `sha256(node_id.encode())[:16]` hex. Node IDs are stable slugs that never change after creation. Add a test asserting element IDs are unchanged when only labels change.

**Phase:** diagram.py (Phase 1 in build order).

---

## Moderate Pitfalls (Require Attention)

### P6 — fontFamily Value Mismatch
**Risk:** Excalidraw uses integer font family codes. Using `fontFamily: 1` (Virgil) or `fontFamily: 3` (Cascadia) produces a different visual aesthetic than the Excalidraw default. Using an invalid code (e.g., `fontFamily: 0`) silently falls back to browser default.

**Prevention:** Use `fontFamily: 5` in all generated elements. Add a constant `EXCALIDRAW_FONT_FAMILY = 5` in `diagram.py`. Test by opening a generated file in Obsidian + Excalidraw and verifying visual appearance.

---

### P7 — ## Drawing Section Header Case/Spacing
**Risk:** The Excalidraw Obsidian plugin parses `.excalidraw.md` files by looking for a specific markdown section. If the header is `## drawing` (lowercase), `###Drawing`, or has trailing spaces, the plugin fails to parse the diagram silently — the file opens as blank.

**Prevention:** Use exactly `## Drawing\n` with no trailing spaces. Add a unit test that writes a diagram file and asserts the exact header string is present.

---

### P8 — Tag Write-Back Bypassing Trust Boundary
**Risk:** If diagram tag write-back directly modifies vault note frontmatter (rather than going through `propose_vault_note`), it can overwrite user edits, corrupt YAML frontmatter, or touch notes outside graphify's managed scope.

**Prevention:** All tag write-back goes through `propose_vault_note`. Never use direct file writes for vault note modification. Add a test asserting that `propose_vault_note` is the only call path for tag writes.

---

### P9 — Overwriting User-Edited Diagrams
**Risk:** On re-run, if graphify unconditionally overwrites existing `.excalidraw.md` files, user layout adjustments (manually repositioned nodes, custom annotations) are lost.

**Prevention:** On re-run, check if the existing file was modified after the last graphify run (compare mtime or content hash). If user edits detected, skip overwrite and log a warning. Provide `--force-diagrams` flag to override.

---

### P10 — Layout Algorithm Coordinate Overflow
**Risk:** `nx.spring_layout` returns normalized floats in `[-1, 1]`. If these are used as Excalidraw coordinates directly, all elements cluster near origin (coordinates 0.0–1.0 in a canvas that expects 0–2000). The diagram appears as a single pixel.

**Prevention:** Scale layout coordinates: `x = (norm_x + 1) * 500`, `y = (norm_y + 1) * 400`. Add a test asserting that generated element coordinates have a spread of at least 200 canvas units.

---

## Minor Pitfalls (Watch During Implementation)

### P11 — Diagram Index Note Stale Links
On re-run with fewer seeds (e.g., because max_seeds reduced graph), the diagram index note may contain stale wikilinks to deleted diagram files. Always regenerate the index from scratch on each run.

### P12 — diagram_hints() Topology Heuristics Wrong for Edge Cases
The topology-based diagram type hints in `analyze.py` are heuristics. A chain-like community might actually be a class hierarchy better shown as architecture. Always allow profile.yaml override of per-community diagram type.

### P13 — CI Import of Optional mcp_excalidraw
If any test unconditionally imports from `mcp_excalidraw`, CI will fail since it is not installed. All references must be inside `try: import mcp_excalidraw except ImportError: mcp_excalidraw = None` guards, consistent with how graphify handles other optional deps.

### P14 — Seed Expansion Depth Too Large
BFS expansion at depth 3+ on a dense graph can include the entire graph as one subgraph, defeating the purpose of seed-based diagrams. Default depth=2 is appropriate. Cap configurable max at depth=3.

### P15 — Double-Nested Output Directory (from v1.4 lesson)
The v1.4 CR-01 pitfall showed that `tmp_path` tests can hide double-nesting bugs in output path construction. When diagram files are written to `graphify-out/diagrams/`, verify the path construction uses the same pattern as `snapshot.py` (fixed in v1.4) to avoid double-nesting.
