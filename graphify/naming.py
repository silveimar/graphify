"""Naming helpers for repo identity and concept MOC provenance."""
from __future__ import annotations

import configparser
import datetime
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable, Literal, NamedTuple

import networkx as nx


class ResolvedRepoIdentity(NamedTuple):
    identity: str
    source: Literal["cli-flag", "profile", "fallback-git-remote", "fallback-directory"]
    raw_value: str
    warnings: tuple[str, ...] = ()


class ConceptName(NamedTuple):
    community_id: int
    title: str
    filename_stem: str
    source: Literal["llm-cache", "llm-fresh", "fallback", "cache-tolerant"]
    signature: str
    reason: str


_REPO_IDENTITY_MAX_LEN = 80
_CONCEPT_STOP_WORDS = {
    "community",
    "node",
    "file",
    "source",
    "module",
    "class",
    "function",
    "method",
    "test",
}
_CONCEPT_CACHE_VERSION = 1
_CONCEPT_CACHE_NAME = "concept-names.json"
_GENERIC_TITLES = {"community", "concept", "node", "file", "source", "module"}
_MAX_TITLE_LEN = 80


def normalize_repo_identity(value: str) -> str:
    """Normalize a repo identity into a short path-safe slug."""
    if "/" in value or "\\" in value or ".." in value:
        raise ValueError("repo identity must not contain path segments or '..'")

    raw = value.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if not slug:
        return "repo"
    if len(slug) > _REPO_IDENTITY_MAX_LEN:
        suffix = hashlib.sha256(slug.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:_REPO_IDENTITY_MAX_LEN - 9]}-{suffix}"
    return slug


def _repo_slug_from_remote_url(remote_url: str) -> str | None:
    """Extract a repository basename from a git remote URL."""
    url = remote_url.strip()
    if not url:
        return None

    # Handles both path-style HTTPS remotes and SCP-style git@host:owner/repo.git.
    last_segment = re.split(r"[/:\s]+", url.rstrip("/"))[-1]
    if last_segment.endswith(".git"):
        last_segment = last_segment[:-4]
    try:
        return normalize_repo_identity(last_segment)
    except ValueError:
        return None


def _repo_slug_from_git_config(cwd: Path) -> tuple[str, str] | None:
    """Read .git/config with stdlib configparser and return (slug, raw_url)."""
    git_config = Path(cwd) / ".git" / "config"
    if not git_config.exists():
        return None

    parser = configparser.ConfigParser()
    try:
        parser.read(git_config, encoding="utf-8")
    except configparser.Error:
        return None

    for section in parser.sections():
        if not section.startswith("remote "):
            continue
        remote_url = parser.get(section, "url", fallback="").strip()
        slug = _repo_slug_from_remote_url(remote_url)
        if slug:
            return slug, remote_url
    return None


def _accepted_explicit_identity(
    value: str | None,
    source: Literal["cli-flag", "profile"],
    warnings: list[str],
) -> tuple[str, str] | None:
    if value is None:
        return None
    try:
        identity = normalize_repo_identity(value)
    except ValueError as exc:
        warning = f"{source} repo identity rejected: {exc}"
        warnings.append(warning)
        print(f"[graphify] repo identity warning: {warning}", file=sys.stderr)
        return None
    if identity == "repo" and not value.strip():
        warning = f"{source} repo identity rejected: value must be non-empty"
        warnings.append(warning)
        print(f"[graphify] repo identity warning: {warning}", file=sys.stderr)
        return None
    return identity, value


