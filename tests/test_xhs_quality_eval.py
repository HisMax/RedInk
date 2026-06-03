import json
import subprocess
import sys

from backend.services.content import ContentService
from backend.services.content_case_library import (
    append_case_records,
    build_case_records,
    load_case_records,
    save_case_records,
    select_prompt_examples,
    select_re_evaluated_prompt_examples,
    summarize_case_records,
    update_case_review,
    write_case_library_report,
    write_prompt_examples,
)
from backend.services.content_revision_loop import (
    apply_revision_results_to_case_library,
    build_revised_case_records,
    build_revision_requests,
    load_revision_results,
    load_revision_requests,
    run_revision_requests,
    write_revision_results,
    write_revision_requests,
)
from backend.services.xhs_quality_eval import (
    apply_quality_baseline,
    build_case_outline,
    compare_quality_trend,
    load_previous_eval_results,
    load_quality_cases,
    run_quality_eval,
    write_jsonl_report,
    write_markdown_report,
)
from backend.services.xhs_quality_history import (
    summarize_loop_history,
    write_loop_history_markdown,
)
from backend.services.xhs_quality_loop import run_quality_loop
from backend.services.xhs_re_evaluation import (
    apply_improvement_gate,
    apply_re_evaluation_results_to_case_library,
    run_re_evaluation,
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


class FakePromptExampleContentService:
    def __init__(self):
        self.calls = []

    def generate_content(self, topic, outline, prompt_examples=None):
        self.calls.append({
            "topic": topic,
            "outline": outline,
            "prompt_examples": prompt_examples,
        })
        return {
            "success": True,
            "titles": [f"{topic} 标题"],
            "copywriting": f"{topic} 正文，参考了已验证样本。",
            "tags": ["小红书", "内容创作"],
        }


class FakeTextClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


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


class FakeRevisionService:
    def __init__(self):
        self.calls = []

    def suggest_revisions(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "trace_id": kwargs["trace_id"],
            "revision": {
                "titles": ["改后标题"],
                "copywriting": "改后正文",
                "tags": ["改后标签"],
                "revision_summary": ["强化开头钩子"],
            },
        }


class FakeReEvaluationQualityService:
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
            "trace_id": "xhs_reeval_trace",
            "quality_score": {
                "overall": 86,
                "decision": "approve",
                "issues": [],
                "suggestions": ["保留改稿后的具体参数"],
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


def test_content_service_injects_quality_prompt_examples():
    client = FakeTextClient(json.dumps({
        "titles": ["新标题"],
        "copywriting": "新正文",
        "tags": ["咖啡", "新手"],
    }, ensure_ascii=False))
    service = ContentService(
        client=client,
        text_config={"active_provider": "fake", "providers": {"fake": {"model": "fake-model"}}},
        prompt_template="topic={topic}\noutline={outline}",
    )

    result = service.generate_content(
        topic="新手如何学会手冲咖啡",
        outline="原始大纲",
        prompt_examples=[
            {
                "topic": "新手如何学会手冲咖啡",
                "title": "改后标题",
                "copywriting": "改后正文",
                "tags": ["咖啡", "新手"],
                "quality_overall": 93,
                "previous_overall": 88,
                "score_delta": 5,
                "revision_summary": ["强化钩子和行动路径"],
            }
        ],
    )

    prompt = client.calls[0]["prompt"]
    assert result["success"] is True
    assert "已验证优质样本参考" in prompt
    assert "改后标题" in prompt
    assert "质量分：93" in prompt
    assert "提升：+5" in prompt
    assert "强化钩子和行动路径" in prompt


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
    assert "步骤讲清楚" in results[0]["copywriting"]
    assert results[0]["copywriting_length"] > 0
    assert "质量评测" in results[0]["tags"]
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
    assert results[0]["copywriting"] == "新手如何学会手冲咖啡 正文，包含清晰步骤和用户收益。"
    assert results[0]["tags"] == ["小红书", "内容创作"]
    assert results[0]["overall"] == 87
    assert results[0]["issues_count"] == 1
    assert results[0]["suggestions_count"] == 1


def test_run_quality_eval_live_passes_prompt_examples_to_content_service():
    cases = [
        {
            "id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "expected_traits": ["有具体步骤"],
        }
    ]
    prompt_examples = [
        {
            "topic": "新手如何学会手冲咖啡",
            "title": "改后标题",
            "copywriting": "改后正文",
            "quality_overall": 93,
            "score_delta": 5,
        }
    ]
    content_service = FakePromptExampleContentService()
    quality_service = FakeQualityService()

    results = run_quality_eval(
        cases,
        live=True,
        content_service=content_service,
        quality_service=quality_service,
        prompt_examples=prompt_examples,
    )

    assert results[0]["error"] is None
    assert content_service.calls[0]["prompt_examples"] == prompt_examples


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


def test_load_previous_eval_results_accepts_jsonl_and_payload_json(tmp_path):
    jsonl_path = tmp_path / "previous.jsonl"
    jsonl_path.write_text(
        "\n".join([
            json.dumps({"case_id": "coffee_beginner", "overall": 90}, ensure_ascii=False),
            json.dumps({"case_id": "office_efficiency", "overall": 84}, ensure_ascii=False),
        ]) + "\n",
        encoding="utf-8",
    )
    payload_path = tmp_path / "previous.json"
    payload_path.write_text(
        json.dumps({
            "mode": "dry-run",
            "results": [{"case_id": "coffee_beginner", "overall": 91}],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    assert load_previous_eval_results(jsonl_path)[0]["overall"] == 90
    assert load_previous_eval_results(payload_path)[0]["overall"] == 91


def test_compare_quality_trend_fails_when_score_drop_exceeds_threshold():
    current = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "current_trace",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 84,
            "decision": "approve",
            "issues_count": 1,
            "suggestions_count": 2,
            "publish_gate_enabled": False,
            "baseline_passed": True,
            "baseline_reason": "",
            "error": None,
        },
        {
            "case_id": "new_case",
            "category": "知识科普",
            "topic": "新增案例",
            "trace_id": "current_trace_2",
            "titles": ["标题"],
            "title_count": 1,
            "copywriting_length": 30,
            "tag_count": 2,
            "overall": 88,
            "decision": "approve",
            "issues_count": 0,
            "suggestions_count": 1,
            "publish_gate_enabled": False,
            "baseline_passed": True,
            "baseline_reason": "",
            "error": None,
        },
    ]
    previous = [{"case_id": "coffee_beginner", "overall": 90}]

    annotated, comparison = compare_quality_trend(current, previous, max_score_drop=3)

    assert comparison["passed"] is False
    assert comparison["compared_count"] == 1
    assert comparison["skipped_count"] == 1
    assert comparison["failed_count"] == 1
    assert annotated[0]["previous_overall"] == 90
    assert annotated[0]["score_delta"] == -6
    assert annotated[0]["trend_passed"] is False
    assert annotated[0]["trend_reason"] == "score dropped 6 points (from 90 to 84)"
    assert annotated[1]["previous_overall"] is None
    assert annotated[1]["trend_passed"] is True
    assert comparison["failures"][0]["case_id"] == "coffee_beginner"


def test_content_case_library_appends_review_ready_records(tmp_path):
    results = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "xhs_fake_trace",
            "titles": ["标题A", "标题B"],
            "copywriting": "正文内容",
            "tags": ["咖啡", "新手"],
            "title_count": 2,
            "copywriting_length": 4,
            "tag_count": 2,
            "overall": 87,
            "decision": "approve",
            "issues_count": 1,
            "suggestions_count": 2,
            "publish_gate_enabled": False,
            "baseline_passed": True,
            "baseline_reason": "",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        }
    ]

    records = build_case_records(
        results,
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    library_path = tmp_path / "content_cases.jsonl"

    append_case_records(records, library_path)
    loaded = load_case_records(library_path)

    assert len(loaded) == 1
    assert loaded[0]["schema_version"] == "xhs_content_case.v1"
    assert loaded[0]["record_id"] == "eval_001:coffee_beginner"
    assert loaded[0]["content"]["titles"] == ["标题A", "标题B"]
    assert loaded[0]["content"]["copywriting"] == "正文内容"
    assert loaded[0]["content"]["tags"] == ["咖啡", "新手"]
    assert loaded[0]["quality"]["overall"] == 87
    assert loaded[0]["human_review"]["status"] == "unreviewed"
    assert loaded[0]["human_review"]["issue_types"] == []


def test_content_case_library_updates_human_review_fields(tmp_path):
    results = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "xhs_fake_trace",
            "titles": ["标题A", "标题B"],
            "copywriting": "正文内容",
            "tags": ["咖啡", "新手"],
            "overall": 87,
            "decision": "approve",
            "issues_count": 1,
            "suggestions_count": 2,
            "baseline_passed": True,
            "baseline_reason": "",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        }
    ]
    records = build_case_records(
        results,
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )

    updated_records, updated = update_case_review(
        records,
        "eval_001:coffee_beginner",
        status="reviewed",
        publishable=True,
        viral_potential=5,
        issue_types=["title_generic", "hook_weak"],
        selected_title="标题B",
        edited_copywriting="人工改稿正文",
        notes="可以进入发布池",
        reviewed_at="2026-06-04T10:00:00Z",
    )
    library_path = tmp_path / "content_cases.jsonl"
    save_case_records(updated_records, library_path)
    loaded = load_case_records(library_path)

    assert updated["human_review"]["status"] == "reviewed"
    assert loaded[0]["human_review"]["publishable"] is True
    assert loaded[0]["human_review"]["viral_potential"] == 5
    assert loaded[0]["human_review"]["issue_types"] == ["title_generic", "hook_weak"]
    assert loaded[0]["human_review"]["selected_title"] == "标题B"
    assert loaded[0]["human_review"]["edited_copywriting"] == "人工改稿正文"
    assert loaded[0]["human_review"]["notes"] == "可以进入发布池"
    assert loaded[0]["human_review"]["reviewed_at"] == "2026-06-04T10:00:00Z"


