"""Phase 54 — Obsidian per-relation parity tests (CGRAPH-04).

These tests are RED until Wave 3 (Plan 54-04) lands the per-relation section
populators in `graphify/templates.py`. Every test references a D-54.XX
decision in 54-CONTEXT.md so the planner-checker can trace coverage.

Contract under test (forward, on CODE notes):
    ## Implements / ## Documents / ## Tests / ## Realizes / ## Instantiates
    (canonical order, empty-suppression)

Contract under test (inverse, on concept MOCs):
    ## Implemented by / ## Documented by / ## Tested by / ## Realized by /
    ## Instantiated by  (canonical order, empty-suppression)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import networkx as nx
import pytest

from graphify.build import build_from_json
from graphify.export import to_obsidian


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

_ALL_RELATIONS: tuple[str, ...] = (
    "implements", "documents", "tests", "realizes", "instantiates",
)

# D-54.07: canonical FORWARD section ordering on CODE notes.
_FORWARD_SECTIONS: dict[str, str] = {
    "Implements": "implements",
    "Documents": "documents",
    "Tests": "tests",
    "Realizes": "realizes",
    "Instantiates": "instantiates",
}
_FORWARD_ORDER: tuple[str, ...] = tuple(_FORWARD_SECTIONS.keys())

# D-54.08: canonical INVERSE section ordering on concept MOC notes.
_INVERSE_SECTIONS: dict[str, str] = {
    "Implemented by": "implements",
    "Documented by": "documents",
    "Tested by": "tests",
    "Realized by": "realizes",
    "Instantiated by": "instantiates",
}
_INVERSE_ORDER: tuple[str, ...] = tuple(_INVERSE_SECTIONS.keys())

_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "concept_code"
_ROUND_TRIP = _FIXTURE_ROOT / "round_trip.json"
_VAULT_PARITY = _FIXTURE_ROOT / "vault_parity"


def _build_test_vault(tmp_path: Path) -> tuple[Path, nx.Graph]:
    """Load round_trip.json, build graph, run to_obsidian.

    Single community packs all 6 nodes so both rationale nodes (c_concept,
    c_concept2) surface as concept MOCs from the export pipeline.
    """
    extraction = json.loads(_ROUND_TRIP.read_text())
    G = build_from_json(extraction)
    communities = {0: [n["id"] for n in extraction["nodes"]]}
    out_dir = tmp_path / "vault"
    to_obsidian(G, communities, str(out_dir))
    return out_dir, G


def _h2_headers_in_order(text: str) -> list[str]:
    """Return the H2 headers (sans '## ' prefix) in the order they appear."""
    return re.findall(r"^## (.+?)$", text, flags=re.MULTILINE)


def _is_subsequence(observed: list[str], canonical: tuple[str, ...]) -> bool:
    """True when `observed` is a subsequence of `canonical` (skips allowed)."""
    j = 0
    for header in observed:
        if header not in canonical:
            continue
        try:
            new_j = canonical.index(header, j)
        except ValueError:
            return False
        j = new_j + 1
    return True


def _section_block(text: str, header: str) -> str | None:
    """Return the body of '## <header>' up to (but not including) the next '## '."""
    pattern = rf"^## {re.escape(header)}\s*\n((?:.*\n)*?)(?=^## |\Z)"
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1) if m else None


def _wikilinks_in_section(text: str, header: str) -> list[str]:
    """All [[link]] targets under a given H2 section.

    Strips display-alias suffix `|alias]]` so we get the link target.
    """
    block = _section_block(text, header)
    if block is None:
        return []
    targets: list[str] = []
    for raw in re.findall(r"\[\[(.+?)\]\]", block):
        target = raw.split("|", 1)[0].strip()
        if target:
            targets.append(target)
    return targets


def _count_graph_edges_by_relation(G: nx.Graph) -> dict[str, int]:
    counts: dict[str, int] = {rel: 0 for rel in _ALL_RELATIONS}
    for _, _, data in G.edges(data=True):
        rel = data.get("relation")
        if rel in counts:
            counts[rel] += 1
    return counts


def _count_vault_wikilinks_by_relation(
    vault_dir: Path, sections: dict[str, str]
) -> dict[str, int]:
    """Walk vault MD files, count wikilinks per H2 section header.

    sections: {"Implements": "implements", ...}
    """
    counts: dict[str, int] = {rel: 0 for rel in _ALL_RELATIONS}
    for md_path in vault_dir.rglob("*.md"):
        text = md_path.read_text()
        for header, rel in sections.items():
            pattern = rf"^## {re.escape(header)}\n((?:- \[\[.+?\]\]\n?)+)"
            for match in re.finditer(pattern, text, flags=re.MULTILINE):
                counts[rel] += match.group(1).count("[[")
    return counts


def _find_md_for_label(vault_dir: Path, label: str) -> Path | None:
    """Locate a generated MD note whose H1 title is the label.

    Filename conventions vary by profile (title_case vs kebab-case vs
    profile-driven prefixes like `CODE_<repo>_<label>.md`); the most
    deterministic identifier in the rendered note is the H1 line `# <label>`
    emitted by every built-in template. Sorting `rglob` and preferring the
    H1-title match makes label resolution reproducible across filesystems
    where `rglob` order is filesystem-dependent (macOS APFS inode order vs.
    Linux ext4 lexical order).

    Fallback: if no H1 match is found, fall back to first whole-word body
    match (legacy semantics) for non-titled artifacts.
    """
    title_re = re.compile(rf"^# {re.escape(label)}\s*$", flags=re.MULTILINE)
    needle = re.compile(rf"\b{re.escape(label)}\b")
    paths = sorted(vault_dir.rglob("*.md"))
    # Pass 1: H1 title match (deterministic single hit per label per built-in
    # template — every note emits exactly one `# ${label}` line).
    for md_path in paths:
        if title_re.search(md_path.read_text()):
            return md_path
    # Pass 2: legacy whole-word body match (sorted for determinism).
    for md_path in paths:
        if needle.search(md_path.read_text()):
            return md_path
    return None


def _concept_code_edges(G: nx.Graph) -> list[tuple[str, str, str]]:
    """Yield (src, tgt, relation) triples for the 5 concept↔code relations."""
    out: list[tuple[str, str, str]] = []
    for u, v, data in G.edges(data=True):
        rel = data.get("relation")
        if rel not in _ALL_RELATIONS:
            continue
        # Use _src/_tgt orientation if Phase 53 set it; else fall back to (u, v).
        src = data.get("_src", u)
        tgt = data.get("_tgt", v)
        if not isinstance(src, str) or not isinstance(tgt, str):
            src, tgt = u, v
        out.append((src, tgt, rel))
    return out


# ---------------------------------------------------------------------------
# RED Tests (Wave 1 — must fail on `main`)
# ---------------------------------------------------------------------------


def test_code_note_per_relation_sections_canonical_order(tmp_path):
    """D-54.07: CODE note for k_klass MUST emit forward H2 headers in
    canonical subsequence order: Implements / Documents / Tests / Realizes /
    Instantiates. Empty sections are suppressed (k_klass has only Implements
    + Realizes), so the observed subsequence skips Documents/Tests/Instantiates."""
    vault_dir, G = _build_test_vault(tmp_path)
    md = _find_md_for_label(vault_dir, "Klass")
    assert md is not None, f"could not locate CODE note for Klass under {vault_dir}"
    text = md.read_text()
    headers = [h for h in _h2_headers_in_order(text) if h in _FORWARD_ORDER]
    # D-54.07: subsequence (not equality — empty sections allowed to be skipped)
    assert _is_subsequence(headers, _FORWARD_ORDER), (
        f"forward headers {headers!r} are not a subsequence of {_FORWARD_ORDER!r}"
    )
    # And at least Implements must be present for k_klass
    assert "Implements" in headers, headers


def test_concept_moc_inverse_sections_canonical_order(tmp_path):
    """D-54.08: concept MOC for c_concept (AuthService) MUST emit inverse H2
    headers as a subsequence of: Implemented by / Documented by / Tested by /
    Realized by / Instantiated by."""
    vault_dir, G = _build_test_vault(tmp_path)
    md = _find_md_for_label(vault_dir, "AuthService")
    assert md is not None, f"could not locate concept MOC for AuthService under {vault_dir}"
    text = md.read_text()
    headers = [h for h in _h2_headers_in_order(text) if h in _INVERSE_ORDER]
    # D-54.08: subsequence
    assert _is_subsequence(headers, _INVERSE_ORDER), (
        f"inverse headers {headers!r} are not a subsequence of {_INVERSE_ORDER!r}"
    )
    # AuthService MOC has at least Implemented by + Tested by + Documented by
    assert "Implemented by" in headers, headers


def test_empty_relation_section_suppressed(tmp_path):
    """D-54.07 / empty-suppression: k_subklass has only `instantiates` edges,
    so its CODE note MUST contain '## Instantiates' AND MUST NOT emit empty
    forward sections for the other 4 relations."""
    vault_dir, _G = _build_test_vault(tmp_path)
    md = _find_md_for_label(vault_dir, "SubKlass")
    assert md is not None, f"could not locate CODE note for SubKlass under {vault_dir}"
    text = md.read_text()
    # D-54.07: only Instantiates section is present among the 5 forward relations
    assert "## Instantiates" in text, text
    for forbidden in ("## Implements", "## Documents", "## Tests", "## Realizes"):
        assert forbidden not in text, (
            f"empty-suppression violated: {forbidden!r} present in SubKlass note"
        )


def test_forward_parity_edges_to_wikilinks(tmp_path):
    """D-54.12 (forward parity): every concept↔code edge in the graph whose
    `_src` is a code/test/document node MUST appear as a wikilink under the
    matching forward H2 section in that node's note."""
    vault_dir, G = _build_test_vault(tmp_path)
    # Map node id -> label for human-friendly assertion messages.
    label_of = {n: G.nodes[n].get("label", n) for n in G.nodes()}
    file_type_of = {n: G.nodes[n].get("file_type", "") for n in G.nodes()}

    forward_inverse = {v: k for k, v in _FORWARD_SECTIONS.items()}

    missing: list[str] = []
    for src, tgt, rel in _concept_code_edges(G):
        # Forward parity asks: when src is a code-side artifact, the section
        # under src's note carries a wikilink to tgt.
        if file_type_of.get(src) not in ("code", "document"):
            continue
        src_md = _find_md_for_label(vault_dir, label_of[src])
        if src_md is None:
            missing.append(f"no note for src={src!r} ({label_of[src]})")
            continue
        text = src_md.read_text()
        section = forward_inverse[rel]
        targets = _wikilinks_in_section(text, section)
        # D-54.12: target label must appear in the section's wikilinks
        if not any(label_of[tgt] in t for t in targets):
            missing.append(
                f"{label_of[src]} ## {section} missing wikilink to {label_of[tgt]}; "
                f"saw {targets!r}"
            )
    assert not missing, "forward parity violations:\n  " + "\n  ".join(missing)


