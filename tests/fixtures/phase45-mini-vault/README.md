# phase45-mini-vault

Synthetic Obsidian vault for Phase 45 integration smoke tests.

Contains `.obsidian/`, `.graphify/profile.yaml` (minimal v1.8-valid stub), sample markdown under `notes/`, and `src/hi.py`.

Purpose: assert `detect()` returns at least one file and never emits `graphify-out` segments unless the fixture documents an intentional exception.
