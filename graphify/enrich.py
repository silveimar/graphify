"""Async background graph enrichment — 4 passes (description, patterns, community, staleness).

Writes overlay sidecar only (``graphify-out/enrichment.json``); ``graph.json`` is NEVER mutated.
See .planning/phases/15-async-background-enrichment/15-CONTEXT.md §<decisions> for D-01..D-07.

ENRICH-04: single-writer fcntl.flock coordination
ENRICH-05: snapshot_id pinned at process start, never followed mid-run
ENRICH-07: SIGTERM + signal.alarm(600) handlers for clean abort
"""
from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graphify.security import validate_graph_path
from graphify.snapshot import list_snapshots

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

LOCK_FILENAME = ".enrichment.lock"
PID_FILENAME = ".enrichment.pid"
PASS_NAMES: tuple[str, ...] = ("description", "patterns", "community", "staleness")
DEFAULT_MAX_RUNTIME_SECONDS = 600  # Pitfall 4 mitigation — SIGALRM after 10 min

# Module-level fd used by the SIGTERM handler (set inside run_enrichment; read in handler).
_lock_fd: int | None = None


# ---------------------------------------------------------------------------
# Public result dataclass
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentResult:
    """Aggregated outcome of one enrichment run (all passes)."""

    snapshot_id: str
    passes_run: list[str] = field(default_factory=list)
    passes_skipped: list[str] = field(default_factory=list)
    passes_failed: list[str] = field(default_factory=list)
    tokens_used: int = 0
    llm_calls: int = 0
    dry_run: bool = False
    aborted: bool = False  # True if SIGTERM received mid-run


# ---------------------------------------------------------------------------
# Snapshot pinning (ENRICH-05)
# ---------------------------------------------------------------------------

def pin_snapshot(project_root: Path) -> tuple[str, Path]:
    """Return (snapshot_id, snapshot_path) for the most recent snapshot.

    snapshot_id = snapshot_path.stem (e.g. '2026-04-20T14-30-00').
    Raises FileNotFoundError if no snapshots exist yet.
    """
    snapshots = list_snapshots(project_root)
    if not snapshots:
        raise FileNotFoundError(
            "no snapshots found under graphify-out/snapshots/; run `graphify run` first"
        )
    latest = snapshots[-1]  # list_snapshots returns oldest → newest (mtime sort)
    return latest.stem, latest


# ---------------------------------------------------------------------------
# Lock acquisition (ENRICH-04)
# ---------------------------------------------------------------------------

