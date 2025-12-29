"""Image API 图片生成器"""
import logging
import base64
import requests
from typing import Dict, Any, Optional, List, Union
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image

logger = logging.getLogger(__name__)


class ImageApiGenerator(ImageGeneratorBase):
    """Image API 生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 ImageApiGenerator...")
        raw_base_url = (config.get('base_url') or 'https://api.example.com').rstrip('/')
        if raw_base_url.endswith('/v3') or ('volces' in raw_base_url.lower()) or ('ark' in raw_base_url.lower()):
            self.api_version = 'v3'
        else:
            self.api_version = 'v1'

        if raw_base_url.endswith('/v1') or raw_base_url.endswith('/v3'):
            self.base_url = raw_base_url.rsplit('/', 1)[0]
        else:
            self.base_url = raw_base_url

        self.model = config.get('model', 'default-model')
        self.default_aspect_ratio = config.get('default_aspect_ratio', '3:4')
        self.image_size = config.get('image_size', '4K')

        # 支持自定义端点路径
        endpoint_type = config.get('endpoint_type', f'/{self.api_version}/images/generations')
        # 兼容旧的简写格式
        if endpoint_type == 'images':
            endpoint_type = f'/{self.api_version}/images/generations'
        elif endpoint_type == 'chat':
            endpoint_type = f'/{self.api_version}/chat/completions'
        # 确保以 / 开头
        if not endpoint_type.startswith('/'):
            endpoint_type = '/' + endpoint_type

        if endpoint_type.startswith('/v1/') and self.api_version == 'v3':
            endpoint_type = '/v3/' + endpoint_type[len('/v1/'):]
        elif endpoint_type.startswith('/v3/') and self.api_version == 'v1':
            endpoint_type = '/v1/' + endpoint_type[len('/v3/'):]
        self.endpoint_type = endpoint_type

        logger.info(f"ImageApiGenerator 初始化完成: base_url={self.base_url}, model={self.model}, endpoint={self.endpoint_type}")

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        if not self.api_key:
            logger.error("Image API Key 未配置")
            raise ValueError(
                "Image API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )
        return True

    def get_supported_sizes(self) -> List[str]:
        """获取支持的图片尺寸"""
        return ["1K", "2K", "4K"]

    def get_supported_aspect_ratios(self) -> List[str]:
        """获取支持的宽高比"""
        return ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = None,
        temperature: float = 1.0,
        model: str = None,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None,
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 图片描述
            aspect_ratio: 宽高比
            temperature: 创意度（未使用，保留接口兼容）
            model: 模型名称
            reference_image: 单张参考图片数据（向后兼容）
            reference_images: 多张参考图片数据列表

        Returns:
            生成的图片二进制数据
        """
        self.validate_config()

        if aspect_ratio is None:
            aspect_ratio = self.default_aspect_ratio

        if model is None:
            model = self.model

        logger.info(f"Image API 生成图片: model={model}, aspect_ratio={aspect_ratio}, endpoint={self.endpoint_type}")

        # 根据端点类型选择不同的生成方式
        if 'chat' in self.endpoint_type or 'completions' in self.endpoint_type:
            return self._generate_via_chat_api(prompt, aspect_ratio, model, reference_image, reference_images)
        else:
            return self._generate_via_images_api(prompt, aspect_ratio, model, reference_image, reference_images)

    def _generate_via_images_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None
    ) -> bytes:
        """通过 /v1/images/generations 端点生成图片"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "response_format": "b64_json",
            "aspect_ratio": aspect_ratio,
            "image_size": self.image_size,
            "watermark": False
        }

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，添加到 image 数组
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片")
            image_uris = []
            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_image}"
                image_uris.append(data_uri)

            payload["image"] = image_uris

            ref_count = len(all_reference_images)
            enhanced_prompt = f"""参考提供的 {ref_count} 张图片的风格（色彩、光影、构图、氛围），生成一张新图片。

新图片内容：{prompt}

