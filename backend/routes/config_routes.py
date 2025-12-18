"""
配置管理相关 API 路由

包含功能：
- 获取当前配置
- 更新配置
- 测试服务商连接
"""

import logging
from pathlib import Path
import yaml
from flask import Blueprint, request, jsonify
from .utils import prepare_providers_for_response

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path(__file__).parent.parent.parent
IMAGE_CONFIG_PATH = CONFIG_DIR / 'image_providers.yaml'
TEXT_CONFIG_PATH = CONFIG_DIR / 'text_providers.yaml'


def create_config_blueprint():
    """创建配置路由蓝图（工厂函数，支持多次调用）"""
    config_bp = Blueprint('config', __name__)

    # ==================== 配置读写 ====================

    @config_bp.route('/config', methods=['GET'])
    def get_config():
        """
        获取当前配置

        返回：
        - success: 是否成功
        - config: 配置对象
          - text_generation: 文本生成配置
          - image_generation: 图片生成配置
        """
        try:
            # 读取图片生成配置
            image_config = _read_config(IMAGE_CONFIG_PATH, {
                'active_provider': 'google_genai',
                'providers': {}
            })

            # 读取文本生成配置
            text_config = _read_config(TEXT_CONFIG_PATH, {
                'active_provider': 'google_gemini',
                'providers': {}
            })

            return jsonify({
                "success": True,
                "config": {
                    "text_generation": {
                        "active_provider": text_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            text_config.get('providers', {})
                        )
                    },
                    "image_generation": {
                        "active_provider": image_config.get('active_provider', ''),
                        "providers": prepare_providers_for_response(
                            image_config.get('providers', {})
                        )
                    }
                }
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"获取配置失败: {str(e)}"
            }), 500

    @config_bp.route('/config', methods=['POST'])
    def update_config():
        """
        更新配置

        请求体：
        - image_generation: 图片生成配置（可选）
        - text_generation: 文本生成配置（可选）

        返回：
        - success: 是否成功
        - message: 结果消息
        """
        try:
            data = request.get_json()

            # 更新图片生成配置
            if 'image_generation' in data:
                _update_provider_config(
                    IMAGE_CONFIG_PATH,
                    data['image_generation']
                )

            # 更新文本生成配置
            if 'text_generation' in data:
                _update_provider_config(
                    TEXT_CONFIG_PATH,
                    data['text_generation']
                )

            # 清除配置缓存，确保下次使用时读取新配置
            _clear_config_cache()

            return jsonify({
                "success": True,
                "message": "配置已保存"
            })

        except Exception as e:
            return jsonify({
                "success": False,
                "error": f"更新配置失败: {str(e)}"
            }), 500

    # ==================== 连接测试 ====================

    @config_bp.route('/config/test', methods=['POST'])
    def test_connection():
        """
        测试服务商连接

        请求体：
        - type: 服务商类型（google_genai/google_gemini/openai_compatible/image_api/wan2.6-t2i/modelscope_z_image）
        - provider_name: 服务商名称（用于从配置读取 API Key）
        - api_key: API Key（可选，若不提供则从配置读取）
        - base_url: Base URL（可选）
        - model: 模型名称（可选）

        返回：
        - success: 是否成功
        - message: 测试结果消息
        """
        try:
            data = request.get_json()
            provider_type = data.get('type')
            provider_name = data.get('provider_name')

            if not provider_type:
                return jsonify({"success": False, "error": "缺少 type 参数"}), 400

            # 构建配置
            config = {
                'api_key': data.get('api_key'),
                'base_url': data.get('base_url'),
                'model': data.get('model'),
                'endpoint_type': data.get('endpoint_type')
            }

            # 如果没有提供 api_key，从配置文件读取
            if not config['api_key'] and provider_name:
                config = _load_provider_config(provider_type, provider_name, config)

            if not config['api_key']:
                return jsonify({"success": False, "error": "API Key 未配置"}), 400

            # 根据类型执行测试
            result = _test_provider_connection(provider_type, config)
            return jsonify(result), 200 if result['success'] else 400

        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return config_bp


