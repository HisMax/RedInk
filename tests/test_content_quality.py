from backend.services.content_quality import (
    QUALITY_SCORE_KEYS,
    build_publish_gate,
    create_trace_id,
    normalize_quality_score,
    summarize_text,
)


def test_create_trace_id_has_prefix_and_unique_suffix():
    trace_id = create_trace_id()

    assert trace_id.startswith("xhs_")
    assert len(trace_id) > len("xhs_")


def test_summarize_text_trims_long_content():
    text = "A" * 130

    assert summarize_text(text, max_chars=20) == "A" * 20


def test_normalize_quality_score_fills_missing_fields_and_clamps_values():
    result = normalize_quality_score({
        "overall": 120,
        "hook_strength": -10,
        "decision": "approve",
        "issues": ["标题太泛"],
        "suggestions": ["增加具体利益点"]
    })

    assert result["overall"] == 100
    assert result["hook_strength"] == 0
    assert result["decision"] == "revise"
    assert result["issues"] == ["标题太泛"]
    assert result["suggestions"] == ["增加具体利益点"]
    for key in QUALITY_SCORE_KEYS:
        assert key in result


def test_normalize_quality_score_blocks_high_compliance_risk():
    result = normalize_quality_score({
        "overall": 88,
        "compliance_risk": 85,
        "decision": "approve"
    })

    assert result["decision"] == "block"


def test_build_publish_gate_requires_approved_quality_and_assets():
    quality = normalize_quality_score({
        "overall": 82,
        "compliance_risk": 20,
        "decision": "approve"
    })

    gate = build_publish_gate(
        quality_score=quality,
        has_assets=True,
        has_title=True,
        has_copywriting=True,
        has_tags=True,
    )

    assert gate["enabled"] is True
    assert gate["requires_user_confirm"] is True
    assert gate["risk_checked"] is True


def test_build_publish_gate_stays_closed_when_quality_requires_revision():
    quality = normalize_quality_score({
        "overall": 61,
        "compliance_risk": 20,
        "decision": "revise"
    })

    gate = build_publish_gate(
        quality_score=quality,
        has_assets=True,
        has_title=True,
        has_copywriting=True,
        has_tags=True,
    )

    assert gate["enabled"] is False
