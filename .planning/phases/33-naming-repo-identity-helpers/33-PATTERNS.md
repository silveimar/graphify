# Phase 33: Naming & Repo Identity Helpers - Pattern Map

**Mapped:** 2026-04-28
**Files analyzed:** 10 new/modified files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `graphify/naming.py` | utility | transform + file-I/O | `graphify/output.py`, `graphify/cache.py`, `graphify/merge.py` | role-match |
| `graphify/profile.py` | config | request-response validation | `graphify/profile.py` existing schema sections | exact |
| `graphify/__main__.py` | CLI route | request-response | existing `--obsidian` and `run` flag parsing | exact |
| `graphify/export.py` | export service | file-I/O | `to_obsidian()` community label injection | exact |
| `graphify/mapping.py` | mapper utility | transform | `_derive_community_label()` and `_assemble_communities()` | exact |
| `graphify/templates.py` | renderer utility | transform + file-I/O sink | `render_moc()` / `_render_moc_like()` | role-match |
| `tests/test_naming.py` | test | transform + file-I/O | `tests/test_output.py`, `tests/test_cache.py` | role-match |
| `tests/test_profile.py` | test | config validation | existing `validate_profile()` tests | exact |
| `tests/test_export.py` | test | file-I/O dry-run | existing `to_obsidian()` dry-run tests | exact |
| `tests/test_main_flags.py` | test | CLI subprocess | existing `--output` flag wiring tests | exact |

## Pattern Assignments

### `graphify/naming.py` (utility, transform + file-I/O)

**Analogs:** `graphify/output.py`, `graphify/cache.py`, `graphify/merge.py`, `graphify/detect.py`

**Imports and data carrier pattern** (`graphify/output.py` lines 17-30):
```python
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple


class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: Literal["profile", "cli-flag", "default"]
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14
```

Copy this shape for `ResolvedRepoIdentity` and concept naming provenance: immutable `NamedTuple` returns, `Literal` source values, `Path` inputs, no global mutable state.

**Precedence and stderr source reporting pattern** (`graphify/output.py` lines 44-99):
```python
def resolve_output(cwd: Path, *, cli_output: str | None = None) -> ResolvedOutput:
    """Resolve final output destination per D-06..D-13.

    Precedence: cli_output > profile.output > v1.0 default paths.
    Emits stderr lines per D-09 (precedence) and the VAULT-08 detection report.
    """
    cwd_resolved = cwd.resolve()
    is_vault = is_obsidian_vault(cwd_resolved)

    # CLI flag wins over profile (D-08, D-10): treat as literal CWD-relative or absolute
    if cli_output is not None:
        cli_path = Path(cli_output)
        flag_path = (
            cli_path.resolve()
            if cli_path.is_absolute()
            else (cwd_resolved / cli_output).resolve()
        )
        ...
            print(
                f"[graphify] vault detected at {cwd_resolved} — "
                f"output: {flag_path} (source=cli-flag)",
                file=sys.stderr,
            )
            print(
                f"[graphify] --output={cli_output} overrides profile output "
                f"({profile_mode_label}, path={flag_path})",
                file=sys.stderr,
            )
            return ResolvedOutput(True, cwd_resolved, flag_path, artifacts_dir, "cli-flag")
        # No vault, explicit flag: silent (no precedence line — nothing to override)
        return ResolvedOutput(False, None, flag_path, flag_path, "cli-flag")
```

Repo identity should mirror this: resolve once, make the source explicit, print a single `[graphify]` stderr line only when appropriate, and keep no-vault/no-profile fallback deterministic and quiet except for the required winning-source report.

**Hash key and traversal rejection pattern** (`graphify/cache.py` lines 32-67):
```python
def _sanitize_model_id(model_id: str) -> str:
    """Reject path-like model_id values (cache poisoning / traversal)."""
    if ".." in model_id or "/" in model_id or "\\" in model_id:
        raise ValueError("model_id must not contain path segments or '..'")
    if not model_id:
        return ""
    # Reasonable length cap
    if len(model_id) > 512:
        raise ValueError("model_id too long")
    return model_id


def file_hash(path: Path, model_id: str = "") -> str:
    """SHA256 of file contents + resolved path, optional ROUTE-04 model_id suffix."""
    _sanitize_model_id(model_id)
    inner = _inner_hash(path)
    return _cache_key_string(inner, model_id)
```

