"""Vault detection and output destination resolution (Phase 27).

Resolves the (vault, notes_dir, artifacts_dir, source) tuple consumed by
the run/--obsidian commands, Phase 28 self-ingest pruning, and Phase 29
doctor diagnostics.

Decisions implemented:
  - D-04: strict CWD-only `.obsidian/` detection (no parent walk)
  - D-05: vault detected + missing profile -> refuse loudly
  - D-02: vault detected + profile missing 'output:' block -> refuse loudly
  - D-08: --output flag > profile.output > v1.0 defaults
  - D-09: precedence stderr line emitted exactly once when --output overrides profile
  - D-11: build artifacts ALWAYS sibling-of-vault when auto-adopt fires
  - D-12: no vault, no flag -> byte-identical v1.0 paths, silent stderr
  - D-13: single ResolvedOutput data structure consumed by Phase 28/29

Phase 41 (VCLI-01..02) — resolve_execution_paths precedence (single source of truth for help/README):
  1. explicit_vault (--vault PATH)
  2. GRAPHIFY_VAULT env (when set and non-empty)
  3. --vault-list file: all valid vault roots on distinct lines; one root → use it; several → TTY
     interactive pick, non-TTY → exit 2 with candidate list (Phase 41 D-03).
  4. CWD-only resolve_output(cwd, cli_output=...) — Phase 27 behavior
  When cli_output is set, inner resolution may yield source=cli-flag (D-02); pin kinds apply only to profile-driven rows.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, NamedTuple

# Phase 41: vault-cli / vault-env / vault-list pin kinds for doctor/CLI banners (VCLI-01..03).
ResolvedSource = Literal[
    "profile",
    "cli-flag",
    "default",
    "vault-cli",
    "vault-env",
    "vault-list",
]


class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: ResolvedSource
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14


def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection (D-04). No parent-walking."""
    return (path / ".obsidian").is_dir()


def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)


def _ensure_vault_root(path: Path) -> Path:
    """Resolve *path* and require a directory with `.obsidian/` (Phase 41 pin validation)."""
    p = path.expanduser().resolve()
    if not p.is_dir():
        raise _refuse(f"Vault path is not a directory: {p}")
    if not is_obsidian_vault(p):
        raise _refuse(
            f"Not an Obsidian vault (missing .obsidian/ directory): {p}"
        )
    return p


def _list_vault_roots_from_list_file(list_file: Path, cwd_resolved: Path) -> tuple[Path, list[Path]]:
    """Resolve list file path and return ``(list_path, vault_roots)`` in line order (D-03)."""
    lp = list_file if list_file.is_absolute() else (cwd_resolved / list_file).resolve()
    if not lp.is_file():
        raise _refuse(f"--vault-list file not found: {lp}")
    try:
        raw = lp.read_text(encoding="utf-8")
    except OSError as exc:
        raise _refuse(f"Cannot read --vault-list file {lp}: {exc}") from exc
    roots: list[Path] = []
    seen: set[Path] = set()
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        candidate = Path(s).expanduser()
        root = candidate.resolve() if candidate.is_absolute() else (cwd_resolved / candidate).resolve()
        if is_obsidian_vault(root) and root not in seen:
            seen.add(root)
            roots.append(root)
    return lp, roots


def _pick_vault_from_list_file(list_file: Path, cwd_resolved: Path) -> Path:
    """Pick vault root from --vault-list file (single root or interactive multi-root; D-03)."""
    lp, roots = _list_vault_roots_from_list_file(list_file, cwd_resolved)
    if not roots:
        raise _refuse(
            f"No valid Obsidian vault roots found in --vault-list file: {lp}"
        )
    if len(roots) == 1:
        return roots[0]
    if sys.stderr.isatty() and sys.stdin.isatty():
        print(
            "[graphify] Multiple vault roots in --vault-list file; choose one:",
            file=sys.stderr,
        )
        for idx, p in enumerate(roots, start=1):
            print(f"  [{idx}] {p}", file=sys.stderr)
        while True:
            try:
                raw = input("Enter number (1-{}): ".format(len(roots)))
                n = int(raw.strip())
                if 1 <= n <= len(roots):
                    return roots[n - 1]
            except (ValueError, EOFError):
                pass
            print("[graphify] Invalid choice; try again.", file=sys.stderr)
    print(
        "[graphify] Multiple vault roots in --vault-list file; non-interactive session.",
        file=sys.stderr,
    )
    print(
        "Pin one vault with --vault PATH or GRAPHIFY_VAULT, or pass a list with one candidate:",
        file=sys.stderr,
    )
    for idx, p in enumerate(roots, start=1):
        print(f"  [{idx}] {p}", file=sys.stderr)
    raise SystemExit(2)


