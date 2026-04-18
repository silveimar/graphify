# Agent capability manifest: build, hash, validate, atomic write (Phase 13).
from __future__ import annotations

import hashlib
import json
import os
from importlib import metadata
from pathlib import Path
from typing import Any

_MANIFEST_VERSION = "1"
_PKG = "graphifyy"


def _graphify_version() -> str:
    try:
        return metadata.version(_PKG)
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _tool_meta_path() -> Path:
    return Path(__file__).resolve().parent / "capability_tool_meta.yaml"


def _load_yaml_meta() -> dict[str, Any]:
    path = _tool_meta_path()
    raw = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "capability manifest requires PyYAML (pip install 'graphifyy[mcp]')"
        ) from e
    data = yaml.safe_load(raw) or {}
    return data if isinstance(data, dict) else {}


def extract_tool_examples(docstring: str | None) -> list[str]:
    """Parse an `Examples:` block out of a handler docstring (MANIFEST-10).

    Grammar:
      1. Split `docstring` into lines.
      2. Locate the first line whose stripped value is exactly `Examples:`
         (case-sensitive, no trailing text after the colon).
      3. From the next line onward, collect lines until one of:
           - a blank line (whitespace-only), or
           - another `^[A-Za-z][A-Za-z ]*:$` section header
             (e.g. `Args:`, `Returns:`, `Raises:`), or
           - EOF.
      4. For each collected line, call `.strip()`; drop empties; keep insertion order.
      5. Return the resulting list.

    Non-string / None input returns `[]` safely. Order-preserving and deterministic
    so `canonical_manifest_hash(build_manifest_dict())` stays stable across runs.
    """
    if not isinstance(docstring, str):
        return []
    lines = docstring.split("\n")
    # Locate Examples: header
    header_idx = -1
    for i, line in enumerate(lines):
        if line.strip() == "Examples:":
            header_idx = i
            break
    if header_idx < 0:
        return []
    examples: list[str] = []
    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if stripped == "":
            break
        # Detect another section header: alphabetic letters + spaces, ending in ':'
        if _is_section_header(stripped):
            break
        examples.append(stripped)
    return examples


def _is_section_header(stripped_line: str) -> bool:
    """Return True for lines like 'Args:', 'Returns:', 'Raises:' — alphabetic+spaces, trailing colon."""
    if not stripped_line.endswith(":"):
        return False
    head = stripped_line[:-1]
    if not head:
        return False
    if not head[0].isalpha() or not head[0].isupper():
        return False
    for ch in head:
        if not (ch.isalpha() or ch == " "):
            return False
    return True


def _tool_to_manifest_entry(
    tool: Any,
    meta_defaults: dict[str, Any],
    handler_docstring: str | None = None,
) -> dict[str, Any]:
    name = tool.name
    defaults = meta_defaults.get(name) or {}
    cost = defaults.get("cost_class", "cheap")
    if cost not in ("free", "cheap", "expensive"):
        cost = "cheap"
    det = defaults.get("deterministic", False)
    if not isinstance(det, bool):
        det = bool(det)
    cacheable = defaults.get("cacheable_until", "graph_mtime")
    if not isinstance(cacheable, str):
        cacheable = str(cacheable)
    comp = defaults.get("composable_from", [])
    if not isinstance(comp, list):
        comp = []
    comp = [str(x) for x in comp]
    # MANIFEST-10: per-tool _meta dict with docstring-extracted examples.
    # Merge any YAML-sourced _meta (future-proof) with the extracted examples.
    yaml_meta = defaults.get("_meta") or {}
    if not isinstance(yaml_meta, dict):
        yaml_meta = {}
    merged_meta = dict(yaml_meta)
    merged_meta["examples"] = extract_tool_examples(handler_docstring)
    return {
        "name": name,
        "description": tool.description,
        "inputSchema": tool.inputSchema,
        "cost_class": cost,
        "deterministic": det,
        "cacheable_until": cacheable,
        "composable_from": comp,
        "_meta": merged_meta,
    }


