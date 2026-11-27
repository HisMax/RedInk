"""Atlas Cloud Media API image generator."""
import base64
import logging
import time
from typing import Any, Dict, Optional

import requests

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


class AtlasCloudImageGenerator(ImageGeneratorBase):
    """Generate images through the Atlas Cloud asynchronous Media API."""

    DEFAULT_BASE_URL = "https://api.atlascloud.ai/api/v1"
    DEFAULT_MODEL = "bytedance/seedream-v5.0-lite"
    DEFAULT_SIZE = "1728*2304"
    DEFAULT_OUTPUT_FORMAT = "png"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = (config.get("base_url") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = config.get("model") or self.DEFAULT_MODEL
        self.size = config.get("size") or config.get("image_size") or self.DEFAULT_SIZE
        self.output_format = config.get("output_format") or self.DEFAULT_OUTPUT_FORMAT
        self.poll_interval_seconds = _non_negative_float(
            config.get("poll_interval_seconds"),
            default=3.0,
        )
        self.max_poll_attempts = _positive_int(
            config.get("max_poll_attempts"),
            default=120,
        )
        self.session = requests.Session()

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError(
                "Atlas Cloud API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        return True

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs,
    ) -> bytes:
        """Submit an Atlas Cloud image task, poll for completion, then download the image."""
        self.validate_config()

        request_model = model or self.model
        payload = {
            "model": request_model,
            "prompt": prompt,
            "size": kwargs.get("size") or self.size,
            "output_format": kwargs.get("output_format") or self.output_format,
            "enable_base64_output": bool(kwargs.get("enable_base64_output", False)),
        }

        logger.info(f"Atlas Cloud 生成图片: model={request_model}, size={payload['size']}")
        prediction = self._submit_task(payload)
        outputs = self._poll_outputs(prediction["id"])
        return self._read_output(outputs[0])

    def _submit_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/model/generateImage",
            headers=self._headers(),
            json=payload,
            timeout=60,
        )
        if response.status_code != 200:
            raise Exception(f"Atlas Cloud 提交任务失败: HTTP {response.status_code}: {response.text[:500]}")

        data = _unwrap_data(response.json())
        request_id = data.get("id") or data.get("request_id")
        if not request_id:
            raise Exception(f"Atlas Cloud 提交响应缺少任务 ID: {str(data)[:500]}")
        return {"id": request_id}

    def _poll_outputs(self, request_id: str) -> list[str]:
        last_status = ""
        for attempt in range(self.max_poll_attempts):
            response = self._get_prediction_response(request_id)
            if response.status_code != 200:
                raise Exception(f"Atlas Cloud 查询任务失败: HTTP {response.status_code}: {response.text[:500]}")

            data = _unwrap_data(response.json())
            last_status = str(data.get("status") or "").lower()
            outputs = data.get("outputs") or data.get("output") or []
            if isinstance(outputs, str):
                outputs = [outputs]

            if last_status in {"completed", "succeeded", "success"} and outputs:
                return outputs
            if last_status in {"failed", "canceled", "cancelled"}:
                raise Exception(f"Atlas Cloud 图片任务失败: {str(data)[:500]}")

            if attempt < self.max_poll_attempts - 1:
                time.sleep(self.poll_interval_seconds)

        raise Exception(f"Atlas Cloud 图片任务超时，最后状态: {last_status or 'unknown'}")

    def _get_prediction_response(self, request_id: str):
        response = self.session.get(
            f"{self.base_url}/model/result/{request_id}",
            headers=self._headers(),
            timeout=60,
        )
        if response.status_code != 404:
            return response
        return self.session.get(
            f"{self.base_url}/model/prediction/{request_id}",
            headers=self._headers(),
            timeout=60,
        )

    def _read_output(self, output: str) -> bytes:
        if output.startswith("data:image"):
            return base64.b64decode(output.split(",", 1)[1])
        if _looks_like_base64(output):
            return base64.b64decode(output)

        response = self.session.get(output, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Atlas Cloud 图片下载失败: HTTP {response.status_code}")
        return response.content

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


def _unwrap_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def _looks_like_base64(value: str) -> bool:
    stripped = value.strip()
    return bool(stripped) and not stripped.startswith(("http://", "https://"))


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _non_negative_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
        return parsed if parsed >= 0 else default
    except (TypeError, ValueError):
        return default
