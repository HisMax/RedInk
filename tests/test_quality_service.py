import json

import pytest

from backend.services.quality import QualityService


class FakeTextClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_evaluate_content_returns_normalized_quality_score():
    client = FakeTextClient(json.dumps({
        "overall": 86,
        "topic_clarity": 90,
        "hook_strength": 84,
        "information_density": 80,
        "user_value": 88,
        "xhs_style_fit": 82,
        "originality": 78,
        "title_strength": 85,
        "copy_readability": 89,
        "tag_fit": 76,
        "cover_readability": 81,
        "compliance_risk": 12,
        "decision": "approve",
        "issues": [],
        "suggestions": ["封面副标题可以更具体"]
    }, ensure_ascii=False))
    service = QualityService(
        client=client,
        text_config={
            "active_provider": "fake",
            "providers": {
                "fake": {
                    "model": "fake-model",
                    "temperature": 0.2,
                    "max_output_tokens": 2000
                }
            }
        },
        prompt_template="topic={topic}\noutline={outline}\ntitles={titles}\ncopy={copywriting}\ntags={tags}",
    )

    result = service.evaluate_content(
        topic="适合新手的手冲咖啡教程",
        outline="[封面]\n手冲咖啡入门",
        titles=["5分钟学会手冲咖啡"],
        copywriting="新手也能学会的手冲咖啡步骤。",
        tags=["咖啡", "手冲咖啡"],
        trace_id="xhs_test123",
    )

    assert result["success"] is True
    assert result["trace_id"] == "xhs_test123"
    assert result["quality_score"]["overall"] == 86
    assert result["quality_score"]["decision"] == "approve"
    assert result["publish_gate"]["enabled"] is False
    assert client.calls[0]["model"] == "fake-model"


def test_evaluate_content_requires_titles_and_copywriting():
    service = QualityService(
        client=FakeTextClient("{}"),
        text_config={"active_provider": "fake", "providers": {"fake": {}}},
        prompt_template="unused",
    )

    with pytest.raises(ValueError, match="titles"):
        service.evaluate_content(
            topic="主题",
            outline="大纲",
            titles=[],
            copywriting="正文",
            tags=["标签"],
        )

    with pytest.raises(ValueError, match="copywriting"):
        service.evaluate_content(
            topic="主题",
            outline="大纲",
            titles=["标题"],
            copywriting="",
            tags=["标签"],
        )


def test_evaluate_content_extracts_json_from_markdown_block():
    client = FakeTextClient("""```json
{"overall": 70, "compliance_risk": 10, "decision": "revise", "issues": ["信息密度偏低"], "suggestions": ["增加步骤细节"]}
```""")
    service = QualityService(
        client=client,
        text_config={"active_provider": "fake", "providers": {"fake": {}}},
        prompt_template="topic={topic}",
    )

    result = service.evaluate_content(
        topic="主题",
        outline="大纲",
        titles=["标题"],
        copywriting="正文",
        tags=["标签"],
    )

    assert result["quality_score"]["decision"] == "revise"
    assert result["quality_score"]["issues"] == ["信息密度偏低"]