def resolve_repo_identity(
    cwd: Path,
    *,
    cli_identity: str | None = None,
    profile: dict | None = None,
) -> ResolvedRepoIdentity:
    """Resolve repo identity with CLI > profile > git remote > directory precedence."""
    warnings: list[str] = []

    cli_result = _accepted_explicit_identity(cli_identity, "cli-flag", warnings)
    if cli_result is not None:
        identity, raw_value = cli_result
        print(f"[graphify] repo identity: {identity} (source=cli-flag)", file=sys.stderr)
        return ResolvedRepoIdentity(identity, "cli-flag", raw_value, tuple(warnings))

    profile_identity = None
    repo_block = profile.get("repo") if isinstance(profile, dict) else None
    if isinstance(repo_block, dict):
        profile_identity = repo_block.get("identity")
    if isinstance(profile_identity, str):
        profile_result = _accepted_explicit_identity(profile_identity, "profile", warnings)
        if profile_result is not None:
            identity, raw_value = profile_result
            print(f"[graphify] repo identity: {identity} (source=profile)", file=sys.stderr)
            return ResolvedRepoIdentity(identity, "profile", raw_value, tuple(warnings))

    git_result = _repo_slug_from_git_config(cwd)
    if git_result is not None:
        identity, raw_value = git_result
        print(
            f"[graphify] repo identity: {identity} (source=fallback-git-remote)",
            file=sys.stderr,
        )
        return ResolvedRepoIdentity(
            identity,
            "fallback-git-remote",
            raw_value,
            tuple(warnings),
        )

    raw_value = Path(cwd).name
    identity = normalize_repo_identity(raw_value)
    print(
        f"[graphify] repo identity: {identity} (source=fallback-directory)",
        file=sys.stderr,
    )
    return ResolvedRepoIdentity(identity, "fallback-directory", raw_value, tuple(warnings))


