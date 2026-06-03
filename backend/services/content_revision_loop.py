"""
Revision loop helpers for Xiaohongshu content case records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


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
                "source_record_id": request.get("source_record_id"),
                "success": bool(result.get("success")),
                "trace_id": result.get("trace_id"),
                "revision": result.get("revision"),
                "error": result.get("error"),
            })
        except Exception as exc:
            results.append({
                "schema_version": RESULT_SCHEMA_VERSION,
                "request_id": request.get("request_id"),
                "source_record_id": request.get("source_record_id"),
                "success": False,
                "trace_id": revision_input.get("trace_id"),
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


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
