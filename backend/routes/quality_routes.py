"""
Quality evaluation and revision API routes.
"""

import logging
import time

from flask import Blueprint, jsonify, request

from backend.services.quality import get_quality_service
from backend.services.revision import get_revision_service
from .utils import log_error, log_request

logger = logging.getLogger(__name__)


def create_quality_blueprint():
    quality_bp = Blueprint("quality", __name__)

    @quality_bp.route("/quality/evaluate", methods=["POST"])
    def evaluate_content_quality():
        start_time = time.time()
        try:
            data = request.get_json() or {}
            topic = data.get("topic", "")
            outline = data.get("outline", "")
            titles = data.get("titles", [])
            copywriting = data.get("copywriting", "")
            tags = data.get("tags", [])
            trace_id = data.get("trace_id")

            log_request("/quality/evaluate", {
                "topic": topic[:50] if topic else "",
                "titles_count": len(titles) if isinstance(titles, list) else 0,
                "copywriting_length": len(copywriting),
                "trace_id": trace_id,
            })

            if not topic or not outline or not titles or not copywriting:
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic、outline、titles、copywriting 不能为空。"
                }), 400

            result = get_quality_service().evaluate_content(
                topic=topic,
                outline=outline,
                titles=titles,
                copywriting=copywriting,
                tags=tags,
                trace_id=trace_id,
            )
            logger.info("质量评分 API 完成，耗时 %.2fs", time.time() - start_time)
            return jsonify(result), 200
        except Exception as e:
            log_error("/quality/evaluate", e)
            return jsonify({
                "success": False,
                "error": f"质量评分失败。\n错误详情: {str(e)}"
            }), 500

    @quality_bp.route("/quality/revise", methods=["POST"])
    def revise_content():
        try:
            data = request.get_json() or {}
            topic = data.get("topic", "")
            outline = data.get("outline", "")
            titles = data.get("titles", [])
            copywriting = data.get("copywriting", "")
            tags = data.get("tags", [])
            quality_score = data.get("quality_score", {})
            trace_id = data.get("trace_id")

            if not topic or not outline or not titles or not copywriting or not quality_score:
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic、outline、titles、copywriting、quality_score 不能为空。"
                }), 400

            result = get_revision_service().suggest_revisions(
                topic=topic,
                outline=outline,
                titles=titles,
                copywriting=copywriting,
                tags=tags,
                quality_score=quality_score,
                trace_id=trace_id,
            )
            return jsonify(result), 200
        except Exception as e:
            log_error("/quality/revise", e)
            return jsonify({
                "success": False,
                "error": f"内容改写失败。\n错误详情: {str(e)}"
            }), 500

    return quality_bp
