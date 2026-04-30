# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.4.x   | Yes       |
| 0.3.x   | Yes       |
| < 0.3   | No        |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Report security issues via GitHub's private vulnerability reporting, or email the maintainer directly. Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to release a fix within 7 days for critical issues.

## Security Model

graphify is a **local development tool**. It runs as a Claude Code skill and optionally as a local MCP stdio server. It makes no network calls during graph analysis - only during `ingest` (explicit URL fetch by the user).

### Threat Surface

| Vector | Mitigation |
|--------|-----------|
| SSRF via URL fetch | `security.validate_url()` allows only `http` and `https` schemes, blocks private/loopback/link-local IPs, and blocks cloud metadata endpoints. Redirect targets are re-validated. All fetch paths including tweet oEmbed go through `safe_fetch()`. |
| Oversized downloads | `safe_fetch()` streams responses and aborts at 50 MB. `safe_fetch_text()` aborts at 10 MB. |
| Non-2xx HTTP responses | `safe_fetch()` raises `HTTPError` on non-2xx status codes - error pages are not silently treated as content. |
| Path traversal in MCP server | `security.validate_graph_path()` resolves paths and requires them to be inside `graphify-out/`. Also requires the `graphify-out/` directory to exist. |
| XSS in graph HTML output | `security.sanitize_label()` strips control characters, caps at 256 chars, and HTML-escapes all node labels and edge titles before pyvis embeds them. |
| Prompt injection via node labels | `sanitize_label()` also applied to MCP text output - node labels from user-controlled source files cannot break the text format returned to agents. |
| YAML frontmatter injection | `_yaml_str()` escapes backslashes, double quotes, and newlines before embedding user-controlled strings (webpage titles, query questions) in YAML frontmatter. |
| YAML frontmatter injection (vault adapter) | `profile.safe_frontmatter_value()` quotes values containing YAML structural characters (`:`, `#`, `[`, `]`, etc.) and strips control characters. Prevents node labels from breaking frontmatter structure in Obsidian notes. |
| Path traversal in vault adapter | `profile.validate_vault_path()` resolves paths and requires them to stay inside the vault directory. Applied to all profile-derived folder mappings and template paths. No `~` expansion, no absolute paths, no `..` sequences allowed in profile paths. |
| Filename injection in vault adapter | `profile.safe_filename()` applies Unicode NFC normalization, strips OS-illegal characters, and caps length at 200 characters with SHA256 hash suffix for collision handling. Prevents malicious node labels from creating files outside the vault. |
| Tag injection in vault adapter | `profile.safe_tag()` slugifies community names to lowercase hyphen-separated strings with `x-` prefix for leading digits, producing valid Obsidian tags. |
| Encoding crashes on source files | All tree-sitter byte slices decoded with `errors="replace"` - non-UTF-8 source files degrade gracefully instead of crashing extraction. |
| Symlink traversal | `os.walk(..., followlinks=False)` is explicit throughout `detect.py`. |
| Corrupted graph.json | `_load_graph()` in `serve.py` wraps `json.JSONDecodeError` and prints a clear recovery message instead of crashing. |

### Harness memory import/export (Phase 40)

| Risk | Mitigation |
|------|------------|
| Untrusted harness files (markdown / JSON interchange) | `harness_import.import_harness_path` reads only inside `graphify-out/` via `validate_graph_path`; byte cap `MAX_HARNESS_IMPORT_BYTES` (same order as text fetch cap); decoding errors fail closed. |
| Prompt injection via imported labels or bodies | Layered `sanitize_label`, `sanitize_harness_text`, and `guard_harness_injection_patterns` in `security.py`; optional `strict` rejects on pattern hit (SEC-01). |
| Path traversal on harness paths | `validate_graph_path` resolves and confines reads/writes to the artifacts root — CLI, MCP, and library share the same checks (PORT-05, SEC-03). |
| MCP vs CLI trust mismatch | MCP tools `import_harness` and `export_harness_interchange` call `import_harness_path` / `export_interchange_v1` — no duplicate parsers in `serve.py` (SEC-03, D-05). |
| Oversized harness payloads | Read capped before decode; long free-text fields capped in `sanitize_harness_text`. |

