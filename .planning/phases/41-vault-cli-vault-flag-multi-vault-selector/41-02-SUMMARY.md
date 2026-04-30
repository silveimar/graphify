# Phase 41 Plan 02 — Summary

## Delivered

- **`graphify/__main__.py`**: Leading global `--vault` / `--vault-list` stripped before dispatch; `_strip_vault_flags_from_tokens`, `_merge_vault_pins`, **`_resolve_cli_paths`**; **`run`**, **`--obsidian`**, **`elicit`**, **`import-harness`** use resolver + `_PROFILE_DRIVEN_SOURCES` for D-07; `load_profile` uses `resolved.vault_path` when set.
- **`tests/test_vault_cli.py`**: subprocess checks for `GRAPHIFY_VAULT`, `doctor --vault`, multi-list exit 2.

## Verification

`pytest tests/test_vault_cli.py tests/test_output.py tests/test_main_flags.py -q`

## Notes

Approach: mutate `sys.argv` via `_strip_leading_vault_global_argv` so existing parsers keep working.
