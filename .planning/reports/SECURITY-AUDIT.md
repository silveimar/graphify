# Security audit: SECURITY.md vs implementation

**Scope:** Retroactive verification of the Threat Surface table in repository-root `SECURITY.md` against the `graphify` package. **Date:** 2026-04-29. **Output path:** `.planning/reports/SECURITY-AUDIT.md` (directory writable; not a fallback to repo root).

## Executive summary

**Verdict: PARTIAL (mostly aligned, documentation gaps and one behavioral nuance).**

The documented mitigations are largely **implemented in code** with clear call sites. A few **SECURITY.md** claims overstate or slightly misdescribe the implementation (notably `sanitize_label` vs HTML escaping, and symlink following). A **strong, under-documented** defense exists for HTML export (`_js_safe` closing `</script>` breakout). **Corrupted `graph.json`** is handled with a clear stderr message, but the process still **exits** (`sys.exit(1)`), which is stricter than “no crash” wording might imply.

---

## Threat / mitigation verification table

| Threat (per SECURITY.md) | Documented mitigation | Code evidence | Status |
|--------------------------|------------------------|---------------|--------|
| SSRF via URL fetch | `validate_url()`: http(s), block private/loopback/link-local, cloud metadata; redirects re-validated; fetches through `safe_fetch()` | `graphify/security.py`: `validate_url`, `_NoFileRedirectHandler.redirect_request` → `validate_url(newurl)`; `safe_fetch` / `safe_fetch_text` call `validate_url` then stream with cap | **VERIFIED** |
| Oversized downloads | 50 MB binary, 10 MB text | `graphify/security.py`: `_MAX_FETCH_BYTES` (50 MB), `_MAX_TEXT_BYTES` (10 MB); `safe_fetch` / `safe_fetch_text` defaults | **VERIFIED** |
| Non-2xx HTTP | `safe_fetch` raises on non-2xx | `graphify/security.py` `safe_fetch`: checks `status` / `code`, raises `HTTPError` if not 2xx | **VERIFIED** |
| Path traversal (MCP) | `validate_graph_path()` under `graphify-out/`, base must exist | `graphify/security.py` `validate_graph_path`; `graphify/serve.py` imports and uses `validate_graph_path` for graph file resolution (e.g. `validated = validate_graph_path(...)`) | **VERIFIED** |
| XSS in graph HTML | `sanitize_label` + HTML escape for pyvis | `graphify/export.py`: `sanitize_label` on labels; `title` uses `_html.escape(label)`; **also** `def _js_safe(obj): return json.dumps(obj).replace("</", "<\\/")` before embedding JSON in `<script>` | **VERIFIED** (defense is layered; see findings) |
| Prompt injection (MCP labels) | `sanitize_label` on MCP text | `graphify/serve.py`: widespread `sanitize_label(...)` on returned fields and narrative lines | **VERIFIED** |
| YAML injection (ingest) | `_yaml_str()` escaping | `graphify/ingest.py`: `def _yaml_str(s: str) -> str` (backslash, quote, newlines); used in generated frontmatter strings | **VERIFIED** |
| YAML injection (vault) | `profile.safe_frontmatter_value()` | `graphify/profile.py` `safe_frontmatter_value`; `graphify/profile.py` `_dump_frontmatter` routes string values through it | **VERIFIED** |
| Path traversal (vault adapter) | `profile.validate_vault_path()` | `graphify/profile.py` `validate_vault_path`; used from `graphify/output.py`, `graphify/templates.py`, `graphify/merge.py`, `graphify/migration.py`, `graphify/vault_promote.py`, `graphify/__main__.py`, etc. | **VERIFIED** |
| Filename injection (vault) | `profile.safe_filename()` | `graphify/profile.py` `safe_filename`; `graphify/export.py` uses `safe_filename(...)` for note names | **VERIFIED** |
| Tag injection | `profile.safe_tag()` | `graphify/profile.py` `safe_tag`; `graphify/export.py` sets `community_tag` via `safe_tag` | **VERIFIED** |
| Encoding crashes | tree-sitter / reads use `errors="replace"` | `graphify/extract.py`: multiple `.decode("utf-8", errors="replace")` and `read_text(..., errors="replace")` | **VERIFIED** |
| Symlink traversal | `os.walk(..., followlinks=False)` in `detect.py` | `graphify/detect.py`: `collect_files` uses `os.walk(scan_root, followlinks=follow_symlinks)` with **`follow_symlinks: bool = False`** default on `detect()`. Not hard-coded `False` if callers pass `True`. | **PARTIAL** |
| Corrupted `graph.json` | `_load_graph()` handles bad JSON gracefully | `graphify/serve.py` `def _load_graph`: `except json.JSONDecodeError` prints recovery message to stderr **then `sys.exit(1)`** | **PARTIAL** |

