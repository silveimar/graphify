from __future__ import annotations

"""Allowlist frontmatter augmentation for user files (Phase 70 / VPROF-03 augmentation half).

Body bytes are guaranteed byte-identical (D-07). DO NOT use cache.file_hash here
(it strips frontmatter). DO NOT introduce PyYAML on the write path — re-emit via
graphify.profile._dump_frontmatter only.

Decisions:
- D-04: list keys (tags, related_to, up, references) → union with user order preserved
- D-05: scalar keys (comments, analysis, type) → only-if-absent
- D-06: stateless re-add — if user deletes a key, graphify will re-add it next run
- D-07: body bytes byte-identical pre/post augmentation
- D-16: "community" scalar gated on profile.augment.allow_community (default false)
"""

import os
from pathlib import Path

from graphify.merge import _find_body_start, _parse_frontmatter
from graphify.profile import _dump_frontmatter

_ALLOWLIST_LISTS = frozenset({"tags", "related_to", "up", "references"})  # D-04
_ALLOWLIST_SCALARS = frozenset({"comments", "analysis", "type"})           # D-05
# "community" is admitted into the scalar allowlist iff D-16 gate enabled.

_BOM = "﻿"


def augment_user_file_frontmatter(
    target: Path,
    augmentations: dict,
    profile: dict,
) -> tuple[Path, list[str]]:
    """Merge allowlist keys from `augmentations` into `target`'s frontmatter.

    Body bytes after the closing `---` delimiter are guaranteed byte-identical
    pre/post call (D-07). If no allowlist keys would change, the file is not
    rewritten.

    Returns
    -------
    (target, sorted_changed_keys)
        Empty list when no change was made.

    Raises
    ------
    Any exception from underlying I/O. The atomic-replace pattern guarantees the
    original file content is preserved on mid-write failure.
    """
    raw_bytes = target.read_bytes()
    raw = raw_bytes.decode("utf-8")
    had_bom = raw.startswith(_BOM)
    text = raw[1:] if had_bom else raw
    ended_with_newline = text.endswith("\n")

    body_start = _find_body_start(text)
    body = text[body_start:]
    existing_fm = _parse_frontmatter(text) or {}

    # D-16: gate "community" key on profile.augment.allow_community
    allow_community = bool(
        (profile or {}).get("augment", {}).get("allow_community", False)
    )
    scalars_allowed = set(_ALLOWLIST_SCALARS)
    if allow_community:
        scalars_allowed.add("community")

    merged = dict(existing_fm)  # preserves user insertion order
    changed_keys: list[str] = []

    for key, incoming in augmentations.items():
        if key in _ALLOWLIST_LISTS:
            # D-04: union, preserve user order, append new items at end
            current = list(merged.get(key, []) or [])
            incoming_list = list(incoming) if isinstance(incoming, list) else [incoming]
            new_items = [it for it in incoming_list if it not in current]
            if new_items:
                merged[key] = current + new_items
                changed_keys.append(key)
            elif key not in merged:
                # No new items and key was absent → still create empty? No:
                # only create when there is at least one item to add.
                if incoming_list:
                    merged[key] = incoming_list
                    changed_keys.append(key)
        elif key in scalars_allowed:
            # D-05: only-if-absent
            if key not in merged or merged.get(key) in (None, ""):
                merged[key] = incoming
                changed_keys.append(key)
        else:
            # Non-allowlist key (or community without gate) → ignore
            continue

    if not changed_keys:
        return (target, [])

    new_fm = _dump_frontmatter(merged)
    # _dump_frontmatter does NOT emit a trailing newline. Always insert exactly
    # one "\n" between the closing "---" and `body`: the parser strips that one
    # delimiter-terminating newline on read, so emitting it here produces a file
    # whose post-frontmatter byte slice equals `body` exactly (D-07).
    new_text = new_fm + "\n" + body

    # D-07 trailing-newline preservation
    if ended_with_newline and not new_text.endswith("\n"):
        new_text += "\n"
    if had_bom:
        new_text = _BOM + new_text

    tmp = target.with_suffix(target.suffix + ".tmp")
    # Use write_bytes to avoid any text-mode newline translation; D-07 requires
    # body bytes byte-identical, including preservation of CRLF sequences.
    tmp.write_bytes(new_text.encode("utf-8"))
    try:
        os.replace(tmp, target)
    except Exception:
        # Cleanup tmp; original target untouched
        try:
            tmp.unlink()
        except OSError:
            pass
        raise

    return (target, sorted(changed_keys))