def build_manifest_dict() -> dict[str, Any]:
    """JSON-serializable manifest from introspected MCP tools + MANIFEST-06 YAML.

    Per MANIFEST-10, each tool entry carries `_meta.examples: list[str]`
    extracted from the matching handler's docstring via `extract_tool_examples`.
    """
    # Import inside the function so test monkeypatches of
    # `graphify.mcp_tool_registry.build_handler_docstrings` take effect.
    from graphify import mcp_tool_registry

    tools = mcp_tool_registry.build_mcp_tools()
    meta_defaults = _load_yaml_meta()
    try:
        docstrings = mcp_tool_registry.build_handler_docstrings()
    except Exception:
        docstrings = {}
    if not isinstance(docstrings, dict):
        docstrings = {}
    return {
        "manifest_version": _MANIFEST_VERSION,
        "graphify_version": _graphify_version(),
        "CAPABILITY_TOOLS": [
            _tool_to_manifest_entry(t, meta_defaults, docstrings.get(t.name))
            for t in tools
        ],
    }


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Stable UTF-8 bytes for hashing (sorted keys, compact separators)."""
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_manifest_hash(manifest_dict: dict[str, Any]) -> str:
    """SHA-256 hex digest of canonical manifest JSON (MANIFEST-07)."""
    return hashlib.sha256(canonical_json_bytes(manifest_dict)).hexdigest()


def validate_manifest(manifest_dict: dict[str, Any]) -> None:
    """Validate against bundled JSON Schema (raises jsonschema.ValidationError on failure)."""
    try:
        import jsonschema
    except ImportError as e:
        raise ImportError(
            "manifest validation requires jsonschema (pip install 'graphifyy[mcp]')"
        ) from e
    schema_path = Path(__file__).resolve().parent / "capability_manifest.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(manifest_dict)


def write_manifest_atomic(out_dir: Path, data: dict[str, Any]) -> Path:
    """Write graphify-out/manifest.json via .tmp + os.replace."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "manifest.json"
    tmp = target.with_suffix(".tmp")
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, target)
    return target


def write_runtime_manifest(out_dir: Path) -> Path:
    """Build and write manifest.json (MANIFEST-02 hook after graph export)."""
    data = build_manifest_dict()
    validate_manifest(data)
    return write_manifest_atomic(out_dir, data)


def load_committed_server_json(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path.cwd()
    path = root / "server.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_cli(*, repo_root: Path | None = None) -> tuple[int, str]:
    """Return (exit_code, stderr_text). D-03 stable stderr on failure."""
    root = repo_root or Path.cwd()
    lines: list[str] = []
    try:
        built = build_manifest_dict()
        validate_manifest(built)
        actual_hash = canonical_manifest_hash(built)
        server = load_committed_server_json(root)
        expected = (
            (server.get("_meta") or {}).get("manifest_content_hash")
            or server.get("manifest_content_hash")
        )
        if not expected:
            lines.append("error: server.json missing _meta.manifest_content_hash")
            lines.append(f"  path: {root / 'server.json'}")
            lines.append("regenerate:")
            lines.append("  graphify capability --stdout > server.json")
            return 1, "\n".join(lines) + "\n"
        if expected != actual_hash:
            lines.append("error: manifest content hash mismatch (committed vs generated)")
            lines.append(f"  expected: {expected}")
            lines.append(f"  actual:   {actual_hash}")
            lines.append(f"  server.json: {root / 'server.json'}")
            lines.append("regenerate:")
            lines.append("  graphify capability --stdout > server.json")
            return 1, "\n".join(lines) + "\n"
        return 0, ""
    except Exception as exc:
        lines.append(f"error: capability validate failed: {exc}")
        lines.append(f"  cwd: {root}")
        lines.append("regenerate:")
        lines.append("  graphify capability --stdout > server.json")
        return 1, "\n".join(lines) + "\n"


def print_manifest_stdout() -> None:
    """Print canonical manifest JSON (MANIFEST-04)."""
    data = build_manifest_dict()
    validate_manifest(data)
    print(json.dumps(data, indent=2, ensure_ascii=False))
