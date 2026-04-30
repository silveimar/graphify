# Phase 41 Plan 04 — Summary

## Delivered

- **`README.md`**: Subsection **Vault selection for scripting** (precedence, `--vault`, `GRAPHIFY_VAULT`, `--vault-list`, D-03 TTY vs CI, `--output` composition); links to `graphify/output.py` as precedence source of truth.
- **`graphify/__main__.py`**: Top-level `--help` block listing vault flags and precedence.

## Verification

```bash
python -m graphify --help | rg 'GRAPHIFY_VAULT|--vault'
python -c "from pathlib import Path; t=Path('README.md').read_text(encoding='utf-8'); assert 'GRAPHIFY_VAULT' in t and 'Vault selection' in t"
```
