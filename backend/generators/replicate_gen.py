"""Replicate 图片生成器"""
import os
import logging
import requests
from typing import Dict, Any, Optional, List
from .base import ImageGeneratorBase

logger = logging.getLogger(__name__)

try:
    import replicate
except ImportError:
    replicate = None


class ReplicateGenerator(ImageGeneratorBase):
    """
    基于 Replicate 的图片生成器
    支持 Z-Image, Flux 等模型
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化生成器

        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'prunaai/z-image-turbo:0870559624690b3709350177b9d521d84e54d297026d725358b8f73193429e91')
        
        # 默认参数
        self.default_steps = 9
        self.default_guidance = 0.0

        if not replicate:
            logger.warning("未安装 replicate 包，请运行 pip install replicate")

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key)

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "3:4",
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            aspect_ratio: 宽高比
            **kwargs: 其他参数

        Returns:
            图片二进制数据
        """
        if not replicate:
            raise ImportError("Replicate package not installed")

        # 使用 Client 实例避免全局环境变量污染
        client = replicate.Client(api_token=self.api_key)

        logger.info(f"Replicate 生成图片: model={self.model}, aspect_ratio={aspect_ratio}")

        # 解析宽高比
        width, height = self._get_dimensions(aspect_ratio)

        try:
            # 准备输入参数
            input_params = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_inference_steps": kwargs.get('steps', self.default_steps),
                "guidance_scale": kwargs.get('guidance', self.default_guidance),
                "output_format": "png"
            }
            
            # 添加其他参数
            if 'seed' in kwargs:
                input_params['seed'] = kwargs['seed']

            # 调用 Replicate
            output = client.run(
                self.model,
                input=input_params
            )

            # Replicate 通常返回图片 URL 列表或单个 URL
            image_url = output[0] if isinstance(output, list) else output
            
            # 下载图片
            return self._download_image(str(image_url))

        except Exception as e:
            logger.error(f"Replicate 生成失败: {str(e)}")
            raise RuntimeError(f"图片生成失败: {str(e)}")

    def _get_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """根据宽高比获取尺寸"""
        # 基础尺寸 (针对 Z-Image Turbo 优化)
        base = 1024
        
        ratios = {
            "1:1": (1024, 1024),
            "3:4": (896, 1152),  # 约等于 3:4
            "4:3": (1152, 896),
            "9:16": (768, 1344), # 约等于 9:16
            "16:9": (1344, 768),
        }
        
        return ratios.get(aspect_ratio, (1024, 1024))

    def _download_image(self, url: str) -> bytes:
        """下载图片"""
        logger.info(f"下载图片: {url[:100]}...")
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                return response.content
            else:
                raise Exception(f"HTTP {response.status_code}")
        except Exception as e:
            raise Exception(f"下载图片失败: {str(e)}")

    def get_supported_aspect_ratios(self) -> List[str]:
        return ["1:1", "3:4", "4:3", "9:16", "16:9"]