def _stringify_source_file(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return "|".join(str(item) for item in value)
    return str(value or "")


def _community_signature(G: nx.Graph, members: list[str]) -> str:
    """Hash sorted member IDs, labels, and source files into a stable signature."""
    payload = []
    for node_id in sorted(str(member) for member in members):
        data = G.nodes.get(node_id, {})
        payload.append(
            {
                "id": node_id,
                "label": str(data.get("label", node_id)),
                "source_file": _stringify_source_file(data.get("source_file", "")),
            }
        )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _top_terms(G: nx.Graph, members: list[str], limit: int = 3) -> list[str]:
    """Return title-cased, meaningful label terms weighted by node degree."""
    scores: dict[str, tuple[int, str]] = {}
    for member in sorted(str(m) for m in members):
        data = G.nodes.get(member, {})
        if data.get("file_type") == "file":
            continue
        label = str(data.get("label", member))
        weight = int(G.degree(member)) if member in G else 0
        for raw_term in re.split(r"[^A-Za-z0-9]+", label):
            term = raw_term.strip()
            if not term:
                continue
            key = term.lower()
            if key in _CONCEPT_STOP_WORDS:
                continue
            current_score = scores.get(key, (0, term))[0]
            scores[key] = (current_score + max(weight, 1), term)

    ranked = sorted(scores.items(), key=lambda item: (-item[1][0], item[0]))
    return [term.title() for _, (_, term) in ranked[:limit]]


def _fallback_title(
    G: nx.Graph,
    members: list[str],
    cid: int,
    signature: str,
) -> str:
    """Build a deterministic concept title from top terms and a stable suffix."""
    suffix = f"c{cid}{signature[:2]}"
    terms = _top_terms(G, members)
    if not terms:
        return f"Concept {suffix}"
    return f"{' '.join(terms)} {suffix}"


def _filename_stem(title: str) -> str:
    name = unicodedata.normalize("NFC", title.replace(" ", "_"))
    name = re.sub(
        r'[\\/*?:"<>|#^[\]\x00-\x1f\x7f\u0085\u2028\u2029]', "", name
    ).strip() or "unnamed"
    if len(name) > 200:
        suffix = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        name = name[:191] + "_" + suffix
    return name


def _load_concept_name_cache(artifacts_dir: Path) -> dict:
    """Load concept name sidecar cache, returning an empty cache on corruption."""
    cache_path = Path(artifacts_dir) / _CONCEPT_CACHE_NAME
    if not cache_path.exists():
        return {"version": _CONCEPT_CACHE_VERSION, "entries": {}}

    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(
            "[graphify] concept naming cache corrupted or unreadable — "
            "falling back to deterministic names",
            file=sys.stderr,
        )
        return {"version": _CONCEPT_CACHE_VERSION, "entries": {}}

    if isinstance(raw, dict) and isinstance(raw.get("entries"), dict):
        return {
            "version": raw.get("version", _CONCEPT_CACHE_VERSION),
            "entries": raw["entries"],
            "updated_at": raw.get("updated_at", ""),
        }

    if isinstance(raw, dict):
        entries: dict[str, dict] = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                entry = dict(value)
                entry.setdefault("community_id", key)
                entry.setdefault("signature", entry.get("signature", key))
                entries[str(key)] = entry
        return {"version": _CONCEPT_CACHE_VERSION, "entries": entries}

    print(
        "[graphify] concept naming cache corrupted or unreadable — "
        "falling back to deterministic names",
        file=sys.stderr,
    )
    return {"version": _CONCEPT_CACHE_VERSION, "entries": {}}


def _save_concept_name_cache(artifacts_dir: Path, cache: dict) -> None:
    """Write concept name sidecar cache atomically."""
    cache_path = Path(artifacts_dir) / _CONCEPT_CACHE_NAME
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(".json.tmp")
    payload = {
        "version": _CONCEPT_CACHE_VERSION,
        "entries": cache.get("entries", {}),
        "updated_at": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, cache_path)
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise


def _validate_title_candidate(
    title: str | None,
    used_titles: set[str],
) -> tuple[bool, str]:
    if title is None:
        return False, "empty"
    candidate = str(title).strip()
    if not candidate:
        return False, "empty"
    if len(candidate) > _MAX_TITLE_LEN:
        return False, "too-long"
    lowered = candidate.lower()
    if lowered in _GENERIC_TITLES:
        return False, "generic"
    if lowered in used_titles:
        return False, "duplicate"
    if "/" in candidate or "\\" in candidate or ".." in candidate:
        return False, "path-like"
    if "[[" in candidate or "]]" in candidate or "|" in candidate:
        return False, "wikilink-breaking"
    if "{{" in candidate or "}}" in candidate or "{%" in candidate or "%}" in candidate:
        return False, "template-breaking"
    if re.search(r"[\x00-\x1f\x7f\u0085\u2028\u2029]", candidate):
        return False, "control-character"
    return True, "accepted"


def _cache_entries(cache: dict) -> dict[str, dict]:
    entries = cache.get("entries", {})
    return entries if isinstance(entries, dict) else {}


def _cache_entry_to_name(
    cid: int,
    signature: str,
    entry: dict,
    source: Literal["llm-cache", "cache-tolerant"],
    reason: str,
) -> ConceptName:
    title = str(entry.get("title", "")).strip()
    filename_stem = str(entry.get("filename_stem") or _filename_stem(title))
    return ConceptName(
        community_id=cid,
        title=title,
        filename_stem=filename_stem,
        source=source,
        signature=signature,
        reason=reason,
    )


def _find_exact_cache_match(cache: dict, cid: int, signature: str) -> dict | None:
    entries = _cache_entries(cache)
    entry = entries.get(signature)
    if isinstance(entry, dict):
        return entry
    legacy_entry = entries.get(str(cid))
    if isinstance(legacy_entry, dict):
        return legacy_entry
    return None


def _find_tolerant_cache_match(cache: dict, top_terms: list[str]) -> dict | None:
    if not top_terms:
        return None
    target_terms = {term.lower() for term in top_terms}
    minimum_overlap = min(2, len(target_terms))
    for entry in _cache_entries(cache).values():
        if not isinstance(entry, dict):
            continue
        cached_terms = {
            str(term).lower()
            for term in entry.get("top_terms", [])
            if str(term).strip()
        }
        if len(target_terms & cached_terms) >= minimum_overlap:
            return entry
    return None


def _cache_record(name: ConceptName, top_terms: list[str]) -> dict:
    return {
        "community_id": name.community_id,
        "filename_stem": name.filename_stem,
        "reason": name.reason,
        "signature": name.signature,
        "source": name.source,
        "title": name.title,
        "top_terms": top_terms,
    }


def _fallback_name(
    G: nx.Graph,
    members: list[str],
    cid: int,
    signature: str,
    reason: str,
) -> ConceptName:
    title = _fallback_title(G, members, cid, signature)
    return ConceptName(
        community_id=cid,
        title=title,
        filename_stem=_filename_stem(title),
        source="fallback",
        signature=signature,
        reason=reason,
    )


def resolve_concept_names(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    artifacts_dir: Path,
    *,
    llm_namer: Callable[[dict], str | None] | None = None,
    dry_run: bool = False,
) -> dict[int, ConceptName]:
    """Resolve concept MOC names with cache-backed LLM names and fallback."""
    concept_config = profile.get("naming", {}).get("concept_names", {})
    enabled = bool(concept_config.get("enabled", True))
    try:
        budget = float(concept_config.get("budget", 1.0))
    except (TypeError, ValueError):
        budget = 0.0

    cache = _load_concept_name_cache(artifacts_dir)
    updated_entries = dict(_cache_entries(cache))
    used_titles: set[str] = set()

    resolved: dict[int, ConceptName] = {}
    for cid in sorted(communities):
        members = communities[cid]
        signature = _community_signature(G, members)
        top_terms = _top_terms(G, members)

        if not enabled:
            name = _fallback_name(G, members, cid, signature, "disabled")
            resolved[cid] = name
            used_titles.add(name.title.lower())
            updated_entries[signature] = _cache_record(name, top_terms)
            continue

        cached = _find_exact_cache_match(cache, cid, signature)
        if cached is not None:
            valid, reason = _validate_title_candidate(
                str(cached.get("title", "")),
                used_titles,
            )
            if valid:
                name = _cache_entry_to_name(
                    cid,
                    signature,
                    cached,
                    "llm-cache",
                    "cache hit",
                )
                resolved[cid] = name
                used_titles.add(name.title.lower())
                updated_entries[signature] = _cache_record(name, top_terms)
                continue

        tolerant = _find_tolerant_cache_match(cache, top_terms)
        if tolerant is not None:
            valid, reason = _validate_title_candidate(
                str(tolerant.get("title", "")),
                used_titles,
            )
            if valid:
                previous_signature = str(tolerant.get("signature", "unknown"))
                name = _cache_entry_to_name(
                    cid,
                    signature,
                    tolerant,
                    "cache-tolerant",
                    (
                        "tolerant cache hit "
                        f"previous_signature={previous_signature} "
                        f"current_signature={signature}"
                    ),
                )
                resolved[cid] = name
                used_titles.add(name.title.lower())
                updated_entries[signature] = _cache_record(name, top_terms)
                continue

        if budget <= 0:
            name = _fallback_name(G, members, cid, signature, "budget-disabled")
            resolved[cid] = name
            used_titles.add(name.title.lower())
            updated_entries[signature] = _cache_record(name, top_terms)
            continue

        if llm_namer is not None:
            try:
                candidate = llm_namer(
                    {
                        "community_id": cid,
                        "signature": signature,
                        "top_terms": top_terms,
                        "members": members,
                    }
                )
            except Exception as exc:
                name = _fallback_name(G, members, cid, signature, f"llm-error: {exc}")
            else:
                valid, reason = _validate_title_candidate(candidate, used_titles)
                if valid and candidate is not None:
                    title = str(candidate).strip()
                    name = ConceptName(
                        community_id=cid,
                        title=title,
                        filename_stem=_filename_stem(title),
                        source="llm-fresh",
                        signature=signature,
                        reason="accepted",
                    )
                else:
                    name = _fallback_name(
                        G,
                        members,
                        cid,
                        signature,
                        f"llm rejected: {reason}",
                    )
        else:
            name = _fallback_name(G, members, cid, signature, "llm-unavailable")

        resolved[cid] = name
        used_titles.add(name.title.lower())
        updated_entries[signature] = _cache_record(name, top_terms)

    if not dry_run:
        cache["entries"] = updated_entries
        _save_concept_name_cache(artifacts_dir, cache)
    return resolved
