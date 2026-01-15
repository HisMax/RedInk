import logging
import sys
from pathlib import Path
from flask import Flask, send_from_directory
from flask_cors import CORS
from backend.config import Config
from backend.routes import register_routes
from backend.models import db
import os


def setup_logging():
    """配置日志系统"""
    # 创建根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # 清除已有的处理器
    root_logger.handlers.clear()

    # 控制台处理器 - 详细格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        "\n%(asctime)s | %(levelname)-8s | %(name)s\n  └─ %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # 设置各模块的日志级别
    logging.getLogger("backend").setLevel(logging.DEBUG)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root_logger


def create_app():
    # 设置日志
    logger = setup_logging()
    logger.info("🚀 正在启动 红墨 AI图文生成器...")

    # 检查是否存在前端构建产物（Docker 环境）
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        logger.info("📦 检测到前端构建产物，启用静态文件托管模式")
        app = Flask(__name__, static_folder=str(frontend_dist), static_url_path="")
    else:
        logger.info("🔧 开发模式，前端请单独启动")
        app = Flask(__name__)

    app.config.from_object(Config)

    # 数据库配置
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "history", "redink.db"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 确保 history 目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        _ensure_history_indexes()

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": Config.CORS_ORIGINS,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type"],
            }
        },
    )

    # 注册所有 API 路由
    register_routes(app)

    # 启动时验证配置
    _validate_config_on_startup(logger)

    # 根据是否有前端构建产物决定根路由行为
    if frontend_dist.exists():

        @app.route("/")
        def serve_index():
            return send_from_directory(app.static_folder, "index.html")

        # 处理 Vue Router 的 HTML5 History 模式
        @app.errorhandler(404)
        def fallback(e):
            return send_from_directory(app.static_folder, "index.html")
    else:

        @app.route("/")
        def index():
            return {
                "message": "红墨 AI图文生成器 API",
                "version": "0.1.0",
                "endpoints": {
                    "health": "/api/health",
                    "outline": "POST /api/outline",
                    "generate": "POST /api/generate",
                    "images": "GET /api/images/<filename>",
                },
            }

    return app


def _ensure_history_indexes():
    """确保历史记录相关索引存在（幂等）"""
    from sqlalchemy import text

    statements = [
        "CREATE INDEX IF NOT EXISTS idx_history_records_status ON history_records (status)",
        "CREATE INDEX IF NOT EXISTS idx_history_records_created_at ON history_records (created_at)",
        "CREATE INDEX IF NOT EXISTS idx_history_records_task_id ON history_records (task_id)",
        "CREATE INDEX IF NOT EXISTS idx_history_records_status_created_at ON history_records (status, created_at)",
    ]

    for stmt in statements:
        db.session.execute(text(stmt))
    db.session.commit()


def _validate_config_on_startup(logger):
    """启动时验证配置"""
    from pathlib import Path
    import yaml

    logger.info("📋 检查配置文件...")

    # 检查 text_providers.yaml
    text_config_path = Path(__file__).parent.parent / "text_providers.yaml"
    if text_config_path.exists():
        try:
            with open(text_config_path, "r", encoding="utf-8") as f:
                text_config = yaml.safe_load(f) or {}
            active = text_config.get("active_provider", "未设置")
            providers = list(text_config.get("providers", {}).keys())
            logger.info(f"✅ 文本生成配置: 激活={active}, 可用服务商={providers}")

            # 检查激活的服务商是否有 API Key
            if active in text_config.get("providers", {}):
                provider = text_config["providers"][active]
                if not provider.get("api_key"):
                    logger.warning(f"⚠️  文本服务商 [{active}] 未配置 API Key")
                else:
                    logger.info(f"✅ 文本服务商 [{active}] API Key 已配置")
        except Exception as e:
            logger.error(f"❌ 读取 text_providers.yaml 失败: {e}")
    else:
        logger.warning("⚠️  text_providers.yaml 不存在，将使用默认配置")

    # 检查 image_providers.yaml
    image_config_path = Path(__file__).parent.parent / "image_providers.yaml"
    if image_config_path.exists():
        try:
            with open(image_config_path, "r", encoding="utf-8") as f:
                image_config = yaml.safe_load(f) or {}
            active = image_config.get("active_provider", "未设置")
            providers = list(image_config.get("providers", {}).keys())
            logger.info(f"✅ 图片生成配置: 激活={active}, 可用服务商={providers}")

            # 检查激活的服务商是否有 API Key
            if active in image_config.get("providers", {}):
                provider = image_config["providers"][active]
                if not provider.get("api_key"):
                    logger.warning(f"⚠️  图片服务商 [{active}] 未配置 API Key")
                else:
                    logger.info(f"✅ 图片服务商 [{active}] API Key 已配置")
        except Exception as e:
            logger.error(f"❌ 读取 image_providers.yaml 失败: {e}")
    else:
        logger.warning("⚠️  image_providers.yaml 不存在，将使用默认配置")

    logger.info("✅ 配置检查完成")


if __name__ == "__main__":
    app = create_app()
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