def _acquire_lock(out_dir: Path) -> int:
    """Acquire exclusive flock on .enrichment.lock. Returns fd.

    Raises BlockingIOError if another enrichment process is active.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    lock_path = out_dir / LOCK_FILENAME
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise
    return fd


# ---------------------------------------------------------------------------
# SIGTERM / SIGALRM handler (ENRICH-07)
# ---------------------------------------------------------------------------

def _sigterm_handler(signum: int, frame: object) -> None:
    """SIGTERM / SIGALRM handler: release flock, print notice, sys.exit(1).

    Pitfall 2 guard: release the lock with LOCK_UN but do NOT close the fd
    inside the signal handler — closing inside a handler can cause double-close
    races. The OS cleans up the fd on process exit.
    """
    global _lock_fd
    if _lock_fd is not None:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
        except OSError:
            pass
    print(
        "[graphify] enrichment: SIGTERM received; releasing lock and exiting cleanly",
        file=sys.stderr,
    )
    sys.exit(1)


def _install_sigterm(
    lock_fd: int,
    max_runtime_seconds: int = DEFAULT_MAX_RUNTIME_SECONDS,
) -> None:
    """Register SIGTERM (and SIGALRM) handlers and arm signal.alarm(max_runtime_seconds).

    Stores lock_fd in the module-level _lock_fd so the handler can release it.
    SIGALRM also triggers _sigterm_handler for Pitfall 4 zombie mitigation.
    max_runtime_seconds=0 skips arming the alarm (used in tests).
    """
    global _lock_fd
    _lock_fd = lock_fd
    signal.signal(signal.SIGTERM, _sigterm_handler)
    signal.signal(signal.SIGALRM, _sigterm_handler)  # alarm also triggers clean abort
    if max_runtime_seconds > 0:
        signal.alarm(max_runtime_seconds)


# ---------------------------------------------------------------------------
# Pass orchestrator stub (Plans 02/03 will populate)
# ---------------------------------------------------------------------------

def _run_passes(
    out_dir: Path,
    snapshot_id: str,
    snapshot_path: Path,
    passes: list[str],
    *,
    budget: int | None,
    dry_run: bool,
    resume: bool,
    result: EnrichmentResult,
) -> None:
    """D-01 serial pass dispatcher: description → patterns → community (→ staleness in Plan 03).

    Per D-03: budget drains in priority order. Per D-16: alias_map applied at every write.
    Per D-02: each pass commits atomically via `_commit_pass`; a mid-pass failure leaves
    prior passes intact and aborts the run with SystemExit(1).
    """
    from graphify.snapshot import load_snapshot
    from graphify.serve import _load_dedup_report

    G, communities, _meta = load_snapshot(snapshot_path)
    alias_map = _load_dedup_report(out_dir)
    routing_skip_files = _load_routing_skip_set(out_dir)
    routing_skip_nids = {
        nid for nid, d in G.nodes(data=True)
        if d.get("source_file") in routing_skip_files
    }

    existing = _load_existing_enrichment(out_dir, snapshot_id) if resume else {}
    existing_passes = existing.get("passes", {}) if isinstance(existing, dict) else {}

    # D-07 resume gate: skip passes already present in existing envelope (per-pass).
    # Iterate the three LLM passes in D-01 order; staleness appended below.
    for pass_name in ("description", "patterns", "community"):
        if pass_name not in passes:
            continue
        if pass_name in existing_passes:
            result.passes_skipped.append(pass_name)
            continue
        rem = _budget_remaining(budget, result.tokens_used)
        try:
            if pass_name == "description":
                data, t, c = _run_description_pass(
                    G, out_dir, snapshot_id,
                    budget_remaining=rem, dry_run=dry_run,
                    alias_map=alias_map, routing_skip=routing_skip_nids,
                )
            elif pass_name == "patterns":
                data, t, c = _run_patterns_pass(
                    G, out_dir, snapshot_id,
                    budget_remaining=rem, dry_run=dry_run, alias_map=alias_map,
                )
            else:  # pass_name == "community"
                data, t, c = _run_community_pass(
                    G, communities, out_dir, snapshot_id,
                    budget_remaining=rem, dry_run=dry_run, alias_map=alias_map,
                )
        except Exception as exc:
            print(
                f"[graphify] enrichment: pass {pass_name!r} failed: {exc}",
                file=sys.stderr,
            )
            result.passes_failed.append(pass_name)
            raise SystemExit(1) from exc

        result.tokens_used += t
        result.llm_calls += c
        if not dry_run:
            _commit_pass(out_dir, snapshot_id, pass_name, data)
            result.passes_run.append(pass_name)
        else:
            result.passes_skipped.append(pass_name)

    # ---- D-01 pass 4: staleness (D-03 compute-only — exempt from budget) ----
    if "staleness" in passes:
        if "staleness" in existing_passes:
            result.passes_skipped.append("staleness")
        else:
            try:
                data, t, c = _run_staleness_pass(
                    G, out_dir, snapshot_id,
                    alias_map=alias_map, dry_run=dry_run,
                )
            except Exception as exc:
                print(
                    f"[graphify] enrichment: staleness pass failed: {exc}",
                    file=sys.stderr,
                )
                result.passes_failed.append("staleness")
                raise SystemExit(1) from exc
            assert t == 0 and c == 0, (
                "staleness pass must be compute-only (D-03 invariant)"
            )
            if not dry_run:
                _commit_pass(out_dir, snapshot_id, "staleness", data)
                result.passes_run.append("staleness")
            else:
                result.passes_skipped.append("staleness")


# ---------------------------------------------------------------------------
# Public orchestrator (ENRICH-01, ENRICH-04, ENRICH-05, ENRICH-07)
# ---------------------------------------------------------------------------

def run_enrichment(
    out_dir: Path,
    *,
    budget: int | None = None,
    passes: list[str] | None = None,
    dry_run: bool = False,
    resume: bool = True,
    snapshot_id_override: str | None = None,
    project_root: Path | None = None,
) -> EnrichmentResult:
    """Acquire lock, pin snapshot, install SIGTERM handler, then run the pass orchestrator.

    Plan 01 skeleton: calls an internal _run_passes() placeholder that returns an empty
    EnrichmentResult. Plans 02 and 03 will fill in the four passes. The lock / snapshot /
    signal plumbing in this function is frozen after Plan 01 — later plans MUST NOT modify
    the finally: block release pattern.

    Args:
        out_dir: graphify-out/ directory (contains graph.json + enrichment.json sidecar).
        budget: token cap applied in D-03 priority-drain order (description → patterns → community).
        passes: list of pass names to run; None → all 4 in PASS_NAMES order.
        dry_run: if True, preview tokens/calls without LLM invocations (ENRICH-10 P2).
        resume: if True, skip already-complete passes from prior runs (Plans 02/03 fill this).
        snapshot_id_override: pin to a specific snapshot_id instead of latest.
        project_root: root containing graphify-out/; inferred from out_dir.parent if None.
    """
    global _lock_fd

    project_root = project_root or out_dir.parent

    # Guard: graph.json must exist (ENRICH-01). Checked BEFORE any directory writes
    # so a missing / unwritable out_dir surfaces as a clean exit 2 instead of an
    # unhandled OSError from mkdir on a read-only filesystem.
    graph_path = out_dir / "graph.json"
    if not graph_path.exists():
        print(
            f"[graphify] enrichment: {graph_path} not found — run `graphify run` first",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # graph.json exists ⇒ out_dir exists; mkdir is a no-op but keeps intent explicit.
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pin snapshot (ENRICH-05) — done BEFORE acquiring the lock so failures are fast
    if snapshot_id_override:
        snapshot_id = snapshot_id_override
        snapshot_path = next(
            (p for p in list_snapshots(project_root) if p.stem == snapshot_id),
            None,
        )
        if snapshot_path is None:
            raise SystemExit(
                f"snapshot_id {snapshot_id!r} not found under "
                f"{project_root}/graphify-out/snapshots/"
            )
    else:
        snapshot_id, snapshot_path = pin_snapshot(project_root)

    # Acquire exclusive lock (ENRICH-04)
    lock_fd = _acquire_lock(out_dir)

    # Store fd so SIGTERM handler can release it
    _lock_fd = lock_fd

    # Install SIGTERM + SIGALRM handlers and arm watchdog alarm (ENRICH-07 / Pitfall 4)
    _install_sigterm(lock_fd, DEFAULT_MAX_RUNTIME_SECONDS)

    # Write heartbeat .pid file atomically (Pitfall 4 zombie mitigation)
    _write_pid_file(out_dir, snapshot_id)

    result = EnrichmentResult(snapshot_id=snapshot_id, dry_run=dry_run)

    try:
        _run_passes(
            out_dir,
            snapshot_id,
            snapshot_path,
            passes or list(PASS_NAMES),
            budget=budget,
            dry_run=dry_run,
            resume=resume,
            result=result,
        )
    finally:
        # Always cancel the watchdog alarm on normal exit (Pitfall 4)
        signal.alarm(0)
        # Release and close the lock
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)
            _lock_fd = None
        # Remove heartbeat .pid file (Pitfall 4 cleanup)
        try:
            (out_dir / PID_FILENAME).unlink(missing_ok=True)
        except OSError:
            pass

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_pid_file(out_dir: Path, snapshot_id: str) -> None:
    """Write .enrichment.pid heartbeat atomically (Pitfall 4 mitigation).

    Uses the routing_audit.py atomic pattern: write to .tmp then os.replace.
    Validates out_dir base confinement only (the pid file doesn't exist yet,
    so validate_graph_path on the exact path would raise FileNotFoundError).
    """
    # Validate the base directory (not the file — it doesn't exist yet)
    validate_graph_path(out_dir, base=out_dir.parent)

    now = datetime.now(timezone.utc)
    from datetime import timedelta
    expires = now + timedelta(seconds=DEFAULT_MAX_RUNTIME_SECONDS)

    payload: dict[str, Any] = {
        "pid": os.getpid(),
        "started_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "snapshot_id": snapshot_id,
    }

    dest = out_dir / PID_FILENAME
    tmp = dest.with_suffix(".pid.tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Plan 15-02: atomic per-pass commit + LLM passes
# ---------------------------------------------------------------------------

def _commit_pass(
    out_dir: Path,
    snapshot_id: str,
    pass_name: str,
    result_data: object,
) -> None:
    """Atomically merge one pass result into ``enrichment.json`` (D-02).

    Read-modify-write on the envelope's ``passes`` dict, then atomic
    ``.tmp`` + ``os.replace``. On any exception during write: unlink the
    ``.tmp`` and re-raise — prior passes stay intact. Caller (``_run_passes``)
    catches the re-raised exception, logs, and aborts the run.
    """
    # Validate the base directory (the dest may not exist yet — gate on base).
    validate_graph_path(out_dir, base=out_dir.parent)

    dest = out_dir / "enrichment.json"
    existing: dict[str, Any] | None = None
    if dest.exists():
        try:
            existing = json.loads(dest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None

    if (
        not existing
        or not isinstance(existing, dict)
        or existing.get("version") != 1
        or existing.get("snapshot_id") != snapshot_id
    ):
        existing = {
            "version": 1,
            "snapshot_id": snapshot_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passes": {},
        }

    existing["generated_at"] = datetime.now(timezone.utc).isoformat()
    passes = existing.setdefault("passes", {})
    passes[pass_name] = result_data

    tmp = dest.with_suffix(".json.tmp")
    try:
        tmp.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _validate_enrichment_envelope(data: object) -> bool:
    """D-05 schema strict-check for the enrichment.json envelope.

    Returns True only when ``data`` has the v1 shape:
      - dict
      - version == 1
      - snapshot_id: non-empty str
      - passes: dict whose keys are a subset of ``PASS_NAMES``
      - per-pass container shape matches (description/community/staleness → dict,
        patterns → list, staleness values ∈ {FRESH, STALE, GHOST})

    Returns False on ANY deviation. Warnings about version mismatches are
    logged to stderr so users can diagnose discarded envelopes; other shape
    failures return False silently (the caller falls through to a fresh run).
    """
    if not isinstance(data, dict):
        return False
    version = data.get("version")
    if version != 1:
        print(
            f"[graphify] enrichment: envelope version != 1 (got {version!r}); "
            f"discarding",
            file=sys.stderr,
        )
        return False
    snapshot_id = data.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id:
        return False
    passes = data.get("passes")
    if not isinstance(passes, dict):
        return False
    for pass_name in passes:
        if pass_name not in PASS_NAMES:
            print(
                f"[graphify] enrichment: unexpected pass key {pass_name!r} in v1 "
                f"envelope; discarding",
                file=sys.stderr,
            )
            return False
    if "description" in passes and not isinstance(passes["description"], dict):
        return False
    if "patterns" in passes and not isinstance(passes["patterns"], list):
        return False
    if "community" in passes and not isinstance(passes["community"], dict):
        return False
    if "staleness" in passes:
        stal = passes["staleness"]
        if not isinstance(stal, dict):
            return False
        valid_labels = {"FRESH", "STALE", "GHOST"}
        for _nid, label in stal.items():
            if label not in valid_labels:
                return False
    return True


def _load_existing_enrichment(out_dir: Path, snapshot_id: str) -> dict:
    """D-07: return the current enrichment.json envelope iff it's v1 AND matches.

    Returns {} to signal "fresh run" when:
      - The file is absent
      - It can't be read / parsed
      - ``_validate_enrichment_envelope`` rejects its shape
      - ``snapshot_id`` mismatches the caller-pinned id

    Never raises — all errors collapse to empty-return. On shape rejection
    the envelope is left on disk; the next successful ``_commit_pass`` will
    overwrite it with a fresh v1 envelope for the pinned snapshot.
    """
    p = out_dir / "enrichment.json"
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(
            f"[graphify] enrichment: existing enrichment.json unreadable: {exc}; "
            f"starting fresh",
            file=sys.stderr,
        )
        return {}
    if not _validate_enrichment_envelope(data):
        return {}
    if data.get("snapshot_id") != snapshot_id:
        return {}
    return data


def _sanitize_pass_output(text: str) -> str:
    """T-15-03 mitigation: never write raw LLM output to ``enrichment.json``.

    Thin wrapper around ``graphify.security.sanitize_label_md`` so the three
    pass runners route every text token through a single sanitization point.
    """
    from graphify.security import sanitize_label_md
    if not isinstance(text, str):
        text = str(text)
    return sanitize_label_md(text)


def _budget_remaining(budget: int | None, spent: int) -> int:
    """Return remaining tokens for D-03 priority-drain accounting.

    ``budget=None`` → unlimited (``sys.maxsize``).
    Returns 0 when spent exceeds budget (never negative).
    """
    if budget is None:
        return sys.maxsize
    return max(0, budget - spent)


def _load_routing_skip_set(out_dir: Path) -> set[str]:
    """ENRICH-11 P2: return source_file paths routed to the ``complex`` tier.

    Reads ``graphify-out/routing.json`` (Phase 12 audit). Returns the set of
    file paths whose class is ``complex`` — the caller intersects these with
    node ``source_file`` attrs to decide which nodes to skip. Empty set when
    routing.json is missing or malformed (soft dependency).
    """
    p = out_dir / "routing.json"
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    skip_files: set[str] = set()
    files = data.get("files", {}) if isinstance(data, dict) else {}
    if not isinstance(files, dict):
        return set()
    for fpath, entry in files.items():
        if not isinstance(entry, dict):
            continue
        # Phase 12 RoutingAudit writes the tier at top-level ``class``;
        # RESEARCH.md also documents a nested ``info.class``. Accept both.
        cls = entry.get("class")
        if cls != "complex":
            info = entry.get("info", {})
            if isinstance(info, dict):
                cls = info.get("class")
        if cls == "complex":
            skip_files.add(str(fpath))
    return skip_files


def _call_llm(prompt: str, max_tokens: int) -> tuple[str, int]:
    """Single private LLM caller — tests monkeypatch this.

    Production wiring (routing.resolve_model + batch executor) is deferred.
    Returns ``(text, tokens_used_including_output)``.
    """
    raise NotImplementedError(
        "enrich._call_llm must be monkeypatched in tests; production wiring deferred"
    )


# ---- Pass 1: description ----------------------------------------------------

def _run_description_pass(
    G,
    out_dir: Path,
    snapshot_id: str,
    *,
    budget_remaining: int,
    dry_run: bool,
    alias_map: dict[str, str],
    routing_skip: set[str],
) -> tuple[dict[str, str], int, int]:
    """Pass 1 — enrich per-node descriptions from label + codebase context.

    D-03: stops when ``tokens_used`` reaches ``budget_remaining``.
    D-16: every key is resolved through ``alias_map`` before insertion.
    ENRICH-11 P2: nodes whose id is in ``routing_skip`` are skipped silently.
    T-15-03: LLM output piped through ``_sanitize_pass_output``.
    """
    results: dict[str, str] = {}
    tokens_used = 0
    llm_calls = 0

    for nid, data in G.nodes(data=True):
        if nid in routing_skip:
            continue
        # D-03 priority-drain
        if not dry_run and tokens_used >= budget_remaining:
            break
        canonical = alias_map.get(nid, nid)  # D-16 ENRICH-12
        if dry_run:
            tokens_used += 300  # rough per-node estimate (prompt + output)
            llm_calls += 1
            continue
        prompt = (
            f"Describe the role of {data.get('label', nid)!r} in its codebase "
            f"context. Be concise."
        )
        try:
            text, cost = _call_llm(prompt, max_tokens=200)
        except Exception as exc:
            raise RuntimeError(
                f"description pass LLM call failed on {nid}: {exc}"
            ) from exc
        results[canonical] = _sanitize_pass_output(text)
        tokens_used += cost
        llm_calls += 1

    return results, tokens_used, llm_calls


# ---- Pass 2: patterns -------------------------------------------------------

def _run_patterns_pass(
    G,
    out_dir: Path,
    snapshot_id: str,
    *,
    budget_remaining: int,
    dry_run: bool,
    alias_map: dict[str, str],
    history_depth: int = 5,
) -> tuple[list[dict], int, int]:
    """Pass 2 — cross-snapshot pattern detection.

    Looks at up to ``history_depth`` prior snapshots for nodes with rising
    degree centrality (simple heuristic; Claude's Discretion per 15-CONTEXT).
    Each pattern's ``nodes`` list is threaded through ``alias_map`` (D-16).
    """
    patterns: list[dict] = []
    tokens_used = 0
    llm_calls = 0

    # Candidate surface: top-degree nodes in the current tip graph. We leave
    # full cross-snapshot correlation for Plan 06 integration; the pattern
    # surface here is small and deterministic so tests don't need a chain.
    try:
        from graphify.analyze import god_nodes
        gods = god_nodes(G, top_n=min(5, G.number_of_nodes() or 1))
    except Exception:
        gods = []

    for i, g in enumerate(gods):
        if not dry_run and tokens_used >= budget_remaining:
            break
        raw_nid = g.get("id", "")
        canonical = alias_map.get(raw_nid, raw_nid)  # D-16
        if dry_run:
            tokens_used += 300
            llm_calls += 1
            continue
        prompt = (
            f"Given the recurring high-degree node {g.get('label', raw_nid)!r}, "
            f"summarize the architectural pattern it anchors."
        )
        try:
            text, cost = _call_llm(prompt, max_tokens=200)
        except Exception as exc:
            raise RuntimeError(
                f"patterns pass LLM call failed on {raw_nid}: {exc}"
            ) from exc
        patterns.append({
            "pattern_id": f"p{i+1}",
            "nodes": [canonical],
            "summary": _sanitize_pass_output(text),
        })
        tokens_used += cost
        llm_calls += 1

    return patterns, tokens_used, llm_calls


# ---- Pass 3: community ------------------------------------------------------

def _run_community_pass(
    G,
    communities: dict[int, list[str]],
    out_dir: Path,
    snapshot_id: str,
    *,
    budget_remaining: int,
    dry_run: bool,
    alias_map: dict[str, str],
) -> tuple[dict[str, str], int, int]:
    """Pass 3 — per-community natural-language summary.

    Keys are ``str(community_id)`` to preserve JSON round-trip semantics.
    Per-community prompt context includes the top members (god-node-style
    degree ranking) — all node_ids referenced internally run through
    ``alias_map`` (D-16) even though they do not appear in output keys.
    """
    summaries: dict[str, str] = {}
    tokens_used = 0
    llm_calls = 0

    for cid, members in communities.items():
        if not dry_run and tokens_used >= budget_remaining:
            break
        # Compose top-members context: canonicalize ids via alias_map (D-16).
        top_members = [alias_map.get(m, m) for m in members[:5]]
        labels = [G.nodes[m].get("label", m) for m in members[:5] if m in G.nodes]
        if dry_run:
            tokens_used += 300
            llm_calls += 1
            continue
        prompt = (
            f"Summarize community {cid} with members {labels!r} "
            f"(ids: {top_members!r}) in one sentence."
        )
        try:
            text, cost = _call_llm(prompt, max_tokens=200)
        except Exception as exc:
            raise RuntimeError(
                f"community pass LLM call failed on community {cid}: {exc}"
            ) from exc
        summaries[str(cid)] = _sanitize_pass_output(text)
        tokens_used += cost
        llm_calls += 1

    return summaries, tokens_used, llm_calls


# ---- Pass 4: staleness (compute-only, reuses delta.classify_staleness) ----

def _run_staleness_pass(
    G,
    out_dir: Path,
    snapshot_id: str,
    *,
    alias_map: dict[str, str],
    dry_run: bool = False,
) -> tuple[dict[str, str], int, int]:
    """D-01 pass 4 — compute-only staleness classification.

    Wraps ``delta.classify_staleness(node_data)`` for every node; ALWAYS
    returns ``(result, 0, 0)`` so the orchestrator's D-03 budget accounting
    stays untouched by this pass. Keys are threaded through ``alias_map``
    (D-16) so only canonical node_ids appear in the output dict.

    ``dry_run`` is accepted for signature uniformity with the LLM passes but
    has no effect here — the classification is cheap, and Plan 06's
    ``--dry-run`` preview still benefits from an accurate staleness snapshot.
    """
    from graphify.delta import classify_staleness

    results: dict[str, str] = {}
    valid_labels = {"FRESH", "STALE", "GHOST"}
    for nid, data in G.nodes(data=True):
        canonical = alias_map.get(nid, nid)  # D-16
        label = classify_staleness(data)
        if label not in valid_labels:
            # Defense-in-depth (T-15-05): only persist the expected enum.
            print(
                f"[graphify] enrichment: unexpected staleness label {label!r} "
                f"for node {nid!r}; skipping",
                file=sys.stderr,
            )
            continue
        results[canonical] = label
    return results, 0, 0  # D-03 compute-only invariant