---

## Manifest / atomic-write spot-check (`detect.py`, `merge.py`)

| Area | Finding | Status |
|------|---------|--------|
| `detect.save_manifest` | Writes via `dest.with_suffix(".json.tmp")`, `flush` + `os.fsync`, `os.replace`; tmp cleanup on `OSError` | **VERIFIED** |
| `detect._save_output_manifest` | Same atomic pattern under `artifacts_dir`; paths derived from `artifacts_dir / _OUTPUT_MANIFEST_NAME`; tmp sibling `.json.tmp` | **VERIFIED** |
| `merge._save_manifest` | `tmp = manifest_path.with_suffix(".json.tmp")`, `fsync`, `os.replace`, tmp unlink on `OSError`; `import os` present in apply-layer section (module uses late imports for side-effectful helpers) | **VERIFIED** |
| Path escape via manifest path | Manifest destinations are constructed by pipeline defaults or validated vault/output paths—not raw user `"../"` strings in these writers; tmp files sit beside the target manifest | **VERIFIED** (within graphify’s path model) |

---

## `graphify/security.py` usage on hot paths

| Area | Uses `security` helpers? | Notes |
|------|-------------------------|--------|
| **ingest** | Yes | `from graphify.security import safe_fetch, safe_fetch_text, validate_url` (`graphify/ingest.py`) |
| **export (HTML/JSON pipeline)** | Partial | `sanitize_label` from `security`; vault strings use `profile.safe_*` |
| **serve (MCP)** | Yes | `sanitize_label`, `validate_graph_path` |
| **migration** | Indirect | Uses `profile.validate_vault_path` (vault row in SECURITY.md), not `security.validate_graph_path` |

This split is **consistent** with SECURITY.md’s separation of generic URL/path guards vs vault-specific profile helpers.

---

## Findings by severity

### Medium (documentation accuracy)

1. **SECURITY.md implies `sanitize_label()` HTML-escapes.** In code, `sanitize_label` strips control characters and truncates (`graphify/security.py`); **HTML escaping** for the vis tooltip is explicit (`export.py`: `_html.escape(label)`), and **JSON-in-script** safety uses **`_js_safe`** (`json.dumps` + `</` escaping). **Recommendation:** Update SECURITY.md to describe the **three layers**: `sanitize_label`, `_html.escape` where needed, `_js_safe` for embedded JSON.

2. **Symlink policy wording.** Docs say `followlinks=False` “throughout” `detect.py`; implementation exposes **`follow_symlinks`** (default `False`) passed to `os.walk`. **Recommendation:** Document “default: do not follow symlinks” and any CLI flag that sets `True`.

### Low

3. **Corrupted graph handling.** User-facing message is clear; behavior is **process exit** with code 1, not continued operation. **Recommendation:** Rephrase SECURITY.md from “instead of crashing” to “fails with a clear message and nonzero exit” if that is the intended contract.

4. **Obsidian tag prefix detail.** `safe_tag` documents leading-digit handling; implementation prefixes **`x`** without a hyphen (e.g. digit-leading slugs become `x…`). **Recommendation:** Align SECURITY.md wording with the exact slug rules.

### Informational (strong but under-documented)

5. **`export._js_safe`** mitigates breaking out of `<script>` when embedding node/edge JSON—worth a bullet in SECURITY.md.

---

## Recommendations (minimal)

1. Edit **SECURITY.md** Threat Surface rows for **XSS / labels** to match code: `sanitize_label` + **`html.escape`** (or equivalent) + **`_js_safe`** for script embedding.
2. Adjust **symlink** bullet to “default `follow_symlinks=False` in `detect()` / `collect_files`”.
3. Optionally add **one sentence** on **`_js_safe`** / `</script>` hardening in the HTML export path.

---

## Files reviewed (non-exhaustive)

- `SECURITY.md` (repository root)
- `graphify/security.py`, `graphify/ingest.py`, `graphify/export.py`, `graphify/serve.py`, `graphify/detect.py`, `graphify/merge.py`, `graphify/profile.py`, `graphify/extract.py` (spot-check + ripgrep)
