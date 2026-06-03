from backend.services.history import HistoryService


def test_create_record_initializes_quality_metadata(tmp_path):
    service = HistoryService()
    service.history_dir = str(tmp_path)
    service.index_file = str(tmp_path / "index.json")
    service._init_index()

    record_id = service.create_record(
        topic="手冲咖啡教程",
        outline={"raw": "大纲", "pages": []},
        task_id=None,
        trace_id="xhs_hist123",
        content={
            "titles": ["标题"],
            "copywriting": "正文",
            "tags": ["标签"]
        },
        quality={
            "quality_score": {"overall": 80, "decision": "approve"},
            "publish_gate": {"enabled": False}
        },
    )

    record = service.get_record(record_id)
    assert record["trace_id"] == "xhs_hist123"
    assert record["content"]["titles"] == ["标题"]
    assert record["quality"]["quality_score"]["overall"] == 80
    assert record["revision_history"] == []


def test_update_record_persists_quality_and_revision_history(tmp_path):
    service = HistoryService()
    service.history_dir = str(tmp_path)
    service.index_file = str(tmp_path / "index.json")
    service._init_index()
    record_id = service.create_record(
        topic="手冲咖啡教程",
        outline={"raw": "大纲", "pages": []},
        task_id=None,
    )

    success = service.update_record(
        record_id,
        trace_id="xhs_update123",
        content={
            "titles": ["新标题"],
            "copywriting": "新正文",
            "tags": ["新标签"]
        },
        quality={
            "quality_score": {"overall": 72, "decision": "revise"},
            "publish_gate": {"enabled": False}
        },
        revision_entry={
            "titles": ["新标题"],
            "revision_summary": ["提升标题具体度"]
        },
    )

    assert success is True
    record = service.get_record(record_id)
    assert record["trace_id"] == "xhs_update123"
    assert record["content"]["copywriting"] == "新正文"
    assert record["quality"]["quality_score"]["decision"] == "revise"
    assert record["revision_history"][0]["revision_summary"] == ["提升标题具体度"]
