"""Per-file complexity classification and model routing (Phase 12, ROUTE-01..07)."""
from __future__ import annotations

import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as e:  # pragma: no cover - exercised when PyYAML missing
    yaml = None  # type: ignore[assignment]
    _YAML_ERR = e
else:
    _YAML_ERR = None

# Code suffixes aligned with extract._DISPATCH (ROUTE-06 floor applies to these)
CODE_SUFFIXES: frozenset[str] = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".c", ".h", ".cpp", ".cc",
    ".cxx", ".hpp", ".rb", ".cs", ".kt", ".kts", ".scala", ".php", ".swift", ".lua", ".toc",
    ".zig", ".ps1", ".ex", ".exs", ".m", ".mm", ".jl", ".vue", ".svelte",
})
IMAGE_SUFFIXES: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"})

TIER_ORDER: dict[str, int] = {
    "trivial": 0,
    "simple": 1,
    "complex": 2,
    "vision": 3,
}


def tier_rank(name: str) -> int:
    return TIER_ORDER.get(name, 0)


@dataclass
class ComplexityMetrics:
    """Metrics used to suggest a tier before floors."""

    path: Path
    file_type: str  # code | document | image
    cyclomatic_max: float
    line_count: int
    import_count: int
    symbol_count: int
    nesting_hint: int
    suggested_tier: str  # trivial | simple | complex


@dataclass
class ResolvedRoute:
    """One routing decision for a file."""

    tier: str
    model_id: str
    endpoint: str
    skip_extraction: bool = False
    metrics: ComplexityMetrics | None = None

    def rank(self) -> int:
        return tier_rank(self.tier)


_DEFAULT_CONFIG: dict[str, Any] = {}


def _package_yaml_path() -> Path:
    return Path(__file__).resolve().parent / "routing_models.yaml"


def load_routing_config(path: Path | None = None) -> dict[str, Any]:
    """Load routing YAML via yaml.safe_load only (no eval). Merges safe defaults."""
    if yaml is None:
        raise ImportError(
            "graphify routing requires PyYAML — pip install 'graphifyy[routing]' or PyYAML"
        ) from _YAML_ERR
    p = path or _package_yaml_path()
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return dict(_DEFAULT_CONFIG)
    return raw


def _count_imports(text: str) -> int:
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("import ") or s.startswith("from "):
            n += 1
    return n


def _count_symbols_py(text: str) -> int:
    """Lightweight symbol count: defs + class lines."""
    n = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("def ", "class ", "async def ")):
            n += 1
    return n


def _nesting_hint_generic(text: str) -> int:
    """Brace/bracket depth heuristic (no tree-sitter)."""
    depth = max_d = 0
    for ch in text:
        if ch in "{[(":
            depth += 1
            max_d = max(max_d, depth)
        elif ch in "}])":
            depth = max(0, depth - 1)
    return max_d


def _classify_python(path: Path, text: str, thresholds: dict[str, Any]) -> ComplexityMetrics:
    trivial_cc = int(thresholds.get("trivial_max_cc", 5))
    simple_cc = int(thresholds.get("simple_max_cc", 15))
    cc_max = 0.0
    try:
        from radon.complexity import cc_visit  # type: ignore[import-untyped]

        blocks = cc_visit(text)
        if blocks:
            cc_max = max(getattr(b, "complexity", 0) for b in blocks)
    except Exception:
        # Conservative: use line-based proxy when radon missing or parse fails
        cc_max = max(1.0, len(text.splitlines()) / 50.0)

    lines = len(text.splitlines())
    imp = _count_imports(text)
    sym = _count_symbols_py(text)
    nest = _nesting_hint_generic(text)

    if cc_max <= trivial_cc and lines <= int(thresholds.get("trivial_max_lines", 80)):
        suggested = "trivial"
    elif cc_max <= simple_cc and lines <= int(thresholds.get("simple_max_lines", 400)):
        suggested = "simple"
    else:
        suggested = "complex"

    return ComplexityMetrics(
        path=path,
        file_type="code",
        cyclomatic_max=cc_max,
        line_count=lines,
        import_count=imp,
        symbol_count=sym,
        nesting_hint=nest,
        suggested_tier=suggested,
    )


