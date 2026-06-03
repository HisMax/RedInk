"""
Revision loop helpers for Xiaohongshu content case records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.services.content_case_library import SCHEMA_VERSION


REQUEST_SCHEMA_VERSION = "xhs_revision_request.v1"
RESULT_SCHEMA_VERSION = "xhs_revision_result.v1"


def build_revision_requests(
    records: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    created_at: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Build revision requests from records that need another writing pass."""
    timestamp = created_at or _utc_now()
    requests = []
    for record in records:
        reasons = _trigger_reasons(record)
        content = record.get("content") or {}
        if not reasons or not content.get("copywriting"):
            continue

        case = record.get("case") or {}
        quality = record.get("quality") or {}
        review = record.get("human_review") or {}
        request = {
            "schema_version": REQUEST_SCHEMA_VERSION,
            "request_id": f"{run_id}:{record.get('record_id')}",
            "run_id": run_id,
            "source_record_id": record.get("record_id"),
            "created_at": timestamp,
            "trigger_reasons": reasons,
            "revision_input": {
                "topic": case.get("topic", ""),
                "outline": _build_outline(case, review),
                "titles": _as_list(content.get("titles")),
                "copywriting": content.get("copywriting", ""),
                "tags": _as_list(content.get("tags")),
                "quality_score": _build_quality_score(quality, review, reasons),
                "trace_id": quality.get("trace_id"),
            },
        }
        requests.append(request)
        if limit is not None and len(requests) >= limit:
            break

    return requests