Use the same reject-then-hash approach for repo identity slugs and community signature keys. Do not let repo identity or LLM titles become path segments until after validation and final sink-specific sanitization.

**Sidecar JSON read/write pattern** (`graphify/merge.py` lines 1066-1098):
```python
def _load_manifest(manifest_path: Path) -> dict[str, dict]:
    """Load vault-manifest.json, returning {} on missing or corrupt."""
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            "[graphify] vault-manifest.json corrupted or unreadable — treating all notes as unmodified",
            file=sys.stderr,
        )
        return {}


def _save_manifest(manifest_path: Path, manifest: dict[str, dict]) -> None:
    """Write manifest atomically via tmp + os.replace (D-05)."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        os.replace(tmp, manifest_path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

Concept naming cache/provenance should live under `graphify-out/` using this tolerant load and atomic save style. Corrupt cache should warn and fall back, not abort export.

**Output manifest atomic write variant** (`graphify/detect.py` lines 385-439):
```python
def _save_output_manifest(
    artifacts_dir: Path,
    notes_dir: Path,
    written_files: list[str],
    run_id: str | None = None,
) -> None:
    """Append a run entry and write output-manifest.json atomically (D-29)."""
    ...
    tmp = manifest_path.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(manifest, indent=2, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, manifest_path)
    except OSError:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        raise
```

Use this stronger fsync variant if the naming cache is treated as a run manifest. Use `sort_keys=True` for stable diffs.

### `graphify/profile.py` (config, request-response validation)

**Analog:** `graphify/profile.py`

**Default profile and allowlisted top-level keys** (lines 62-155):
```python
_DEFAULT_PROFILE: dict = {
    "taxonomy": {
        "version": "v1.8",
        "root": "Atlas/Sources/Graphify",
        ...
    },
    "folder_mapping": {
        "moc": "Atlas/Sources/Graphify/MOCs/",
        ...
    },
    "naming": {"convention": "title_case"},
    ...
}

_VALID_TOP_LEVEL_KEYS = {
    "folder_mapping", "naming", "merge", "mapping_rules", "obsidian",
    "topology", "mapping", "tag_taxonomy", "profile_sync", "diagram_types",
    "output", "taxonomy",
    "extends", "includes", "community_templates",
    "dataview_queries",
}
```

Add `repo` as a top-level key, not under `naming`. Add concept naming controls under the existing `naming` block only if the planner chooses that schema.

**Validation accumulator pattern** (lines 543-558 and 697-709):
```python
def validate_profile(profile: dict) -> list[str]:
    """Validate a profile dict. Returns a list of error strings — empty means valid."""
    if not isinstance(profile, dict):
        return ["Profile must be a YAML mapping (dict)"]

    errors: list[str] = []

    # Unknown top-level keys
    for key in profile:
        if key not in _VALID_TOP_LEVEL_KEYS:
            errors.append(f"Unknown profile key '{key}' — valid keys are: {sorted(_VALID_TOP_LEVEL_KEYS)}")
    ...
    # naming section
    naming = profile.get("naming")
    if naming is not None:
        if not isinstance(naming, dict):
            errors.append("'naming' must be a mapping (dict)")
        else:
            convention = naming.get("convention")
            if convention is not None and convention not in _VALID_NAMING_CONVENTIONS:
                errors.append(
                    f"Invalid naming convention '{convention}' — "
                    f"valid values are: {sorted(_VALID_NAMING_CONVENTIONS)}"
                )
