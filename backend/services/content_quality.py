"""
Content quality helpers for Xiaohongshu note generation.

This module contains deterministic helpers only. It does not call models.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List


QUALITY_SCORE_KEYS = [
    "overall",
    "topic_clarity",
    "hook_strength",
    "information_density",
    "user_value",
    "xhs_style_fit",
    "originality",
    "title_strength",
    "copy_readability",
    "tag_fit",
    "cover_readability",
    "compliance_risk",
]

DECISIONS = {"approve", "revise", "block"}


def create_trace_id(prefix: str = "xhs") -> str:
    """Create a compact trace id for one content generation run."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def summarize_text(text: str, max_chars: int = 160) -> str:
    """Return a compact single-line summary for logs and history records."""
    if not text:
        return ""
    compact = " ".join(str(text).split())
    return compact[:max_chars]


def _clamp_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _has_invalid_score(raw: Dict[str, Any]) -> bool:
    for key in QUALITY_SCORE_KEYS:
        if key not in raw:
            continue
        try:
            score = float(raw[key])
        except (TypeError, ValueError):
            return True
        if score < 0 or score > 100:
            return True
    return False


def _normalize_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def normalize_quality_score(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize model output into a stable QualityScore shape."""
    normalized: Dict[str, Any] = {}
    has_invalid_score = _has_invalid_score(raw)

    for key in QUALITY_SCORE_KEYS:
        normalized[key] = _clamp_score(raw.get(key, 0))

    requested_decision = str(raw.get("decision", "revise")).strip().lower()
    if requested_decision not in DECISIONS:
        requested_decision = "revise"

    if normalized["compliance_risk"] >= 80 or normalized["overall"] < 40:
        decision = "block"
    elif (
        requested_decision == "approve"
        and normalized["overall"] >= 75
        and normalized["compliance_risk"] <= 35
        and not has_invalid_score
    ):
        decision = "approve"
    elif requested_decision == "block":
        decision = "block"
    else:
        decision = "revise"

    normalized["decision"] = decision
    normalized["issues"] = _normalize_string_list(raw.get("issues"))
    normalized["suggestions"] = _normalize_string_list(raw.get("suggestions"))

    return normalized


def build_publish_gate(
    quality_score: Dict[str, Any],
    has_assets: bool,
    has_title: bool,
    has_copywriting: bool,
    has_tags: bool,
) -> Dict[str, bool]:
    """Build the publish gate metadata saved with a history record."""
    decision = quality_score.get("decision")
    risk_checked = quality_score.get("compliance_risk", 100) < 80
    ready = all([has_assets, has_title, has_copywriting, has_tags, risk_checked])

    return {
        "enabled": bool(ready and decision == "approve"),
        "requires_user_confirm": True,
        "assets_ready": bool(has_assets),
        "title_ready": bool(has_title),
        "copy_ready": bool(has_copywriting),
        "tags_ready": bool(has_tags),
        "risk_checked": bool(risk_checked),
    }
