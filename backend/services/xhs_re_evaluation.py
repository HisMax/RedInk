"""
Re-evaluate revised Xiaohongshu content case records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


RESULT_SCHEMA_VERSION = "xhs_re_evaluation_result.v1"
DEFAULT_MIN_IMPROVEMENT = 0


def run_re_evaluation(
    records: Iterable[Dict[str, Any]],
    *,
    live: bool = False,
    quality_service: Optional[Any] = None,
    run_id: str = "xhs_re_evaluation",
    evaluated_at: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Evaluate revised records and compare them with their source case scores."""
    rows = list(records)
    source_by_id = {row.get("record_id"): row for row in rows}
    candidates = select_re_evaluation_records(rows, limit=limit)
    timestamp = evaluated_at or _utc_now()

    if live and quality_service is None:
        from backend.services.quality import QualityService

        quality_service = QualityService()

    results = []
    for record in candidates:
        source_record = source_by_id.get((record.get("revision_meta") or {}).get("source_record_id"))
        case = record.get("case") or {}
        content = record.get("content") or {}
        outline = _build_re_evaluation_outline(record, source_record)
        try:
            if live:
                quality = quality_service.evaluate_content(
                    topic=case.get("topic", ""),
                    outline=outline,
                    titles=_as_list(content.get("titles")),
                    copywriting=content.get("copywriting", ""),
                    tags=_as_list(content.get("tags")),
                )
            else:
                quality = _dry_run_quality(record, source_record)

            if not quality.get("success"):
                results.append(_error_result(record, source_record, run_id, timestamp, quality.get("error", "质量评分失败")))
                continue
            results.append(_success_result(record, source_record, quality, run_id, timestamp))
        except Exception as exc:
            results.append(_error_result(record, source_record, run_id, timestamp, str(exc)))

    return results