def test_backward_parity_wikilinks_to_edges(tmp_path):
    """D-54.12 (backward parity): every wikilink emitted under any of the 10
    Phase 54 H2 sections (5 forward + 5 inverse) MUST correspond to a graph
    edge with the matching `relation`. Forward sections live on code-side
    files; inverse sections live on MOC-side files."""
    vault_dir, G = _build_test_vault(tmp_path)
    label_of = {n: G.nodes[n].get("label", n) for n in G.nodes()}
    # Build relation -> set of {(active_label, passive_label)} from edges
    edges_by_relation: dict[str, set[tuple[str, str]]] = {
        rel: set() for rel in _ALL_RELATIONS
    }
    for src, tgt, rel in _concept_code_edges(G):
        edges_by_relation[rel].add((label_of[src], label_of[tgt]))

    violations: list[str] = []
    total_links_seen = 0
    for md_path in vault_dir.rglob("*.md"):
        text = md_path.read_text()
        # Forward sections — wikilinks point at concept MOCs (target side)
        for header, rel in _FORWARD_SECTIONS.items():
            for target in _wikilinks_in_section(text, header):
                total_links_seen += 1
                if not any(target in passive for _, passive in edges_by_relation[rel]):
                    violations.append(
                        f"{md_path.name} ## {header} -> {target!r} "
                        f"has no matching {rel} edge"
                    )
        # Inverse sections — wikilinks point at code-side artifacts (src side)
        for header, rel in _INVERSE_SECTIONS.items():
            for target in _wikilinks_in_section(text, header):
                total_links_seen += 1
                if not any(target in active for active, _ in edges_by_relation[rel]):
                    violations.append(
                        f"{md_path.name} ## {header} -> {target!r} "
                        f"has no matching {rel} edge"
                    )
    # D-54.12: must observe forward + inverse wikilinks summing to 2× edges
    # (each typed edge appears once on the code-side note as forward and once
    # on the concept MOC as inverse — see _count_vault_wikilinks_by_relation
    # parity bookkeeping). Original RED assertion conflated single-side count
    # with total — corrected here to match the actual per-relation contract.
    edge_count = sum(_count_graph_edges_by_relation(G).values())
    expected_total = 2 * edge_count
    assert total_links_seen == expected_total, (
        f"backward parity must inspect forward+inverse wikilinks for all "
        f"{edge_count} concept↔code edges (expected {expected_total} total); "
        f"observed {total_links_seen} wikilinks across all 10 Phase 54 sections"
    )
    assert not violations, "backward parity violations:\n  " + "\n  ".join(violations)


