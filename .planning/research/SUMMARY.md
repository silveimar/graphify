# Milestone v1.9 — Scope synthesis (planning)

This milestone activates dormant seeds **SEED-001**, **SEED-002**, and **SEED-vault-root-aware-cli** (remainder after v1.7 Option C).

## Themes

1. **Onboarding / tacit-to-explicit (SEED-001)** — Structured elicitation fills the graph when users lack an existing corpus; outputs pair with harness artifacts (SOUL/HEARTBEAT/USER).

2. **Harness portability + defenses (SEED-002)** — Expand beyond Claude-target harness export: additional formats, inverse import, canonical schemas. Prompt-injection and trust-boundary defenses are mandatory before inverse-import is broadly advertised.

3. **Vault CLI (seed remainder)** — v1.7 delivered CWD vault detection and profile-driven routing; v1.9 adds explicit `--vault` and a minimal multi-vault selector/discovery path so scripts and power users are not CWD-dependent.

## Risks called out in seeds

- Elicitation quality is prompt-heavy; keep evaluation criteria observable (artifacts + graph checks).
- Harness formats churn; prefer documented mappings + tests over chasing every proprietary variant.
- Vault UX must stay aligned with `doctor`, `--dry-run`, and self-ingestion rules from v1.7–v1.8.