要求：
1. 保持相似的色调和氛围
2. 使用相似的光影处理
3. 保持一致的画面质感
4. 如果参考图中有人物或产品，可以适当融入"""
            payload["prompt"] = enhanced_prompt

        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.debug(f"  发送请求到: {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=300)

        if response.status_code != 200:
            error_detail = response.text[:500]
            logger.error(f"Image API 请求失败: status={response.status_code}, error={error_detail}")
            raise Exception(
                f"Image API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {api_url}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 请求参数不符合API要求\n"
                "3. API服务端错误\n"
                "4. Base URL配置错误\n"
                "建议：检查API密钥和base_url配置"
            )

        result = response.json()
        logger.debug(f"  API 响应: data 长度={len(result.get('data', []))}")

        if "data" in result and len(result["data"]) > 0:
            item = result["data"][0]

            if "b64_json" in item:
                b64_data_uri = item["b64_json"]
                if b64_data_uri.startswith('data:'):
                    b64_string = b64_data_uri.split(',', 1)[1]
                else:
                    b64_string = b64_data_uri
                image_data = base64.b64decode(b64_string)
                logger.info(f"✅ Image API 图片生成成功: {len(image_data)} bytes")
                return image_data

        logger.error(f"无法从响应中提取图片数据: {str(result)[:200]}")
        raise Exception(
            f"图片数据提取失败：未找到 b64_json 数据。\n"
            f"API响应片段: {str(result)[:500]}\n"
            "可能原因：\n"
            "1. API返回格式与预期不符\n"
            "2. response_format 参数未生效\n"
            "3. 该模型不支持 b64_json 格式\n"
            "建议：检查API文档确认返回格式要求"
        )

    def _generate_via_chat_api(
        self,
        prompt: str,
        aspect_ratio: str,
        model: str,
        reference_image: Optional[bytes] = None,
        reference_images: Optional[List[bytes]] = None
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成图片（如即梦 API）"""
        import re

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建用户消息内容
        user_content: Any = prompt

        # 收集所有参考图片
        all_reference_images = []
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，构建多模态消息
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片到 chat 消息")
            content_parts = [{"type": "text", "text": prompt}]

            for idx, img_data in enumerate(all_reference_images):
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                })

            user_content = content_parts

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 4096,
            "temperature": 1.0
        }

        api_url = f"{self.base_url}{self.endpoint_type}"
        logger.info(f"Chat API 生成图片: {api_url}, model={model}")

        response = requests.post(api_url, headers=headers, json=payload, timeout=300)

        if response.status_code != 200:
            error_detail = response.text[:500]
            status_code = response.status_code

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
                    f"【请求地址】{api_url}\n"
                    f"【模型】{model}"
                )

        result = response.json()
        logger.debug(f"Chat API 响应: {str(result)[:500]}")

        extracted = self._extract_image_from_chat_result(result)
        if extracted is not None:
            return extracted

        raise Exception(
            "❌ 无法从 Chat API 响应中提取图片数据\n\n"
            f"【响应内容】\n{str(result)[:500]}\n\n"
            "【可能原因】\n"
            "1. 该模型不支持图片生成\n"
            "2. 响应格式与预期不符\n"
            "3. 提示词被安全过滤\n\n"
            "【解决方案】\n"
            "1. 确认模型名称正确\n"
            "2. 修改提示词后重试"
        )

    def _extract_image_from_chat_result(self, result: Any) -> Optional[bytes]:
        import re

        if isinstance(result, dict):
            data = result.get('data')
            if isinstance(data, list) and data:
                item = data[0] if isinstance(data[0], dict) else None
                if item:
                    if 'b64_json' in item and isinstance(item['b64_json'], str):
                        b64_string = item['b64_json']
                        if b64_string.startswith('data:'):
                            b64_string = b64_string.split(',', 1)[1]
                        return base64.b64decode(b64_string)
                    if 'url' in item and isinstance(item['url'], str):
                        return self._download_image(item['url'].strip())

            choices = result.get('choices')
            if isinstance(choices, list) and choices:
                choice0 = choices[0] if isinstance(choices[0], dict) else None
                message = (choice0 or {}).get('message')
                content = (message or {}).get('content') if isinstance(message, dict) else None

                if isinstance(content, list):
                    for part in content:
                        if not isinstance(part, dict):
                            continue
                        part_type = part.get('type')
                        if part_type in {'image_url', 'image'}:
                            image_url = part.get('image_url')
                            if isinstance(image_url, dict):
                                url = image_url.get('url')
                                if isinstance(url, str) and url.strip():
                                    url = url.strip()
                                    if url.startswith('data:image'):
                                        return base64.b64decode(url.split(',', 1)[1])
                                    if url.startswith('http://') or url.startswith('https://'):
                                        return self._download_image(url)

                if isinstance(content, str):
                    text = content.strip()

                    pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
                    urls = re.findall(pattern, text)
                    if urls:
                        logger.info(f"从 Markdown 提取到 {len(urls)} 张图片，下载第一张...")
                        return self._download_image(urls[0])

                    base64_pattern = r'!\[.*?\]\((data:image\/[^;]+;base64,[^\s\)]+)\)'
                    base64_urls = re.findall(base64_pattern, text)
                    if base64_urls:
                        logger.info("从 Markdown 提取到 Base64 图片数据")
                        base64_data = base64_urls[0].split(",", 1)[1]
                        return base64.b64decode(base64_data)

                    if text.startswith('data:image') and ',' in text:
                        logger.info("检测到 Base64 图片数据")
                        return base64.b64decode(text.split(',', 1)[1])

                    if text.startswith('http://') or text.startswith('https://'):
                        logger.info("检测到图片 URL")
                        return self._download_image(text)

        return None

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