# ==================== 辅助函数 ====================

def _read_config(path: Path, default: dict) -> dict:
    """读取配置文件"""
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or default
    return default


def _write_config(path: Path, config: dict):
    """写入配置文件"""
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def _update_provider_config(config_path: Path, new_data: dict):
    """
    更新服务商配置

    Args:
        config_path: 配置文件路径
        new_data: 新的配置数据
    """
    # 读取现有配置
    existing_config = _read_config(config_path, {'providers': {}})

    # 更新 active_provider
    if 'active_provider' in new_data:
        existing_config['active_provider'] = new_data['active_provider']

    # 更新 providers
    if 'providers' in new_data:
        existing_providers = existing_config.get('providers', {})
        new_providers = new_data['providers']

        for name, new_provider_config in new_providers.items():
            # 如果新配置的 api_key 是空的，保留原有的
            if new_provider_config.get('api_key') in [True, False, '', None]:
                if name in existing_providers and existing_providers[name].get('api_key'):
                    new_provider_config['api_key'] = existing_providers[name]['api_key']
                else:
                    new_provider_config.pop('api_key', None)

            # 移除不需要保存的字段
            new_provider_config.pop('api_key_env', None)
            new_provider_config.pop('api_key_masked', None)

        existing_config['providers'] = new_providers

    # 保存配置
    _write_config(config_path, existing_config)


def _clear_config_cache():
    """清除配置缓存"""
    try:
        from backend.config import Config
        Config._image_providers_config = None
    except Exception:
        pass

    try:
        from backend.services.image import reset_image_service
        reset_image_service()
    except Exception:
        pass


def _load_provider_config(provider_type: str, provider_name: str, config: dict) -> dict:
    """
    从配置文件加载服务商配置

    Args:
        provider_type: 服务商类型
        provider_name: 服务商名称
        config: 当前配置（会被合并）

    Returns:
        dict: 合并后的配置
    """
    # 确定配置文件路径
    if provider_type in ['openai_compatible', 'google_gemini']:
        config_path = TEXT_CONFIG_PATH
    else:
        config_path = IMAGE_CONFIG_PATH

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f) or {}
            providers = yaml_config.get('providers', {})

            if provider_name in providers:
                saved = providers[provider_name]
                config['api_key'] = saved.get('api_key')

                if not config['base_url']:
                    config['base_url'] = saved.get('base_url')
                if not config['model']:
                    config['model'] = saved.get('model')
                if not config.get('endpoint_type'):
                    config['endpoint_type'] = saved.get('endpoint_type')

    return config


def _test_provider_connection(provider_type: str, config: dict) -> dict:
    """
    测试服务商连接

    Args:
        provider_type: 服务商类型
        config: 服务商配置

    Returns:
        dict: 测试结果
    """
    test_prompt = "请回复'你好，红墨'"

    if provider_type == 'google_genai':
        return _test_google_genai(config)

    elif provider_type == 'google_gemini':
        return _test_google_gemini(config, test_prompt)

    elif provider_type == 'openai_compatible':
        return _test_openai_compatible(config, test_prompt)

    elif provider_type == 'image_api':
        return _test_image_api(config)
    elif provider_type == 'wan2.6-t2i':
        return _test_wan26_t2i(config)
    elif provider_type == 'modelscope_z_image':
        return _test_modelscope_z_image(config)

    else:
        raise ValueError(f"不支持的类型: {provider_type}")


