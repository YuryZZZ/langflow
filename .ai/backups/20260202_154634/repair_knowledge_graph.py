#!/usr/bin/env python3
"""repair_knowledge_graph.py

Ensures `.ai/knowledge-graph.json` exists and conforms to the strict schema used by
MCP memory tool wrappers:

{
  "entities": [
    {"name": "...", "entityType": "...", "observations": ["..."]}
  ],
  "relations": [
    {"from": "...", "to": "...", "relationType": "..."}
  ]
}

Also attempts best-effort migration from legacy formats:
- `.ai/knowledge_graph/graph.json` (nodes/edges)
- `.ai/knowledge_graph/knowledge-graph.json` (entities/relations with `type`, optional `stats`)
- JSONL backups like `.ai/knowledge-graph.json.backup` / `.ai/knowledge-graph.backup.json`

Safe to run repeatedly.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CANONICAL_ENTITY_KEYS = ("name", "entityType", "observations")
CANONICAL_REL_KEYS = ("from", "to", "relationType")


def _now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _safe_json_load(path: Path) -> Optional[Any]:
    try:
        return json.loads(_safe_read_text(path))
    except Exception:
        return None


def _backup_file(src: Path, project_root: Path) -> Optional[Path]:
    try:
        if not src.exists() or not src.is_file():
            return None
        backup_root = project_root / ".ai" / "backups" / _now_stamp()
        backup_root.mkdir(parents=True, exist_ok=True)
        dst = backup_root / src.name
        shutil.copy2(src, dst)
        return dst
    except Exception:
        return None


def _normalize_entities(raw_entities: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_entities, list):
        return out
    for e in raw_entities:
        if not isinstance(e, dict):
            continue
        name = str(e.get("name") or e.get("id") or "").strip()
        if not name:
            continue
        entity_type = str(e.get("entityType") or e.get("type") or "unknown").strip() or "unknown"

        obs = e.get("observations")
        if isinstance(obs, list):
            observations = [str(x) for x in obs if str(x).strip()]
        elif obs is None:
            observations = []
        else:
            observations = [str(obs)]

        extra = {k: v for k, v in e.items() if k not in ("name", "id", "entityType", "type", "observations")}
        if extra:
            try:
                observations.append("extra=" + json.dumps(extra, ensure_ascii=True, sort_keys=True))
            except Exception:
                observations.append("extra=<unserializable>")

        out.append({"name": name, "entityType": entity_type, "observations": observations})
    return out


def _normalize_relations(raw_rel: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(raw_rel, list):
        return out
    for r in raw_rel:
        if not isinstance(r, dict):
            continue
        fr = str(r.get("from") or "").strip()
        to = str(r.get("to") or "").strip()
        rel_type = str(r.get("relationType") or r.get("type") or "related_to").strip() or "related_to"
        if not fr or not to:
            continue
        out.append({"from": fr, "to": to, "relationType": rel_type})
    return out


def _is_canonical(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    ents = obj.get("entities")
    rels = obj.get("relations")
    if not isinstance(ents, list) or not isinstance(rels, list):
        return False
    for e in ents:
        if not isinstance(e, dict):
            return False
        if set(e.keys()) - set(CANONICAL_ENTITY_KEYS):
            return False
    for r in rels:
        if not isinstance(r, dict):
            return False
        if set(r.keys()) - set(CANONICAL_REL_KEYS):
            return False
    return True


def _from_graph_json(path: Path) -> Optional[Dict[str, Any]]:
    obj = _safe_json_load(path)
    if not isinstance(obj, dict):
        return None
    nodes = obj.get("nodes")
    edges = obj.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return None

    entities: List[Dict[str, Any]] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        name = str(n.get("name") or n.get("id") or "").strip()
        if not name:
            continue
        entity_type = str(n.get("type") or "unknown").strip() or "unknown"
        observations: List[str] = []
        data = n.get("data")
        if data is not None:
            try:
                observations.append("data=" + json.dumps(data, ensure_ascii=True, sort_keys=True))
            except Exception:
                observations.append("data=<unserializable>")
        created = n.get("created")
        if created:
            observations.append("created=" + str(created))
        entities.append({"name": name, "entityType": entity_type, "observations": observations})

    relations: List[Dict[str, Any]] = []
    for e in edges:
        if not isinstance(e, dict):
            continue
        fr = str(e.get("from") or "").strip()
        to = str(e.get("to") or "").strip()
        rel_type = str(e.get("type") or "related_to").strip() or "related_to"
        if fr and to:
            relations.append({"from": fr, "to": to, "relationType": rel_type})

    return {"entities": entities, "relations": relations}


def _from_simple_graph(path: Path) -> Optional[Dict[str, Any]]:
    obj = _safe_json_load(path)
    if not isinstance(obj, dict):
        return None
    return {"entities": _normalize_entities(obj.get("entities")), "relations": _normalize_relations(obj.get("relations"))}


def _from_jsonl_backup(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return None
    entities: List[Dict[str, Any]] = []
    relations: List[Dict[str, Any]] = []
    for raw in _safe_read_text(path).splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        t = str(obj.get("type") or "").strip().lower()
        if t == "entity":
            entities.extend(_normalize_entities([obj]))
        elif t == "relation":
            relations.extend(_normalize_relations([obj]))
    if not entities and not relations:
        return None
    return {"entities": entities, "relations": relations}


def repair(project_root: Path, verbose: bool = True) -> Tuple[Path, str]:
    project_root = project_root.resolve()
    ai_dir = project_root / ".ai"
    ai_dir.mkdir(parents=True, exist_ok=True)
    target = ai_dir / "knowledge-graph.json"

    existing = _safe_json_load(target) if target.exists() else None
    if _is_canonical(existing):
        if verbose:
            print(f"[KG] OK: {target} (already canonical)")
        return target, "already_canonical"

    if target.exists():
        _backup_file(target, project_root)

    candidates: List[Tuple[str, Path]] = [
        ("graph_json", ai_dir / "knowledge_graph" / "graph.json"),
        ("knowledge_graph_json", ai_dir / "knowledge_graph" / "knowledge-graph.json"),
        ("backup_jsonl_1", ai_dir / "knowledge-graph.json.backup"),
        ("backup_jsonl_2", ai_dir / "knowledge-graph.backup.json"),
    ]

    chosen_label: str = "empty"
    out: Dict[str, Any] = {"entities": [], "relations": []}

    for label, p in candidates:
        if not p.exists():
            continue
        if label == "graph_json":
            obj = _from_graph_json(p)
        elif label == "knowledge_graph_json":
            obj = _from_simple_graph(p)
        else:
            obj = _from_jsonl_backup(p)
        if obj is None:
            continue
        out = obj
        chosen_label = label
        if _is_canonical(out):
            break

    canonical = {"entities": _normalize_entities(out.get("entities")), "relations": _normalize_relations(out.get("relations"))}

    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(canonical, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)

    if verbose:
        print(f"[KG] repaired: {target}")
        print(f"[KG] source: {chosen_label}")
        print(f"[KG] entities={len(canonical['entities'])} relations={len(canonical['relations'])}")

    return target, chosen_label


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    project_root = Path(args.project_root).expanduser().resolve() if args.project_root else Path.cwd().resolve()
    try:
        repair(project_root, verbose=(not args.quiet))
        return 0
    except Exception as e:
        if not args.quiet:
            print(f"[KG] repair failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
