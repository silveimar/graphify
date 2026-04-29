"""Naming helpers for repo identity and concept MOC provenance."""
from __future__ import annotations

import configparser
import hashlib
import re
import sys
from pathlib import Path
from typing import Literal, NamedTuple


class ResolvedRepoIdentity(NamedTuple):
    identity: str
    source: Literal["cli-flag", "profile", "fallback-git-remote", "fallback-directory"]
    raw_value: str
    warnings: tuple[str, ...] = ()


class ConceptName(NamedTuple):
    community_id: int
    title: str
    filename_stem: str
    source: str
    signature: str
    reason: str


_REPO_IDENTITY_MAX_LEN = 80


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


def resolve_concept_names(*args: object, **kwargs: object) -> dict[int, ConceptName]:
    """Placeholder contract for later concept naming implementation."""
    raise NotImplementedError("concept naming is implemented in a later Phase 33 plan")
