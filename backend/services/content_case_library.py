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


def save_case_records(records: Iterable[Dict[str, Any]], path: str | Path) -> int:
    """Rewrite a JSONL case library and return the count written."""
    case_path = Path(path)
    case_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with case_path.open("w", encoding="utf-8") as f:
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


def update_case_review(
    records: Iterable[Dict[str, Any]],
    record_id: str,
    *,
    status: Optional[str] = None,
    publishable: Optional[bool] = None,
    viral_potential: Optional[int] = None,
    issue_types: Optional[List[str]] = None,
    selected_title: Optional[str] = None,
    edited_copywriting: Optional[str] = None,
    notes: Optional[str] = None,
    reviewed_at: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Update a single case record's human review fields."""
    updated_records = []
    updated_record = None

    for record in records:
        row = dict(record)
        if row.get("record_id") == record_id:
            review = dict(row.get("human_review") or {})
            if status is not None:
                review["status"] = status
            if publishable is not None:
                review["publishable"] = publishable
            if viral_potential is not None:
                review["viral_potential"] = viral_potential
            if issue_types is not None:
                review["issue_types"] = issue_types
            if selected_title is not None:
                review["selected_title"] = selected_title
            if edited_copywriting is not None:
                review["edited_copywriting"] = edited_copywriting
            if notes is not None:
                review["notes"] = notes
            review["reviewed_at"] = reviewed_at or _utc_now()
            row["human_review"] = review
            updated_record = row
        updated_records.append(row)

    if updated_record is None:
        raise ValueError(f"content case record not found: {record_id}")

    return updated_records, updated_record


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