def test_content_case_library_summarizes_reviews_and_exports_examples(tmp_path):
    results = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "trace_1",
            "titles": ["标题A", "标题B"],
            "copywriting": "正文A",
            "tags": ["咖啡", "新手"],
            "overall": 90,
            "decision": "approve",
            "issues_count": 0,
            "suggestions_count": 1,
            "baseline_passed": True,
            "baseline_reason": "",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        },
        {
            "case_id": "office_efficiency",
            "category": "职场效率",
            "topic": "打工人如何用AI整理会议纪要",
            "trace_id": "trace_2",
            "titles": ["标题C"],
            "copywriting": "正文B",
            "tags": ["AI", "会议纪要"],
            "overall": 78,
            "decision": "revise",
            "issues_count": 2,
            "suggestions_count": 3,
            "baseline_passed": False,
            "baseline_reason": "overall 78 below 80",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        },
    ]
    records = build_case_records(
        results,
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    records, _updated = update_case_review(
        records,
        "eval_001:coffee_beginner",
        status="reviewed",
        publishable=True,
        viral_potential=5,
        issue_types=["hook_strong"],
        selected_title="标题B",
        edited_copywriting="人工优质改稿",
        notes="可作为模板",
        reviewed_at="2026-06-04T10:00:00Z",
    )
    records, _updated = update_case_review(
        records,
        "eval_001:office_efficiency",
        status="needs_revision",
        publishable=False,
        viral_potential=2,
        issue_types=["hook_weak", "benefit_unclear"],
        notes="需要重写",
        reviewed_at="2026-06-04T10:05:00Z",
    )

    summary = summarize_case_records(records)
    examples = select_prompt_examples(records, min_viral_potential=4, limit=5)
    report_path = tmp_path / "case_report.md"
    examples_path = tmp_path / "prompt_examples.jsonl"

    write_case_library_report(summary, report_path)
    write_prompt_examples(examples, examples_path)

    assert summary["total_count"] == 2
    assert summary["reviewed_count"] == 2
    assert summary["publishable_count"] == 1
    assert summary["needs_revision_count"] == 1
    assert summary["average_quality_overall"] == 84
    assert summary["average_viral_potential"] == 3.5
    assert summary["issue_type_counts"]["hook_weak"] == 1
    assert summary["top_cases"][0]["record_id"] == "eval_001:coffee_beginner"
    assert examples[0]["title"] == "标题B"
    assert examples[0]["copywriting"] == "人工优质改稿"
    assert "Content Case Library Report" in report_path.read_text(encoding="utf-8")
    exported = [json.loads(line) for line in examples_path.read_text(encoding="utf-8").splitlines()]
    assert exported[0]["record_id"] == "eval_001:coffee_beginner"


def test_revision_loop_builds_requests_from_failed_or_rejected_cases(tmp_path):
    results = [
        {
            "case_id": "coffee_beginner",
            "category": "知识科普",
            "topic": "新手如何学会手冲咖啡",
            "trace_id": "trace_1",
            "titles": ["标题A"],
            "copywriting": "正文A",
            "tags": ["咖啡"],
            "overall": 79,
            "decision": "revise",
            "issues_count": 1,
            "suggestions_count": 2,
            "baseline_passed": False,
            "baseline_reason": "overall 79 below 80",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        },
        {
            "case_id": "office_efficiency",
            "category": "职场效率",
            "topic": "打工人如何用AI整理会议纪要",
            "trace_id": "trace_2",
            "titles": ["标题B"],
            "copywriting": "正文B",
            "tags": ["AI"],
            "overall": 88,
            "decision": "approve",
            "issues_count": 0,
            "suggestions_count": 1,
            "baseline_passed": True,
            "baseline_reason": "",
            "trend_passed": True,
            "trend_reason": "",
            "error": None,
        },
    ]
    records = build_case_records(
        results,
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    records, _updated = update_case_review(
        records,
        "eval_001:coffee_beginner",
        status="needs_revision",
        publishable=False,
        issue_types=["hook_weak"],
        notes="开头没有痛点",
        reviewed_at="2026-06-04T10:00:00Z",
    )
    requests = build_revision_requests(
        records,
        run_id="revision_001",
        created_at="2026-06-04T12:00:00Z",
    )
    requests_path = tmp_path / "revision_requests.jsonl"
    write_revision_requests(requests, requests_path)
    loaded = load_revision_requests(requests_path)

    assert len(requests) == 1
    assert requests[0]["schema_version"] == "xhs_revision_request.v1"
    assert requests[0]["request_id"] == "revision_001:eval_001:coffee_beginner"
    assert requests[0]["source_record_id"] == "eval_001:coffee_beginner"
    assert "baseline_failed" in requests[0]["trigger_reasons"]
    assert "human_rejected" in requests[0]["trigger_reasons"]
    assert requests[0]["revision_input"]["topic"] == "新手如何学会手冲咖啡"
    assert requests[0]["revision_input"]["copywriting"] == "正文A"
    assert "hook_weak" in requests[0]["revision_input"]["quality_score"]["issues"]
    assert loaded[0]["request_id"] == requests[0]["request_id"]


def test_revision_loop_runs_requests_with_injected_revision_service():
    requests = [
        {
            "request_id": "revision_001:eval_001:coffee_beginner",
            "source_record_id": "eval_001:coffee_beginner",
            "revision_input": {
                "topic": "新手如何学会手冲咖啡",
                "outline": "类别：知识科普\n主题：新手如何学会手冲咖啡",
                "titles": ["标题A"],
                "copywriting": "正文A",
                "tags": ["咖啡"],
                "quality_score": {
                    "issues": ["hook_weak"],
                    "suggestions": ["强化开头钩子"],
                },
                "trace_id": "trace_1",
            },
        }
    ]
    service = FakeRevisionService()

    results = run_revision_requests(requests, revision_service=service)

    assert len(service.calls) == 1
    assert service.calls[0]["topic"] == "新手如何学会手冲咖啡"
    assert results[0]["schema_version"] == "xhs_revision_result.v1"
    assert results[0]["success"] is True
    assert results[0]["revision"]["titles"] == ["改后标题"]


def test_revision_loop_builds_revised_case_records_from_successful_results():
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revision_results = [
        {
            "schema_version": "xhs_revision_result.v1",
            "request_id": "revision_001:eval_001:coffee_beginner",
            "source_record_id": "eval_001:coffee_beginner",
            "success": True,
            "trace_id": "revision_trace_1",
            "revised_at": "2026-06-04T12:30:00Z",
            "revision": {
                "titles": ["改后标题"],
                "copywriting": "改后正文",
                "tags": ["改后标签"],
                "revision_summary": ["强化开头钩子"],
            },
        },
        {
            "schema_version": "xhs_revision_result.v1",
            "request_id": "revision_001:missing",
            "source_record_id": "missing",
            "success": False,
            "trace_id": "revision_trace_2",
            "revision": None,
            "error": "failed",
        },
    ]

    revised_records = build_revised_case_records(
        source_records,
        revision_results,
        run_id="revision_001",
        created_at="2026-06-04T13:00:00Z",
    )

    assert len(revised_records) == 1
    revised = revised_records[0]
    assert revised["schema_version"] == "xhs_content_case.v1"
    assert revised["record_id"] == "revision_001:eval_001:coffee_beginner:revised"
    assert revised["source"] == "xhs_revision_loop"
    assert revised["case"]["topic"] == "新手如何学会手冲咖啡"
    assert revised["content"]["titles"] == ["改后标题"]
    assert revised["content"]["copywriting"] == "改后正文"
    assert revised["quality"]["decision"] == "pending_re_evaluation"
    assert revised["quality"]["trace_id"] == "revision_trace_1"
    assert revised["human_review"]["status"] == "unreviewed"
    assert revised["revision_meta"]["source_record_id"] == "eval_001:coffee_beginner"
    assert revised["revision_meta"]["request_id"] == "revision_001:eval_001:coffee_beginner"
    assert revised["revision_meta"]["source_quality_trace_id"] == "quality_trace_1"
    assert revised["revision_meta"]["revision_summary"] == ["强化开头钩子"]


def test_revision_loop_applies_revised_records_without_duplicates():
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revision_results = [
        {
            "request_id": "revision_001:eval_001:coffee_beginner",
            "source_record_id": "eval_001:coffee_beginner",
            "success": True,
            "trace_id": "revision_trace_1",
            "revision": {
                "titles": ["改后标题"],
                "copywriting": "改后正文",
                "tags": ["改后标签"],
                "revision_summary": ["强化开头钩子"],
            },
        },
    ]

    updated_once, revised_once = apply_revision_results_to_case_library(
        source_records,
        revision_results,
        run_id="revision_001",
        created_at="2026-06-04T13:00:00Z",
    )
    updated_twice, revised_twice = apply_revision_results_to_case_library(
        updated_once,
        revision_results,
        run_id="revision_001",
        created_at="2026-06-04T14:00:00Z",
    )

    assert len(revised_once) == 1
    assert len(revised_twice) == 1
    assert len(updated_once) == 2
    assert len(updated_twice) == 2
    assert updated_twice[-1]["record_id"] == "revision_001:eval_001:coffee_beginner:revised"
    assert updated_twice[-1]["created_at"] == "2026-06-04T14:00:00Z"


def test_re_evaluation_runs_pending_revised_cases_and_compares_source_score():
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revised_records = build_revised_case_records(
        source_records,
        [
            {
                "request_id": "revision_001:eval_001:coffee_beginner",
                "source_record_id": "eval_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题"],
                    "copywriting": "改后正文",
                    "tags": ["改后标签"],
                    "revision_summary": ["强化开头钩子"],
                },
            }
        ],
        run_id="revision_001",
        created_at="2026-06-04T13:00:00Z",
    )
    service = FakeReEvaluationQualityService()

    results = run_re_evaluation(
        source_records + revised_records,
        live=True,
        quality_service=service,
        run_id="reeval_001",
        evaluated_at="2026-06-04T15:00:00Z",
    )
    results, comparison = apply_improvement_gate(results, min_improvement=0)

    assert len(service.calls) == 1
    assert service.calls[0]["topic"] == "新手如何学会手冲咖啡"
    assert "源记录：eval_001:coffee_beginner" in service.calls[0]["outline"]
    assert results[0]["schema_version"] == "xhs_re_evaluation_result.v1"
    assert results[0]["record_id"] == "revision_001:eval_001:coffee_beginner:revised"
    assert results[0]["source_record_id"] == "eval_001:coffee_beginner"
    assert results[0]["previous_overall"] == 79
    assert results[0]["overall"] == 86
    assert results[0]["score_delta"] == 7
    assert results[0]["improvement_passed"] is True
    assert comparison["passed"] is True
    assert comparison["improved_count"] == 1