```

Repo and naming-control schema checks should accumulate errors, validate types explicitly, and never raise. Match existing message style with dotted paths such as `repo.identity` or `naming.concept_names.enabled`.

**Safety helper pattern** (lines 1028-1098):
```python
def safe_tag(name: str) -> str:
    """Slugify a community name into a valid Obsidian tag component."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if slug and slug[0].isdigit():
        slug = "x" + slug
    return slug or "community"


def safe_filename(label: str, max_len: int = 200) -> str:
    """Sanitize a label for use as a filename."""
    name = unicodedata.normalize("NFC", label)
    name = re.sub(
        r'[\\/*?:"<>|#^[\]\x00-\x1f\x7f\u0085\u2028\u2029]', "", name
    ).strip() or "unnamed"
    if len(name) > max_len:
        suffix = hashlib.sha256(name.encode()).hexdigest()[:8]
        name = name[:max_len - 9] + "_" + suffix
    return name
```

Do not duplicate sink sanitizers inside `naming.py`. Validate candidates for broad safety, then route accepted/fallback titles through `safe_filename`, `safe_tag`, `_emit_wikilink`, and `_dump_frontmatter` at their existing sinks.

### `graphify/__main__.py` (CLI route, request-response)

**Analog:** existing `--obsidian` and `run` parsing branches.

**Help text pattern** (`graphify/__main__.py` lines 1170-1193):
```python
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print("Usage: graphify <command>")
    ...
    print("  --obsidian              export an already-built graphify-out/graph.json to an Obsidian vault (MRG-03)")
    print("    --graph <path>          path to graph.json (default graphify-out/graph.json)")
    print("    --obsidian-dir <path>   output vault directory (default graphify-out/obsidian)")
    print("    --dry-run               print the merge plan via format_merge_plan without writing files")
    print("    --force                 force update of user-modified notes (preserves sentinel blocks)")
```

Add `--repo-identity <slug>` to help in both relevant command sections if planner selects that flag. Keep wording direct and command-local.

**Manual argv parsing for `--obsidian`** (lines 1359-1395):
```python
if cmd == "--obsidian":
    graph_path = "graphify-out/graph.json"
    obsidian_dir = "graphify-out/obsidian"
    dry_run = False
    force = False
    obsidian_dedup = False
    user_passed_obsidian_dir = False
    cli_output: str | None = None
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--graph" and i + 1 < len(args):
            graph_path = args[i + 1]; i += 2
        ...
        elif args[i] == "--output" and i + 1 < len(args):
            cli_output = args[i + 1]; i += 2
        elif args[i].startswith("--output="):
            cli_output = args[i].split("=", 1)[1]; i += 1
        ...
        else:
            print(f"error: unknown --obsidian option: {args[i]}", file=sys.stderr)
            sys.exit(2)

    from graphify.output import resolve_output
    resolved = resolve_output(Path.cwd(), cli_output=cli_output)
```

Parse `--repo-identity` and `--repo-identity=` in the same loop. Unknown options exit `2`; missing value should follow the existing unknown/usage style rather than silently defaulting.

**Manual argv parsing for `run`** (lines 2189-2217):
```python
# graphify run [path] [--router] [--output <path>]
from graphify.pipeline import run_corpus
from graphify.output import resolve_output

rest = list(sys.argv[2:])
use_router = "--router" in rest
rest = [a for a in rest if a != "--router"]

# Parse --output / --output=<path> (D-08 unified override flag)
cli_output: str | None = None
filtered: list[str] = []
i = 0
while i < len(rest):
    if rest[i] == "--output" and i + 1 < len(rest):
        cli_output = rest[i + 1]; i += 2
    elif rest[i].startswith("--output="):
        cli_output = rest[i].split("=", 1)[1]; i += 1
    else:
        filtered.append(rest[i]); i += 1
rest = filtered
raw_target = rest[0] if rest else "."

resolved = resolve_output(Path.cwd(), cli_output=cli_output)
```

Add repo identity parsing before `raw_target` selection so the flag is removed from positional arguments. Prefer passing `cli_repo_identity` into a resolver over reimplementing precedence in CLI branches.

### `graphify/export.py` (export service, file-I/O)

**Analog:** `to_obsidian()` and visualization community labels.

**Signature and local import pattern** (lines 518-555):
```python
def to_obsidian(
    G: nx.Graph,
    communities: dict[int, list[str]],
    output_dir: str,
    *,
    profile: dict | None = None,
    community_labels: dict[int, str] | None = None,
    cohesion: dict[int, float] | None = None,
    dry_run: bool = False,
    force: bool = False,
    obsidian_dedup: bool = False,
) -> "MergeResult | MergePlan":
    """Export graph as an Obsidian vault using the profile-driven pipeline."""
    # Function-local imports so `graphify install` ... doesn't force heavy deps at CLI entry time.
    from graphify.profile import load_profile
    from graphify.mapping import classify
    from graphify.templates import render_note, render_moc
    from graphify.merge import (
        compute_merge_plan,
        apply_merge_plan,
        RenderedNote,
        split_rendered_note,
        _load_manifest,
    )
```

Keep imports of `naming.py` local if they would pull optional dependencies or create cycles. Add optional keyword arguments rather than breaking positional API.

**Manifest and profile load pattern** (lines 574-585):
```python
# Manifest lives in the parent of the vault dir (typically graphify-out/).
_vault_dir = out.resolve()
manifest_path = _vault_dir.parent / "vault-manifest.json"
manifest = _load_manifest(manifest_path)

# D-74: always run the new pipeline. No `if profile is None` branching.
if profile is None:
    profile = load_profile(out)

mapping_result = classify(G, communities, profile, cohesion=cohesion)
```

Concept naming sidecar should use `out.resolve().parent` / artifacts dir, not vault-owned `.graphify/`.

**Community label injection pattern** (lines 590-599):
```python
# community_labels flows through per_community context — when caller
# passes display labels, inject them as community_name override into
# the matching ClassificationContext so render_moc picks them up.
if community_labels:
    for cid, label in community_labels.items():
        if cid in per_community:
            ctx = dict(per_community[cid])
            ctx.setdefault("community_name", label)
            per_community[cid] = ctx
```

`resolve_concept_names()` should feed this existing surface. If Phase 33 wants generated names to override mapping-derived names, planner should use assignment instead of `setdefault`; otherwise preserve current mapping labels.

**Dry-run pattern** (lines 675-687):
```python
plan = compute_merge_plan(
    out, rendered_notes, profile,
    skipped_node_ids=skipped,
    manifest=manifest,
    force=force,
)
if dry_run:
    return plan
return apply_merge_plan(
    plan, out, rendered_notes, profile,
    manifest_path=manifest_path,
    old_manifest=manifest,
)
```

If naming sidecar writes are added, ensure `dry_run=True` does not write generated cache files. Provenance can be returned or printed, but persistent writes belong only on full run.

### `graphify/mapping.py` (mapper utility, transform)

**Analog:** `_derive_community_label()` and `_assemble_communities()`.

**Current fallback label pattern to replace/augment** (lines 416-430):
```python
def _derive_community_label(G: nx.Graph, members: list[str], cid: int) -> str:
    """D-58: community label = top-god-node-in-community label."""
    ranked = sorted(
        (m for m in members if not _is_file_node(G, m) and not _is_concept_node(G, m)),
        key=lambda m: (-G.degree(m), m),
    )
    if not ranked:
        return f"Community {cid}"
    top = ranked[0]
    return str(G.nodes[top].get("label", top))
```

Use this as the minimal deterministic baseline, but Phase 33 should move stronger top-term plus suffix logic into `graphify/naming.py` so mapping can stay focused on classification.

**Per-community context assembly pattern** (lines 578-603):
```python
labels: dict[int, str] = {
    cid: _derive_community_label(G, communities[cid], cid)
    for cid in communities
}
...
for cid in above_cids:
    name = labels[cid]
    tag = safe_tag(name)
    per_community[cid] = ClassificationContext(
        note_type="moc",
        folder=moc_folder,
        community_name=name,
        parent_moc_label=name,
        community_tag=tag,
        members_by_type={"thing": [], "statement": [], "person": [], "source": []},
        sub_communities=[],
        sibling_labels=[],
        cohesion=float(cohesion.get(cid, 0.0)) if cohesion else 0.0,
    )
```

Planner should either pass resolved labels into export after `classify()` or replace `labels` with helper-provided labels while preserving the same `ClassificationContext` keys.

### `graphify/templates.py` (renderer utility, transform + final sink)

**Analog:** `resolve_filename()`, `_emit_wikilink()`, `_render_moc_like()`.

**Final filename sink pattern** (lines 103-128):
```python
def resolve_filename(label: str, convention: str) -> str:
    """Convert a node label to a filename stem (no .md extension)."""
    if convention == "title_case":
        words = re.split(r"[ \t_]+", label)
        result = "_".join(w.capitalize() for w in words if w)
    elif convention == "kebab-case":
        words = re.split(r"[ \t_]+", label.lower())
        result = "-".join(w for w in words if w)
    else:  # "preserve" or unknown → fall through to safe_filename
        result = label
    return safe_filename(result)
```

Do not pre-render filenames in `naming.py` unless needed for cache/provenance. Display names should still pass through this sink before disk write.

**Wikilink alias pattern** (lines 649-667):
```python
def _sanitize_wikilink_alias(label: str) -> str:
    """Replace characters that would break wikilink alias syntax."""
    out = label
    for bad, repl in _WIKILINK_ALIAS_FORBIDDEN.items():
        out = out.replace(bad, repl)
    out = _WIKILINK_ALIAS_CONTROL_RE.sub(" ", out)
    return out


def _emit_wikilink(label: str, convention: str) -> str:
    """Return `[[filename|label]]` auto-aliased to display label."""
    fname = resolve_filename(label, convention)
    alias = _sanitize_wikilink_alias(label)
    return f"[[{fname}|{alias}]]"
```

LLM-generated labels must be considered unsafe until they pass this path for wikilinks and `safe_frontmatter_value()` for YAML.

**MOC render input contract** (lines 1251-1261 and 1270-1291):
```python
# Derive community display name. Preference order:
#   1. ctx["community_name"]  (explicit; Phase 3 populates for MOC/Community Overview)
#   2. ctx["parent_moc_label"] (fallback — Phase 3 may put MOC self-label here)
#   3. "Community {id}"
community_name: str = (
    ctx.get("community_name")
    or ctx.get("parent_moc_label")
    or f"Community {community_id}"
)
community_tag = ctx.get("community_tag") or safe_tag(community_name)
...
fm_fields = _build_frontmatter_fields(
    ...
    tags=tags,
    note_type="moc" if template_key == "moc" else "community",
    ...
    community=community_name,
    created=created if created is not None else datetime.date.today(),
    cohesion=cohesion,
)
```

Phase 33 concept names should arrive as `ctx["community_name"]` and let templates compute tag/frontmatter/filename consistently.

### `tests/test_naming.py` (test, transform + file-I/O)

**Analogs:** `tests/test_output.py`, `tests/test_cache.py`

**Pure resolver tests with `tmp_path` and `capsys`** (`tests/test_output.py` lines 59-71 and 160-172):
```python
def test_resolve_output_no_vault_default_paths(tmp_path, capsys):
    result = resolve_output(tmp_path)
    assert result == ResolvedOutput(
        vault_detected=False,
        vault_path=None,
        notes_dir=Path("graphify-out/obsidian"),
        artifacts_dir=Path("graphify-out"),
        source="default",
    )
    captured = capsys.readouterr()
    assert "vault detected" not in captured.err
    assert "[graphify]" not in captured.err


def test_resolve_output_cli_flag_overrides_profile_emits_stderr(tmp_path, capsys):
    pytest.importorskip("yaml")
    vault = _setup_vault(tmp_path, "output:\n  mode: vault-relative\n  path: Notes\n")
    result = resolve_output(vault, cli_output="custom-out")
    assert result.source == "cli-flag"
    captured = capsys.readouterr()
    assert "--output=custom-out overrides profile output" in captured.err
    assert captured.err.count("overrides profile output") == 1
```

Use these for repo identity precedence: CLI wins, profile wins, git remote fallback wins, cwd fallback wins, winning source message emitted once.

**Cache roundtrip and miss tests** (`tests/test_cache.py` lines 46-60 and 126-140):
```python
def test_cache_roundtrip(tmp_file, cache_root):
    """Save then load returns the same result dict."""
    result = {"nodes": [{"id": "n1", "label": "Node1"}], "edges": []}
    save_cached(tmp_file, result, root=cache_root)
    loaded = load_cached(tmp_file, root=cache_root)
    assert loaded == result


def test_model_id_splits_cache(tmp_path, cache_root):
    """ROUTE-04: different model_id → different cache paths; empty matches legacy key."""
    f = tmp_path / "a.py"
    f.write_text("print(1)", encoding="utf-8")
    h0 = file_hash(f)
    h1 = file_hash(f, model_id="m-a")
    h2 = file_hash(f, model_id="m-b")
    assert h0 != h1
    assert h1 != h2
```

Use these for concept naming cache exact signature reuse, corrupt cache fallback, and small-change tolerant source provenance.

### `tests/test_profile.py` (test, config validation)

**Analog:** existing profile validation tests.

**Profile loading and error reporting pattern** (lines 65-102):
```python
def test_load_profile_with_yaml(tmp_path):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text(
        'taxonomy:\n'
        '  version: "v1.8"\n'
        '  root: "Custom/Graphify"\n'
        ...
        encoding="utf-8",
    )
    result = load_profile(tmp_path)
    assert result["folder_mapping"]["moc"] == "Custom/Graphify/Maps/"


def test_load_profile_invalid_yaml_prints_errors(tmp_path, capsys):
    profile_dir = tmp_path / ".graphify"
    profile_dir.mkdir()
    (profile_dir / "profile.yaml").write_text("unknown_key: 1\n", encoding="utf-8")
    result = load_profile(tmp_path)
    captured = capsys.readouterr()
    assert "[graphify] profile error:" in captured.err
    assert "Unknown profile key 'unknown_key'" in captured.err
    assert result == _deep_merge(_DEFAULT_PROFILE, {})
```

Add tests for valid `repo.identity`, invalid `repo` type, invalid `repo.identity` type/empty/path-like value, and valid/invalid concept naming controls.

**Validation accumulator pattern** (lines 125-155 and 209-214):
```python
def test_validate_profile_valid_empty_dict():
    assert validate_profile({}) == []


def test_validate_profile_unknown_key():
    errors = validate_profile({"bad_key": 1})
    assert len(errors) == 1
    assert "Unknown profile key 'bad_key'" in errors[0]


def test_validate_profile_collects_multiple_errors():
    """D-03: collect all errors, not fail-on-first."""
    profile = {"key1": 1, "key2": 2, "key3": 3}
    errors = validate_profile(profile)
    assert len(errors) == 3
```

Preserve the collect-all-errors behavior for new schema keys.

### `tests/test_export.py` (test, file-I/O dry-run)

**Analog:** existing `to_obsidian()` dry-run tests.

**Minimal graph + dry-run pattern** (lines 191-230):
```python
def test_to_obsidian_no_profile_dry_run_uses_graphify_default_paths(tmp_path):
    from graphify.export import to_obsidian
    import networkx as nx

    G = nx.Graph()
    G.add_node(
        "transformer",
        label="Transformer",
        file_type="code",
        source_file="model.py",
        source_location="L1",
        community=0,
    )
    G.add_node(
        "softmax",
        label="Softmax",
        file_type="code",
        source_file="model.py",
        source_location="L2",
        community=0,
    )
    G.add_edge("transformer", "softmax", relation="calls", confidence="EXTRACTED")
    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()

    plan = to_obsidian(
        G,
        communities={0: ["transformer", "softmax"]},
        output_dir=str(obsidian_dir),
        dry_run=True,
    )
```

Use this for proving resolved concept labels appear in MOC paths/plan actions and that `dry_run=True` does not persist naming sidecar files.

**Community label visualization test pattern** (lines 110-118):
```python
def test_to_html_contains_legend_with_labels():
    G = make_graph()
    communities = cluster(G)
    labels = {cid: f"Group {cid}" for cid in communities}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "graph.html"
        to_html(G, communities, str(out), community_labels=labels)
        content = out.read_text()
        assert "Group 0" in content
```

For `to_obsidian()`, assert the same community label surface with rendered filenames/frontmatter instead of HTML content.

### `tests/test_main_flags.py` (test, CLI subprocess)

**Analog:** existing `--output` CLI flag wiring.

**Subprocess helper pattern** (lines 12-36):
```python
def _graphify(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke `python -m graphify <args>` in cwd, return CompletedProcess."""
    full_env = os.environ.copy()
    worktree_root = Path(__file__).resolve().parent.parent
    existing_pp = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = (
        f"{worktree_root}{os.pathsep}{existing_pp}" if existing_pp else str(worktree_root)
    )
    if env:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-m", "graphify", *args],
        cwd=str(cwd),
        env=full_env,
        capture_output=True,
        text=True,
        timeout=60,
    )
