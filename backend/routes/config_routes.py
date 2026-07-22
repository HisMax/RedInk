"""
配置管理相关 API 路由

包含功能：
- 获取当前配置
- 更新配置
- 测试服务商连接
"""

import logging
from pathlib import Path
from typing import NamedTuple
import yaml
from flask import Blueprint, request, jsonify
from .utils import (
    api_error_response,
    prepare_providers_for_response,
    validation_error,
)

logger = logging.getLogger(__name__)


class LlmSmokeResult(NamedTuple):
    text: str
    source: str
    finish_reason: str

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
            return api_error_response(e, context={"endpoint": "/api/config"})

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
            return api_error_response(e, context={"endpoint": "/api/config"})

    # ==================== 连接测试 ====================

    @config_bp.route('/config/test', methods=['POST'])
    def test_connection():
        """
        测试服务商连接

        请求体：
        - type: 服务商类型（google_genai/google_gemini/openai_compatible/image_api/atlascloud_image）
        - provider_name: 服务商名称（用于从配置读取 API Key）
        - api_key: API Key（可选，若不提供则从配置读取）
        - base_url: Base URL（可选）
        - model: 模型名称（可选）

        返回：
        - success: 是否成功
        - message: 测试结果消息
        """
        data = {}
        config = {}
        try:
            data = request.get_json(silent=True) or {}
            provider_type = data.get('type')
            provider_name = data.get('provider_name')

            if not provider_type:
                return api_error_response(
                    validation_error("缺少 type 参数", "请选择服务商类型后再测试连接。")
                )
            if provider_type not in ['google_genai', 'google_gemini', 'openai_compatible', 'image_api', 'atlascloud_image']:
                return api_error_response(
                    validation_error(f"不支持的类型: {provider_type}", "请选择正确的服务商类型后再测试连接。")
                )

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
                return api_error_response(
                    validation_error("API Key 未配置", "请先填写并保存该服务商的 API Key。"),
                    context=_error_context(provider_type, provider_name, config),
                )

            # 根据类型执行测试
            result = _test_provider_connection(provider_type, config)
            return jsonify(result), 200 if result['success'] else 400

        except Exception as e:
            return api_error_response(
                e,
                context=_error_context(
                    data.get('type') if data else None,
                    data.get('provider_name') if data else None,
                    config or data,
                ),
            )

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
    test_prompt = "请只回复：红墨连接测试成功"

    if provider_type == 'google_genai':
        return _test_google_genai(config)

    elif provider_type == 'google_gemini':
        return _test_google_gemini(config, test_prompt)

    elif provider_type == 'openai_compatible':
        return _test_openai_compatible(config, test_prompt)

    elif provider_type == 'image_api':
        return _test_image_api(config)

    elif provider_type == 'atlascloud_image':
        return _test_atlascloud_image(config)

    else:
        raise ValueError(f"不支持的类型: {provider_type}")


def _error_context(provider_type: str = None, provider_name: str = None, config: dict = None) -> dict:
    config = config or {}
    base_url = config.get('base_url')
    endpoint_type = config.get('endpoint_type')
    return {
        "provider_type": provider_type,
        "provider": provider_name,
        "base_url": base_url,
        "model": config.get('model'),
        "endpoint": endpoint_type,
    }


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
    result = _test_openai_chat_completion(config, test_prompt)
    return _check_response(result)


def _test_image_api(config: dict) -> dict:
    """测试图片 API 连接"""
    import requests

    base_url = config['base_url'].rstrip('/') if config.get('base_url') else 'https://api.openai.com'
    if base_url.endswith('/v1'):
        base_url = base_url[:-3]

    endpoint_type = config.get('endpoint_type', '')

    # 如果端点是 chat/completions 类型，用真实 LLM 请求来测试
    if endpoint_type and ('chat' in endpoint_type or 'completions' in endpoint_type):
        result = _test_openai_chat_completion(
            config,
            "请只回复：红墨连接测试成功",
        )
        return _llm_smoke_response_payload(result)

    # 标准 images API，尝试 /v1/models
    url = f"{base_url}/v1/models"
    response = requests.get(
        url,
        headers={'Authorization': f"Bearer {config['api_key']}"},
        timeout=30
    )

    if response.status_code == 200:
        return {
            "success": True,
            "message": "连接成功！仅代表连接稳定，不确定是否可以稳定支持图片生成"
        }
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")


def _test_atlascloud_image(config: dict) -> dict:
    """测试 Atlas Cloud Media API 连接和模型目录。"""
    import requests

    base_url = (config.get('base_url') or 'https://api.atlascloud.ai/api/v1').rstrip('/')
    model = config.get('model') or 'bytedance/seedream-v5.0-lite'

    response = requests.get(
        f"{base_url}/models",
        headers={'Authorization': f"Bearer {config['api_key']}"},
        timeout=30,
    )
    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        payload = response.json()
    except Exception as exc:
        raise Exception(f"Atlas Cloud 模型目录响应不是合法 JSON: {response.text[:500]}") from exc

    model_ids = _extract_model_ids(payload)
    if model_ids and model not in model_ids:
        return {
            "success": True,
            "warning": True,
            "status": "warning",
            "message": f"Atlas Cloud 连接成功，但模型目录中未找到 {model}。请确认模型名是否可用。"
        }

    return {
        "success": True,
        "message": "Atlas Cloud 连接成功！模型目录可访问，图片任务提交将在生成时执行。"
    }