def test_re_evaluation_applies_results_to_case_library_records():
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revised_records = build_revised_case_records(
        source_records,
        [
            {
                "request_id": "revision_001:eval_001:coffee_beginner",
                "source_record_id": "eval_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题"],
                    "copywriting": "改后正文",
                    "tags": ["改后标签"],
                    "revision_summary": ["强化开头钩子"],
                },
            }
        ],
        run_id="revision_001",
        created_at="2026-06-04T13:00:00Z",
    )
    results = [
        {
            "schema_version": "xhs_re_evaluation_result.v1",
            "record_id": "revision_001:eval_001:coffee_beginner:revised",
            "source_record_id": "eval_001:coffee_beginner",
            "run_id": "reeval_001",
            "evaluated_at": "2026-06-04T15:00:00Z",
            "trace_id": "xhs_reeval_trace",
            "overall": 86,
            "decision": "approve",
            "issues_count": 0,
            "suggestions_count": 1,
            "publish_gate_enabled": False,
            "error": None,
            "previous_overall": 79,
            "score_delta": 7,
            "improvement_passed": True,
            "improvement_reason": "",
        }
    ]

    updated, updated_count = apply_re_evaluation_results_to_case_library(
        source_records + revised_records,
        results,
    )

    assert updated_count == 1
    revised = updated[-1]
    assert revised["quality"]["decision"] == "approve"
    assert revised["quality"]["overall"] == 86
    assert revised["quality"]["trace_id"] == "xhs_reeval_trace"
    assert revised["quality"]["baseline_passed"] is True
    assert revised["revision_meta"]["re_evaluation"]["run_id"] == "reeval_001"
    assert revised["revision_meta"]["re_evaluation"]["score_delta"] == 7


