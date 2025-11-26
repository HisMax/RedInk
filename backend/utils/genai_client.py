"""Google GenAI 客户端封装"""
import time
import random
from functools import wraps
from google import genai
from google.genai import types


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
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        if attempt < max_retries - 1:
                            # 指数退避 + 随机抖动
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到资源限制，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    # 非 429 错误或重试次数耗尽，直接抛出
                    raise
            raise Exception(
                f"GenAI API 重试 {max_retries} 次后仍失败。\n"
                "可能原因：\n"
                "1. API配额已用尽或达到速率限制\n"
                "2. 网络连接持续不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或检查API配额和网络状态"
            )
        return wrapper
    return decorator


class GenAIClient:
    """GenAI 客户端封装类（已弃用，请使用 GoogleGenAIGenerator）"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError(
                "Google Cloud API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        self.client = genai.Client(
            vertexai=True,
            api_key=self.api_key,
        )

        # 默认安全设置：全部关闭
        self.default_safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ]

    @retry_on_429(max_retries=3, base_delay=2)
    def generate_text(
        self,
        prompt: str,
        model: str = "gemini-3-pro-preview",
        temperature: float = 1.0,
        max_output_tokens: int = 8000,
        use_search: bool = False,
        use_thinking: bool = False,
        images: list = None,
        system_prompt: str = None,
        **kwargs
    ) -> str:
        """
        生成文本

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_output_tokens: 最大输出 token
            use_search: 是否使用搜索
            use_thinking: 是否启用思考模式
            images: 图片列表（暂不支持）
            system_prompt: 系统提示词（暂不支持）

        Returns:
            生成的文本
        """
        parts = [types.Part(text=prompt)]

        if images:
            for img_data in images:
                if isinstance(img_data, bytes):
                    parts.append(types.Part(
                        inline_data=types.Blob(
                            mime_type="image/png",
                            data=img_data
                        )
                    ))

        contents = [
            types.Content(
                role="user",
                parts=parts
            )
        ]

        config_kwargs = {
            "temperature": temperature,
            "top_p": 0.95,
            "max_output_tokens": max_output_tokens,
            "safety_settings": self.default_safety_settings,
        }

        # 添加搜索工具
        if use_search:
            config_kwargs["tools"] = [types.Tool(google_search=types.GoogleSearch())]

        # 添加思考配置
        if use_thinking:
            config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="HIGH")

        generate_content_config = types.GenerateContentConfig(**config_kwargs)

        result = ""
        for chunk in self.client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue
            result += chunk.text

        return result

    @retry_on_429(max_retries=5, base_delay=3)  # 图片生成重试更多次
    def generate_image(
        self,
        prompt: str,
        model: str = "gemini-3-pro-image-preview",
        aspect_ratio: str = "3:4",
        temperature: float = 1.0,
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            model: 模型名称
            aspect_ratio: 宽高比
            temperature: 温度

        Returns:
            图片二进制数据
        """
        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=32768,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=self.default_safety_settings,
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                output_mime_type="image/png",
            ),
        )

        image_data = None
        for chunk in self.client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                for part in chunk.candidates[0].content.parts:
                    # 检查是否有图片数据
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        break

        if not image_data:
            raise ValueError(
                "图片生成失败：API返回为空。\n"
                "可能原因：\n"
                "1. 提示词被安全过滤拦截\n"
                "2. 模型响应异常\n"
                "3. 网络传输中断\n"
                "建议：修改提示词内容后重试，或检查网络连接"
            )

        return image_data


# 全局客户端实例
_client_instance = None

def get_genai_client() -> GenAIClient:
    """获取全局 GenAI 客户端实例"""
    global _client_instance
    if _client_instance is None:
        _client_instance = GenAIClient()
    return _client_instance