def _extract_model_ids(payload) -> set[str]:
    data = payload.get('data') if isinstance(payload, dict) else payload
    if isinstance(data, dict):
        for key in ['models', 'items', 'list']:
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        return set()

    model_ids = set()
    for item in data:
        if isinstance(item, dict):
            model_id = item.get('model') or item.get('id') or item.get('name')
            if isinstance(model_id, str):
                model_ids.add(model_id)
        elif isinstance(item, str):
            model_ids.add(item)
    return model_ids


def _test_openai_chat_completion(config: dict, test_prompt: str) -> LlmSmokeResult:
    """用当前配置发送一次真实 OpenAI-compatible LLM 请求。"""
    import requests

    base_url = _normalize_base_url(config.get('base_url') or 'https://api.openai.com')
    endpoint = _normalize_endpoint(config.get('endpoint_type') or '/v1/chat/completions')
    url = f"{base_url}{endpoint}"

    payload = {
        "model": config.get('model') or 'gpt-3.5-turbo',
        "messages": [{"role": "user", "content": test_prompt}],
        "max_tokens": 256,
        "stream": False
    }
    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30
    )
    if _should_retry_with_max_completion_tokens(response):
        retry_payload = dict(payload)
        retry_payload["max_completion_tokens"] = retry_payload.pop("max_tokens")
        response = requests.post(
            url,
            headers=headers,
            json=retry_payload,
            timeout=30
        )

    if response.status_code != 200:
        raise Exception(f"HTTP {response.status_code}: {response.text[:500]}")

    try:
        result = response.json()
    except Exception as exc:
        raise Exception(f"LLM 响应不是合法 JSON: {response.text[:500]}") from exc

    smoke_result = _extract_chat_completion_text(result)
    if not smoke_result.text.strip() and smoke_result.source not in ["reasoning_tokens"]:
        raise Exception(
            "LLM 响应为空。\n"
            f"响应数据: {str(result)[:500]}"
        )
    return smoke_result


def _extract_chat_completion_text(result: dict) -> LlmSmokeResult:
    choices = result.get('choices')
    if not isinstance(choices, list) or not choices:
        raise Exception(
            "LLM 响应格式异常：未找到 choices。\n"
            f"响应数据: {str(result)[:500]}"
        )

    choice = choices[0] if isinstance(choices[0], dict) else {}
    finish_reason = choice.get('finish_reason') or ""
    message = choice.get('message', {}) if isinstance(choice, dict) else {}
    content = message.get('content')
    if isinstance(content, str) and content.strip():
        return LlmSmokeResult(content.strip(), "content", finish_reason)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get('text') or item.get('content')
                if isinstance(text, str):
                    parts.append(text)
        joined = "\n".join(parts).strip()
        if joined:
            return LlmSmokeResult(joined, "content", finish_reason)

    reasoning_content = message.get('reasoning_content') or message.get('reasoning')
    if isinstance(reasoning_content, str) and reasoning_content.strip():
        return LlmSmokeResult(reasoning_content.strip(), "reasoning_content", finish_reason)

    if finish_reason == "length" and _extract_reasoning_token_count(result) > 0:
        return LlmSmokeResult("", "reasoning_tokens", finish_reason)

    raise Exception(
        "LLM 响应格式异常：未找到 message.content 或 reasoning_content。\n"
        f"响应数据: {str(result)[:500]}"
    )


def _extract_reasoning_token_count(result: dict) -> int:
    usage = result.get("usage") if isinstance(result, dict) else {}
    if not isinstance(usage, dict):
        return 0
    for details_key in ["completion_tokens_details", "output_tokens_details"]:
        details = usage.get(details_key)
        if isinstance(details, dict):
            value = details.get("reasoning_tokens")
            if isinstance(value, int):
                return value
    return 0


def _should_retry_with_max_completion_tokens(response) -> bool:
    if response.status_code not in [400, 422]:
        return False
    text = (response.text or "").lower()
    return (
        "max_tokens" in text
        and (
            "max_completion_tokens" in text
            or "not compatible" in text
            or "unsupported" in text
            or "不支持" in text
        )
    )


def _normalize_base_url(base_url: str) -> str:
    base_url = base_url.rstrip('/')
    if base_url.endswith('/v1'):
        return base_url[:-3]
    return base_url


def _normalize_endpoint(endpoint: str) -> str:
    if endpoint == 'chat':
        endpoint = '/v1/chat/completions'
    elif endpoint == 'images':
        endpoint = '/v1/images/generations'
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    return endpoint


def _format_llm_success_message(result: LlmSmokeResult) -> str:
    if result.source in ["reasoning_content", "reasoning_tokens"]:
        suffix = "，输出预算已耗尽" if result.finish_reason == "length" else ""
        return f"LLM 请求成功！模型返回了推理过程但没有最终文本{suffix}。如果正式生成也出现空内容，请提高输出上限或关闭思考模式后重试。"
    return f"LLM 请求成功！响应: {result.text[:100]}"


def _llm_smoke_response_payload(result: LlmSmokeResult) -> dict:
    payload = {
        "success": True,
        "message": _format_llm_success_message(result),
    }
    if result.source in ["reasoning_content", "reasoning_tokens"]:
        payload["warning"] = True
        payload["status"] = "warning"
    return payload


def _check_response(result: LlmSmokeResult) -> dict:
    """检查响应是否符合预期"""
    if result.source in ["reasoning_content", "reasoning_tokens"]:
        return _llm_smoke_response_payload(result)

    if "红墨" in result.text:
        return _llm_smoke_response_payload(result)
    else:
        return {
            "success": True,
            "message": f"LLM 请求成功，但响应内容不符合预期: {result.text[:100]}"
        }
