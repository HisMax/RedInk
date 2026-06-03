"""
Local JSONL content case library for Xiaohongshu evaluations.
"""

from __future__ import annotations

import json
from collections import Counter
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


def load_prompt_examples(path: str | Path, *, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load prompt examples from JSONL."""
    examples_path = Path(path)
    if not examples_path.exists():
        return []
    examples = []
    with examples_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            examples.append(json.loads(line))
            if limit is not None and len(examples) >= limit:
                break
    return examples


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


def summarize_case_records(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize review outcomes and content quality for a case library."""
    rows = list(records)
    reviewed = [
        row for row in rows
        if (row.get("human_review") or {}).get("status") not in (None, "", "unreviewed")
    ]
    publishable = [
        row for row in rows
        if (row.get("human_review") or {}).get("publishable") is True
    ]
    needs_revision = [
        row for row in rows
        if _needs_revision(row)
    ]

    issue_counts = Counter()
    for row in rows:
        issue_counts.update(_as_list((row.get("human_review") or {}).get("issue_types")))

    quality_scores = [
        (row.get("quality") or {}).get("overall")
        for row in rows
        if isinstance((row.get("quality") or {}).get("overall"), (int, float))
    ]
    viral_scores = [
        (row.get("human_review") or {}).get("viral_potential")
        for row in rows
        if isinstance((row.get("human_review") or {}).get("viral_potential"), (int, float))
    ]

    return {
        "total_count": len(rows),
        "reviewed_count": len(reviewed),
        "publishable_count": len(publishable),
        "needs_revision_count": len(needs_revision),
        "average_quality_overall": _average(quality_scores),
        "average_viral_potential": _average(viral_scores),
        "issue_type_counts": dict(sorted(issue_counts.items())),
        "top_cases": _top_cases(rows),
    }


def select_prompt_examples(
    records: Iterable[Dict[str, Any]],
    *,
    min_viral_potential: int = 4,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Select publishable, high-potential cases as prompt examples."""
    candidates = []
    for row in records:
        review = row.get("human_review") or {}
        if review.get("publishable") is not True:
            continue
        viral_potential = review.get("viral_potential")
        if not isinstance(viral_potential, (int, float)) or viral_potential < min_viral_potential:
            continue
        content = row.get("content") or {}
        case = row.get("case") or {}
        candidates.append({
            "record_id": row.get("record_id"),
            "category": case.get("category"),
            "topic": case.get("topic"),
            "title": review.get("selected_title") or _first(content.get("titles")),
            "copywriting": review.get("edited_copywriting") or content.get("copywriting", ""),
            "tags": _as_list(content.get("tags")),
            "quality_overall": (row.get("quality") or {}).get("overall"),
            "viral_potential": viral_potential,
            "notes": review.get("notes", ""),
        })

    candidates.sort(
        key=lambda item: (
            item.get("viral_potential") or 0,
            item.get("quality_overall") or 0,
            item.get("record_id") or "",
        ),
        reverse=True,
    )
    return candidates[:limit]


def select_re_evaluated_prompt_examples(
    records: Iterable[Dict[str, Any]],
    *,
    min_overall: int = 85,
    min_score_delta: int = 3,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Select improved revised cases as automatic prompt examples."""
    candidates = []
    for row in records:
        revision_meta = row.get("revision_meta") or {}
        re_evaluation = revision_meta.get("re_evaluation") or {}
        quality = row.get("quality") or {}
        content = row.get("content") or {}
        if not revision_meta.get("source_record_id"):
            continue
        if quality.get("decision") != "approve":
            continue
        if _coalesce_bool(quality.get("improvement_passed"), re_evaluation.get("improvement_passed")) is not True:
            continue

        overall = _coalesce_number(quality.get("overall"), re_evaluation.get("overall"))
        score_delta = _coalesce_number(quality.get("score_delta"), re_evaluation.get("score_delta"))
        previous_overall = _coalesce_number(quality.get("previous_overall"), re_evaluation.get("previous_overall"))
        if not isinstance(overall, (int, float)) or overall < min_overall:
            continue
        if not isinstance(score_delta, (int, float)) or score_delta < min_score_delta:
            continue
        if not content.get("copywriting"):
            continue

        case = row.get("case") or {}
        candidates.append({
            "record_id": row.get("record_id"),
            "source_record_id": revision_meta.get("source_record_id"),
            "category": case.get("category"),
            "topic": case.get("topic"),
            "title": _first(content.get("titles")),
            "copywriting": content.get("copywriting", ""),
            "tags": _as_list(content.get("tags")),
            "quality_overall": overall,
            "previous_overall": previous_overall,
            "score_delta": score_delta,
            "example_source": "re_evaluation",
            "revision_summary": _as_list(revision_meta.get("revision_summary")),
            "notes": "auto-selected from revision re-evaluation",
        })

    candidates.sort(
        key=lambda item: (
            item.get("score_delta") or 0,
            item.get("quality_overall") or 0,
            item.get("record_id") or "",
        ),
        reverse=True,
    )
    return candidates[:limit]


def write_case_library_report(summary: Dict[str, Any], path: str | Path) -> None:
    """Write a compact Markdown report for a case library summary."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Content Case Library Report",
        "",
        f"- Total cases: {summary['total_count']}",
        f"- Reviewed cases: {summary['reviewed_count']}",
        f"- Publishable cases: {summary['publishable_count']}",
        f"- Needs revision: {summary['needs_revision_count']}",
        f"- Average quality: {summary['average_quality_overall']}",
        f"- Average viral potential: {summary['average_viral_potential']}",
        "",
        "## Issue Types",
        "",
    ]
    issue_counts = summary.get("issue_type_counts") or {}
    if issue_counts:
        for issue_type, count in issue_counts.items():
            lines.append(f"- {issue_type}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "## Top Cases", ""])
    top_cases = summary.get("top_cases") or []
    if top_cases:
        for case in top_cases:
            lines.append(
                f"- {case['record_id']}: viral={case['viral_potential']}, "
                f"quality={case['quality_overall']}, topic={case['topic']}"
            )
    else:
        lines.append("- None")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_prompt_examples(examples: Iterable[Dict[str, Any]], path: str | Path) -> int:
    """Write prompt examples as JSONL."""
    examples_path = Path(path)
    examples_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with examples_path.open("w", encoding="utf-8") as f:
        for example in examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
            count += 1
    return count


def _needs_revision(record: Dict[str, Any]) -> bool:
    review = record.get("human_review") or {}
    quality = record.get("quality") or {}
    return (
        review.get("status") == "needs_revision"
        or review.get("publishable") is False
        or quality.get("baseline_passed") is False
    )


def _top_cases(records: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    rows = []
    for row in records:
        review = row.get("human_review") or {}
        if review.get("publishable") is not True:
            continue
        case = row.get("case") or {}
        rows.append({
            "record_id": row.get("record_id"),
            "topic": case.get("topic"),
            "category": case.get("category"),
            "quality_overall": (row.get("quality") or {}).get("overall"),
            "viral_potential": review.get("viral_potential"),
        })
    rows.sort(
        key=lambda item: (
            item.get("viral_potential") or 0,
            item.get("quality_overall") or 0,
            item.get("record_id") or "",
        ),
        reverse=True,
    )
    return rows[:limit]


def _average(values: List[int | float]) -> float | int | None:
    if not values:
        return None
    result = sum(values) / len(values)
    if result.is_integer():
        return int(result)
    return round(result, 2)


def _first(value: Any) -> Any:
    values = _as_list(value)
    return values[0] if values else None


def _coalesce_number(*values: Any) -> int | float | None:
    for value in values:
        if isinstance(value, (int, float)):
            return value
    return None


def _coalesce_bool(*values: Any) -> bool | None:
    for value in values:
        if isinstance(value, bool):
            return value
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
