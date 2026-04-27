"""Per-run routing.json audit trail (ROUTE-05, Phase 12)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class RoutingAudit:
    """Collect per-file routing decisions; flush atomically to graphify-out/routing.json."""

    def __init__(self) -> None:
        self._files: dict[str, dict[str, Any]] = {}

    def record(
        self,
        path: Path,
        class_: str,
        model: str,
        endpoint: str,
        tokens_used: int,
        ms: float,
    ) -> None:
        key = str(path)
        self._files[key] = {
            "class": class_,
            "model": model,
            "endpoint": endpoint,
            "tokens_used": int(tokens_used),
            "ms": float(ms),
        }

    def flush(self, out_dir: Path) -> Path:
        """Write ``routing.json`` under *out_dir* using atomic replace. D-07/D-08: same pattern as dedup."""
        out_dir = Path(out_dir).resolve()
        cwd = Path.cwd().resolve()
        try:
            out_dir.relative_to(cwd)
        except ValueError as e:
            raise ValueError(
                f"routing audit output path {out_dir} escapes working directory {cwd}"
            ) from e
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "routing.json"
        # MANIFEST-09/10: read existing routing.json, merge new run's files on top (last-write-wins by path).
        existing: dict[str, Any] = {}
        if dest.exists():
            try:
                existing = json.loads(dest.read_text(encoding="utf-8")).get("files", {}) or {}
            except (json.JSONDecodeError, OSError):
                existing = {}
        merged_files = {**existing, **self._files}
        payload = {"version": 1, "files": dict(sorted(merged_files.items()))}
        tmp = dest.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp, dest)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        return dest
