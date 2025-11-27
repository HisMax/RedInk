"""OpenAI 兼容接口图片生成器"""
import logging
import time
import random
import base64
from functools import wraps
from typing import Dict, Any
import requests
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


def retry_on_error(max_retries=5, base_delay=3):
    """错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    # 检查是否是速率限制错误
                    if "429" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            logger.warning(f"遇到速率限制，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    # 其他错误或重试耗尽
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.warning(f"请求失败: {error_str[:100]}，{wait_time}秒后重试")
                        time.sleep(wait_time)
                        continue
                    raise
            logger.error(f"图片生成失败: 重试 {max_retries} 次后仍失败")
            raise Exception(
                f"图片生成失败：重试 {max_retries} 次后仍失败。\n"
                "可能原因：\n"
                "1. API持续限流或配额不足\n"
                "2. 网络连接持续不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或检查API配额和网络状态"
            )
        return wrapper
    return decorator


class OpenAICompatibleGenerator(ImageGeneratorBase):
    """OpenAI 兼容接口图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 OpenAICompatibleGenerator...")

        if not self.api_key:
            logger.error("OpenAI 兼容 API Key 未配置")
            raise ValueError(
                "OpenAI 兼容 API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        if not self.base_url:
            logger.error("OpenAI 兼容 API Base URL 未配置")
            raise ValueError(
                "OpenAI 兼容 API Base URL 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 Base URL"
            )

        # 规范化 base_url：去除末尾 /v1
        self.base_url = self.base_url.rstrip('/').rstrip('/v1')

        # 默认模型
        self.default_model = config.get('model', 'dall-e-3')

        # API 端点类型: 'images' 或 'chat'
        self.endpoint_type = config.get('endpoint_type', 'images')

        logger.info(f"OpenAICompatibleGenerator 初始化完成: base_url={self.base_url}, model={self.default_model}, endpoint={self.endpoint_type}")

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key and self.base_url)

    @retry_on_error(max_retries=5, base_delay=3)
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        model: str = None,
        quality: str = "standard",
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            size: 图片尺寸 (如 "1024x1024", "2048x2048", "4096x4096")
            model: 模型名称
            quality: 质量 ("standard" 或 "hd")
            **kwargs: 其他参数

        Returns:
            图片二进制数据
        """
        if model is None:
            model = self.default_model

        logger.info(f"OpenAI 兼容 API 生成图片: model={model}, size={size}, endpoint={self.endpoint_type}")

        if self.endpoint_type == 'images':
            return self._generate_via_images_api(prompt, size, model, quality)
        elif self.endpoint_type == 'chat':
            return self._generate_via_chat_api(prompt, size, model)
        else:
            logger.error(f"不支持的端点类型: {self.endpoint_type}")
            raise ValueError(
                f"不支持的端点类型: {self.endpoint_type}\n"
                "支持的类型: images, chat\n"
                "解决方案：\n"
                "在 image_providers.yaml 中设置正确的 endpoint_type\n"
                "- 'images': 使用 /v1/images/generations 端点 (标准)\n"
                "- 'chat': 使用 /v1/chat/completions 端点 (特殊)"
            )

    def _generate_via_images_api(
        self,
        prompt: str,
        size: str,
        model: str,
        quality: str
    ) -> bytes:
        """通过 /v1/images/generations 端点生成"""
        url = f"{self.base_url}/v1/images/generations"
        logger.debug(f"  发送请求到: {url}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"  # 使用base64格式更可靠
        }

        # 如果模型支持quality参数
        if quality and model.startswith('dall-e'):
            payload["quality"] = quality

        response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"OpenAI Images API 请求失败: status={response.status_code}, error={error_detail}")
            raise Exception(
                f"OpenAI Images API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {url}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 模型名称不正确或无权访问\n"
                "3. 请求参数不符合要求\n"
                "4. API配额已用尽\n"
                "5. Base URL配置错误\n"
                "建议：检查API密钥、base_url和模型名称配置"
            )

        result = response.json()
        logger.debug(f"  API 响应: data 长度={len(result.get('data', []))}")

        if "data" not in result or len(result["data"]) == 0:
            logger.error(f"API 未返回图片数据: {str(result)[:200]}")
            raise ValueError(
                "OpenAI API 未返回图片数据。\n"
                f"响应内容: {str(result)[:500]}\n"
                "可能原因：\n"
                "1. 提示词被安全过滤拦截\n"
                "2. 模型不支持图片生成\n"
                "3. 请求格式不正确\n"
                "建议：修改提示词或检查模型配置"
            )

        image_data = result["data"][0]

        # 处理base64格式
        if "b64_json" in image_data:
            img_bytes = base64.b64decode(image_data["b64_json"])
            logger.info(f"✅ OpenAI Images API 图片生成成功: {len(img_bytes)} bytes")
            return img_bytes

        # 处理URL格式
        elif "url" in image_data:
            logger.debug(f"  下载图片 URL...")
            img_response = requests.get(image_data["url"], timeout=60)
            if img_response.status_code == 200:
                logger.info(f"✅ OpenAI Images API 图片生成成功: {len(img_response.content)} bytes")
                return img_response.content
            else:
                logger.error(f"下载图片失败: {img_response.status_code}")
                raise Exception(f"下载图片失败: {img_response.status_code}")

        else:
            logger.error(f"无法从响应中提取图片数据: {str(image_data)[:200]}")
            raise ValueError(
                "无法从API响应中提取图片数据。\n"
                f"响应数据: {str(image_data)[:500]}\n"
                "可能原因：\n"
                "1. 响应格式不包含 b64_json 或 url 字段\n"
                "2. response_format 参数未生效\n"
                "建议：检查API文档确认图片返回格式"
            )

    def _generate_via_chat_api(
        self,
        prompt: str,
        size: str,
        model: str
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成（某些服务商使用此方式）"""
        url = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4096,
            "temperature": 1.0,
            # 尝试添加图片相关参数
            "response_format": {"type": "image"},
            "size": size
        }

        response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"OpenAI Chat API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {url}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 该服务商不支持通过 chat 端点生成图片\n"
                "3. 请求参数格式错误\n"
                "4. API配额已用尽\n"
                "建议：尝试将 endpoint_type 改为 'images' 或检查API密钥"
            )

        result = response.json()

        # 这部分需要根据具体服务商的返回格式调整
        # 假设返回格式类似OpenAI
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            # 需要根据实际返回格式解析图片数据
            # 这里是一个示例，实际需要调整
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                # 如果是base64
                if isinstance(content, str) and content.startswith("data:image"):
                    base64_data = content.split(",")[1]
                    return base64.b64decode(base64_data)

        raise ValueError(
            "无法从 Chat API 响应中提取图片数据。\n"
            f"响应内容: {str(result)[:500]}\n"
            "可能原因：\n"
            "1. 该服务商不支持通过 chat 端点生成图片\n"
            "2. 响应格式与预期不符\n"
            "建议：\n"
            "1. 尝试将 endpoint_type 改为 'images'\n"
            "2. 或联系API服务提供商确认正确的调用方式"
        )

    def get_supported_sizes(self) -> list:
        """获取支持的图片尺寸"""
        # 默认OpenAI支持的尺寸
        return self.config.get('supported_sizes', [
            "1024x1024",
            "1792x1024",
            "1024x1792",
            "2048x2048",
            "4096x4096"
        ])