def test_content_case_library_selects_re_evaluated_prompt_examples():
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题A"],
                "copywriting": "原正文A",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            },
            {
                "case_id": "office_efficiency",
                "category": "职场效率",
                "topic": "打工人如何用AI整理会议纪要",
                "trace_id": "quality_trace_2",
                "titles": ["原标题B"],
                "copywriting": "原正文B",
                "tags": ["AI"],
                "overall": 84,
                "decision": "approve",
                "issues_count": 0,
                "suggestions_count": 1,
                "baseline_passed": True,
                "baseline_reason": "",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            },
        ],
        run_id="eval_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revised_records = build_revised_case_records(
        source_records,
        [
            {
                "request_id": "revision_001:eval_001:coffee_beginner",
                "source_record_id": "eval_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题A"],
                    "copywriting": "改后正文A",
                    "tags": ["咖啡", "新手"],
                    "revision_summary": ["强化开头钩子"],
                },
            },
            {
                "request_id": "revision_001:eval_001:office_efficiency",
                "source_record_id": "eval_001:office_efficiency",
                "success": True,
                "trace_id": "revision_trace_2",
                "revision": {
                    "titles": ["改后标题B"],
                    "copywriting": "改后正文B",
                    "tags": ["AI", "会议纪要"],
                    "revision_summary": ["补充工具流程"],
                },
            },
        ],
        run_id="revision_001",
        created_at="2026-06-04T13:00:00Z",
    )
    records, _updated_count = apply_re_evaluation_results_to_case_library(
        source_records + revised_records,
        [
            {
                "record_id": "revision_001:eval_001:coffee_beginner:revised",
                "source_record_id": "eval_001:coffee_beginner",
                "run_id": "reeval_001",
                "evaluated_at": "2026-06-04T15:00:00Z",
                "trace_id": "xhs_reeval_trace_1",
                "overall": 88,
                "decision": "approve",
                "issues_count": 0,
                "suggestions_count": 1,
                "publish_gate_enabled": False,
                "error": None,
                "previous_overall": 79,
                "score_delta": 9,
                "improvement_passed": True,
                "improvement_reason": "",
            },
            {
                "record_id": "revision_001:eval_001:office_efficiency:revised",
                "source_record_id": "eval_001:office_efficiency",
                "run_id": "reeval_001",
                "evaluated_at": "2026-06-04T15:00:00Z",
                "trace_id": "xhs_reeval_trace_2",
                "overall": 85,
                "decision": "approve",
                "issues_count": 0,
                "suggestions_count": 1,
                "publish_gate_enabled": False,
                "error": None,
                "previous_overall": 84,
                "score_delta": 1,
                "improvement_passed": True,
                "improvement_reason": "",
            },
        ],
    )

    examples = select_re_evaluated_prompt_examples(
        records,
        min_overall=85,
        min_score_delta=3,
        limit=5,
    )

    assert len(examples) == 1
    assert examples[0]["record_id"] == "revision_001:eval_001:coffee_beginner:revised"
    assert examples[0]["source_record_id"] == "eval_001:coffee_beginner"
    assert examples[0]["title"] == "改后标题A"
    assert examples[0]["copywriting"] == "改后正文A"
    assert examples[0]["quality_overall"] == 88
    assert examples[0]["previous_overall"] == 79
    assert examples[0]["score_delta"] == 9
    assert examples[0]["example_source"] == "re_evaluation"
    assert examples[0]["revision_summary"] == ["强化开头钩子"]


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


