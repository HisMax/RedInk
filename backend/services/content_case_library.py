"""
Local JSONL content case library for Xiaohongshu evaluations.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "xhs_content_case.v1"


def build_case_records(
    results: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    source: str,
    created_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convert evaluation results into review-ready content case records."""
    timestamp = created_at or _utc_now()
    records = []
    for result in results:
        case_id = result.get("case_id")
        records.append({
            "schema_version": SCHEMA_VERSION,
            "record_id": f"{run_id}:{case_id}",
            "run_id": run_id,
            "source": source,
            "created_at": timestamp,
            "case": {
                "case_id": case_id,
                "category": result.get("category"),
                "topic": result.get("topic"),
            },
            "content": {
                "titles": _as_list(result.get("titles")),
                "copywriting": result.get("copywriting") or "",
                "tags": _as_list(result.get("tags")),
            },
            "quality": {
                "trace_id": result.get("trace_id"),
                "overall": result.get("overall"),
                "decision": result.get("decision"),
                "issues_count": result.get("issues_count", 0),
                "suggestions_count": result.get("suggestions_count", 0),
                "baseline_passed": result.get("baseline_passed"),
                "baseline_reason": result.get("baseline_reason", ""),
                "trend_passed": result.get("trend_passed"),
                "trend_reason": result.get("trend_reason", ""),
                "error": result.get("error"),
            },
            "human_review": {
                "status": "unreviewed",
                "publishable": None,
                "viral_potential": None,
                "issue_types": [],
                "selected_title": None,
                "edited_copywriting": None,
                "notes": "",
            },
        })
    return records


def append_case_records(records: Iterable[Dict[str, Any]], path: str | Path) -> int:
    """Append content case records to a JSONL file and return the count written."""
    case_path = Path(path)
    case_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with case_path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_case_records(path: str | Path) -> List[Dict[str, Any]]:
    """Load local content case JSONL records."""
    case_path = Path(path)
    if not case_path.exists():
        return []
    with case_path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
