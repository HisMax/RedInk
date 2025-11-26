"""Text API 客户端封装"""
import time
import random
import base64
import requests
from functools import wraps
from typing import List, Optional, Union
from .image_compressor import compress_image


def retry_on_429(max_retries=3, base_delay=2):
    """429 错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到限流，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    raise
            raise Exception(
                f"Text API 重试 {max_retries} 次后仍失败。\n"
                "可能原因：\n"
                "1. API持续限流或配额不足\n"
                "2. 网络连接持续不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或联系API服务提供商"
            )
        return wrapper
    return decorator


class TextChatClient:
    """Text API 客户端封装类"""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(
                "Text API Key 未配置。\n"
                "解决方案：在系统设置页面编辑文本生成服务商，填写 API Key"
            )

        self.base_url = base_url or "https://api.openai.com"
        self.chat_endpoint = f"{self.base_url}/v1/chat/completions"

    def _encode_image_to_base64(self, image_data: bytes) -> str:
        """将图片数据编码为 base64"""
        return base64.b64encode(image_data).decode('utf-8')

    def _build_content_with_images(
        self,
        text: str,
        images: List[Union[bytes, str]] = None
    ) -> Union[str, List[dict]]:
        """
        构建包含图片的 content

        Args:
            text: 文本内容
            images: 图片列表，可以是 bytes（图片数据）或 str（URL）

        Returns:
            如果没有图片，返回纯文本；有图片则返回多模态内容列表
        """
        if not images:
            return text

        content = [{"type": "text", "text": text}]

        for img in images:
            if isinstance(img, bytes):
                # 压缩图片到 200KB 以内
                compressed_img = compress_image(img, max_size_kb=200)
                # 图片数据，转为 base64 data URL
                base64_data = self._encode_image_to_base64(compressed_img)
                image_url = f"data:image/png;base64,{base64_data}"
            else:
                # 已经是 URL
                image_url = img

            content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        return content

    @retry_on_429(max_retries=3, base_delay=2)
    def generate_text(
        self,
        prompt: str,
        model: str = "gemini-3-pro-preview",
        temperature: float = 1.0,
        max_output_tokens: int = 8000,
        images: List[Union[bytes, str]] = None,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        生成文本（支持图片输入）

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_output_tokens: 最大输出 token
            images: 图片列表（可选）
            system_prompt: 系统提示词（可选）

        Returns:
            生成的文本
        """
        messages = []

        # 添加系统提示词
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })

        # 构建用户消息内容
        content = self._build_content_with_images(prompt, images)
        messages.append({
            "role": "user",
            "content": content
        })

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "stream": False
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.post(
            self.chat_endpoint,
            json=payload,
            headers=headers,
            timeout=300  # 5分钟超时
        )

        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"Text API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {self.chat_endpoint}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 模型名称不正确或无权访问\n"
                "3. 请求超时或网络问题\n"
                "4. API配额已用尽\n"
                "5. Base URL配置错误\n"
                "建议：检查 TEXT_API_KEY 和 TEXT_API_BASE_URL 配置"
            )

        result = response.json()

        # 提取生成的文本
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise Exception(
                f"Text API 响应格式异常：未找到生成的文本。\n"
                f"响应数据: {str(result)[:500]}\n"
                "可能原因：\n"
                "1. API返回格式与OpenAI标准不一致\n"
                "2. 请求被拒绝或过滤\n"
                "3. 模型输出为空\n"
                "建议：检查API文档确认响应格式"
            )


def get_text_chat_client(provider_config: dict):
    """
    获取 Text Chat 客户端实例（根据 type 返回对应客户端）

    Args:
        provider_config: 服务商配置字典
            - type: 'google_gemini' 或 'openai_compatible'
            - api_key: API密钥
            - base_url: API基础URL（仅 openai_compatible 需要）

    Returns:
        GenAIClient 或 TextChatClient
    """
    provider_type = provider_config.get('type', 'openai_compatible')
    api_key = provider_config.get('api_key')

    if provider_type == 'google_gemini':
        from .genai_client import GenAIClient
        return GenAIClient(api_key=api_key)
    else:
        base_url = provider_config.get('base_url')
        return TextChatClient(api_key=api_key, base_url=base_url)