def _classify_non_python_code(path: Path, text: str, thresholds: dict[str, Any]) -> ComplexityMetrics:
    lines = len(text.splitlines())
    imp = _count_imports(text)
    sym = len(re.findall(r"\b(function|def|class|fn|pub struct|interface)\b", text))
    nest = _nesting_hint_generic(text)
    if lines < 40 and imp <= 3:
        suggested = "trivial"
    elif lines < 200:
        suggested = "simple"
    else:
        suggested = "complex"
    return ComplexityMetrics(
        path=path,
        file_type="code",
        cyclomatic_max=float(min(lines // 10, 50)),
        line_count=lines,
        import_count=imp,
        symbol_count=sym,
        nesting_hint=nest,
        suggested_tier=suggested,
    )


def classify_file(path: Path, *, thresholds: dict[str, Any] | None = None) -> ComplexityMetrics:
    """AST/heuristic complexity classification (ROUTE-01)."""
    th = thresholds or {}
    suf = path.suffix.lower()
    if suf in IMAGE_SUFFIXES:
        return ComplexityMetrics(
            path=path,
            file_type="image",
            cyclomatic_max=0.0,
            line_count=0,
            import_count=0,
            symbol_count=0,
            nesting_hint=0,
            suggested_tier="trivial",
        )
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ComplexityMetrics(
            path=path,
            file_type="document",
            cyclomatic_max=0.0,
            line_count=0,
            import_count=0,
            symbol_count=0,
            nesting_hint=0,
            suggested_tier="simple",
        )

    if suf == ".py":
        return _classify_python(path, text, th)
    if suf in CODE_SUFFIXES:
        return _classify_non_python_code(path, text, th)
    return ComplexityMetrics(
        path=path,
        file_type="document",
        cyclomatic_max=0.0,
        line_count=len(text.splitlines()),
        import_count=_count_imports(text),
        symbol_count=0,
        nesting_hint=0,
        suggested_tier="simple",
    )


def _tier_entry(config: dict[str, Any], name: str) -> dict[str, Any]:
    tiers = config.get("tiers") or {}
    entry = tiers.get(name) or {}
    return entry if isinstance(entry, dict) else {}


def resolve_model(
    metrics: ComplexityMetrics,
    file_type: str | None,
    config: dict[str, Any],
) -> ResolvedRoute:
    """Map metrics + file type to tier + model; enforce ROUTE-06 floor for code."""
    ft = file_type or metrics.file_type
    tiers_cfg = config.get("tiers") or {}
    vision_cfg = config.get("vision") or config.get("image") or {}

    if ft == "image":
        mid = str((vision_cfg or {}).get("model_id") or "").strip()
        ep = str((vision_cfg or {}).get("endpoint") or "").strip()
        if not mid:
            return ResolvedRoute(
                tier="vision",
                model_id="",
                endpoint=ep,
                skip_extraction=True,
                metrics=metrics,
            )
        return ResolvedRoute(
            tier="vision",
            model_id=mid,
            endpoint=ep or "https://api.anthropic.com/v1/messages",
            skip_extraction=False,
            metrics=metrics,
        )

    name = metrics.suggested_tier
    if ft == "code":
        # ROUTE-06: never below simple (mid)
        if tier_rank(name) < tier_rank("simple"):
            name = "simple"

    entry = _tier_entry(config, name)
    mid = str(entry.get("model_id") or "").strip()
    ep = str(entry.get("endpoint") or "").strip()
    return ResolvedRoute(tier=name, model_id=mid, endpoint=ep, skip_extraction=False, metrics=metrics)


@dataclass
class Router:
    """Holds config + ROUTE-07 concurrency primitives + classify/resolve."""

    config: dict[str, Any]
    _semaphore: threading.Semaphore = field(init=False, repr=False)
    _429_backoff: threading.Event = field(init=False, repr=False)
    _429_lock: threading.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        cap = int(os.environ.get("GRAPHIFY_EXTRACT_MAX_CONCURRENT", "4"))
        self._semaphore = threading.Semaphore(max(1, cap))
        self._429_backoff = threading.Event()
        self._429_lock = threading.Lock()

    @property
    def thresholds(self) -> dict[str, Any]:
        th = self.config.get("thresholds") or {}
        return th if isinstance(th, dict) else {}

    def tier_order(self) -> dict[str, int]:
        return dict(TIER_ORDER)

    def classify(self, path: Path) -> ComplexityMetrics:
        return classify_file(path, thresholds=self.thresholds)

    def resolve(self, path: Path) -> ResolvedRoute:
        m = self.classify(path)
        return resolve_model(m, m.file_type, self.config)

    def acquire_slot(self) -> None:
        self._semaphore.acquire()

    def release_slot(self) -> None:
        self._semaphore.release()

    def enter_slot(self):
        class _Cm:
            def __init__(self, r: Router) -> None:
                self._r = r

            def __enter__(self) -> None:
                self._r.acquire_slot()
                self._r.wait_for_backoff()

            def __exit__(self, *exc: object) -> None:
                self._r.release_slot()

        return _Cm(self)

    def signal_429(self) -> None:
        with self._429_lock:
            self._429_backoff.set()

    def clear_429(self) -> None:
        with self._429_lock:
            self._429_backoff.clear()

    def wait_for_backoff(self) -> None:
        if self._429_backoff.is_set():
            time.sleep(0.05)

    def resolve_for_path(self, path: Path) -> ResolvedRoute:
        """Alias for resolve (tests / extract)."""
        return self.resolve(path)


def default_router(config_path: Path | None = None) -> Router:
    """Load YAML and construct Router."""
    cfg = load_routing_config(config_path)
    return Router(cfg)
