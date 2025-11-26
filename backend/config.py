import yaml
from pathlib import Path


class Config:
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 12398
    CORS_ORIGINS = ['http://localhost:5173', 'http://localhost:3000']
    OUTPUT_DIR = 'output'

    _image_providers_config = None

    @classmethod
    def load_image_providers_config(cls):
        if cls._image_providers_config is not None:
            return cls._image_providers_config

        config_path = Path(__file__).parent.parent / 'image_providers.yaml'

        if not config_path.exists():
            cls._image_providers_config = {
                'active_provider': 'google_genai',
                'providers': {}
            }
            return cls._image_providers_config

        with open(config_path, 'r', encoding='utf-8') as f:
            cls._image_providers_config = yaml.safe_load(f) or {}

        return cls._image_providers_config

    @classmethod
    def get_active_image_provider(cls):
        config = cls.load_image_providers_config()
        return config.get('active_provider', 'google_genai')

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None):
        config = cls.load_image_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_image_provider()

        if provider_name not in config.get('providers', {}):
            available = ', '.join(config.get('providers', {}).keys())
            raise ValueError(
                f"未找到图片生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加图片生成服务商\n"
                "2. 或检查 image_providers.yaml 文件"
            )

        provider_config = config['providers'][provider_name].copy()

        if not provider_config.get('api_key'):
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        return provider_config

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        cls._image_providers_config = None
