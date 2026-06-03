"""
API 路由模块

本模块将 API 路由按功能拆分为多个子模块：
- outline_routes: 大纲生成相关 API
- image_routes: 图片生成/获取相关 API
- history_routes: 历史记录 CRUD API
- config_routes: 配置管理 API
- content_routes: 内容生成相关 API（标题、文案、标签）

所有路由都注册到统一的 /api 前缀下
"""

from flask import Blueprint


def create_api_blueprint():
    """
    创建并配置主 API 蓝图

    每次调用都会创建新的蓝图实例，支持多次 create_app() 调用（如测试环境）

    Returns:
        配置好的 api Blueprint
    """
    from .outline_routes import create_outline_blueprint
    from .image_routes import create_image_blueprint
    from .history_routes import create_history_blueprint
    from .config_routes import create_config_blueprint
    from .content_routes import create_content_blueprint
    from .quality_routes import create_quality_blueprint

    # 创建主 API 蓝图
    api_bp = Blueprint('api', __name__, url_prefix='/api')

    # 将子蓝图注册到主蓝图（不带额外前缀）
    api_bp.register_blueprint(create_outline_blueprint())
    api_bp.register_blueprint(create_image_blueprint())
    api_bp.register_blueprint(create_history_blueprint())
    api_bp.register_blueprint(create_config_blueprint())
    api_bp.register_blueprint(create_content_blueprint())
    api_bp.register_blueprint(create_quality_blueprint())

    return api_bp


def register_routes(app):
    """
    注册所有 API 路由到 Flask 应用

    Args:
        app: Flask 应用实例
    """
    api_bp = create_api_blueprint()
    app.register_blueprint(api_bp)


__all__ = ['register_routes', 'create_api_blueprint']
