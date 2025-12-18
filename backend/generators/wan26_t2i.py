"""通义万相 Wan2.6 文生图生成器"""
import logging
import base64
import requests
from typing import Dict, Any, Optional

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


def _aspect_ratio_to_size(aspect_ratio: str) -> str:
    mapping = {
        "1:1": "1280*1280",
        "2:3": "800*1200",
        "3:2": "1200*800",
        "3:4": "960*1280",
        "4:3": "1280*960",
        "9:16": "720*1280",
        "16:9": "1280*720",
        "21:9": "1344*576",
    }
    return mapping.get(aspect_ratio, "1280*1280")


def _normalize_size(size: Optional[str], aspect_ratio: str) -> str:
    if not size:
        return _aspect_ratio_to_size(aspect_ratio)

    normalized = str(size).strip().lower().replace("x", "*")
    normalized = normalized.replace("×", "*")
    parts = [p for p in normalized.split("*") if p]
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{int(parts[0])}*{int(parts[1])}"

    return _aspect_ratio_to_size(aspect_ratio)


def _extract_image_url_or_b64(data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    output = (data.get("output") or {}) if isinstance(data, dict) else {}

    results = output.get("results")
    if isinstance(results, list) and results:
        first = results[0] or {}
        if isinstance(first, dict):
            return {
                "url": first.get("url"),
                "b64": first.get("b64_json") or first.get("b64") or first.get("base64"),
            }

    choices = output.get("choices")
    if isinstance(choices, list) and choices:
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message") or {}
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    url = part.get("image") or part.get("image_url") or part.get("url")
                    b64 = part.get("b64_json") or part.get("b64") or part.get("base64")
                    if url or b64:
                        return {"url": url, "b64": b64}
            elif isinstance(content, dict):
                url = content.get("image") or content.get("image_url") or content.get("url")
                b64 = content.get("b64_json") or content.get("b64") or content.get("base64")
                if url or b64:
                    return {"url": url, "b64": b64}

    return {"url": None, "b64": None}


class Wan26T2IGenerator(ImageGeneratorBase):
    """通义万相 Wan2.6 文生图生成器（同步接口）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not self.api_key:
            raise ValueError(
                "通义万相 API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        base_url = (config.get("base_url") or "https://dashscope.aliyuncs.com/api/v1").strip()
        base_url = base_url.rstrip("/")
        if "/services/aigc/multimodal-generation/generation" in base_url:
            base_url = base_url.split("/services/aigc/multimodal-generation/generation", 1)[0].rstrip("/")
        if base_url.endswith("/api"):
            base_url = f"{base_url}/v1"
        elif "/api/" not in base_url and "dashscope" in base_url:
            base_url = f"{base_url}/api/v1"
        self.base_url = base_url
        self.endpoint_path = "/services/aigc/multimodal-generation/generation"

        self.model = config.get("model") or "wan2.6-t2i"
        self.default_aspect_ratio = config.get("default_aspect_ratio", "3:4")
        self.prompt_extend = bool(config.get("prompt_extend", True))
        self.watermark = bool(config.get("watermark", False))
        self.default_timeout_seconds = int(config.get("timeout_seconds", 120))

        logger.info(f"Wan26T2IGenerator 初始化完成: base_url={self.base_url}, model={self.model}")

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError(
                "通义万相 API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        return True

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        model: Optional[str] = None,
        size: Optional[str] = None,
        negative_prompt: str = "",
        prompt_extend: Optional[bool] = None,
        watermark: Optional[bool] = None,
        **kwargs
    ) -> bytes:
        self.validate_config()

        if not aspect_ratio:
            aspect_ratio = self.default_aspect_ratio

        if not model:
            model = self.model

        final_size = _normalize_size(size, aspect_ratio)
        final_prompt_extend = self.prompt_extend if prompt_extend is None else bool(prompt_extend)
        final_watermark = self.watermark if watermark is None else bool(watermark)

        url = f"{self.base_url}{self.endpoint_path}"
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {
                "negative_prompt": negative_prompt or "",
                "prompt_extend": final_prompt_extend,
                "watermark": final_watermark,
                "n": 1,
                "size": final_size,
            },
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(f"通义万相生成图片: model={model}, size={final_size}")
        resp = requests.post(url, headers=headers, json=payload, timeout=self.default_timeout_seconds)

        if resp.status_code != 200:
            detail = (resp.text or "")[:500]
            raise Exception(
                f"通义万相请求失败 (HTTP {resp.status_code})\n"
                f"错误详情: {detail}\n"
                f"请求地址: {url}"
            )

        data = resp.json() if resp.content else {}
        extracted = _extract_image_url_or_b64(data)
        image_url = extracted.get("url")
        b64_data = extracted.get("b64")

        if image_url:
            img_resp = requests.get(image_url, timeout=60)
            if img_resp.status_code != 200:
                raise Exception(f"通义万相图片下载失败 (HTTP {img_resp.status_code})")
            return img_resp.content

        if b64_data:
            if isinstance(b64_data, str) and b64_data.startswith("data:"):
                b64_data = b64_data.split(",", 1)[1]
            return base64.b64decode(b64_data)

        raise Exception(f"通义万相响应中未找到图片结果: {str(data)[:500]}")