def _test_google_genai(config: dict) -> dict:
    """测试 Google GenAI 图片生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
        # 测试列出模型
        try:
            list(client.models.list())
            return {
                "success": True,
                "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
            }
        except Exception as e:
            raise Exception(f"连接测试失败: {str(e)}")
    else:
        return {
            "success": True,
            "message": "Vertex AI 无法通过 API Key 测试连接（需要 OAuth2 认证）。请在实际生成图片时验证配置是否正确。"
        }


def _test_google_gemini(config: dict, test_prompt: str) -> dict:
    """测试 Google Gemini 文本生成服务"""
    from google import genai

    if config.get('base_url'):
        client = genai.Client(
            api_key=config['api_key'],
            http_options={
                'base_url': config['base_url'],
                'api_version': 'v1beta'
            },
            vertexai=False
        )
    else:
        client = genai.Client(
            api_key=config['api_key'],
            vertexai=True
        )

    model = config.get('model') or 'gemini-2.0-flash-exp'
    response = client.models.generate_content(
        model=model,
        contents=test_prompt
    )
    result_text = response.text if hasattr(response, 'text') else str(response)

    return _check_response(result_text)


def _test_openai_compatible(config: dict, test_prompt: str) -> dict:
    """测试 OpenAI 兼容接口"""
    import requests

    base_url = config['base_url'].rstrip('/').rstrip('/v1') if config.get('base_url') else 'https://api.openai.com'
    url = f"{base_url}/v1/chat/completions"

    payload = {
        "model": config.get('model') or 'gpt-3.5-turbo',
        "messages": [{"role": "user", "content": test_prompt}],
        "max_tokens": 50
    }

    response = requests.post(
        url,
        headers={
            'Authorization': f"Bearer {config['api_key']}",
            'Content-Type': 'application/json'
        },
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    result = response.json()
    result_text = result['choices'][0]['message']['content']

    return _check_response(result_text)


def _test_image_api(config: dict) -> dict:
    """测试图片 API 连接"""
    import requests
    # 改为直接使用用户提供的 endpoint_type 进行 POST 测试
    base_url = ((config.get('base_url') or 'https://api.openai.com')).strip().rstrip('/')
    endpoint_type = ((config.get('endpoint_type') or '/v1/images/generations')).strip()
    if not endpoint_type.startswith('/'):
        endpoint_type = '/' + endpoint_type

    # 避免 base_url 结尾包含版本号导致重复（如 /api/v3 + /v3/...）
    try:
        import re
        m = re.match(r'^/(v\d+)(/.*)?$', endpoint_type)
        version_prefix = m.group(1) if m else None
        if version_prefix and base_url.endswith('/' + version_prefix):
            base_url = base_url[:-(len(version_prefix) + 1)]
    except Exception:
        pass

    url = f"{base_url}{endpoint_type}"
    logger.info(f"正在测试图片 API 连接: {url}")

    try:
        # 使用最小合法的 POST 负载进行连通性测试
        payload = {
            "model": config.get("model") or "seedream-4.5",
            "prompt": "测试连接：你好，红墨",
            # 通用 OpenAI 兼容字段，避免过于特殊参数导致报错
            "n": 1,
            "size": "1024x1024",
            "response_format": "b64_json"
        }
        headers = {
            'Authorization': f"Bearer {config['api_key']}",
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=payload, headers=headers, timeout=15)
        logger.info(f"图片 API 测试响应: status={response.status_code}, url={url}, body={response.text[:200]}")

        if response.status_code == 200:
            return {
                "success": True,
                "message": "连接成功！图片生成端点可用。"
            }
        elif response.status_code == 401:
             return {
                "success": False,
                "error": "连接失败：API Key 无效 (HTTP 401)"
            }
        elif response.status_code in [400, 403]:
             # 400/403 通常表示连通性正常，但参数/权限有问题
             return {
                 "success": True,
                 "message": f"连接连通（HTTP {response.status_code}）。若生成失败，请检查模型名、参数或账户权限。"
             }
        else:
             # 保留对 404 的严格失败提示
             raise Exception(f"HTTP {response.status_code}: 无法连接到服务商。请检查 Base URL、endpoint_type 和模型是否正确。\n测试路径: {url}")

    except Exception as e:
        logger.error(f"图片 API 测试异常: {e}")
        return {
            "success": False,
            "error": f"连接失败: {str(e)}"
        }


def _test_wan26_t2i(config: dict) -> dict:
    import requests

    base_url = (config.get("base_url") or "https://dashscope.aliyuncs.com/api/v1").strip().rstrip("/")
    if "/services/aigc/multimodal-generation/generation" in base_url:
        base_url = base_url.split("/services/aigc/multimodal-generation/generation", 1)[0].rstrip("/")
    if base_url.endswith("/api"):
        base_url = f"{base_url}/v1"
    elif "/api/" not in base_url and "dashscope" in base_url:
        base_url = f"{base_url}/api/v1"
    url = f"{base_url}/services/aigc/multimodal-generation/generation"

    payload = {
        "model": config.get("model") or "wan2.6-t2i",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "测试连接：你好，红墨"}],
                }
            ]
        },
        "parameters": {
            "negative_prompt": "",
            "prompt_extend": False,
            "watermark": False,
            "n": 1,
            "size": "960*1280",
        },
    }

    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    logger.info(f"通义万相测试响应: status={response.status_code}, url={url}, body={response.text[:200]}")

    if response.status_code == 200:
        try:
            data = response.json() if response.content else {}
            output = data.get("output") or {}
            results = output.get("results") or []
            choices = output.get("choices") or []

            has_result = bool(results)
            if not has_result and isinstance(choices, list) and choices:
                for choice in choices:
                    if not isinstance(choice, dict):
                        continue
                    message = choice.get("message") or {}
                    content = message.get("content") if isinstance(message, dict) else None
                    if isinstance(content, list) and any(isinstance(p, dict) and p.get("image") for p in content):
                        has_result = True
                        break

            if has_result:
                return {
                    "success": True,
                    "message": "连接成功！通义万相文生图端点可用。"
                }
            return {
                "success": True,
                "message": "连接成功（HTTP 200），但未返回图片结果字段。请在实际生成时验证。"
            }
        except Exception:
            return {
                "success": True,
                "message": "连接成功（HTTP 200）。"
            }


def _test_modelscope_z_image(config: dict) -> dict:
    import requests

    base_url = ((config.get("base_url") or "https://api-inference.modelscope.cn")).strip().rstrip("/")
    endpoint_type = ((config.get("endpoint_type") or "/v1/images/generations")).strip()
    if not endpoint_type.startswith("/"):
        endpoint_type = "/" + endpoint_type

    url = f"{base_url}{endpoint_type}"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
        "X-ModelScope-Async-Mode": "true",
    }
    payload = {
        "model": config.get("model") or "Tongyi-MAI/Z-Image-Turbo",
        "prompt": "测试连接：你好，红墨",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=20)
    logger.info(f"ModelScope Z-Image 测试响应: status={response.status_code}, url={url}, body={response.text[:200]}")

    if response.status_code == 200:
        try:
            data = response.json() if response.content else {}
        except Exception:
            data = {}

        task_id = data.get("task_id") or data.get("id")
        if task_id:
            return {
                "success": True,
                "message": "连接成功！已创建异步任务。"
            }
        return {
            "success": True,
            "message": "连接成功（HTTP 200）。"
        }

    if response.status_code == 401:
        return {
            "success": False,
            "error": "连接失败：API Key 无效 (HTTP 401)"
        }

    if response.status_code in [400, 403, 404]:
        return {
            "success": True,
            "message": f"连接连通（HTTP {response.status_code}）。若生成失败，请检查模型名、参数或账户权限。"
        }

    return {
        "success": False,
        "error": f"连接失败：HTTP {response.status_code}: {response.text[:200]}"
    }


def _check_response(result_text: str) -> dict:
    """检查响应是否符合预期"""
    if "你好" in result_text and "红墨" in result_text:
        return {
            "success": True,
            "message": f"连接成功！响应: {result_text[:100]}"
        }
    else:
        return {
            "success": True,
            "message": f"连接成功，但响应内容不符合预期: {result_text[:100]}"
        }
