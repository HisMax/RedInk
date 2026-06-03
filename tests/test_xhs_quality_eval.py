import json
import subprocess
import sys

from backend.services.xhs_quality_eval import (
    apply_quality_baseline,
    build_case_outline,
    load_quality_cases,
    run_quality_eval,
    write_jsonl_report,
    write_markdown_report,
)


class FakeContentService:
    def __init__(self):
        self.calls = []

    def generate_content(self, topic, outline):
        self.calls.append({"topic": topic, "outline": outline})
        return {
            "success": True,
            "titles": [f"{topic} 标题"],
            "copywriting": f"{topic} 正文，包含清晰步骤和用户收益。",
            "tags": ["小红书", "内容创作"],
        }


class FakeQualityService:
    def __init__(self):
        self.calls = []

    def evaluate_content(self, topic, outline, titles, copywriting, tags):
        self.calls.append({
            "topic": topic,
            "outline": outline,
            "titles": titles,
            "copywriting": copywriting,
            "tags": tags,
        })
        return {
            "success": True,
            "trace_id": "xhs_fake_trace",
            "quality_score": {
                "overall": 87,
                "decision": "approve",
                "issues": ["标题还可以更具体"],
                "suggestions": ["增加收藏理由"],
            },
            "publish_gate": {"enabled": False},
        }


def test_load_quality_cases_reads_fixture():
    cases = load_quality_cases("tests/fixtures/xhs_quality_cases.json")

    assert len(cases) == 5
    assert cases[0]["id"] == "coffee_beginner"
    assert cases[0]["topic"] == "新手如何学会手冲咖啡"


def test_build_case_outline_includes_expected_traits():
    case = {
        "id": "coffee_beginner",
        "category": "知识科普",
        "topic": "新手如何学会手冲咖啡",
        "expected_traits": ["有具体步骤", "有参数"],
    }

    outline = build_case_outline(case)

    assert "类别：知识科普" in outline
    assert "主题：新手如何学会手冲咖啡" in outline
    assert "- 有具体步骤" in outline
    assert "- 有参数" in outline


def test_run_quality_eval_dry_run_returns_summary_without_services():
    cases = [
        {
            "id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "expected_traits": ["有具体步骤", "有参数"],
        }
    ]

    results = run_quality_eval(cases)

    assert results[0]["case_id"] == "coffee_beginner"
    assert results[0]["title_count"] == 3
    assert results[0]["copywriting_length"] > 0
    assert results[0]["tag_count"] >= 3
    assert results[0]["overall"] >= 70
    assert results[0]["decision"] == "approve"
    assert results[0]["error"] is None


def test_run_quality_eval_live_uses_injected_services():
    cases = [
        {
            "id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "expected_traits": ["有具体步骤", "有参数"],
        }
    ]
    content_service = FakeContentService()
    quality_service = FakeQualityService()

    results = run_quality_eval(
        cases,
        live=True,
        content_service=content_service,
        quality_service=quality_service,
    )

    assert len(content_service.calls) == 1
    assert len(quality_service.calls) == 1
    assert quality_service.calls[0]["titles"] == ["新手如何学会手冲咖啡 标题"]
    assert results[0]["trace_id"] == "xhs_fake_trace"
    assert results[0]["overall"] == 87
    assert results[0]["issues_count"] == 1
    assert results[0]["suggestions_count"] == 1


def test_apply_quality_baseline_marks_failures_by_score_decision_and_error():
    results = [
        {
            "case_id": "passed_case",
            "category": "知识科普",
            "topic": "通过案例",
            "trace_id": "trace_1",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 87,
            "decision": "approve",
            "issues_count": 0,
            "suggestions_count": 1,
            "publish_gate_enabled": False,
            "error": None,
        },
        {
            "case_id": "low_score",
            "category": "知识科普",
            "topic": "低分案例",
            "trace_id": "trace_2",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 79,
            "decision": "approve",
            "issues_count": 1,
            "suggestions_count": 2,
            "publish_gate_enabled": False,
            "error": None,
        },
        {
            "case_id": "needs_revision",
            "category": "知识科普",
            "topic": "返修案例",
            "trace_id": "trace_3",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 86,
            "decision": "revise",
            "issues_count": 1,
            "suggestions_count": 2,
            "publish_gate_enabled": False,
            "error": None,
        },
        {
            "case_id": "error_case",
            "category": "知识科普",
            "topic": "错误案例",
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
            "error": "内容生成失败",
        },
    ]

    annotated, baseline = apply_quality_baseline(
        results,
        min_overall=80,
        allowed_decisions=["approve"],
    )

    assert baseline["passed"] is False
    assert baseline["passed_count"] == 1
    assert baseline["failed_count"] == 3
    assert annotated[0]["baseline_passed"] is True
    assert annotated[0]["baseline_reason"] == ""
    assert annotated[1]["baseline_reason"] == "overall 79 below 80"
    assert annotated[2]["baseline_reason"] == "decision revise not allowed"
    assert annotated[3]["baseline_reason"] == "evaluation error: 内容生成失败"
    assert [failure["case_id"] for failure in baseline["failures"]] == [
        "low_score",
        "needs_revision",
        "error_case",
    ]


def test_report_writers_create_jsonl_and_markdown(tmp_path):
    results = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "xhs_fake_trace",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 87,
            "decision": "approve",
            "issues_count": 1,
            "suggestions_count": 2,
            "publish_gate_enabled": False,
            "error": None,
        }
    ]
    annotated, _baseline = apply_quality_baseline(results, min_overall=80, allowed_decisions=["approve"])
    jsonl_path = tmp_path / "report.jsonl"
    markdown_path = tmp_path / "report.md"

    write_jsonl_report(annotated, jsonl_path)
    write_markdown_report(annotated, markdown_path)

    jsonl_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert jsonl_rows[0]["case_id"] == "coffee_beginner"
    assert jsonl_rows[0]["baseline_passed"] is True

    markdown = markdown_path.read_text(encoding="utf-8")
    assert "| coffee_beginner | 知识科普 | approve | 87 |" in markdown
    assert "| pass |" in markdown


def test_cli_dry_run_outputs_summary_json():
    completed = subprocess.run(
        [sys.executable, "scripts/run_xhs_quality_eval.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["case_count"] == 5
    assert len(payload["results"]) == 5
    assert payload["baseline"]["passed"] is True


def test_cli_exits_nonzero_when_baseline_fails():
    completed = subprocess.run(
        [sys.executable, "scripts/run_xhs_quality_eval.py", "--min-overall", "95"],
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["baseline"]["passed"] is False
    assert payload["baseline"]["failed_count"] == 5
