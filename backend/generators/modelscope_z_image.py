import logging
import re
import time
from typing import Dict, Any, Optional, List

import requests

from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


class ModelScopeZImageGenerator(ImageGeneratorBase):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        base_url = (config.get('base_url') or 'https://api-inference.modelscope.cn').strip().rstrip('/')
        endpoint_type = (config.get('endpoint_type') or '/v1/images/generations').strip()
        if not endpoint_type.startswith('/'):
            endpoint_type = '/' + endpoint_type

        version_match = re.search(r'^/(v\d+)', endpoint_type)
        if version_match:
            version_prefix = '/' + version_match.group(1)
            if base_url.endswith(version_prefix):
                base_url = base_url[:-len(version_prefix)].rstrip('/')
        elif base_url.endswith('/v1') and endpoint_type.startswith('/v1'):
            base_url = base_url[:-3].rstrip('/')

        self.base_url = base_url
        self.endpoint_type = endpoint_type

        self.model = config.get('model') or 'Tongyi-MAI/Z-Image-Turbo'
        self.task_endpoint = (config.get('task_endpoint') or '/v1/tasks').strip()
        if not self.task_endpoint.startswith('/'):
            self.task_endpoint = '/' + self.task_endpoint

        self.poll_interval_seconds = float(config.get('poll_interval_seconds') or 3)
        self.max_wait_seconds = float(config.get('max_wait_seconds') or 300)
        self.max_prompt_chars = int(config.get('max_prompt_chars') or 1900)

        logger.info(
            f"ModelScopeZImageGenerator 初始化完成: base_url={self.base_url}, model={self.model}, endpoint={self.endpoint_type}"
        )

    def _normalize_prompt(self, prompt: str) -> str:
        text = (prompt or "").strip()
        max_chars = self.max_prompt_chars
        if max_chars < 100:
            max_chars = 100
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip()

    def validate_config(self) -> bool:
        if not self.api_key:
            raise ValueError(
                "ModelScope API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        if not self.base_url:
            raise ValueError(
                "ModelScope Base URL 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 Base URL（例如 https://api-inference.modelscope.cn）"
            )
        return True

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ) -> bytes:
        self.validate_config()

        model_id = (model or self.model).strip()
        if not model_id:
            raise ValueError(
                "ModelScope 模型未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写模型（例如 Tongyi-MAI/Z-Image-Turbo）"
            )

        normalized_prompt = self._normalize_prompt(prompt)
        create_url = f"{self.base_url}{self.endpoint_type}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Async-Mode": "true",
        }
        payload: Dict[str, Any] = {
            "model": model_id,
            "prompt": normalized_prompt,
            "n": 1,
            "size": kwargs.get("size") or self.config.get("size") or "1024x1024",
        }

        logger.info(f"ModelScope Z-Image 提交任务: model={model_id}, url={create_url}")
        response = requests.post(create_url, headers=headers, json=payload, timeout=60)

        if response.status_code != 200:
            detail = response.text[:800]
            raise Exception(
                f"ModelScope 图片生成请求失败 (状态码: {response.status_code})\n"
                f"请求地址: {create_url}\n"
                f"错误详情: {detail}"
            )

        data = response.json() or {}
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            raise Exception(
                "ModelScope 响应中未找到 task_id。\n"
                f"响应片段: {str(data)[:800]}"
            )

        task_url = f"{self.base_url}{self.task_endpoint}/{task_id}"
        status_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-ModelScope-Task-Type": "image_generation",
        }

        deadline = time.time() + self.max_wait_seconds
        last_status: Optional[str] = None
        while True:
            if time.time() > deadline:
                raise Exception(
                    f"ModelScope 任务超时（{self.max_wait_seconds}s）。task_id={task_id}, last_status={last_status}"
                )

            status_resp = requests.get(task_url, headers=status_headers, timeout=60)
            if status_resp.status_code != 200:
                detail = status_resp.text[:800]
                raise Exception(
                    f"ModelScope 任务查询失败 (状态码: {status_resp.status_code})\n"
                    f"请求地址: {task_url}\n"
                    f"错误详情: {detail}"
                )

            task_data = status_resp.json() or {}
            task_status = (task_data.get("task_status") or task_data.get("status") or "").upper()
            last_status = task_status or last_status

            if task_status == "SUCCEED":
                output_images = task_data.get("output_images") or []
                if not isinstance(output_images, list) or not output_images:
                    raise Exception(
                        "ModelScope 任务成功但未返回图片地址。\n"
                        f"响应片段: {str(task_data)[:800]}"
                    )
                image_url = output_images[0]
                if not isinstance(image_url, str) or not image_url.strip():
                    raise Exception(
                        "ModelScope 返回的图片地址无效。\n"
                        f"响应片段: {str(task_data)[:800]}"
                    )
                img_resp = requests.get(image_url, timeout=120)
                if img_resp.status_code != 200:
                    raise Exception(
                        f"下载图片失败 (状态码: {img_resp.status_code})\n"
                        f"图片地址: {image_url}\n"
                        f"错误详情: {img_resp.text[:200]}"
                    )
                return img_resp.content

            if task_status == "FAILED":
                error_msg = (
                    task_data.get("message")
                    or task_data.get("error")
                    or task_data.get("output")
                    or "未知错误"
                )
                raise Exception(f"ModelScope 图片生成失败: {error_msg}")

            time.sleep(self.poll_interval_seconds)