def select_re_evaluation_records(
    records: Iterable[Dict[str, Any]],
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Select revised records waiting for another quality pass."""
    candidates = []
    for record in records:
        if not _is_pending_re_evaluation(record):
            continue
        candidates.append(record)
        if limit is not None and len(candidates) >= limit:
            break
    return candidates


def apply_improvement_gate(
    results: Iterable[Dict[str, Any]],
    *,
    min_improvement: int = DEFAULT_MIN_IMPROVEMENT,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Annotate re-evaluation results with an improvement gate."""
    annotated = []
    failures = []
    improved_count = 0
    for result in results:
        row = dict(result)
        reason = _improvement_failure_reason(row, min_improvement)
        row["improvement_passed"] = not reason
        row["improvement_reason"] = reason
        if reason:
            failures.append({
                "record_id": row.get("record_id"),
                "source_record_id": row.get("source_record_id"),
                "previous_overall": row.get("previous_overall"),
                "overall": row.get("overall"),
                "score_delta": row.get("score_delta"),
                "reason": reason,
            })
        else:
            improved_count += 1
        annotated.append(row)

    return annotated, {
        "passed": not failures,
        "checked_count": len(annotated),
        "improved_count": improved_count,
        "failed_count": len(failures),
        "min_improvement": min_improvement,
        "failures": failures,
    }


def apply_re_evaluation_results_to_case_library(
    records: Iterable[Dict[str, Any]],
    results: Iterable[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], int]:
    """Update revised case records with their re-evaluation quality scores."""
    updated_records = [dict(record) for record in records]
    index_by_record_id = {
        record.get("record_id"): index
        for index, record in enumerate(updated_records)
        if record.get("record_id")
    }
    updated_count = 0
    for result in results:
        record_id = result.get("record_id")
        index = index_by_record_id.get(record_id)
        if index is None:
            continue

        row = dict(updated_records[index])
        quality = dict(row.get("quality") or {})
        quality.update({
            "trace_id": result.get("trace_id"),
            "overall": result.get("overall"),
            "decision": result.get("decision"),
            "issues_count": result.get("issues_count", 0),
            "suggestions_count": result.get("suggestions_count", 0),
            "publish_gate_enabled": result.get("publish_gate_enabled"),
            "baseline_passed": result.get("improvement_passed"),
            "baseline_reason": result.get("improvement_reason", ""),
            "trend_passed": result.get("improvement_passed"),
            "trend_reason": result.get("improvement_reason", ""),
            "error": result.get("error"),
        })
        quality["improvement_passed"] = result.get("improvement_passed")
        quality["improvement_reason"] = result.get("improvement_reason", "")
        quality["previous_overall"] = result.get("previous_overall")
        quality["score_delta"] = result.get("score_delta")
        row["quality"] = quality

        revision_meta = dict(row.get("revision_meta") or {})
        revision_meta["re_evaluation"] = {
            "run_id": result.get("run_id"),
            "trace_id": result.get("trace_id"),
            "evaluated_at": result.get("evaluated_at"),
            "previous_overall": result.get("previous_overall"),
            "overall": result.get("overall"),
            "score_delta": result.get("score_delta"),
            "improvement_passed": result.get("improvement_passed"),
            "improvement_reason": result.get("improvement_reason", ""),
        }
        row["revision_meta"] = revision_meta

        updated_records[index] = row
        updated_count += 1

    return updated_records, updated_count


def write_re_evaluation_jsonl(results: Iterable[Dict[str, Any]], path: str | Path) -> None:
    """Write re-evaluation results as JSONL."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")


def write_re_evaluation_markdown(results: Iterable[Dict[str, Any]], path: str | Path) -> None:
    """Write a compact Markdown report for re-evaluation results."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Xiaohongshu Revision Re-evaluation",
        "",
        "| Record | Source | Decision | Prev | Current | Delta | Improvement | Trace | Error |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for result in results:
        error = (result.get("error") or result.get("improvement_reason") or "").replace("|", "\\|")
        lines.append(
            "| {record_id} | {source_record_id} | {decision} | {previous_overall} | {overall} | "
            "{score_delta} | {improvement} | {trace_id} | {error} |".format(
                record_id=result.get("record_id", ""),
                source_record_id=result.get("source_record_id", ""),
                decision=result.get("decision", ""),
                previous_overall=_format_optional_number(result.get("previous_overall")),
                overall=_format_optional_number(result.get("overall")),
                score_delta=_format_delta(result.get("score_delta")),
                improvement=_format_gate(result.get("improvement_passed")),
                trace_id=result.get("trace_id", ""),
                error=error,
            )
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _is_pending_re_evaluation(record: Dict[str, Any]) -> bool:
    quality = record.get("quality") or {}
    revision_meta = record.get("revision_meta") or {}
    content = record.get("content") or {}
    return (
        quality.get("decision") == "pending_re_evaluation"
        and bool(revision_meta.get("source_record_id"))
        and bool(content.get("copywriting"))
    )


def _build_re_evaluation_outline(
    record: Dict[str, Any],
    source_record: Optional[Dict[str, Any]],
) -> str:
    case = record.get("case") or {}
    revision_meta = record.get("revision_meta") or {}
    source_quality = (source_record or {}).get("quality") or {}
    lines = [
        f"类别：{case.get('category', '')}",
        f"主题：{case.get('topic', '')}",
        f"源记录：{revision_meta.get('source_record_id', '')}",
        f"源评分：{_format_optional_number(source_quality.get('overall'))}",
    ]
    summary = _as_list(revision_meta.get("revision_summary"))
    if summary:
        lines.append("改稿摘要：")
        lines.extend(f"- {item}" for item in summary)
    return "\n".join(lines)


def _dry_run_quality(record: Dict[str, Any], source_record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    source_quality = (source_record or {}).get("quality") or {}
    source_overall = source_quality.get("overall")
    if not isinstance(source_overall, (int, float)):
        source_overall = 80

    revision_meta = record.get("revision_meta") or {}
    summary_bonus = 4 + min(4, len(_as_list(revision_meta.get("revision_summary"))))
    overall = min(95, source_overall + summary_bonus)
    decision = "approve" if overall >= 80 else "revise"
    return {
        "success": True,
        "trace_id": f"xhs_reeval_{_safe_id(record.get('record_id', 'case'))}",
        "quality_score": {
            "overall": overall,
            "decision": decision,
            "issues": [] if decision == "approve" else ["改稿后仍需补充信息密度"],
            "suggestions": ["保留改稿后的清晰表达", "继续补充可执行细节"],
        },
        "publish_gate": {"enabled": False},
    }


def _success_result(
    record: Dict[str, Any],
    source_record: Optional[Dict[str, Any]],
    quality: Dict[str, Any],
    run_id: str,
    evaluated_at: str,
) -> Dict[str, Any]:
    case = record.get("case") or {}
    content = record.get("content") or {}
    revision_meta = record.get("revision_meta") or {}
    quality_score = quality.get("quality_score") or {}
    publish_gate = quality.get("publish_gate") or {}
    issues = _as_list(quality_score.get("issues"))
    suggestions = _as_list(quality_score.get("suggestions"))
    previous_overall = ((source_record or {}).get("quality") or {}).get("overall")
    current_overall = quality_score.get("overall")
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "record_id": record.get("record_id"),
        "source_record_id": revision_meta.get("source_record_id"),
        "run_id": run_id,
        "evaluated_at": evaluated_at,
        "case_id": case.get("case_id"),
        "category": case.get("category"),
        "topic": case.get("topic"),
        "trace_id": quality.get("trace_id"),
        "titles": _as_list(content.get("titles")),
        "copywriting": content.get("copywriting", ""),
        "tags": _as_list(content.get("tags")),
        "title_count": len(_as_list(content.get("titles"))),
        "copywriting_length": len(content.get("copywriting", "")),
        "tag_count": len(_as_list(content.get("tags"))),
        "overall": current_overall,
        "decision": quality_score.get("decision"),
        "issues_count": len(issues),
        "suggestions_count": len(suggestions),
        "publish_gate_enabled": publish_gate.get("enabled"),
        "error": None,
        "previous_overall": previous_overall,
        "score_delta": _score_delta(current_overall, previous_overall),
    }


def _error_result(
    record: Dict[str, Any],
    source_record: Optional[Dict[str, Any]],
    run_id: str,
    evaluated_at: str,
    error: str,
) -> Dict[str, Any]:
    case = record.get("case") or {}
    revision_meta = record.get("revision_meta") or {}
    previous_overall = ((source_record or {}).get("quality") or {}).get("overall")
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "record_id": record.get("record_id"),
        "source_record_id": revision_meta.get("source_record_id"),
        "run_id": run_id,
        "evaluated_at": evaluated_at,
        "case_id": case.get("case_id"),
        "category": case.get("category"),
        "topic": case.get("topic"),
        "trace_id": None,
        "titles": [],
        "copywriting": "",
        "tags": [],
        "title_count": 0,
        "copywriting_length": 0,
        "tag_count": 0,
        "overall": None,
        "decision": "error",
        "issues_count": 0,
        "suggestions_count": 0,
        "publish_gate_enabled": False,
        "error": error,
        "previous_overall": previous_overall,
        "score_delta": None,
    }


def _improvement_failure_reason(result: Dict[str, Any], min_improvement: int) -> str:
    if result.get("error"):
        return f"re-evaluation error: {result['error']}"
    delta = result.get("score_delta")
    if not isinstance(delta, (int, float)):
        return "score delta missing"
    if delta < min_improvement:
        return f"score delta {_format_number(delta)} below {_format_number(min_improvement)}"
    return ""


def _score_delta(current: Any, previous: Any) -> Optional[int | float]:
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)):
        return None
    return current - previous


def _format_gate(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return "n/a"


def _format_optional_number(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    return _format_number(value)


def _format_delta(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return ""
    formatted = _format_number(value)
    if value > 0:
        return f"+{formatted}"
    return formatted


def _format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _safe_id(value: Any) -> str:
    return "".join(ch if str(ch).isalnum() else "_" for ch in str(value))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
