"""图片生成器工厂"""
from typing import Dict, Any
from .base import ImageGeneratorBase
from .google_genai import GoogleGenAIGenerator
from .openai_compatible import OpenAICompatibleGenerator
from .image_api import ImageApiGenerator
from .wan26_t2i import Wan26T2IGenerator
from .modelscope_z_image import ModelScopeZImageGenerator


class ImageGeneratorFactory:
    """图片生成器工厂类"""

    # 注册的生成器类型
    GENERATORS = {
        'google_genai': GoogleGenAIGenerator,
        'openai': OpenAICompatibleGenerator,
        'openai_compatible': OpenAICompatibleGenerator,
        'image_api': ImageApiGenerator,
        'wan2.6-t2i': Wan26T2IGenerator,
        'modelscope_z_image': ModelScopeZImageGenerator,
    }

    @classmethod
    def create(cls, provider: str, config: Dict[str, Any]) -> ImageGeneratorBase:
        """
        创建图片生成器实例

        Args:
            provider: 服务商类型 ('google_genai', 'openai', 'openai_compatible')
            config: 配置字典

        Returns:
            图片生成器实例

        Raises:
            ValueError: 不支持的服务商类型
        """
        if provider not in cls.GENERATORS:
            available = ', '.join(cls.GENERATORS.keys())
            raise ValueError(
                f"不支持的图片生成服务商: {provider}\n"
                f"支持的服务商类型: {available}\n"
                "解决方案：\n"
                "1. 检查 image_providers.yaml 中的 active_provider 配置\n"
                "2. 确认 provider.type 字段是否正确\n"
                "3. 或使用环境变量 IMAGE_PROVIDER 指定服务商"
            )

        generator_class = cls.GENERATORS[provider]
        return generator_class(config)

    @classmethod
    def register_generator(cls, name: str, generator_class: type):
        """
        注册自定义生成器

        Args:
            name: 生成器名称
            generator_class: 生成器类
        """
        if not issubclass(generator_class, ImageGeneratorBase):
            raise TypeError(
                f"注册失败：生成器类必须继承自 ImageGeneratorBase。\n"
                f"提供的类: {generator_class.__name__}\n"
                f"基类: ImageGeneratorBase"
            )

        cls.GENERATORS[name] = generator_class
