"""Google GenAI 图片生成器"""
import time
import random
import base64
from functools import wraps
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image


def retry_on_429(max_retries=5, base_delay=3):
    """429 错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        if attempt < max_retries - 1:
                            # 指数退避 + 随机抖动
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到资源限制，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    # 其他错误也进行重试
                    elif attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10) + random.uniform(0, 1)
                        print(f"[重试] 请求失败: {error_str[:100]}，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    raise
            raise Exception(
                f"图片生成失败：重试 {max_retries} 次后仍失败。\n"
                f"最后错误: {last_error}\n"
                "可能原因：\n"
                "1. API配额已用尽或达到速率限制\n"
                "2. 网络连接不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或检查API配额和网络状态"
            )
        return wrapper
    return decorator


class GoogleGenAIGenerator(ImageGeneratorBase):
    """Google GenAI 图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not self.api_key:
            raise ValueError(
                "Google GenAI API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key\n"
                "获取 API Key: https://aistudio.google.com/app/apikey"
            )

        # 初始化客户端
        client_kwargs = {
            "api_key": self.api_key,
        }

        # 记录是否使用 vertexai 模式
        self.is_vertexai = True

        # 如果有 base_url，则配置 http_options 并禁用 vertexai (通常代理使用标准 Gemini API 路径)
        if hasattr(self, 'config') and self.config.get('base_url'):
            client_kwargs["http_options"] = {
                "base_url": self.config['base_url'],
                "api_version": "v1beta"
            }
            client_kwargs["vertexai"] = False
            self.is_vertexai = False
        else:
            # 默认保持原有行为
            client_kwargs["vertexai"] = True

        self.client = genai.Client(**client_kwargs)

        # 默认安全设置
        self.safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ]

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key)

    @retry_on_429(max_retries=5, base_delay=3)
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "3:4",
        temperature: float = 1.0,
        model: str = "gemini-3-pro-image-preview",
        reference_image: Optional[bytes] = None,
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            aspect_ratio: 宽高比 (如 "3:4", "1:1", "16:9")
            temperature: 温度
            model: 模型名称
            reference_image: 参考图片二进制数据（用于保持风格一致）
            **kwargs: 其他参数

        Returns:
            图片二进制数据
        """
        # 构建 parts 列表
        parts = []

        # 如果有参考图，先添加参考图和说明
        if reference_image:
            # 压缩参考图到 200KB 以内
            compressed_ref = compress_image(reference_image, max_size_kb=200)
            # 添加参考图
            parts.append(types.Part(
                inline_data=types.Blob(
                    mime_type="image/png",
                    data=compressed_ref
                )
            ))
            # 添加带参考说明的提示词
            enhanced_prompt = f"""请参考上面这张图片的视觉风格（包括配色、排版风格、字体风格、装饰元素风格），生成一张风格一致的新图片。

新图片的内容要求：
{prompt}

重要：
1. 必须保持与参考图相同的视觉风格和设计语言
2. 配色方案要与参考图协调一致
3. 排版和装饰元素的风格要统一
4. 但内容要按照新的要求来生成"""
            parts.append(types.Part(text=enhanced_prompt))
        else:
            # 没有参考图，直接使用原始提示词
            parts.append(types.Part(text=prompt))

        contents = [
            types.Content(
                role="user",
                parts=parts
            )
        ]

        image_config_kwargs = {
            "aspect_ratio": aspect_ratio,
        }

        # 只有在 Vertex AI 模式下才支持 output_mime_type
        if self.is_vertexai:
            image_config_kwargs["output_mime_type"] = "image/png"

        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=32768,
            response_modalities=["TEXT", "IMAGE"],
            safety_settings=self.safety_settings,
            image_config=types.ImageConfig(**image_config_kwargs),
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

    def get_supported_aspect_ratios(self) -> list:
        """获取支持的宽高比"""
        return ["1:1", "3:4", "4:3", "16:9", "9:16"]
