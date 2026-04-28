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
"""
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


def is_obsidian_vault(path: Path) -> bool:
    """Strict CWD-only detection (D-04). No parent-walking."""
    return (path / ".obsidian").is_dir()


def _refuse(msg: str) -> SystemExit:
    """Print actionable error to stderr and prepare SystemExit(1)."""
    print(f"[graphify] {msg}", file=sys.stderr)
    return SystemExit(1)


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
    return ResolvedOutput(True, cwd_resolved, notes_dir, artifacts_dir, "profile")
