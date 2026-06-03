"""
Batch evaluation runner for Xiaohongshu quality seed cases.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_CASES_PATH = Path("tests/fixtures/xhs_quality_cases.json")


def load_quality_cases(path: str | Path = DEFAULT_CASES_PATH) -> List[Dict[str, Any]]:
    """Load and validate Xiaohongshu quality seed cases."""
    case_path = Path(path)
    with case_path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

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

    return cases


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
        "| Case | Category | Decision | Overall | Trace | Titles | Copy Len | Tags | Issues | Suggestions | Error |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        error = (result.get("error") or "").replace("|", "\\|")
        row = {**result, "error": error}
        lines.append(
            "| {case_id} | {category} | {decision} | {overall} | {trace_id} | "
            "{title_count} | {copywriting_length} | {tag_count} | {issues_count} | "
            "{suggestions_count} | {error} |".format(**row)
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


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
