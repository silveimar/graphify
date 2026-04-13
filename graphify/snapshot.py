"""graph snapshot persistence - save, load, prune, list."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph


def snapshots_dir(root: Path = Path(".")) -> Path:
    """Returns graphify-out/snapshots/ - creates it if needed."""
    d = Path(root) / "graphify-out" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


def list_snapshots(root: Path = Path(".")) -> list[Path]:
    """Return sorted list of snapshot Paths (oldest first by mtime)."""
    d = snapshots_dir(root)
    snaps = list(d.glob("*.json"))
    snaps.sort(key=lambda p: p.stat().st_mtime)
    return snaps


def save_snapshot(
    G: nx.Graph,
    communities: dict[int, list[str]],
    root: Path = Path("."),
    name: str | None = None,
    cap: int = 10,
) -> Path:
    """Save graph snapshot to graphify-out/snapshots/{timestamp}[_name].json.

    Atomic write via tmp+os.replace. FIFO prune keeps at most `cap` snapshots.
    Returns the path to the saved snapshot.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    if name is not None:
        sanitized = re.sub(r"[^\w-]", "_", name)[:64]
        stem = f"{ts}_{sanitized}"
    else:
        stem = ts

    d = snapshots_dir(root)
    target = d / f"{stem}.json"

    # Serialize graph (same fallback as export.py)
    try:
        data = json_graph.node_link_data(G, edges="links")
    except TypeError:
        data = json_graph.node_link_data(G)

    payload = {
        "graph": data,
        "communities": {str(k): v for k, v in communities.items()},
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
        },
    }

    tmp = target.with_suffix(".tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, target)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    # FIFO prune: keep only newest `cap` snapshots
    snaps = sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for p in snaps[:-cap]:
        p.unlink(missing_ok=True)

    return target


def load_snapshot(path: Path) -> tuple[nx.Graph, dict[int, list[str]], dict]:
    """Load a snapshot from disk.

    Returns (graph, communities_with_int_keys, metadata_dict).
    Raises ValueError on corrupt or incomplete snapshot files.
    """
    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Corrupt snapshot file: {path}") from exc

    if "graph" not in payload or "communities" not in payload:
        raise ValueError(
            f"Snapshot missing required keys ('graph', 'communities'): {path}"
        )

    # Deserialize graph (same fallback as export.py)
    try:
        G = json_graph.node_link_graph(payload["graph"], edges="links")
    except TypeError:
        G = json_graph.node_link_graph(payload["graph"])

    communities = {int(k): v for k, v in payload["communities"].items()}
    metadata = payload.get("metadata", {})

    return G, communities, metadata
