import json

import pytest

from backend.services.revision import RevisionService


class FakeTextClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def generate_text(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def test_suggest_revisions_returns_revised_content():
    client = FakeTextClient(json.dumps({
        "titles": ["新手手冲咖啡避坑指南", "5分钟掌握手冲咖啡", "手冲咖啡这样做更稳"],
        "copywriting": "很多新手手冲咖啡不好喝，其实问题常出在水温、粉水比和闷蒸。\n先把水温控制在92-96度，再按1:15准备咖啡粉和热水。\n最后记住闷蒸30秒，味道会稳定很多。",
        "tags": ["手冲咖啡", "咖啡新手", "咖啡教程", "居家咖啡", "咖啡知识"],
        "revision_summary": ["标题增加了新手痛点", "正文补充了具体参数"]
    }, ensure_ascii=False))
    service = RevisionService(
        client=client,
        text_config={"active_provider": "fake", "providers": {"fake": {"model": "fake-model"}}},
        prompt_template="topic={topic}\nissues={issues}\nsuggestions={suggestions}",
    )

    result = service.suggest_revisions(
        topic="手冲咖啡教程",
        outline="大纲",
        titles=["手冲咖啡教程"],
        copywriting="手冲咖啡很好喝。",
        tags=["咖啡"],
        quality_score={
            "issues": ["信息密度低"],
            "suggestions": ["补充具体参数"]
        },
        trace_id="xhs_rev123",
    )

    assert result["success"] is True
    assert result["trace_id"] == "xhs_rev123"
    assert result["revision"]["titles"][0] == "新手手冲咖啡避坑指南"
    assert result["revision"]["tags"] == ["手冲咖啡", "咖啡新手", "咖啡教程", "居家咖啡", "咖啡知识"]
    assert client.calls[0]["model"] == "fake-model"


def test_suggest_revisions_requires_quality_score():
    service = RevisionService(
        client=FakeTextClient("{}"),
        text_config={"active_provider": "fake", "providers": {"fake": {}}},
        prompt_template="unused",
    )

    with pytest.raises(ValueError, match="quality_score"):
        service.suggest_revisions(
            topic="主题",
            outline="大纲",
            titles=["标题"],
            copywriting="正文",
            tags=["标签"],
            quality_score={},
        )


def test_suggest_revisions_allows_literal_json_braces_in_prompt_template():
    client = FakeTextClient(json.dumps({
        "titles": ["新标题"],
        "copywriting": "新正文",
        "tags": ["标签"],
        "revision_summary": ["补充细节"],
    }, ensure_ascii=False))
    service = RevisionService(
        client=client,
        text_config={"active_provider": "fake", "providers": {"fake": {}}},
        prompt_template='topic={topic}\n输出格式：{\n  "titles": []\n}',
    )

    result = service.suggest_revisions(
        topic="主题",
        outline="大纲",
        titles=["标题"],
        copywriting="正文",
        tags=["标签"],
        quality_score={"issues": ["问题"], "suggestions": ["建议"]},
    )

    assert result["success"] is True
    assert '"titles": []' in client.calls[0]["prompt"]
