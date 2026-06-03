def test_quality_evaluate_route_returns_score(client, monkeypatch):
    class FakeQualityService:
        def evaluate_content(self, **kwargs):
            return {
                "success": True,
                "trace_id": kwargs.get("trace_id") or "xhs_route123",
                "quality_score": {
                    "overall": 82,
                    "compliance_risk": 20,
                    "decision": "approve",
                    "issues": [],
                    "suggestions": []
                },
                "publish_gate": {
                    "enabled": False,
                    "requires_user_confirm": True,
                    "assets_ready": False,
                    "title_ready": True,
                    "copy_ready": True,
                    "tags_ready": True,
                    "risk_checked": True
                }
            }

    monkeypatch.setattr(
        "backend.routes.quality_routes.get_quality_service",
        lambda: FakeQualityService(),
    )

    response = client.post("/api/quality/evaluate", json={
        "topic": "手冲咖啡教程",
        "outline": "大纲",
        "titles": ["5分钟学会手冲咖啡"],
        "copywriting": "正文",
        "tags": ["咖啡"],
        "trace_id": "xhs_route123"
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["trace_id"] == "xhs_route123"
    assert data["quality_score"]["decision"] == "approve"


def test_quality_evaluate_route_validates_required_fields(client):
    response = client.post("/api/quality/evaluate", json={
        "topic": "",
        "outline": "大纲",
        "titles": ["标题"],
        "copywriting": "正文",
        "tags": ["标签"]
    })

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_quality_revise_route_returns_revision(client, monkeypatch):
    class FakeRevisionService:
        def suggest_revisions(self, **kwargs):
            return {
                "success": True,
                "trace_id": kwargs.get("trace_id") or "xhs_revroute",
                "revision": {
                    "titles": ["新标题"],
                    "copywriting": "新正文",
                    "tags": ["新标签"],
                    "revision_summary": ["增强标题利益点"]
                }
            }

    monkeypatch.setattr(
        "backend.routes.quality_routes.get_revision_service",
        lambda: FakeRevisionService(),
    )

    response = client.post("/api/quality/revise", json={
        "topic": "手冲咖啡教程",
        "outline": "大纲",
        "titles": ["旧标题"],
        "copywriting": "旧正文",
        "tags": ["咖啡"],
        "quality_score": {
            "issues": ["标题太泛"],
            "suggestions": ["增加利益点"]
        },
        "trace_id": "xhs_revroute"
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["revision"]["titles"] == ["新标题"]
