"""
Quality evaluation service for generated Xiaohongshu content.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from backend.services.content_quality import (
    build_publish_gate,
    create_trace_id,
    normalize_quality_score,
)
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class QualityService:
    def __init__(
        self,
        client: Optional[Any] = None,
        text_config: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
    ):
        self.text_config = text_config or self._load_text_config()
        self.client = client or self._get_client()
        self.prompt_template = prompt_template or self._load_prompt_template()

    def _load_text_config(self) -> Dict[str, Any]:
        config_path = Path(__file__).parent.parent.parent / "text_providers.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        return {
            "active_provider": "google_gemini",
            "providers": {
                "google_gemini": {
                    "type": "google_gemini",
                    "model": "gemini-2.0-flash-exp",
                    "temperature": 0.2,
                    "max_output_tokens": 2000,
                }
            },
        }

    def _get_client(self):
        active_provider = self.text_config.get("active_provider", "google_gemini")
        providers = self.text_config.get("providers", {})
        if active_provider not in providers:
            available = ", ".join(providers.keys())
            raise ValueError(f"未找到文本生成服务商配置: {active_provider}，可用服务商: {available}")

        provider_config = providers[active_provider]
        if not provider_config.get("api_key"):
            raise ValueError(f"文本服务商 {active_provider} 未配置 API Key")

        return get_text_chat_client(provider_config)

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "quality_prompt.txt",
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        json_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", response_text)
        if json_match:
            return json.loads(json_match.group(1).strip())

        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            return json.loads(response_text[start_idx:end_idx + 1])

        raise ValueError("AI 返回的质量评分不是有效 JSON")

    def _provider_config(self) -> Dict[str, Any]:
        active_provider = self.text_config.get("active_provider", "google_gemini")
        return self.text_config.get("providers", {}).get(active_provider, {})

    def evaluate_content(
        self,
        topic: str,
        outline: str,
        titles: List[str],
        copywriting: str,
        tags: List[str],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not topic:
            raise ValueError("topic 不能为空")
        if not outline:
            raise ValueError("outline 不能为空")
        if not titles:
            raise ValueError("titles 不能为空")
        if not copywriting:
            raise ValueError("copywriting 不能为空")

        current_trace_id = trace_id or create_trace_id()
        prompt = self.prompt_template.format(
            topic=topic,
            outline=outline,
            titles="\n".join(titles),
            copywriting=copywriting,
            tags=" ".join([f"#{tag}" for tag in tags]),
        )

        provider_config = self._provider_config()
        response_text = self.client.generate_text(
            prompt=prompt,
            model=provider_config.get("model", "gemini-2.0-flash-exp"),
            temperature=provider_config.get("temperature", 0.2),
            max_output_tokens=provider_config.get("max_output_tokens", 2000),
        )

        raw_score = self._parse_json_response(response_text)
        quality_score = normalize_quality_score(raw_score)
        publish_gate = build_publish_gate(
            quality_score=quality_score,
            has_assets=False,
            has_title=bool(titles),
            has_copywriting=bool(copywriting),
            has_tags=bool(tags),
        )

        logger.info(
            "质量评分完成 trace_id=%s overall=%s decision=%s",
            current_trace_id,
            quality_score["overall"],
            quality_score["decision"],
        )

        return {
            "success": True,
            "trace_id": current_trace_id,
            "evaluated_at": datetime.now().isoformat(),
            "quality_score": quality_score,
            "publish_gate": publish_gate,
        }


_quality_service = None


def get_quality_service() -> QualityService:
    global _quality_service
    if _quality_service is None:
        _quality_service = QualityService()
    return _quality_service
