"""Scoring prompt + version constant for confidence cache key composition.

Phase 65 (CCONF): the confidence cache is keyed on
``sha256(PROMPT_VERSION || model_id || file_hash)``. Bumping ``PROMPT_VERSION``
must be matched in every shipped ``graphify/skill*.md`` file (drift gate test
in tests/test_skill_prompt_drift.py).
"""
from __future__ import annotations

PROMPT_VERSION: str = "1.13.0"

SCORING_PROMPT_TEMPLATE: str = (
    "Score the relationship between the concept and the code excerpt below "
    "on a scale from 0.0 (unrelated) to 1.0 (clearly the same idea). "
    "Return JSON: {\"score\": <float 0..1>, \"evidence\": <string <=280 chars>}.\n\n"
    "Concept: {concept_label}\n"
    "Code excerpt ({source_file}:{line}):\n{code_snippet}\n"
)