def write_revision_requests(requests: Iterable[Dict[str, Any]], path: str | Path) -> int:
    """Write revision requests as JSONL."""
    request_path = Path(path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with request_path.open("w", encoding="utf-8") as f:
        for request in requests:
            f.write(json.dumps(request, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_revision_requests(path: str | Path) -> List[Dict[str, Any]]:
    """Load revision requests from JSONL."""
    request_path = Path(path)
    if not request_path.exists():
        return []
    with request_path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_revision_requests(
    requests: Iterable[Dict[str, Any]],
    *,
    revision_service: Any,
) -> List[Dict[str, Any]]:
    """Run revision requests with an injected RevisionService-like object."""
    results = []
    for request in requests:
        revision_input = request["revision_input"]
        try:
            result = revision_service.suggest_revisions(
                topic=revision_input["topic"],
                outline=revision_input["outline"],
                titles=revision_input["titles"],
                copywriting=revision_input["copywriting"],
                tags=revision_input["tags"],
                quality_score=revision_input["quality_score"],
                trace_id=revision_input.get("trace_id"),
            )
            results.append({
                "schema_version": RESULT_SCHEMA_VERSION,
                "request_id": request.get("request_id"),
                "run_id": request.get("run_id"),
                "source_record_id": request.get("source_record_id"),
                "success": bool(result.get("success")),
                "trace_id": result.get("trace_id"),
                "revised_at": result.get("revised_at"),
                "revision": result.get("revision"),
                "error": result.get("error"),
            })
        except Exception as exc:
            results.append({
                "schema_version": RESULT_SCHEMA_VERSION,
                "request_id": request.get("request_id"),
                "run_id": request.get("run_id"),
                "source_record_id": request.get("source_record_id"),
                "success": False,
                "trace_id": revision_input.get("trace_id"),
                "revised_at": None,
                "revision": None,
                "error": str(exc),
            })
    return results


def write_revision_results(results: Iterable[Dict[str, Any]], path: str | Path) -> int:
    """Write revision results as JSONL."""
    result_path = Path(path)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with result_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
            count += 1
    return count


def load_revision_results(path: str | Path) -> List[Dict[str, Any]]:
    """Load revision results from JSONL."""
    result_path = Path(path)
    if not result_path.exists():
        return []
    with result_path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_revised_case_records(
    records: Iterable[Dict[str, Any]],
    revision_results: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    created_at: Optional[str] = None,
    source: str = "xhs_revision_loop",
) -> List[Dict[str, Any]]:
    """Convert successful revision results into derived content case records."""
    timestamp = created_at or _utc_now()
    source_by_id = {record.get("record_id"): record for record in records}
    revised_records = []
    for result in revision_results:
        if result.get("success") is not True:
            continue

        source_record_id = result.get("source_record_id")
        source_record = source_by_id.get(source_record_id)
        revision = result.get("revision") or {}
        copywriting = revision.get("copywriting") or ""
        if not source_record or not copywriting:
            continue

        request_id = result.get("request_id") or f"{run_id}:{source_record_id}"
        source_quality = source_record.get("quality") or {}
        revision_summary = _as_list(revision.get("revision_summary"))
        revised_records.append({
            "schema_version": SCHEMA_VERSION,
            "record_id": f"{request_id}:revised",
            "run_id": run_id,
            "source": source,
            "created_at": timestamp,
            "case": dict(source_record.get("case") or {}),
            "content": {
                "titles": _as_list(revision.get("titles")),
                "copywriting": copywriting,
                "tags": _as_list(revision.get("tags")),
            },
            "quality": {
                "trace_id": result.get("trace_id"),
                "overall": None,
                "decision": "pending_re_evaluation",
                "issues_count": 0,
                "suggestions_count": len(revision_summary),
                "baseline_passed": None,
                "baseline_reason": "",
                "trend_passed": None,
                "trend_reason": "",
                "error": result.get("error"),
            },
            "human_review": _default_human_review(),
            "revision_meta": {
                "source_record_id": source_record_id,
                "request_id": request_id,
                "source_quality_trace_id": source_quality.get("trace_id"),
                "revision_trace_id": result.get("trace_id"),
                "revised_at": result.get("revised_at") or timestamp,
                "revision_summary": revision_summary,
            },
        })
    return revised_records


def apply_revision_results_to_case_library(
    records: Iterable[Dict[str, Any]],
    revision_results: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    created_at: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Upsert derived revision case records into an existing case library."""
    existing_records = list(records)
    revised_records = build_revised_case_records(
        existing_records,
        revision_results,
        run_id=run_id,
        created_at=created_at,
    )
    return _upsert_case_records(existing_records, revised_records), revised_records


def _trigger_reasons(record: Dict[str, Any]) -> List[str]:
    quality = record.get("quality") or {}
    review = record.get("human_review") or {}
    reasons = []
    if quality.get("baseline_passed") is False:
        reasons.append("baseline_failed")
    if quality.get("trend_passed") is False:
        reasons.append("trend_failed")
    if quality.get("decision") == "revise":
        reasons.append("quality_decision_revise")
    if review.get("status") == "needs_revision":
        reasons.append("human_needs_revision")
    if review.get("publishable") is False:
        reasons.append("human_rejected")
    return reasons


def _build_outline(case: Dict[str, Any], review: Dict[str, Any]) -> str:
    lines = [
        f"类别：{case.get('category', '')}",
        f"主题：{case.get('topic', '')}",
    ]
    notes = review.get("notes")
    if notes:
        lines.append(f"人工复盘备注：{notes}")
    return "\n".join(lines)


def _build_quality_score(
    quality: Dict[str, Any],
    review: Dict[str, Any],
    reasons: List[str],
) -> Dict[str, Any]:
    issues = list(reasons)
    baseline_reason = quality.get("baseline_reason")
    trend_reason = quality.get("trend_reason")
    if baseline_reason:
        issues.append(baseline_reason)
    if trend_reason:
        issues.append(trend_reason)
    issues.extend(_as_list(review.get("issue_types")))

    suggestions = ["根据质量门禁和人工复盘进行二次改稿"]
    notes = review.get("notes")
    if notes:
        suggestions.append(notes)

    return {
        "overall": quality.get("overall"),
        "decision": quality.get("decision"),
        "issues": issues,
        "suggestions": suggestions,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_human_review() -> Dict[str, Any]:
    return {
        "status": "unreviewed",
        "publishable": None,
        "viral_potential": None,
        "issue_types": [],
        "selected_title": None,
        "edited_copywriting": None,
        "notes": "",
    }


def _upsert_case_records(
    records: List[Dict[str, Any]],
    new_records: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    merged = list(records)
    index_by_record_id = {
        record.get("record_id"): index
        for index, record in enumerate(merged)
        if record.get("record_id")
    }
    for record in new_records:
        record_id = record.get("record_id")
        if record_id in index_by_record_id:
            merged[index_by_record_id[record_id]] = record
            continue
        index_by_record_id[record_id] = len(merged)
        merged.append(record)
    return merged


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
