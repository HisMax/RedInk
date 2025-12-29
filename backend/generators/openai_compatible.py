"""OpenAI 兼容接口图片生成器"""
import logging
import base64
from typing import Dict, Any
import requests
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)


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

        # 规范化 base_url 并识别 API 版本（OpenAI 默认 v1，火山引擎 Ark/Doubao 为 v3）
        raw_base_url = (self.base_url or '').rstrip('/')

        # 识别 Doubao/Ark：如果 base_url 以 /v3 结尾，或域名包含 volces/ark，则使用 v3
        if raw_base_url.endswith('/v3') or ('volces' in raw_base_url.lower()) or ('ark' in raw_base_url.lower()):
            self.api_version = 'v3'
        else:
            self.api_version = 'v1'

        # 去掉末尾版本号，保留基础路径（例如 https://ark.../api）
        if raw_base_url.endswith('/v1') or raw_base_url.endswith('/v3'):
            self.base_url = raw_base_url.rsplit('/', 1)[0]
        else:
            self.base_url = raw_base_url

        # 默认模型
        self.default_model = config.get('model', 'dall-e-3')

        # API 端点类型: 支持完整路径 (如 '/v1/images/generations') 或简写 ('images', 'chat')
        default_endpoint = f"/{self.api_version}/images/generations"
        endpoint_type = config.get('endpoint_type', default_endpoint)
        # 兼容简写：根据识别出的版本拼接正确路径
        if endpoint_type == 'images':
            endpoint_type = f"/{self.api_version}/images/generations"
        elif endpoint_type == 'chat':
            endpoint_type = f"/{self.api_version}/chat/completions"
        self.endpoint_type = endpoint_type

        logger.info(
            f"OpenAICompatibleGenerator 初始化完成: base_url={self.base_url}, api_version={self.api_version}, "
            f"model={self.default_model}, endpoint={self.endpoint_type}"
        )

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key and self.base_url)

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

        # 根据端点路径决定使用哪种 API 方式
        if 'chat' in self.endpoint_type or 'completions' in self.endpoint_type:
            return self._generate_via_chat_api(prompt, size, model)
        else:
            # 默认使用 images API
            return self._generate_via_images_api(prompt, size, model, quality)

    def _generate_via_images_api(
        self,
        prompt: str,
        size: str,
        model: str,
        quality: str
    ) -> bytes:
        """通过 images API 端点生成"""
        # 确保端点以 / 开头
        endpoint = self.endpoint_type if self.endpoint_type.startswith('/') else '/' + self.endpoint_type
        url = f"{self.base_url}{endpoint}"
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

        response = requests.post(url, headers=headers, json=payload, timeout=300)

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
        """
        通过 chat/completions 端点生成图片

        支持多种返回格式：
        1. Markdown 图片链接: ![xxx](url) - 即梦、部分中转站使用
        2. Base64 data URL: data:image/xxx;base64,xxx
        3. 纯图片 URL
        """
        # 确保端点以 / 开头
        endpoint = self.endpoint_type if self.endpoint_type.startswith('/') else '/' + self.endpoint_type
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Chat API 生成图片: {url}, model={model}")

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
            "temperature": 1.0
        }

        response = requests.post(url, headers=headers, json=payload, timeout=300)

        if response.status_code != 200:
            error_detail = response.text[:500]
            status_code = response.status_code

            # 详细的错误信息
            if status_code == 401:
                raise Exception(
                    "❌ API Key 认证失败\n\n"
                    "【可能原因】\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 格式错误\n\n"
                    "【解决方案】\n"
                    "在系统设置页面检查 API Key 是否正确"
                )
            elif status_code == 429:
                raise Exception(
                    "⏳ API 配额或速率限制\n\n"
                    "【解决方案】\n"
                    "1. 稍后再试\n"
                    "2. 检查 API 配额使用情况"
                )
            else:
                raise Exception(
                    f"❌ Chat API 请求失败 (状态码: {status_code})\n\n"
                    f"【错误详情】\n{error_detail[:300]}\n\n"
                    f"【请求地址】{url}\n"
                    f"【模型】{model}"
                )

        result = response.json()
        logger.debug(f"Chat API 响应: {str(result)[:500]}")

        # 解析响应
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]

                if isinstance(content, str):
                    # 1. 尝试解析 Markdown 图片链接: ![xxx](url)
                    image_urls = self._extract_markdown_image_urls(content)
                    if image_urls:
                        # 下载第一张图片
                        logger.info(f"从 Markdown 提取到 {len(image_urls)} 张图片，下载第一张...")
                        return self._download_image(image_urls[0])

                    # 2. 尝试解析 Base64 data URL
                    if content.startswith("data:image"):
                        logger.info("检测到 Base64 图片数据")
                        base64_data = content.split(",")[1]
                        return base64.b64decode(base64_data)

                    # 3. 尝试作为纯 URL 处理
                    if content.startswith("http://") or content.startswith("https://"):
                        logger.info("检测到图片 URL")
                        return self._download_image(content.strip())

        raise ValueError(
            "❌ 无法从 Chat API 响应中提取图片数据\n\n"
            f"【响应内容】\n{str(result)[:500]}\n\n"
            "【可能原因】\n"
            "1. 该模型不支持图片生成\n"
            "2. 响应格式与预期不符\n"
            "3. 提示词被安全过滤\n\n"
            "【解决方案】\n"
            "1. 确认模型名称正确（如 Nano-Banana-Pro）\n"
            "2. 修改提示词后重试"
        )

    def _extract_markdown_image_urls(self, content: str) -> list:
        """
        从 Markdown 内容中提取图片 URL

        支持格式: ![alt text](url) 或 ![](url)
        """
        import re
        # 匹配 ![任意文字](url) 格式
        pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
        urls = re.findall(pattern, content)
        logger.debug(f"从 Markdown 提取到 {len(urls)} 个图片 URL")
        return urls

    def _download_image(self, url: str) -> bytes:
        """下载图片并返回二进制数据"""
        logger.info(f"下载图片: {url[:100]}...")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                logger.info(f"✅ 图片下载成功: {len(response.content)} bytes")
                return response.content
            else:
                raise Exception(f"下载图片失败: HTTP {response.status_code}")
        except requests.exceptions.Timeout:
            raise Exception("❌ 下载图片超时，请重试")
        except Exception as e:
            raise Exception(f"❌ 下载图片失败: {str(e)}")

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