```

Use this for end-to-end `--repo-identity` parsing in both `run` and `--obsidian`.

**Flag precedence assertion pattern** (lines 125-143 and 167-187):
```python
def test_run_output_flag_overrides_profile_emits_d09_line(tmp_path):
    pytest.importorskip("yaml")
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / ".obsidian").mkdir()
    (vault / ".graphify").mkdir()
    (vault / ".graphify" / "profile.yaml").write_text(
        _V18_PROFILE_BASE + "output:\n  mode: vault-relative\n  path: Atlas/Generated\n"
    )
    custom = tmp_path / "elsewhere"
    result = _graphify(["run", "--output", str(custom), "--router"], cwd=vault)
    assert f"--output={custom} overrides profile output" in result.stderr
    assert result.stderr.count("overrides profile output") == 1


def test_obsidian_output_flag_takes_precedence_over_obsidian_dir(tmp_path):
    ...
    result = _graphify(
        ["--obsidian", "--graph", str(vault / "graph.json"),
         "--obsidian-dir", str(tmp_path / "loser"),
         "--output", str(custom), "--force"],
        cwd=vault,
    )
    assert f"--output={custom} overrides profile output" in result.stderr
```

Mirror these for `--repo-identity` > profile `repo.identity` > fallback. Assert source text and avoid exact full-output snapshots.

## Shared Patterns

### Source Precedence and Diagnostics

**Source:** `graphify/output.py`

**Apply to:** `graphify/naming.py`, `graphify/__main__.py`, tests.

Use a pure resolver with explicit source strings, and let CLI/export consume the result. Emit `[graphify]` stderr messages in the resolver rather than spreading precedence reporting across command branches.

### Profile Schema Validation

**Source:** `graphify/profile.py`

**Apply to:** `repo:` and concept naming config.

All new profile keys must be allowlisted, type-checked, and accumulated as error strings. Do not raise from `validate_profile()`.

### Generated Sidecar IO

**Source:** `graphify/cache.py`, `graphify/merge.py`, `graphify/detect.py`

**Apply to:** concept naming cache/provenance.

Load missing/corrupt JSON defensively, write atomically with tmp + `os.replace`, and keep generated state under `graphify-out/`.

### Final Sink Sanitization

**Source:** `graphify/profile.py`, `graphify/templates.py`

**Apply to:** LLM concept titles and repo identity surfaces.

Validate raw candidates early, but continue using existing sink helpers for filenames, tags, wikilinks, Dataview substitution values, and frontmatter. Do not treat one sanitizer as universal.

### Dry-Run Discipline

**Source:** `graphify/export.py`

**Apply to:** `to_obsidian()` concept naming integration.

Dry-run can compute plans and provenance, but must not write note files or naming sidecars.

## No Analog Found

No planned file lacks an analog. The only new module, `graphify/naming.py`, should compose established patterns from `output.py`, `cache.py`, `merge.py`, `mapping.py`, and `templates.py`.

## Metadata

**Analog search scope:** `graphify/*.py`, `tests/test_*.py`, phase `33-CONTEXT.md`, phase `33-RESEARCH.md`
**Files scanned:** 14
**Pattern extraction date:** 2026-04-28
