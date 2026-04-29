"""Wave 0 tests for Phase 33 naming and repo identity helpers."""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx


def _naming_api():
    from graphify.naming import (
        ConceptName,
        ResolvedRepoIdentity,
        resolve_concept_names,
        resolve_repo_identity,
    )

    return ConceptName, ResolvedRepoIdentity, resolve_concept_names, resolve_repo_identity


def _community_graph() -> tuple[nx.Graph, dict[int, list[str]]]:
    G = nx.Graph()
    G.add_node(
        "n_auth_session",
        label="Auth Session",
        file_type="code",
        source_file="auth/session.py",
        source_location="L10",
        community=12,
    )
    G.add_node(
        "n_refresh_token",
        label="Refresh Token",
        file_type="code",
        source_file="auth/tokens.py",
        source_location="L20",
        community=12,
    )
    G.add_node(
        "n_login_flow",
        label="Login Flow",
        file_type="document",
        source_file="docs/login.md",
        source_location="L1",
        community=12,
    )
    G.add_edges_from([
        ("n_auth_session", "n_refresh_token"),
        ("n_auth_session", "n_login_flow"),
    ])
    return G, {12: ["n_auth_session", "n_refresh_token", "n_login_flow"]}


def _profile(**concept_overrides: object) -> dict:
    concept_names = {"enabled": True, "budget": 1.0, "style": "concise"}
    concept_names.update(concept_overrides)
    return {"naming": {"concept_names": concept_names}}


def test_concept_name_uses_cached_llm_title(tmp_path, capsys, monkeypatch):
    ConceptName, _, resolve_concept_names, _ = _naming_api()
    G, communities = _community_graph()
    artifacts_dir = tmp_path / "graphify-out"
    artifacts_dir.mkdir()
    cache_path = artifacts_dir / "concept-names.json"
    cached = ConceptName(
        community_id=12,
        title="Authentication Session Flow",
        filename_stem="Authentication_Session_Flow",
        source="llm-cache",
        signature="placeholder",
        reason="cache hit",
    )
    cache_path.write_text(json.dumps({"12": cached._asdict()}), encoding="utf-8")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("cached title should avoid a fresh LLM naming call")

    result = resolve_concept_names(
        G,
        communities,
        _profile(),
        artifacts_dir,
        llm_namer=fail_if_called,
    )

    assert result[12].title == "Authentication Session Flow"
    assert result[12].source == "llm-cache"
    assert result[12].filename_stem == "Authentication_Session_Flow"
    assert "concept-names.json" in str(cache_path)


def test_fallback_name_uses_terms_and_suffix(tmp_path, capsys, monkeypatch):
    _, _, resolve_concept_names, _ = _naming_api()
    G, communities = _community_graph()

    result = resolve_concept_names(
        G,
        communities,
        _profile(enabled=False),
        tmp_path / "graphify-out",
    )

    name = result[12]
    assert name.source == "fallback"
    assert name.title.startswith("Auth Session")
    assert name.title != "Community 12"
    assert "c12" in name.title.lower() or "12" in name.filename_stem
    assert name.signature


def test_same_signature_reuses_filename(tmp_path, capsys, monkeypatch):
    _, _, resolve_concept_names, _ = _naming_api()
    G, communities = _community_graph()
    artifacts_dir = tmp_path / "graphify-out"

    first = resolve_concept_names(G, communities, _profile(enabled=False), artifacts_dir)
    second = resolve_concept_names(G, communities, _profile(enabled=False), artifacts_dir)

    assert second[12].signature == first[12].signature
    assert second[12].filename_stem == first[12].filename_stem


def test_concept_name_provenance_records_source(tmp_path, capsys, monkeypatch):
    _, _, resolve_concept_names, _ = _naming_api()
    G, communities = _community_graph()

    def generic_title(*args, **kwargs) -> str:
        return "Community"

    result = resolve_concept_names(
        G,
        communities,
        _profile(),
        tmp_path / "graphify-out",
        llm_namer=generic_title,
    )

    name = result[12]
    assert name.source in {"fallback", "cache-tolerant"}
    assert name.signature
    assert "generic" in name.reason.lower() or "rejected" in name.reason.lower()


def test_unsafe_llm_title_rejected(tmp_path, capsys, monkeypatch):
    _, _, resolve_concept_names, _ = _naming_api()
    G, communities = _community_graph()
    unsafe_titles = iter([
        "]] | bad",
        "{{#connections}}",
        "../escape",
        "",
        "Community",
    ])

    for idx, title in enumerate(unsafe_titles):
        result = resolve_concept_names(
            G,
            communities,
            _profile(),
            tmp_path / f"graphify-out-{idx}",
            llm_namer=lambda *args, candidate=title, **kwargs: candidate,
            dry_run=True,
        )
        name = result[12]
        assert name.title not in {title, "Community"}
        assert ".." not in name.filename_stem
        assert "{{#connections}}" not in name.title
        assert "]]" not in name.title
        assert name.source == "fallback"

    assert not any((tmp_path / f"graphify-out-{idx}" / "concept-names.json").exists() for idx in range(5))


def test_repo_identity_cli_wins(tmp_path, capsys, monkeypatch):
    _, ResolvedRepoIdentity, _, resolve_repo_identity = _naming_api()
    result = resolve_repo_identity(
        tmp_path,
        cli_identity="cli-repo",
        profile={"repo": {"identity": "profile-repo"}},
    )

    assert result == ResolvedRepoIdentity(
        identity="cli-repo",
        source="cli-flag",
        raw_value="cli-repo",
        warnings=(),
    )
    captured = capsys.readouterr()
    assert "[graphify] repo identity: cli-repo (source=cli-flag)" in captured.err
    assert captured.err.count("[graphify] repo identity:") == 1


def test_repo_identity_profile_wins(tmp_path, capsys, monkeypatch):
    _, _, _, resolve_repo_identity = _naming_api()
    result = resolve_repo_identity(
        tmp_path,
        profile={"repo": {"identity": "work-vault"}},
    )

    assert result.identity == "work-vault"
    assert result.source == "profile"
    assert result.raw_value == "work-vault"
    captured = capsys.readouterr()
    assert "[graphify] repo identity: work-vault (source=profile)" in captured.err
    assert captured.err.count("[graphify] repo identity:") == 1


def test_repo_identity_fallback_git_remote_then_cwd(tmp_path, capsys, monkeypatch):
    _, _, _, resolve_repo_identity = _naming_api()
    repo = tmp_path / "local-copy"
    repo.mkdir()
    git_dir = repo / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text(
        "[remote \"origin\"]\n"
        "    url = git@github.com:silogia/graphify-fork.git\n",
        encoding="utf-8",
    )

    remote_result = resolve_repo_identity(repo)
    assert remote_result.identity == "graphify-fork"
    assert remote_result.source == "fallback-git-remote"

    plain = tmp_path / "Work Vault"
    plain.mkdir()
    cwd_result = resolve_repo_identity(plain)
    assert cwd_result.identity == "work-vault"
    assert cwd_result.source == "fallback-directory"

    captured = capsys.readouterr()
    assert "[graphify] repo identity: graphify-fork (source=fallback-git-remote)" in captured.err
    assert "[graphify] repo identity: work-vault (source=fallback-directory)" in captured.err
    assert "origin" in (git_dir / "config").read_text(encoding="utf-8")
