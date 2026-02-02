#!/usr/bin/env python3
"""logutil.py - small structured logging helpers (JSONL).

Keep logging consistent across Python processes.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_jsonl(path: Path, event: str, **fields: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        rec: Dict[str, Any] = {"ts": utc_now_iso(), "event": event}
        rec.update(fields)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=True) + "\n")
    except Exception:
        pass
