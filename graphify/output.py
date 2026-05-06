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

import contextlib
import io
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
    "option-b",
]


class ResolvedOutput(NamedTuple):
    vault_detected: bool
    vault_path: Path | None
    notes_dir: Path
    artifacts_dir: Path
    source: ResolvedSource
    exclude_globs: tuple[str, ...] = ()   # Phase 28 D-14


def default_graphify_artifacts_dir(
    target: Path,
    *,
    resolved: ResolvedOutput | None = None,
) -> Path:
    """Directory for routing audits and sidecars when no explicit ``out_dir`` is passed.

    For ``source=default`` (non-vault), use :attr:`Path.cwd` plus profile-relative
    ``artifacts_dir`` so output stays a single top-level ``graphify-out/`` instead
    of nesting under an arbitrary corpus subdirectory (**HYG-05** / Phase 48).
    """
    if resolved is not None and resolved.source == "default":
        return (Path.cwd() / resolved.artifacts_dir).resolve()
    return target / "graphify-out" if target.is_dir() else target.parent / "graphify-out"


def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection (D-04). No parent-walking."""
    return (path / ".obsidian").is_dir()


def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)


EXIT_VAULT_REFUSAL = 1
EXIT_VAULT_GATE = 2


def _emit_vault_error(msg: str, hint: str, *, code: int = EXIT_VAULT_REFUSAL) -> SystemExit:
    """Emit [graphify] error: + hint: lines to stderr and return SystemExit(code).

    VAUX-02: two-line format mirrors doctor.py _FIX_HINTS pattern (D-05).
    Callers: raise _emit_vault_error(msg, hint, code=...)

    Exit-code policy (EXIT-CODE-CONST-01, Phase 62-02):
      - ``EXIT_VAULT_REFUSAL`` (=1, default) — vault-policy refusals (no profile,
        write-into-vault guard, missing/invalid vault root).
      - ``EXIT_VAULT_GATE`` (=2) — VCWD-03 CWD-gate refusal: CWD is a vault, no
        profile present, and no override. Distinct exit code surfaces the gate
        diagnostic to downstream parsers.
    """
    print(f"[graphify] error: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    return SystemExit(code)


_OPTION_B_BREADCRUMB_EMITTED = False


def _reset_option_b_breadcrumb_for_tests() -> None:
    """Reset Option B emission sentinel (test-only helper).

    Phase 63 D-02 emits the Option B info breadcrumb exactly once per process.
    Unit tests that exercise the resolver multiple times in the same process
    (e.g., test_option_b_idempotent_across_calls) need to clear the sentinel
    between assertions. The CLI does not call this — it relies on each
    subprocess being its own process.
    """
    global _OPTION_B_BREADCRUMB_EMITTED
    _OPTION_B_BREADCRUMB_EMITTED = False


def _emit_vault_info(msg: str, hint: str, *, extra_hint: str | None = None) -> None:
    """Emit two- or three-line ``[graphify] info: ... / hint: ...`` breadcrumb (Phase 63 D-01).

    Used for advisory paths (e.g., Option B silent reroute) where no SystemExit
    is desired. Mirrors :func:`_emit_vault_error` shape so a future stderr
    snapshot test (Phase 64 AUDIT-A) can lock both prefixes uniformly.
    """
    print(f"[graphify] info: {msg}", file=sys.stderr)
    print(f"  hint: {hint}", file=sys.stderr)
    if extra_hint is not None:
        print(f"  hint: {extra_hint}", file=sys.stderr)


def emit_option_b_breadcrumb(vault_cwd: Path) -> None:
    """Emit the Option B info breadcrumb at most once per process (D-02).

    Used by both ``_check_vault_cwd_gate`` (CLI dispatch path, before any
    subcommand work runs) and :func:`resolve_output` (direct API path, e.g.,
    unit tests calling ``resolve_output`` directly). The sentinel ensures
    ``graphify run`` from a no-profile vault emits exactly two non-empty
    stderr lines (gate fires → resolver suppresses).
    """
    global _OPTION_B_BREADCRUMB_EMITTED
    if _OPTION_B_BREADCRUMB_EMITTED:
        return
    _OPTION_B_BREADCRUMB_EMITTED = True
    artifacts_dir = (vault_cwd / ".graphify-out").resolve()
    # Phase 63 D-01 third hint: detect-only signal that pre-v1.13 legacy
    # `graphify-out/` artifacts coexist with the new Option B reroute target.
    # No move, no delete, no migration (D-04). Surfaces as advisory `hint:`
    # so users know to run `graphify doctor`.
    extra: str | None = None
    if (vault_cwd / "graphify-out").is_dir():
        extra = "legacy graphify-out/ detected — run `graphify doctor` to review"
    _emit_vault_info(
        "vault CWD without .graphify/profile.yaml — Option B reroute active",
        f"outputs → {artifacts_dir}/",
        extra_hint=extra,
    )


def _ensure_vault_root(path: Path) -> Path:
    """Resolve *path* and require a directory with `.obsidian/` (Phase 41 pin validation)."""
    p = path.expanduser().resolve()
    if not p.is_dir():
        raise _emit_vault_error(
            f"Vault path is not a directory: {p}",
            "Check the path exists and is a directory, not a file.",
            code=EXIT_VAULT_REFUSAL,
        )
    if not is_obsidian_vault(p):
        raise _emit_vault_error(
            f"Not an Obsidian vault (missing .obsidian/ directory): {p}",
            "Pass the root of an Obsidian vault (must contain .obsidian/).",
            code=EXIT_VAULT_REFUSAL,
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
    print(
        "  hint: Re-run from a TTY to pick interactively, or pass --vault explicitly.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def resolve_execution_paths(
    cwd: Path,
    *,
    cli_output: str | None = None,
    explicit_vault: Path | None = None,
    env_vault: str | None = None,
    vault_list_file: Path | None = None,
    obsidian_dir_override: bool = False,
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
        return resolve_output(
            cwd,
            cli_output=cli_output,
            obsidian_dir_override=obsidian_dir_override,
        )

    result = resolve_output(
        effective_root,
        cli_output=cli_output,
        obsidian_dir_override=obsidian_dir_override,
    )
    if result.source == "cli-flag":
        return result
    if pin_kind is not None and result.source == "profile":
        return result._replace(source=pin_kind)
    return result


def resolve_vault_for_parity(
    cwd: Path,
    *,
    explicit_vault: Path | None = None,
    env_vault: str | None = None,
    vault_list_file: Path | None = None,
) -> dict:
    """Return structured parity dict for VAUX-01 test assertions.

    Dict shape:
      {
        "vault_path": Path | None,       # resolved.vault_path
        "source": str,                   # resolved.source
        "profile_path": Path | None,     # vault/.graphify/profile.yaml or None
        "profile_mode": str | None,      # output.mode from profile, or None
        "warnings": list[str],           # stderr lines emitted during resolution
      }
    Calls resolve_execution_paths() — never duplicates resolution logic.
    """
    captured = io.StringIO()
    try:
        with contextlib.redirect_stderr(captured):
            resolved = resolve_execution_paths(
                cwd,
                explicit_vault=explicit_vault,
                env_vault=env_vault,
                vault_list_file=vault_list_file,
            )
    except SystemExit:
        raise

    warnings = [
        ln.strip() for ln in captured.getvalue().splitlines() if ln.strip()
    ]

    profile_path: Path | None = None
    profile_mode: str | None = None
    if resolved.vault_path is not None:
        pp = resolved.vault_path / ".graphify" / "profile.yaml"
        if pp.exists():
            profile_path = pp
            try:
                import yaml  # noqa: F401
                from graphify.profile import load_profile
                prof = load_profile(resolved.vault_path)
                out_block = prof.get("output") if isinstance(prof, dict) else None
                if isinstance(out_block, dict):
                    profile_mode = out_block.get("mode")
            except Exception:
                pass

    return {
        "vault_path": resolved.vault_path,
        "source": resolved.source,
        "profile_path": profile_path,
        "profile_mode": profile_mode,
        "warnings": warnings,
    }


def resolve_output(
    cwd: Path,
    *,
    cli_output: str | None = None,
    obsidian_dir_override: bool = False,
) -> ResolvedOutput:
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

    # Vault detected -> require .graphify/profile.yaml (D-05) ...
    # ... unless Phase 63 Option B silent reroute applies (D-02 strict trigger).
    profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
    if not profile_yaml.exists():
        if obsidian_dir_override:
            # D-02 strict-trigger: --obsidian-dir suppresses Option B; keep legacy refusal.
            raise _refuse(
                f"CWD is an Obsidian vault ({cwd_resolved}) but no .graphify/profile.yaml found. "
                "Create one (see docs/vault-adapter.md), or pass --output <path> to write outside the vault."
            )
        # Phase 63 VOPT-01/02: Option B silent reroute to <vault>/.graphify-out/.
        notes_dir = (cwd_resolved / ".graphify-out" / "obsidian").resolve()
        artifacts_dir = (cwd_resolved / ".graphify-out").resolve()
        # Idempotent emission: gate may have already fired the breadcrumb.
        emit_option_b_breadcrumb(cwd_resolved)
        return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "option-b")

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