def test_cli_loads_prompt_examples_for_quality_eval(tmp_path):
    examples_path = tmp_path / "quality_examples.jsonl"
    examples_path.write_text(
        json.dumps({
            "record_id": "revision_001:eval_001:coffee_beginner:revised",
            "topic": "新手如何学会手冲咖啡",
            "title": "改后标题",
            "copywriting": "改后正文",
            "quality_overall": 93,
            "score_delta": 5,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--prompt-examples-jsonl",
            str(examples_path),
            "--prompt-examples-limit",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["prompt_examples"]["path"] == str(examples_path)
    assert payload["prompt_examples"]["loaded_count"] == 1


def test_cli_can_append_content_case_library(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--case-library",
            str(library_path),
            "--run-id",
            "eval_cli_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    records = load_case_records(library_path)
    assert payload["case_library"]["saved_count"] == 5
    assert records[0]["run_id"] == "eval_cli_001"
    assert records[0]["content"]["copywriting"]
    assert records[0]["human_review"]["status"] == "unreviewed"


def test_review_cli_updates_content_case_library_record(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--case-library",
            str(library_path),
            "--run-id",
            "eval_cli_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["case_library"]["saved_count"] == 5

    review = subprocess.run(
        [
            sys.executable,
            "scripts/review_xhs_content_case.py",
            "--library",
            str(library_path),
            "--record-id",
            "eval_cli_001:coffee_beginner",
            "--status",
            "reviewed",
            "--publishable",
            "true",
            "--viral-potential",
            "5",
            "--issue-type",
            "title_generic",
            "--issue-type",
            "hook_weak",
            "--selected-title",
            "收藏：新手如何学会手冲咖啡完整流程",
            "--edited-copywriting",
            "人工改稿正文",
            "--notes",
            "可以进入发布池",
            "--reviewed-at",
            "2026-06-04T10:00:00Z",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    review_payload = json.loads(review.stdout)
    records = load_case_records(library_path)
    assert review_payload["updated"] is True
    assert review_payload["record_id"] == "eval_cli_001:coffee_beginner"
    assert records[0]["human_review"]["publishable"] is True
    assert records[0]["human_review"]["viral_potential"] == 5
    assert records[0]["human_review"]["issue_types"] == ["title_generic", "hook_weak"]


def test_summarize_cli_writes_case_report_and_prompt_examples(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--case-library",
            str(library_path),
            "--run-id",
            "eval_cli_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["case_library"]["saved_count"] == 5
    subprocess.run(
        [
            sys.executable,
            "scripts/review_xhs_content_case.py",
            "--library",
            str(library_path),
            "--record-id",
            "eval_cli_001:coffee_beginner",
            "--status",
            "reviewed",
            "--publishable",
            "true",
            "--viral-potential",
            "5",
            "--selected-title",
            "收藏：新手如何学会手冲咖啡完整流程",
            "--edited-copywriting",
            "人工优质改稿",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report_path = tmp_path / "case_report.md"
    examples_path = tmp_path / "prompt_examples.jsonl"

    summary = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_xhs_content_cases.py",
            "--library",
            str(library_path),
            "--markdown",
            str(report_path),
            "--examples-jsonl",
            str(examples_path),
            "--min-viral-potential",
            "4",
            "--limit",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(summary.stdout)
    assert payload["summary"]["total_count"] == 5
    assert payload["summary"]["publishable_count"] == 1
    assert payload["examples_count"] == 1
    assert report_path.exists()
    assert examples_path.exists()


def test_summarize_cli_writes_re_evaluated_prompt_examples(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_cli_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revised_records = build_revised_case_records(
        source_records,
        [
            {
                "request_id": "revision_cli_001:eval_cli_001:coffee_beginner",
                "source_record_id": "eval_cli_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题"],
                    "copywriting": "改后正文",
                    "tags": ["咖啡", "新手"],
                    "revision_summary": ["强化开头钩子"],
                },
            }
        ],
        run_id="revision_cli_001",
        created_at="2026-06-04T13:00:00Z",
    )
    records, _updated_count = apply_re_evaluation_results_to_case_library(
        source_records + revised_records,
        [
            {
                "record_id": "revision_cli_001:eval_cli_001:coffee_beginner:revised",
                "source_record_id": "eval_cli_001:coffee_beginner",
                "run_id": "reeval_cli_001",
                "evaluated_at": "2026-06-04T15:00:00Z",
                "trace_id": "xhs_reeval_trace",
                "overall": 88,
                "decision": "approve",
                "issues_count": 0,
                "suggestions_count": 1,
                "publish_gate_enabled": False,
                "error": None,
                "previous_overall": 79,
                "score_delta": 9,
                "improvement_passed": True,
                "improvement_reason": "",
            }
        ],
    )
    save_case_records(records, library_path)
    examples_path = tmp_path / "quality_prompt_examples.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_xhs_content_cases.py",
            "--library",
            str(library_path),
            "--quality-examples-jsonl",
            str(examples_path),
            "--min-quality-overall",
            "85",
            "--min-score-delta",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    examples = [json.loads(line) for line in examples_path.read_text(encoding="utf-8").splitlines()]
    assert payload["quality_examples_count"] == 1
    assert payload["quality_examples_jsonl"] == str(examples_path)
    assert examples[0]["record_id"] == "revision_cli_001:eval_cli_001:coffee_beginner:revised"
    assert examples[0]["score_delta"] == 9
    assert examples[0]["example_source"] == "re_evaluation"


def test_quality_loop_runs_dry_run_end_to_end(tmp_path):
    report_dir = tmp_path / "loop_reports"

    payload = run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        run_id="loop_001",
        min_overall=95,
        min_improvement=0,
        min_quality_overall=85,
        min_score_delta=3,
    )

    case_library = load_case_records(payload["paths"]["case_library"])
    quality_examples = [
        json.loads(line)
        for line in payload["paths"]["quality_examples"].read_text(encoding="utf-8").splitlines()
    ]
    assert payload["evaluation"]["case_count"] == 5
    assert payload["baseline"]["failed_count"] == 5
    assert payload["revision"]["request_count"] == 5
    assert payload["revision"]["result_count"] == 5
    assert payload["re_evaluation"]["candidate_count"] == 5
    assert payload["quality_examples"]["count"] == 5
    assert len(case_library) == 10
    assert len(quality_examples) == 5
    assert quality_examples[0]["example_source"] == "re_evaluation"


def test_quality_loop_writes_run_report_and_replay_index(tmp_path):
    report_dir = tmp_path / "loop_reports"
    index_path = tmp_path / "loop-index.jsonl"

    payload = run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_report_001",
        min_overall=95,
        min_improvement=0,
        min_quality_overall=85,
        min_score_delta=3,
    )

    run_report = json.loads(payload["paths"]["run_report"].read_text(encoding="utf-8"))
    index_rows = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert payload["paths"]["replay_index"] == index_path
    assert run_report["schema_version"] == "xhs_quality_loop_run.v1"
    assert run_report["run_id"] == "loop_report_001"
    assert run_report["parameters"]["min_overall"] == 95
    assert run_report["metrics"]["revision_request_count"] == 5
    assert run_report["metrics"]["quality_examples_count"] == 5
    assert run_report["artifacts"]["quality_examples"].endswith("xhs-quality-prompt-examples.jsonl")
    assert run_report["replay"]["command"][0:3] == ["uv", "run", "python"]
    assert index_rows[-1]["schema_version"] == "xhs_quality_loop_index.v1"
    assert index_rows[-1]["run_id"] == "loop_report_001"
    assert index_rows[-1]["run_report"] == str(payload["paths"]["run_report"])
    assert index_rows[-1]["quality_examples_count"] == 5


def test_quality_loop_replay_index_keeps_distinct_run_reports(tmp_path):
    report_dir = tmp_path / "loop_reports"
    index_path = tmp_path / "loop-index.jsonl"

    first_payload = run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_history_001",
        min_overall=95,
    )
    second_payload = run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_history_002",
        min_overall=95,
    )

    index_rows = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert len(index_rows) == 2
    assert index_rows[0]["run_report"] == str(first_payload["paths"]["run_report"])
    assert index_rows[1]["run_report"] == str(second_payload["paths"]["run_report"])
    assert index_rows[0]["run_report"] != index_rows[1]["run_report"]
    assert first_payload["paths"]["run_report"].exists()
    assert second_payload["paths"]["run_report"].exists()


def test_quality_loop_history_summarizes_replay_index_with_reports(tmp_path):
    report_dir = tmp_path / "loop_reports"
    index_path = tmp_path / "loop-index.jsonl"

    run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_history_001",
        min_overall=95,
    )
    run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_history_002",
        min_overall=95,
    )

    summary = summarize_loop_history(index_path)
    markdown_path = tmp_path / "history.md"
    write_loop_history_markdown(summary, markdown_path)

    markdown = markdown_path.read_text(encoding="utf-8")
    assert summary["schema_version"] == "xhs_quality_loop_history.v1"
    assert summary["run_count"] == 2
    assert summary["latest_run_id"] == "loop_history_002"
    assert summary["runs"][0]["run_id"] == "loop_history_001"
    assert summary["runs"][1]["quality_examples_delta"] == 0
    assert summary["runs"][1]["report_exists"] is True
    assert summary["totals"]["quality_examples_count"] == 10
    assert summary["diagnostics"]["schema_version"] == "xhs_quality_loop_diagnostics.v1"
    assert summary["diagnostics"]["issue_groups"][0]["issue_id"] == "baseline_overall_below_threshold"
    assert summary["diagnostics"]["issue_groups"][0]["priority"] == 1
    assert summary["diagnostics"]["issue_groups"][0]["affected_run_ids"] == [
        "loop_history_001",
        "loop_history_002",
    ]
    assert summary["diagnostics"]["next_actions"][0]["issue_id"] == "baseline_overall_below_threshold"
    assert "| loop_history_002 |" in markdown
    assert "## Diagnostics" in markdown
    assert "baseline_overall_below_threshold" in markdown
    assert "xhs_quality_loop_history.v1" in markdown


def test_quality_loop_history_diagnoses_missing_run_report(tmp_path):
    index_path = tmp_path / "loop-index.jsonl"
    missing_report = tmp_path / "missing-run-report.json"
    index_path.write_text(
        json.dumps({
            "schema_version": "xhs_quality_loop_index.v1",
            "run_id": "missing_report_001",
            "created_at": "2026-06-03T17:00:00Z",
            "run_report": str(missing_report),
            "evaluation_case_count": 5,
            "baseline_failed_count": 0,
            "revision_request_count": 0,
            "re_evaluation_candidate_count": 0,
            "quality_examples_count": 0,
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    summary = summarize_loop_history(index_path)

    assert summary["runs"][0]["report_exists"] is False
    assert summary["diagnostics"]["issue_groups"][0]["issue_id"] == "missing_run_report"
    assert summary["diagnostics"]["issue_groups"][0]["severity"] == "high"
    assert summary["diagnostics"]["next_actions"][0]["action"].startswith("恢复或重跑")


def test_quality_loop_cli_runs_dry_run_end_to_end(tmp_path):
    report_dir = tmp_path / "loop_reports"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_loop.py",
            "--report-dir",
            str(report_dir),
            "--run-id",
            "loop_cli_001",
            "--min-overall",
            "95",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    quality_examples_path = report_dir / "xhs-quality-prompt-examples.jsonl"
    quality_examples = [
        json.loads(line)
        for line in quality_examples_path.read_text(encoding="utf-8").splitlines()
    ]
    assert payload["run_id"] == "loop_cli_001"
    assert payload["revision"]["request_count"] == 5
    assert payload["re_evaluation"]["candidate_count"] == 5
    assert payload["quality_examples"]["count"] == 5
    assert payload["paths"]["quality_examples"] == str(quality_examples_path)
    assert len(quality_examples) == 5


def test_quality_loop_cli_writes_replay_index(tmp_path):
    report_dir = tmp_path / "loop_reports"
    index_path = tmp_path / "loop-index.jsonl"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_loop.py",
            "--report-dir",
            str(report_dir),
            "--replay-index",
            str(index_path),
            "--run-id",
            "loop_index_cli_001",
            "--min-overall",
            "95",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    index_rows = [
        json.loads(line)
        for line in index_path.read_text(encoding="utf-8").splitlines()
    ]
    assert payload["paths"]["replay_index"] == str(index_path)
    assert payload["paths"]["run_report"].endswith("xhs-quality-loop-run.json")
    assert index_rows[-1]["run_id"] == "loop_index_cli_001"
    assert index_rows[-1]["run_report"] == payload["paths"]["run_report"]


def test_quality_loop_history_cli_writes_markdown(tmp_path):
    report_dir = tmp_path / "loop_reports"
    index_path = tmp_path / "loop-index.jsonl"
    markdown_path = tmp_path / "history.md"

    run_quality_loop(
        cases_path="tests/fixtures/xhs_quality_cases.json",
        report_dir=report_dir,
        replay_index_path=index_path,
        run_id="loop_history_cli_001",
        min_overall=95,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_xhs_quality_loop.py",
            "--replay-index",
            str(index_path),
            "--markdown",
            str(markdown_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["summary"]["run_count"] == 1
    assert payload["summary"]["diagnostics"]["issue_groups"][0]["issue_id"] == "baseline_overall_below_threshold"
    assert payload["markdown"] == str(markdown_path)
    assert "## Diagnostics" in markdown
    assert "loop_history_cli_001" in markdown


def test_revision_plan_cli_writes_revision_requests(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--case-library",
            str(library_path),
            "--run-id",
            "eval_cli_001",
            "--min-overall",
            "95",
            "--report-only",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout)["case_library"]["saved_count"] == 5
    requests_path = tmp_path / "revision_requests.jsonl"

    planned = subprocess.run(
        [
            sys.executable,
            "scripts/plan_xhs_revisions.py",
            "--library",
            str(library_path),
            "--requests-jsonl",
            str(requests_path),
            "--run-id",
            "revision_cli_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(planned.stdout)
    requests = load_revision_requests(requests_path)
    assert payload["candidate_count"] == 5
    assert payload["requests_jsonl"] == str(requests_path)
    assert len(requests) == 5
    assert requests[0]["run_id"] == "revision_cli_001"


def test_revision_plan_cli_applies_revision_results_to_case_library(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_cli_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    save_case_records(source_records, library_path)
    results_path = tmp_path / "revision_results.jsonl"
    write_revision_results(
        [
            {
                "schema_version": "xhs_revision_result.v1",
                "request_id": "revision_cli_001:eval_cli_001:coffee_beginner",
                "source_record_id": "eval_cli_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题"],
                    "copywriting": "改后正文",
                    "tags": ["改后标签"],
                    "revision_summary": ["强化开头钩子"],
                },
            }
        ],
        results_path,
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/plan_xhs_revisions.py",
            "--library",
            str(library_path),
            "--apply-results-jsonl",
            str(results_path),
            "--append-revised-cases",
            "--run-id",
            "revision_cli_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    records = load_case_records(library_path)
    loaded_results = load_revision_results(results_path)
    assert payload["applied_results_count"] == 1
    assert payload["revised_case_library"]["saved_count"] == 1
    assert payload["revised_case_library"]["library_count"] == 2
    assert len(records) == 2
    assert len(loaded_results) == 1
    assert records[-1]["record_id"] == "revision_cli_001:eval_cli_001:coffee_beginner:revised"
    assert records[-1]["content"]["copywriting"] == "改后正文"


def test_re_evaluation_cli_updates_revised_cases_and_writes_reports(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"
    source_records = build_case_records(
        [
            {
                "case_id": "coffee_beginner",
                "category": "知识科普",
                "topic": "新手如何学会手冲咖啡",
                "trace_id": "quality_trace_1",
                "titles": ["原标题"],
                "copywriting": "原正文",
                "tags": ["咖啡"],
                "overall": 79,
                "decision": "revise",
                "issues_count": 1,
                "suggestions_count": 2,
                "baseline_passed": False,
                "baseline_reason": "overall 79 below 80",
                "trend_passed": True,
                "trend_reason": "",
                "error": None,
            }
        ],
        run_id="eval_cli_001",
        source="xhs_quality_eval",
        created_at="2026-06-03T12:00:00Z",
    )
    revised_records = build_revised_case_records(
        source_records,
        [
            {
                "request_id": "revision_cli_001:eval_cli_001:coffee_beginner",
                "source_record_id": "eval_cli_001:coffee_beginner",
                "success": True,
                "trace_id": "revision_trace_1",
                "revision": {
                    "titles": ["改后标题"],
                    "copywriting": "改后正文",
                    "tags": ["改后标签"],
                    "revision_summary": ["强化开头钩子"],
                },
            }
        ],
        run_id="revision_cli_001",
        created_at="2026-06-04T13:00:00Z",
    )
    save_case_records(source_records + revised_records, library_path)
    jsonl_path = tmp_path / "re_eval.jsonl"
    markdown_path = tmp_path / "re_eval.md"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_re_evaluation.py",
            "--library",
            str(library_path),
            "--jsonl",
            str(jsonl_path),
            "--markdown",
            str(markdown_path),
            "--run-id",
            "reeval_cli_001",
            "--update-case-library",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    records = load_case_records(library_path)
    jsonl_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    markdown = markdown_path.read_text(encoding="utf-8")
    assert payload["candidate_count"] == 1
    assert payload["comparison"]["passed"] is True
    assert payload["case_library"]["updated_count"] == 1
    assert records[-1]["quality"]["decision"] == "approve"
    assert records[-1]["revision_meta"]["re_evaluation"]["run_id"] == "reeval_cli_001"
    assert jsonl_rows[0]["schema_version"] == "xhs_re_evaluation_result.v1"
    assert "| revision_cli_001:eval_cli_001:coffee_beginner:revised |" in markdown


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


def test_cli_exits_nonzero_when_trend_comparison_fails(tmp_path):
    previous_path = tmp_path / "previous.jsonl"
    previous_path.write_text(
        json.dumps({"case_id": "coffee_beginner", "overall": 95}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_xhs_quality_eval.py",
            "--compare-jsonl",
            str(previous_path),
            "--max-score-drop",
            "3",
        ],
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["baseline"]["passed"] is True
    assert payload["comparison"]["passed"] is False
    assert payload["comparison"]["failed_count"] == 1
    assert payload["results"][0]["trend_passed"] is False


def test_make_eval_quality_runs_dry_run_report(tmp_path):
    completed = subprocess.run(
        [
            "make",
            "eval-quality",
            f"REPORT_DIR={tmp_path}",
            f"PYTHON={sys.executable}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["baseline"]["passed"] is True
    assert (tmp_path / "xhs-quality-eval.jsonl").exists()
    assert (tmp_path / "xhs-quality-eval.md").exists()


def test_make_eval_quality_can_append_case_library(tmp_path):
    library_path = tmp_path / "content_cases.jsonl"

    completed = subprocess.run(
        [
            "make",
            "eval-quality",
            f"REPORT_DIR={tmp_path}",
            f"PYTHON={sys.executable}",
            f"EVAL_CASE_LIBRARY={library_path}",
            "EVAL_RUN_ID=make_eval_001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    records = load_case_records(library_path)
    assert payload["case_library"]["saved_count"] == 5
    assert records[0]["run_id"] == "make_eval_001"


def test_make_eval_quality_can_compare_previous_report(tmp_path):
    previous_path = tmp_path / "previous.jsonl"
    previous_path.write_text(
        json.dumps({"case_id": "coffee_beginner", "overall": 95}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "make",
            "eval-quality",
            f"REPORT_DIR={tmp_path}",
            f"PYTHON={sys.executable}",
            f"EVAL_PREVIOUS={previous_path}",
            "EVAL_MAX_SCORE_DROP=3",
        ],
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode != 0
    assert payload["baseline"]["passed"] is True
    assert payload["comparison"]["passed"] is False
    assert payload["comparison"]["failed_count"] == 1
