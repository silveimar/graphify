"""Naming helpers for repo identity and concept MOC provenance."""
from __future__ import annotations

import configparser
import hashlib
import json
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


def resolve_concept_names(
    G: nx.Graph,
    communities: dict[int, list[str]],
    profile: dict,
    artifacts_dir: Path,
    *,
    llm_namer: Callable[[dict], str | None] | None = None,
    dry_run: bool = False,
) -> dict[int, ConceptName]:
    """Resolve concept MOC names with deterministic fallback behavior."""
    del artifacts_dir, llm_namer, dry_run

    concept_config = profile.get("naming", {}).get("concept_names", {})
    enabled = bool(concept_config.get("enabled", True))
    reason = "llm-unavailable" if enabled else "disabled"

    resolved: dict[int, ConceptName] = {}
    for cid in sorted(communities):
        members = communities[cid]
        signature = _community_signature(G, members)
        title = _fallback_title(G, members, cid, signature)
        resolved[cid] = ConceptName(
            community_id=cid,
            title=title,
            filename_stem=_filename_stem(title),
            source="fallback",
            signature=signature,
            reason=reason,
        )
    return resolved