def resolve_execution_paths(
    cwd: Path,
    *,
    cli_output: str | None = None,
    explicit_vault: Path | None = None,
    env_vault: str | None = None,
    vault_list_file: Path | None = None,
) -> ResolvedOutput:
    """Resolve output using optional vault pins before CWD-only detection (Phase 41).

    Precedence: explicit_vault > GRAPHIFY_VAULT (non-empty) > --vault-list file > ``resolve_output(cwd)``.
    See module docstring for full ordering. Multi-root ``--vault-list`` handling uses stdin on TTY.
    """
    cwd_r = cwd.resolve()
    pin_kind: Literal["vault-cli", "vault-env", "vault-list"] | None = None
    effective_root: Path | None = None

    if explicit_vault is not None:
        effective_root = _ensure_vault_root(explicit_vault)
        pin_kind = "vault-cli"
        if cwd_r != effective_root:
            print(
                f"[graphify] --vault pin uses vault root {effective_root} (cwd={cwd_r})",
                file=sys.stderr,
            )
    elif env_vault and env_vault.strip():
        effective_root = _ensure_vault_root(Path(env_vault.strip()).expanduser())
        pin_kind = "vault-env"
    elif vault_list_file is not None:
        effective_root = _pick_vault_from_list_file(vault_list_file, cwd_r)
        pin_kind = "vault-list"

    if effective_root is None:
        return resolve_output(cwd, cli_output=cli_output)

    result = resolve_output(effective_root, cli_output=cli_output)
    if result.source == "cli-flag":
        return result
    if pin_kind is not None and result.source == "profile":
        return result._replace(source=pin_kind)
    return result


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
        if is_vault:
            # Determine artifacts placement: always sibling-of-vault per D-11
            artifacts_dir = (
                (cwd_resolved.parent / "graphify-out").resolve()
                if cwd_resolved.parent != cwd_resolved
                else flag_path
            )
            # D-09 message reconcile: load profile (if present) so we can report
            # the mode being overridden. Use distinct format when no profile
            # output exists.
            profile_mode_label = "(profile-not-applicable)"
            profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
            if profile_yaml.exists():
                try:
                    import yaml  # noqa: F401
                    from graphify.profile import load_profile

                    prof = load_profile(cwd_resolved)
                    out_block = prof.get("output") if isinstance(prof, dict) else None
                    if isinstance(out_block, dict) and out_block.get("mode"):
                        profile_mode_label = f"mode={out_block['mode']}"
                except Exception:
                    # Loading the profile is best-effort for the message only;
                    # never fail the override path because of profile parse issues.
                    pass
            # Detection report (VAULT-08) + D-09 precedence line
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

    # No vault -> v1.0 backcompat (D-12) — silent, byte-identical paths
    if not is_vault:
        return ResolvedOutput(
            vault_detected=False,
            vault_path=None,
            notes_dir=Path("graphify-out/obsidian"),
            artifacts_dir=Path("graphify-out"),
            source="default",
        )

    # Vault detected -> require .graphify/profile.yaml (D-05)
    profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
    if not profile_yaml.exists():
        raise _refuse(
            f"CWD is an Obsidian vault ({cwd_resolved}) but no .graphify/profile.yaml found. "
            "Create one (see docs/vault-adapter.md), or pass --output <path> to write outside the vault."
        )

    # Function-local imports avoid circular dependency (output -> profile, never reverse)
    try:
        import yaml  # noqa: F401
    except ImportError:
        raise _refuse(
            f"CWD is an Obsidian vault ({cwd_resolved}) but PyYAML is not installed. "
            "Install with: pip install graphifyy[obsidian]"
        )

    from graphify.profile import load_profile

    profile = load_profile(cwd_resolved)
    output_block = profile.get("output")
    if not output_block or not isinstance(output_block, dict):
        raise _refuse(
            f"CWD is an Obsidian vault ({cwd_resolved}) but profile.yaml has no 'output:' block. "
            "Declare 'output: {mode: ..., path: ...}' or pass --output <path>."
        )

    mode = output_block.get("mode")
    path_val = output_block.get("path")

    if mode == "vault-relative":
        # Lazy import — Plan 27-01 is the source of truth for path validators.
        from graphify.profile import validate_vault_path
        notes_dir = validate_vault_path(path_val, cwd_resolved)
    elif mode == "absolute":
        if not isinstance(path_val, str) or not Path(path_val).is_absolute():
            raise _refuse(
                f"profile output.path must be absolute when mode=absolute (got {path_val!r})"
            )
        notes_dir = Path(path_val).resolve()
    elif mode == "sibling-of-vault":
        # Lazy import — `validate_sibling_path` ships in Plan 27-01 (parallel wave).
        # Keeping this import inside the branch lets the rest of resolve_output()
        # function correctly when the sibling-of-vault mode is not exercised.
        from graphify.profile import validate_sibling_path
        notes_dir = validate_sibling_path(path_val, cwd_resolved)
    else:
        raise _refuse(f"profile output.mode {mode!r} invalid")

    # D-11: build artifacts ALWAYS sibling-of-vault when auto-adopt fires
    artifacts_dir = (cwd_resolved.parent / "graphify-out").resolve()

    # VAULT-08 detection report (terse single-line)
    print(
        f"[graphify] vault detected at {cwd_resolved} — "
        f"output: {notes_dir} (source=profile)",
        file=sys.stderr,
    )
    _raw_exclude = profile.get("output", {}).get("exclude", [])
    _exclude_globs: tuple[str, ...] = tuple(_raw_exclude) if isinstance(_raw_exclude, list) else ()
    return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "profile", _exclude_globs)
