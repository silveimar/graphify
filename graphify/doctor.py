"""Doctor diagnostics — read-only orchestration over Phase 27/28 primitives (Phase 29).

Surfaces the resolved vault/profile/output state — already computed by Phases 27 and
28 — as a structured DoctorReport that __main__.py wiring (Plan 29-03) and the
dry-run preview branch (Plan 29-03) consume.

Decisions implemented (D-30..D-41 — see 29-CONTEXT.md):
  - D-32: pure-function module; run_doctor() / format_report() are the public API
  - D-33: DoctorReport carries vault_detection, profile_validation_errors,
          resolved_output, ignore_list (grouped by 4 sources), manifest_history,
          would_self_ingest, recommended_fixes, preview
  - D-34: format_report() emits sections in fixed order, every line [graphify]-prefixed
  - D-35: is_misconfigured() returns True for ANY of: validation errors / unresolvable
          dest / would_self_ingest
  - D-36: validate_profile_preflight() called as-is — no signature change
  - D-37: ignore_list grouped by 4 source labels; no cross-source dedup
  - D-40: hardcoded _FIX_HINTS table maps validator error substrings to verb-first
          imperative fix lines
  - D-41: one fix line per detected issue, in detection order

This module is read-only by design — run_doctor() performs no disk writes,
even on the dry_run=True branch (D-38, D-39): the preview consumes detect()'s
in-memory `files` and `skipped` dicts; no graphify-out/ is created.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from graphify.detect import (
    _SELF_OUTPUT_DIRS,
    _is_nested_output,
    _load_graphifyignore,
    _load_output_manifest,
)
from graphify.output import ResolvedOutput, is_obsidian_vault, resolve_output
from graphify.profile import validate_profile_preflight


# ---------------------------------------------------------------------------
# _FIX_HINTS — D-40 substring → actionable fix line
# ---------------------------------------------------------------------------
# Order-preserving, first-match-wins. Substring match against accumulated
# profile_validation_errors entries. WOULD_SELF_INGEST is a synthetic sentinel
# appended to the error list (and stripped from the user-visible output) when
# would_self_ingest is True, so it flows through the same fix-hint loop.

# D-38: fixed reason ordering for preview output. Shared with _build_preview_section
# and _format_preview so dict iteration order is deterministic regardless of detect()'s
# internal key ordering.
_PREVIEW_SKIP_ORDER: tuple[str, ...] = (
    "nesting",
    "exclude-glob",
    "manifest",
    "sensitive",
    "noise-dir",
)

# D-38: bounded preview caps — first 10 ingest paths, first 5 per skip-reason group.
_PREVIEW_INGEST_SAMPLE_CAP = 10
_PREVIEW_SKIP_SAMPLE_CAP = 5


_FIX_HINTS: list[tuple[str, str]] = [
    (
        "missing .graphify/profile.yaml",
        "[graphify] FIX: Create .graphify/profile.yaml — see docs/vault-adapter.md",
    ),
    (
        "no .graphify/profile.yaml found",
        "[graphify] FIX: Create .graphify/profile.yaml — see docs/vault-adapter.md",
    ),
    (
        "PyYAML",
        "[graphify] FIX: Install PyYAML — pip install 'graphifyy[routing]'",
    ),
    (
        "Unknown taxonomy key",
        "[graphify] FIX: Remove unsupported taxonomy keys or move folder routing under taxonomy.folders in .graphify/profile.yaml",
    ),
    (
        "Unknown taxonomy folder",
        "[graphify] FIX: Use supported taxonomy folder keys: moc, thing, statement, person, source, default, unclassified",
    ),
    (
        "taxonomy.folders",
        "[graphify] FIX: Set taxonomy folders to safe vault-relative paths under the Graphify taxonomy root",
    ),
    (
        "mapping.moc_threshold",
        "[graphify] FIX: Replace mapping.moc_threshold with mapping.min_community_size in .graphify/profile.yaml",
    ),
    (
        "mapping.min_community_size",
        "[graphify] FIX: Add mapping.min_community_size: 3 under mapping: in .graphify/profile.yaml",
    ),
    (
        "MOC-only output",
        "[graphify] FIX: Remove community overview templates/settings and use MOC-only output for v1.8",
    ),
    (
        "sibling-of-vault",
        "[graphify] FIX: Set output.path to a directory inside (or beside) your vault, not above it",
    ),
    (
        "output.mode",
        "[graphify] FIX: Set output.mode to 'vault-relative', 'absolute', or 'sibling-of-vault' in .graphify/profile.yaml",
    ),
    (
        "output.path",
        "[graphify] FIX: Add an output.path: <relative-or-absolute> entry under output: in .graphify/profile.yaml",
    ),
    (
        "no 'output:' block",
        "[graphify] FIX: Add an output: {mode: ..., path: ...} block to .graphify/profile.yaml",
    ),
    (
        "WOULD_SELF_INGEST",
        "[graphify] FIX: Move existing graphify-out/ outside the input scan, or add 'graphify-out/**' to .graphifyignore",
    ),
]


# ---------------------------------------------------------------------------
# Containers — DoctorReport (D-33), PreviewSection (Plan 29-03 will populate)
# ---------------------------------------------------------------------------

@dataclass
class PreviewSection:
    """Dry-run preview section (Plan 29-03 owns population).

    Defined here so its import is stable for Plan 29-03 wiring and __main__.py.
    """
    would_ingest_count: int = 0
    would_ingest_sample: list[str] = field(default_factory=list)
    would_skip_grouped: dict[str, list[str]] = field(default_factory=dict)
    would_skip_counts: dict[str, int] = field(default_factory=dict)
    notes_dir: Optional[Path] = None
    artifacts_dir: Optional[Path] = None


@dataclass
class DoctorReport:
    """Structured diagnostic report — fully populated by run_doctor()."""
    vault_detection: bool = False
    vault_path: Optional[Path] = None
    profile_validation_errors: list[str] = field(default_factory=list)
    profile_validation_warnings: list[str] = field(default_factory=list)
    resolved_output: Optional[ResolvedOutput] = None
    ignore_list: dict[str, list[str]] = field(default_factory=dict)
    manifest_history: Optional[list[dict]] = None
    would_self_ingest: bool = False
    recommended_fixes: list[str] = field(default_factory=list)
    preview: Optional[PreviewSection] = None

    def is_misconfigured(self) -> bool:
        """D-35: True iff profile errors / unresolvable dest / would_self_ingest."""
        if self.profile_validation_errors:
            return True
        if self.resolved_output is None:
            return True
        if self.would_self_ingest:
            return True
        return False


# ---------------------------------------------------------------------------
# _compute_would_self_ingest — D-35 trigger
# ---------------------------------------------------------------------------

def _compute_would_self_ingest(cwd: Path, resolved: Optional[ResolvedOutput]) -> bool:
    """Return True if the resolved destination would be re-ingested by detect().

    Triggers only when a destination path contains a literal _SELF_OUTPUT_DIRS
    component (`graphify-out` / `graphify_out`) AND lives inside the input scan
    (cwd). Vault-relative destinations like `Atlas/Generated` do NOT trip this —
    only paths that overlap with graphify's canonical self-output directory
    names (typical misconfiguration: pointing notes_dir at graphify-out/notes).

    D-12 backcompat: returns False when resolved is None or resolved.source ==
    "default" (no vault adoption → byte-identical v1.0 behavior, no concern).
    """
    if resolved is None:
        return False
    if resolved.source == "default":
        return False

    cwd_resolved = cwd.resolve()
    # Only the literal self-output dirs — NOT resolved.notes_dir.name itself
    # (which would be circular: every nested destination would trip).
    self_dirs = frozenset(_SELF_OUTPUT_DIRS)

    for dest in (resolved.notes_dir, resolved.artifacts_dir):
        try:
            dest_resolved = dest.resolve() if dest.is_absolute() else (cwd_resolved / dest).resolve()
        except (OSError, ValueError):
            continue
        try:
            rel = dest_resolved.relative_to(cwd_resolved)
        except ValueError:
            # Destination lives outside the input scan — safe.
            continue
        for part in rel.parts:
            if _is_nested_output(part, self_dirs):
                return True
    return False


# ---------------------------------------------------------------------------
# Ignore-list (D-37) — union of 4 sources, grouped, no cross-source dedup
# ---------------------------------------------------------------------------

def _build_ignore_list(cwd: Path, resolved: Optional[ResolvedOutput]) -> dict[str, list[str]]:
    """Return ignore-list grouped by source label (D-37). No dedup across sources."""
    ignore: dict[str, list[str]] = {
        "self-output-dirs": sorted(_SELF_OUTPUT_DIRS),
        "resolved-basenames": [],
        "graphifyignore-patterns": _load_graphifyignore(cwd),
        "profile-exclude-globs": [],
    }
    if resolved is not None:
        # Per-key dedup only: include both basenames if they differ from each other,
        # but allow overlap with self-output-dirs (D-37: no cross-source dedup).
        seen: list[str] = []
        for name in (resolved.notes_dir.name, resolved.artifacts_dir.name):
            if name and name not in seen:
                seen.append(name)
        ignore["resolved-basenames"] = seen
        ignore["profile-exclude-globs"] = list(resolved.exclude_globs)
    return ignore


# ---------------------------------------------------------------------------
# Recommended fixes (D-41) — one per detected issue, detection order
# ---------------------------------------------------------------------------

def _build_recommended_fixes(
    profile_validation_errors: list[str],
    would_self_ingest: bool,
    profile_validation_warnings: list[str] | None = None,
) -> list[str]:
    """Map issues to fix lines via _FIX_HINTS substring match (first-match-wins)."""
    fixes: list[str] = []
    seen_fixes: set[str] = set()

    def _match(issue: str) -> Optional[str]:
        for pattern, fix_line in _FIX_HINTS:
            if pattern in issue:
                return fix_line
        return None

    for err in profile_validation_errors:
        fix = _match(err)
        if fix is not None and fix not in seen_fixes:
            fixes.append(fix)
            seen_fixes.add(fix)

    for warning in profile_validation_warnings or []:
        fix = _match(warning)
        if fix is not None and fix not in seen_fixes:
            fixes.append(fix)
            seen_fixes.add(fix)

    if would_self_ingest:
        fix = _match("WOULD_SELF_INGEST")
        if fix is not None and fix not in seen_fixes:
            fixes.append(fix)
            seen_fixes.add(fix)

    return fixes


# ---------------------------------------------------------------------------
# Public API — run_doctor() (D-32) and format_report() (D-34)
# ---------------------------------------------------------------------------

def _build_preview_section(
    detect_result: dict, resolved: ResolvedOutput
) -> PreviewSection:
    """Construct PreviewSection from a real detect() result (D-38, D-39).

    Bounded per D-38:
      - would_ingest_sample: first _PREVIEW_INGEST_SAMPLE_CAP (10) paths
      - would_skip_grouped[reason]: first _PREVIEW_SKIP_SAMPLE_CAP (5) per reason

    Single source of truth: consumes detect_result["files"] (dict[FileType.value,
    list[str]]) and detect_result["skipped"] (dict[reason, list[str]]) — does NOT
    re-implement scanning (D-39).
    """
    # Flatten result["files"] into a single ordered list. Iterate file-type
    # buckets in insertion order; each bucket's list is already sorted by detect().
    files_by_type = detect_result.get("files", {})
    if not isinstance(files_by_type, dict):
        files_by_type = {}
    flattened: list[str] = []
    for bucket in files_by_type.values():
        if isinstance(bucket, list):
            flattened.extend(str(p) for p in bucket)

    skipped = detect_result.get("skipped", {})
    if not isinstance(skipped, dict):
        skipped = {}

    # Preserve the fixed reason order for grouped/counts; only include reasons
    # detect() actually populated this run (omit empty groups for a quieter
    # preview).
    grouped: dict[str, list[str]] = {}
    counts: dict[str, int] = {}
    for reason in _PREVIEW_SKIP_ORDER:
        bucket = skipped.get(reason, [])
        if not isinstance(bucket, list):
            continue
        grouped[reason] = [str(p) for p in bucket[:_PREVIEW_SKIP_SAMPLE_CAP]]
        counts[reason] = len(bucket)

    return PreviewSection(
        would_ingest_count=len(flattened),
        would_ingest_sample=flattened[:_PREVIEW_INGEST_SAMPLE_CAP],
        would_skip_grouped=grouped,
        would_skip_counts=counts,
        notes_dir=resolved.notes_dir,
        artifacts_dir=resolved.artifacts_dir,
    )


def run_doctor(cwd: Path, *, dry_run: bool = False) -> DoctorReport:
    """Build a DoctorReport for the given working directory. Read-only.

    When dry_run=True, additionally calls the real detect() (D-39) and attaches
    a bounded PreviewSection to report.preview. When the destination is
    unresolvable, preview is left as None (is_misconfigured() still returns
    True so exit code stays 1).
    """
    cwd_resolved = cwd.resolve()
    report = DoctorReport()

    # --- Vault detection (D-04 / VAULT-08) --------------------------------
    report.vault_detection = is_obsidian_vault(cwd_resolved)
    report.vault_path = cwd_resolved if report.vault_detection else None

    # --- Profile validation (D-36) ----------------------------------------
    profile_yaml = cwd_resolved / ".graphify" / "profile.yaml"
    templates_dir = cwd_resolved / ".graphify" / "templates"
    if profile_yaml.exists() or templates_dir.exists():
        try:
            result = validate_profile_preflight(cwd_resolved)
            report.profile_validation_errors.extend(result.errors)
            report.profile_validation_warnings.extend(result.warnings)
        except Exception as exc:
            report.profile_validation_errors.append(
                f"profile preflight error: {exc}"
            )

    # --- Output destination resolution (D-13) -----------------------------
    # resolve_output() may SystemExit via _refuse() — capture stderr so the
    # underlying refusal message becomes a profile_validation_errors entry.
    if not report.profile_validation_errors:
        captured = io.StringIO()
        try:
            with contextlib.redirect_stderr(captured):
                report.resolved_output = resolve_output(cwd_resolved)
        except SystemExit:
            report.resolved_output = None
            for line in captured.getvalue().splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # Strip the "[graphify] " prefix if present so _FIX_HINTS substring
                # matching sees the underlying validator wording.
                if stripped.startswith("[graphify] "):
                    stripped = stripped[len("[graphify] "):]
                report.profile_validation_errors.append(stripped)

    # --- would_self_ingest (D-35 trigger) ---------------------------------
    report.would_self_ingest = _compute_would_self_ingest(
        cwd_resolved, report.resolved_output
    )

    # --- Ignore-list (D-37) -----------------------------------------------
    report.ignore_list = _build_ignore_list(cwd_resolved, report.resolved_output)

    # --- Manifest history (D-25) ------------------------------------------
    if report.resolved_output is not None:
        manifest = _load_output_manifest(report.resolved_output.artifacts_dir)
        # Phase 28 envelope uses 'runs' key; preserve a list (or None when no envelope).
        runs = manifest.get("runs") if isinstance(manifest, dict) else None
        report.manifest_history = list(runs) if isinstance(runs, list) else []

    # --- Recommended fixes (D-40, D-41) -----------------------------------
    report.recommended_fixes = _build_recommended_fixes(
        report.profile_validation_errors,
        report.would_self_ingest,
        report.profile_validation_warnings,
    )

    # --- Dry-run preview (D-38, D-39) -------------------------------------
    # Only run detect() when we actually have a resolved destination — when
    # resolved_output is None the misconfiguration is already surfaced via
    # profile_validation_errors and is_misconfigured() returns True. T-29-*:
    # detect() is read-only; no disk writes here.
    if dry_run and report.resolved_output is not None:
        from graphify.detect import detect as _detect_scan
        scan = _detect_scan(cwd_resolved)
        report.preview = _build_preview_section(scan, report.resolved_output)

    return report


def _format_preview(preview: PreviewSection) -> list[str]:
    """Render PreviewSection as [graphify]-prefixed lines (D-38).

    Layout:
      [graphify] === Preview ===
      [graphify] Would ingest: N files
      [graphify]   <path>            (up to _PREVIEW_INGEST_SAMPLE_CAP)
      [graphify]   ... +K more       (when N exceeds the sample cap)
      [graphify] Would skip ({reason}): M files
      [graphify]   <path>            (up to _PREVIEW_SKIP_SAMPLE_CAP)
      [graphify]   ... +K more       (when M exceeds the sample cap)
      [graphify] Would write notes to: {notes_dir}
      [graphify] Would write artifacts to: {artifacts_dir}
    """
    out: list[str] = ["[graphify] === Preview ==="]
    out.append(f"[graphify] Would ingest: {preview.would_ingest_count} files")
    for sample in preview.would_ingest_sample:
        out.append(f"[graphify]   {sample}")
    overflow_ingest = preview.would_ingest_count - len(preview.would_ingest_sample)
    if overflow_ingest > 0:
        out.append(f"[graphify]   ... +{overflow_ingest} more")

    for reason in _PREVIEW_SKIP_ORDER:
        if reason not in preview.would_skip_grouped:
            continue
        paths = preview.would_skip_grouped[reason]
        total = preview.would_skip_counts.get(reason, len(paths))
        out.append(f"[graphify] Would skip ({reason}): {total} files")
        for p in paths:
            out.append(f"[graphify]   {p}")
        overflow_skip = total - len(paths)
        if overflow_skip > 0:
            out.append(f"[graphify]   ... +{overflow_skip} more")

    if preview.notes_dir is not None:
        out.append(f"[graphify] Would write notes to: {preview.notes_dir}")
    if preview.artifacts_dir is not None:
        out.append(f"[graphify] Would write artifacts to: {preview.artifacts_dir}")
    return out


def format_report(report: DoctorReport) -> str:
    """Render DoctorReport as sectioned [graphify]-prefixed text (D-34).

    Section order: Vault Detection / Profile Validation / Output Destination /
    Ignore-List / Preview (when present) / Recommended Fixes.
    """
    lines: list[str] = []

    # --- Vault Detection --------------------------------------------------
    lines.append("[graphify] === Vault Detection ===")
    if report.vault_detection:
        lines.append(f"[graphify] vault detected at {report.vault_path}")
    else:
        lines.append("[graphify] no Obsidian vault detected in CWD")

    # --- Profile Validation -----------------------------------------------
    lines.append("[graphify] === Profile Validation ===")
    if report.profile_validation_errors:
        for err in report.profile_validation_errors:
            lines.append(f"[graphify] error: {err}")
    for warning in report.profile_validation_warnings:
        lines.append(f"[graphify] warning: {warning}")
    if not report.profile_validation_errors:
        lines.append("[graphify] profile valid (or not present)")

    # --- Output Destination -----------------------------------------------
    lines.append("[graphify] === Output Destination ===")
    if report.resolved_output is None:
        lines.append("[graphify] unresolvable — see Profile Validation errors above")
    else:
        ro = report.resolved_output
        lines.append(f"[graphify] notes_dir: {ro.notes_dir}")
        lines.append(f"[graphify] artifacts_dir: {ro.artifacts_dir}")
        lines.append(f"[graphify] source: {ro.source}")
        if report.would_self_ingest:
            lines.append("[graphify] WARNING: resolved destination falls under input scan (would_self_ingest=True)")

    # --- Ignore-List ------------------------------------------------------
    lines.append("[graphify] === Ignore-List ===")
    for source_label in (
        "self-output-dirs",
        "resolved-basenames",
        "graphifyignore-patterns",
        "profile-exclude-globs",
    ):
        entries = report.ignore_list.get(source_label, [])
        if entries:
            joined = ", ".join(entries)
            lines.append(f"[graphify] {source_label}: {joined}")
        else:
            lines.append(f"[graphify] {source_label}: (none)")

    # --- Preview (only when populated; D-38) ------------------------------
    if report.preview is not None:
        lines.extend(_format_preview(report.preview))

    # --- Recommended Fixes ------------------------------------------------
    lines.append("[graphify] === Recommended Fixes ===")
    if report.recommended_fixes:
        for fix in report.recommended_fixes:
            lines.append(fix)
    else:
        lines.append("[graphify] No issues detected.")

    return "\n".join(lines)