Traceability: **PORT-01–PORT-05** (interchange export/import surface, schema artifact, validation, round-trip scope, path policy); **SEC-01–SEC-04** (sanitization, interchange provenance metadata on export, shared MCP/CLI behavior, documentation).

### Phase 40 security audit

| Metric | Count |
|--------|-------|
| Threats reviewed | 11 |
| Closed | 11 |
| Open | 0 |

Per-phase register and evidence: `.planning/phases/40-multi-harness-memory-inverse-import-injection-defenses/40-SECURITY.md` (path as documented; file may be absent until that phase’s audit is materialized).

### Phase 49 security audit (2026-04-30)

**Scope:** CLI `--version` / `-V`, success-path version footer, consolidated `package_version()`, and related changes per `.planning/phases/49-add-version-flag-to-graphify-command-and-also-print-current-/49-01-PLAN.md` `<threat_model>`. Verification is **code-evidence only** (no “intended” mitigations without a grep-backed call site).

**Executive summary:** All three Phase 49 declared mitigations are **implemented and traceable**. Version resolution is centralized in `graphify.version` with no `graphify.*` imports at module import time (avoiding circular import risk). The success footer runs only inside `_cli_exit` when `code == 0`. Install/uninstall (and platform `install`/`uninstall` subcommands) are excluded from the footer via `_suppress_success_version_footer`. The `--version` / `-V` early exit uses `raise SystemExit(0)` and therefore does not emit the stderr footer or run the skill-stamp loop, matching CLI-VER acceptance criteria. **No SUMMARY.md `## Threat Flags`** was present under the phase 49 directory; nothing logged as unregistered attack surface for this pass.

| Threat (plan register) | Mitigation (expected) | Status | Evidence |
|------------------------|------------------------|--------|----------|
| Circular imports | `graphify.version` depends on stdlib only at import time; lazy `importlib.metadata` inside `package_version()` | **COVERED** | `graphify/version.py` — module body is `from __future__ import annotations` + `def package_version()` with `from importlib.metadata import version` only inside the function (lines 6–13). No `import graphify` / no sibling package imports. |
| Footer on error paths | Emit `[graphify] version …` only on success (`code == 0`) | **COVERED** | `graphify/__main__.py` `_cli_exit` (lines 62–65): `if code == 0 and not _suppress_success_version_footer(sys.argv):` then print; all `_cli_exit(` call sites use `0` only. Non-zero exits use `sys.exit(n)` / `raise SystemExit` elsewhere and do not invoke the footer. |
| Install / uninstall noise | Suppress success footer on help, `install`, and `<platform> install\|uninstall` | **COVERED** | `graphify/__main__.py` `_suppress_success_version_footer` (lines 51–59): `argv[1]` in `-h`/`--help`/`install`; or `len(argv) >= 3` and `argv[2]` in `install`/`uninstall`. Matches documented CLI shapes (`graphify install`, `graphify claude uninstall`, `graphify hook uninstall`, etc.). |

**Counts (Phase 49 register only):** COVERED **3** · PARTIAL **0** · MISSING **0**

**Prioritized recommendations**

1. **Low — defensive completeness:** If a future command adds a bare two-token `graphify uninstall` (with `uninstall` as `argv[1]`), extend `_suppress_success_version_footer` to treat `argv[1] == "uninstall"` like `install`. Not required for current documented CLI.
2. **Informational:** Keep `package_version()` as the single non-test reader of `importlib.metadata.version("graphifyy")` when adding new modules (already migrated in `__main__.py`, `capability.py`, `harness_interchange.py`, `elicit.py` per repository grep).

### What graphify does NOT do

- Does not run a network listener (MCP server communicates over stdio only)
- Does not execute code from source files (tree-sitter parses ASTs - no eval/exec)
- Does not use `shell=True` in any subprocess call
- Does not store credentials or API keys

### Optional network calls

- `ingest` subcommand: fetches URLs explicitly provided by the user
- PDF extraction: reads local files only (pypdf does not make network calls)
- watch mode: local filesystem events only (watchdog does not make network calls)
