"""
Batch evaluation runner for Xiaohongshu quality seed cases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_CASES_PATH = Path("tests/fixtures/xhs_quality_cases.json")
DEFAULT_MIN_OVERALL = 80
DEFAULT_ALLOWED_DECISIONS = ("approve",)
DEFAULT_MAX_SCORE_DROP = 3
CASE_SET_SCHEMA_VERSION = "xhs_quality_case_set.v1"
VERSIONED_CASES_SCHEMA_VERSION = "xhs_quality_cases_version.v1"


def load_quality_cases(path: str | Path = DEFAULT_CASES_PATH) -> List[Dict[str, Any]]:
    """Load and validate Xiaohongshu quality seed cases."""
    return load_quality_case_set(path)["cases"]


def load_quality_case_set(path: str | Path = DEFAULT_CASES_PATH) -> Dict[str, Any]:
    """Load legacy or versioned Xiaohongshu quality case sets."""
    case_path = Path(path)
    with case_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        case_set = {
            "schema_version": CASE_SET_SCHEMA_VERSION,
            "path": str(case_path),
            "format": "legacy",
            "source_schema_version": None,
            "version_id": None,
            "created_at": None,
            "metadata": {},
            "cases": payload,
        }
    elif isinstance(payload, dict):
        source_schema_version = payload.get("schema_version")
        if source_schema_version != VERSIONED_CASES_SCHEMA_VERSION:
            raise ValueError(
                "versioned quality case set schema_version must be "
                f"{VERSIONED_CASES_SCHEMA_VERSION}"
            )
        case_set = {
            "schema_version": CASE_SET_SCHEMA_VERSION,
            "path": str(case_path),
            "format": "versioned",
            "source_schema_version": source_schema_version,
            "version_id": payload.get("version_id"),
            "created_at": payload.get("created_at"),
            "metadata": payload.get("metadata") or {},
            "cases": payload.get("cases"),
        }
    else:
        raise ValueError("quality cases fixture must be a JSON array or versioned object")

    _validate_quality_cases(case_set["cases"])
    case_set["case_count"] = len(case_set["cases"])
    return case_set


def case_set_metadata(case_set: Dict[str, Any]) -> Dict[str, Any]:
    """Return case set metadata without embedding case rows."""
    return {key: value for key, value in case_set.items() if key != "cases"}


def _validate_quality_cases(cases: Any) -> None:
    if not isinstance(cases, list):
        raise ValueError("quality cases fixture must be a JSON array")

    required_fields = {"id", "category", "topic", "expected_traits"}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"quality case at index {index} must be an object")
        missing = sorted(required_fields - set(case))
        if missing:
            raise ValueError(f"quality case {case.get('id', index)} missing fields: {', '.join(missing)}")
        if not isinstance(case["expected_traits"], list):
            raise ValueError(f"quality case {case['id']} expected_traits must be a list")


def load_previous_eval_results(path: str | Path) -> List[Dict[str, Any]]:
    """Load previous evaluation results from JSONL, result array, or CLI JSON payload."""
    report_path = Path(path)
    if report_path.suffix == ".jsonl":
        with report_path.open("r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    else:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows = payload.get("results")
        else:
            rows = payload

    if not isinstance(rows, list):
        raise ValueError("previous evaluation report must contain a results array")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"previous evaluation row at index {index} must be an object")
    return rows


def build_case_outline(case: Dict[str, Any]) -> str:
    """Build a lightweight outline from fixture metadata."""
    traits = "\n".join(f"- {trait}" for trait in case.get("expected_traits", []))
    return f"类别：{case['category']}\n主题：{case['topic']}\n预期特征：\n{traits}"


def run_quality_eval(
    cases: Iterable[Dict[str, Any]],
    *,
    live: bool = False,
    content_service: Optional[Any] = None,
    quality_service: Optional[Any] = None,
    prompt_examples: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Run dry-run or live quality evaluation for a sequence of cases."""
    if live:
        if content_service is None:
            from backend.services.content import ContentService

            content_service = ContentService()
        if quality_service is None:
            from backend.services.quality import QualityService

            quality_service = QualityService()

    results = []
    for case in cases:
        outline = build_case_outline(case)
        try:
            if live:
                if prompt_examples:
                    content = content_service.generate_content(
                        case["topic"],
                        outline,
                        prompt_examples=prompt_examples,
                    )
                else:
                    content = content_service.generate_content(case["topic"], outline)
                if not content.get("success"):
                    results.append(_error_result(case, content.get("error", "内容生成失败")))
                    continue

                quality = quality_service.evaluate_content(
                    topic=case["topic"],
                    outline=outline,
                    titles=_as_list(content.get("titles", [])),
                    copywriting=content.get("copywriting", ""),
                    tags=_as_list(content.get("tags", [])),
                )
                if not quality.get("success"):
                    results.append(_error_result(case, quality.get("error", "质量评分失败")))
                    continue
            else:
                content = _dry_run_content(case)
                quality = _dry_run_quality(case)

            results.append(_success_result(case, content, quality))
        except Exception as exc:
            results.append(_error_result(case, str(exc)))

    return results