def test_per_relation_count_parity(tmp_path):
    """D-54.12 (count parity): for each of the 5 relations,
    forward_count == inverse_count == graph_edge_count."""
    vault_dir, G = _build_test_vault(tmp_path)
    graph_counts = _count_graph_edges_by_relation(G)
    forward_counts = _count_vault_wikilinks_by_relation(vault_dir, _FORWARD_SECTIONS)
    inverse_counts = _count_vault_wikilinks_by_relation(vault_dir, _INVERSE_SECTIONS)
    # D-54.12
    for rel in _ALL_RELATIONS:
        assert forward_counts[rel] == graph_counts[rel], (
            f"forward parity broken for {rel}: "
            f"vault={forward_counts[rel]} graph={graph_counts[rel]}"
        )
        assert inverse_counts[rel] == graph_counts[rel], (
            f"inverse parity broken for {rel}: "
            f"vault={inverse_counts[rel]} graph={graph_counts[rel]}"
        )


def test_round_trip_per_relation_sections_idempotent(tmp_path):
    """D-54.11: running `to_obsidian` twice on the same graph MUST produce
    byte-identical content within the `concept_code_relations` sentinel-wrapped
    block of every emitted note. Section ordering and intra-section ordering
    must be deterministic across runs."""
    extraction = json.loads(_ROUND_TRIP.read_text())
    G = build_from_json(extraction)
    communities = {0: [n["id"] for n in extraction["nodes"]]}
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    to_obsidian(G, communities, str(v1))
    to_obsidian(G, communities, str(v2))

    # Sentinel markers per templates._wrap_sentinel — same format as Phase 4
    # frontmatter / wayfinder / connections / metadata blocks.
    begin_marker = "<!-- graphify:concept_code_relations:start -->"
    end_marker = "<!-- graphify:concept_code_relations:end -->"

    # Walk v1 files; for each MD, find matching v2 file and compare sentinel block.
    diffs: list[str] = []
    sentinel_blocks_seen = 0
    for md1 in v1.rglob("*.md"):
        rel_path = md1.relative_to(v1)
        md2 = v2 / rel_path
        if not md2.exists():
            diffs.append(f"missing in v2: {rel_path}")
            continue
        t1 = md1.read_text()
        t2 = md2.read_text()

        def _slice(text: str) -> str | None:
            if begin_marker in text and end_marker in text:
                start = text.index(begin_marker)
                end = text.index(end_marker, start) + len(end_marker)
                return text[start:end]
            return None

        s1, s2 = _slice(t1), _slice(t2)
        if s1 is None and s2 is None:
            continue
        sentinel_blocks_seen += 1
        if s1 != s2:
            diffs.append(f"sentinel block differs in {rel_path}")
    # D-54.11: at least one note MUST emit the concept_code_relations sentinel
    # block — otherwise the idempotence check is vacuous (no block to compare).
    assert sentinel_blocks_seen >= 1, (
        "no concept_code_relations sentinel blocks found in v1 or v2 — "
        "Phase 54 body slot not yet populated"
    )
    assert not diffs, "idempotence violations:\n  " + "\n  ".join(diffs)
