"""Doc-fence-as-fixture tests: lift annotated code fences from docs/TEMPLATES.md and run each through _expand_blocks.

RED gate: docs/TEMPLATES.md does not yet exist (created in Plan 55-05).
Every parametrized test fails with a clear message until that file lands.

Section IDs targeted (D-55.11 — 8 sections):
  conditional-blocks, connection-loops, ordering-invariant, sanitization,
  predicate-catalog, predicate-flags, validation, backward-compat
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import networkx as nx
import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_TEMPLATES_DOC = _REPO_ROOT / "docs" / "TEMPLATES.md"

# ---------------------------------------------------------------------------
# Fence extraction
# ---------------------------------------------------------------------------
# Matches: <!-- test:<id> -->\n```<lang>\n<body>\n```
_FENCE_RE = re.compile(
    r"<!--\s*test:([\w-]+)\s*-->\s*\n```(\w*)\n(.*?)\n```",
    re.DOTALL,
)

# D-55.11 section IDs — the 8 sections that MUST be represented in the doc.
_REQUIRED_SECTION_IDS = [
    "conditional-blocks",
    "connection-loops",
    "ordering-invariant",
    "sanitization",
    "predicate-catalog",
    "predicate-flags",
    "validation",
    "backward-compat",
]


def _load_fences() -> list[tuple[str, str, str]]:
    """Return list of (test_id, lang, body) from docs/TEMPLATES.md fences.

    Returns empty list if the file is missing (RED state).
    """
    if not _TEMPLATES_DOC.exists():
        return []
    text = _TEMPLATES_DOC.read_text(encoding="utf-8")
    return [(tid, lang, body) for tid, lang, body in _FENCE_RE.findall(text)]


# ---------------------------------------------------------------------------
# Shared fixture: minimal BlockContext
# ---------------------------------------------------------------------------

def _minimal_block_context() -> Any:
    """Build a minimal BlockContext backed by a 2-node networkx graph."""
    from graphify.templates import BlockContext

    G = nx.Graph()
    G.add_node("n1", label="Node One", file_type="document", source_file="a.md")
    G.add_node("n2", label="Node Two", file_type="code", source_file="b.py")
    G.add_edge("n1", "n2")

    return BlockContext(
        graph=G,
        node_id="n1",
        edges=[
            {
                "source": "n1",
                "target": "n2",
                "relation": "references",
                "confidence": "EXTRACTED",
                "source_file": "a.md",
                "label": "Node Two",
            }
        ],
        dataview_nonempty=False,
        note_type="thing",
        flag_predicates={},
    )


# ---------------------------------------------------------------------------
# Helpers used by parametrized tests
# ---------------------------------------------------------------------------

def _call_expand_blocks(text: str, ctx: Any) -> str:
    """Import and call _expand_blocks (keeps templates import inside tests)."""
    from graphify.templates import _expand_blocks  # type: ignore[attr-defined]

    return _expand_blocks(text, ctx)


# ---------------------------------------------------------------------------
# Main parametrized test: one test per annotated fence in docs/TEMPLATES.md
# ---------------------------------------------------------------------------

_FENCE_DATA = _load_fences()

# If the doc is missing, create one stub entry per required section ID so that
# pytest collects one clearly-failing test per section (RED state per D-55.12).
if not _FENCE_DATA:
    _PARAMETRIZE_DATA: list[tuple[str, str, str]] = [
        (sid, "", "") for sid in _REQUIRED_SECTION_IDS
    ]
    _MISSING_DOC = True
else:
    _PARAMETRIZE_DATA = _FENCE_DATA
    _MISSING_DOC = False


@pytest.mark.parametrize("test_id,lang,body", _PARAMETRIZE_DATA, ids=[p[0] for p in _PARAMETRIZE_DATA])
def test_docs_template_fence(test_id: str, lang: str, body: str) -> None:
    """Each annotated fence in docs/TEMPLATES.md must render without error via _expand_blocks.

    RED state: fails with a clear message when docs/TEMPLATES.md is absent.
    GREEN state (after Plan 55-05): all fences expand successfully.
    """
    if _MISSING_DOC:
        pytest.fail(
            f"docs/TEMPLATES.md does not yet exist — Plan 55-05 will create it "
            f"(test_id={test_id!r})"
        )

    ctx = _minimal_block_context()
    # Run the fence body through _expand_blocks; must not raise.
    result = _call_expand_blocks(body, ctx)
    # Minimal smoke check: result is a string (not None, not an exception).
    assert isinstance(result, str), (
        f"_expand_blocks returned {type(result)!r} for fence {test_id!r}"
    )


# ---------------------------------------------------------------------------
# Coverage gate: each of the 8 required section IDs must appear in the doc
# (when the doc exists). Fails RED when doc is absent.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("section_id", _REQUIRED_SECTION_IDS)
def test_docs_templates_section_id_present(section_id: str) -> None:
    """Each D-55.11 section ID must be annotated (<!-- test:<id> -->) in docs/TEMPLATES.md.

    RED gate: fails until docs/TEMPLATES.md is created in Plan 55-05.
    """
    if not _TEMPLATES_DOC.exists():
        pytest.fail(
            f"docs/TEMPLATES.md does not yet exist — Plan 55-05 will create it "
            f"(expected section_id={section_id!r})"
        )

    text = _TEMPLATES_DOC.read_text(encoding="utf-8")
    found_ids = {tid for tid, _lang, _body in _FENCE_RE.findall(text)}
    assert section_id in found_ids, (
        f"Section {section_id!r} has no annotated fence (<!-- test:{section_id} -->) "
        f"in docs/TEMPLATES.md. Found: {sorted(found_ids)}"
    )