def apply_quality_baseline(
    results: Iterable[Dict[str, Any]],
    *,
    min_overall: int = DEFAULT_MIN_OVERALL,
    allowed_decisions: Optional[Iterable[str]] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Annotate evaluation results with baseline gate status."""
    allowed = list(allowed_decisions or DEFAULT_ALLOWED_DECISIONS)
    annotated = []
    failures = []

    for result in results:
        row = dict(result)
        reason = _baseline_failure_reason(row, min_overall, allowed)
        row["baseline_passed"] = not reason
        row["baseline_reason"] = reason
        annotated.append(row)

        if reason:
            failures.append({
                "case_id": row.get("case_id"),
                "topic": row.get("topic"),
                "overall": row.get("overall"),
                "decision": row.get("decision"),
                "reason": reason,
            })

    return annotated, {
        "passed": not failures,
        "checked_count": len(annotated),
        "passed_count": len(annotated) - len(failures),
        "failed_count": len(failures),
        "min_overall": min_overall,
        "allowed_decisions": allowed,
        "failures": failures,
    }


def compare_quality_trend(
    results: Iterable[Dict[str, Any]],
    previous_results: Iterable[Dict[str, Any]],
    *,
    max_score_drop: int = DEFAULT_MAX_SCORE_DROP,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Annotate results with score deltas against a previous evaluation report."""
    previous_by_case = {
        row["case_id"]: row
        for row in previous_results
        if row.get("case_id")
    }
    annotated = []
    failures = []
    compared_count = 0
    skipped_count = 0

    for result in results:
        row = dict(result)
        previous = previous_by_case.get(row.get("case_id"))
        previous_overall = previous.get("overall") if previous else None
        current_overall = row.get("overall")

        row["previous_overall"] = previous_overall
        row["score_delta"] = None
        row["trend_passed"] = True
        row["trend_reason"] = ""

        if not isinstance(previous_overall, (int, float)) or not isinstance(current_overall, (int, float)):
            skipped_count += 1
            annotated.append(row)
            continue

        compared_count += 1
        delta = current_overall - previous_overall
        row["score_delta"] = delta
        if delta < -max_score_drop:
            reason = (
                f"score dropped {_format_number(abs(delta))} points "
                f"(from {_format_number(previous_overall)} to {_format_number(current_overall)})"
            )
            row["trend_passed"] = False
            row["trend_reason"] = reason
            failures.append({
                "case_id": row.get("case_id"),
                "topic": row.get("topic"),
                "previous_overall": previous_overall,
                "overall": current_overall,
                "score_delta": delta,
                "reason": reason,
            })

        annotated.append(row)

    return annotated, {
        "passed": not failures,
        "previous_count": len(previous_by_case),
        "checked_count": len(annotated),
        "compared_count": compared_count,
        "skipped_count": skipped_count,
        "failed_count": len(failures),
        "max_score_drop": max_score_drop,
        "failures": failures,
    }


def write_jsonl_report(results: Iterable[Dict[str, Any]], path: str | Path) -> None:
    """Write one evaluation result per line as JSONL."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")


def write_markdown_report(results: Iterable[Dict[str, Any]], path: str | Path) -> None:
    """Write a compact Markdown table for human review."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Xiaohongshu Quality Evaluation",
        "",
        "| Case | Category | Decision | Overall | Prev | Delta | Trace | Titles | Copy Len | Tags | Issues | Suggestions | Baseline | Trend | Error |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for result in results:
        error = (result.get("error") or "").replace("|", "\\|")
        baseline = _format_baseline_status(result)
        baseline_reason = (result.get("baseline_reason") or "").replace("|", "\\|")
        trend = _format_trend_status(result)
        trend_reason = (result.get("trend_reason") or "").replace("|", "\\|")
        row = {
            **result,
            "previous_overall": _format_optional_number(result.get("previous_overall")),
            "score_delta": _format_delta(result.get("score_delta")),
            "baseline": baseline,
            "trend": trend,
            "error": error or baseline_reason or trend_reason,
        }
        lines.append(
            "| {case_id} | {category} | {decision} | {overall} | {previous_overall} | {score_delta} | "
            "{trace_id} | {title_count} | {copywriting_length} | {tag_count} | {issues_count} | "
            "{suggestions_count} | {baseline} | {trend} | {error} |".format(**row)
        )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _dry_run_content(case: Dict[str, Any]) -> Dict[str, Any]:
    topic = case["topic"]
    traits = case.get("expected_traits", [])
    trait_sentence = "；".join(traits) if traits else "结构清晰"
    return {
        "success": True,
        "titles": [
            f"{topic}｜新手照做版",
            f"{topic}，这篇讲清楚",
            f"收藏：{topic}完整流程",
        ],
        "copywriting": f"{topic} 的核心是把步骤讲清楚，并给用户一个可执行的行动路径。重点包括：{trait_sentence}。",
        "tags": [case["category"], "小红书内容", "质量评测", "可执行"],
    }


def _dry_run_quality(case: Dict[str, Any]) -> Dict[str, Any]:
    trait_count = len(case.get("expected_traits", []))
    overall = min(92, 72 + trait_count * 4)
    decision = "approve" if overall >= 80 else "revise"
    return {
        "success": True,
        "trace_id": f"xhs_eval_{case['id']}",
        "quality_score": {
            "overall": overall,
            "decision": decision,
            "issues": [] if decision == "approve" else ["预期特征不足"],
            "suggestions": ["保持步骤具体", "补充收藏理由"],
        },
        "publish_gate": {"enabled": False},
    }


def _success_result(case: Dict[str, Any], content: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    titles = _as_list(content.get("titles", []))
    tags = _as_list(content.get("tags", []))
    quality_score = quality.get("quality_score") or {}
    publish_gate = quality.get("publish_gate") or {}
    issues = _as_list(quality_score.get("issues", []))
    suggestions = _as_list(quality_score.get("suggestions", []))
    return {
        "case_id": case["id"],
        "category": case["category"],
        "topic": case["topic"],
        "trace_id": quality.get("trace_id"),
        "titles": titles,
        "copywriting": content.get("copywriting", ""),
        "tags": tags,
        "title_count": len(titles),
        "copywriting_length": len(content.get("copywriting", "")),
        "tag_count": len(tags),
        "overall": quality_score.get("overall"),
        "decision": quality_score.get("decision"),
        "issues_count": len(issues),
        "suggestions_count": len(suggestions),
        "publish_gate_enabled": publish_gate.get("enabled"),
        "error": None,
    }


def _error_result(case: Dict[str, Any], error: str) -> Dict[str, Any]:
    return {
        "case_id": case.get("id"),
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
    }


def _baseline_failure_reason(result: Dict[str, Any], min_overall: int, allowed_decisions: List[str]) -> str:
    if result.get("error"):
        return f"evaluation error: {result['error']}"

    overall = result.get("overall")
    if not isinstance(overall, (int, float)):
        return "overall missing"
    if overall < min_overall:
        return f"overall {_format_number(overall)} below {_format_number(min_overall)}"

    decision = result.get("decision")
    if decision not in allowed_decisions:
        return f"decision {decision} not allowed"

    return ""


def _format_baseline_status(result: Dict[str, Any]) -> str:
    if "baseline_passed" not in result:
        return "n/a"
    return "pass" if result["baseline_passed"] else "fail"


def _format_trend_status(result: Dict[str, Any]) -> str:
    if "trend_passed" not in result:
        return "n/a"
    return "pass" if result["trend_passed"] else "fail"


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


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
