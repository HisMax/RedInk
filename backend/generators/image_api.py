"""Image API 图片生成器"""
import logging
import time
import random
import base64
import requests
from typing import Dict, Any, Optional, List
from .base import ImageGeneratorBase
from ..utils.image_compressor import compress_image

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, base_delay: float = 2):
    """错误重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        logger.warning(f"请求失败，{delay:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries}): {str(e)[:100]}")
                        time.sleep(delay)
            raise last_error
        return wrapper
    return decorator


class ImageApiGenerator(ImageGeneratorBase):
    """Image API 生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.debug("初始化 ImageApiGenerator...")
        self.base_url = config.get('base_url', 'https://api.example.com').rstrip('/').rstrip('/v1')
        self.model = config.get('model', 'default-model')
        self.default_aspect_ratio = config.get('default_aspect_ratio', '3:4')
        self.image_size = config.get('image_size', '4K')
        logger.info(f"ImageApiGenerator 初始化完成: base_url={self.base_url}, model={self.model}")

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

    @retry_on_error(max_retries=3, base_delay=2)
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
        生成图片（使用 /v1/images/generations）

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

        logger.info(f"Image API 生成图片: model={model}, aspect_ratio={aspect_ratio}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建请求体（使用 /v1/images/generations 格式）
        payload = {
            "model": model,
            "prompt": prompt,
            "response_format": "b64_json",  # 关键！获取 base64 数据而不是 URL
            "aspect_ratio": aspect_ratio,
            "image_size": self.image_size  # 4K 参数（nano-banana-2 专属）
        }

        # 收集所有参考图片
        all_reference_images = []

        # 优先使用 reference_images 列表
        if reference_images and len(reference_images) > 0:
            all_reference_images.extend(reference_images)

        # 向后兼容：如果有单张 reference_image，添加到列表
        if reference_image and reference_image not in all_reference_images:
            all_reference_images.append(reference_image)

        # 如果有参考图片，添加到 image 数组（Data URI 格式）
        if all_reference_images:
            logger.debug(f"  添加 {len(all_reference_images)} 张参考图片")
            image_uris = []
            for idx, img_data in enumerate(all_reference_images):
                # 压缩图片到 200KB 以内
                compressed_img = compress_image(img_data, max_size_kb=200)
                logger.debug(f"  参考图 {idx}: {len(img_data)} -> {len(compressed_img)} bytes")
                base64_image = base64.b64encode(compressed_img).decode('utf-8')
                data_uri = f"data:image/png;base64,{base64_image}"
                image_uris.append(data_uri)

            payload["image"] = image_uris  # images/generations 端点使用 image 数组

            # 增强提示词以利用参考图
            ref_count = len(all_reference_images)
            enhanced_prompt = f"""参考提供的 {ref_count} 张图片的风格（色彩、光影、构图、氛围），生成一张新图片。

新图片内容：{prompt}

要求：
1. 保持相似的色调和氛围
2. 使用相似的光影处理
3. 保持一致的画面质感
4. 如果参考图中有人物或产品，可以适当融入"""
            payload["prompt"] = enhanced_prompt

        # 发送请求
        api_url = f"{self.base_url}/v1/images/generations"
        logger.debug(f"  发送请求到: {api_url}")
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=300
        )

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

        # 提取 b64_json 数据
        if "data" in result and len(result["data"]) > 0:
            item = result["data"][0]

            if "b64_json" in item:
                b64_data_uri = item["b64_json"]

                # 去掉 Data URI 前缀（data:image/png;base64,）
                if b64_data_uri.startswith('data:'):
                    b64_string = b64_data_uri.split(',', 1)[1]
                else:
                    b64_string = b64_data_uri

                # 解码 base64
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
