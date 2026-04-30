# Phase 41 — Pattern Map

## Analog: resolver & tests

| New / changed | Closest analog | Notes |
|---------------|----------------|-------|
| Vault resolution API | `graphify/output.py` — `resolve_output` | Extend or wrap; keep `ResolvedOutput` shape |
| CLI precedence | `tests/test_output.py` — `test_resolve_output_cli_flag_overrides_profile_emits_stderr` | Mirror stderr assertion patterns for `--vault` |
| Profile refusal | `test_resolve_output_vault_no_profile_refuses` | Reuse fixture layout for pinned vault |

## Integration points

- **`graphify/__main__.py`** — early argv scan or `parse_known_args` for global `--vault`, `--vault-list`, env read.
- **`graphify/profile.py`** — `validate_vault_path`, `load_profile(vault_root)`.
- **`graphify/detect.py`** — doctor dry-run skip reasons unchanged except vault root source.

## PATTERN MAPPING COMPLETE
