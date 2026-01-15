"""
历史记录服务 (SQLite 版)

负责管理绘本生成历史记录的存储、查询、更新和删除。
支持草稿、生成中、完成等多种状态流转。
"""

import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from backend.models import db, HistoryRecord


class RecordStatus:
    """历史记录状态常量"""

    DRAFT = "draft"  # 草稿：已创建大纲，未开始生成
    GENERATING = "generating"  # 生成中：正在生成图片
    PARTIAL = "partial"  # 部分完成：有部分图片生成
    COMPLETED = "completed"  # 已完成：所有图片已生成
    ERROR = "error"  # 错误：生成过程中出现错误


class HistoryService:
    def __init__(self):
        """
        初始化历史记录服务
        """
        # 兼容旧路径，用于存储图片
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "history"
        )
        os.makedirs(self.history_dir, exist_ok=True)

    def create_record(
        self, topic: str, outline: Dict, task_id: Optional[str] = None
    ) -> str:
        """创建新的历史记录"""
        record_id = str(uuid.uuid4())

        record = HistoryRecord(
            id=record_id,
            title=topic,
            status=RecordStatus.DRAFT,
            outline=outline,
            task_id=task_id,
            page_count=len(outline.get("pages", [])),
        )

        db.session.add(record)
        db.session.commit()

        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """获取历史记录详情"""
        record = HistoryRecord.query.get(record_id)
        if not record:
            return None
        return record.to_dict()

    def record_exists(self, record_id: str) -> bool:
        """检查历史记录是否存在"""
        return HistoryRecord.query.get(record_id) is not None

    def update_record(
        self,
        record_id: str,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None,
        status: Optional[str] = None,
        thumbnail: Optional[str] = None,
    ) -> bool:
        """更新历史记录"""
        record = HistoryRecord.query.get(record_id)
        if not record:
            return False

        if outline is not None:
            record.outline = outline
            record.page_count = len(outline.get("pages", []))

        if images is not None:
            record.images = images
            if images.get("task_id"):
                record.task_id = images.get("task_id")

        if status is not None:
            record.status = status

        if thumbnail is not None:
            record.thumbnail = thumbnail

        db.session.commit()
        return True

    def delete_record(self, record_id: str) -> bool:
        """删除历史记录"""
        record = HistoryRecord.query.get(record_id)
        if not record:
            return False

        # 删除关联的任务图片目录 (物理删除)
        if record.task_id:
            task_dir = os.path.join(self.history_dir, record.task_id)
            if os.path.exists(task_dir) and os.path.isdir(task_dir):
                try:
                    import shutil

                    shutil.rmtree(task_dir)
                except Exception as e:
                    print(f"删除任务目录失败: {task_dir}, {e}")

        db.session.delete(record)
        db.session.commit()
        return True

    def list_records(
        self, page: int = 1, page_size: int = 20, status: Optional[str] = None
    ) -> Dict:
        """分页获取历史记录列表"""
        query = HistoryRecord.query

        if status:
            query = query.filter_by(status=status)

        pagination = query.order_by(HistoryRecord.created_at.desc()).paginate(
            page=page, per_page=page_size, error_out=False
        )

        return {
            "records": [r.to_index_dict() for r in pagination.items],
            "total": pagination.total,
            "page": page,
            "page_size": page_size,
            "total_pages": pagination.pages,
        }

    def search_records(self, keyword: str) -> List[Dict]:
        """根据关键词搜索历史记录"""
        results = (
            HistoryRecord.query.filter(HistoryRecord.title.ilike(f"%{keyword}%"))
            .order_by(HistoryRecord.created_at.desc())
            .all()
        )

        return [r.to_index_dict() for r in results]

    def get_statistics(self) -> Dict:
        """获取历史记录统计信息"""
        total = HistoryRecord.query.count()

        # 统计各状态的记录数
        from sqlalchemy import func

        status_counts = (
            db.session.query(HistoryRecord.status, func.count(HistoryRecord.id))
            .group_by(HistoryRecord.status)
            .all()
        )

        by_status = {status: count for status, count in status_counts}

        return {"total": total, "by_status": by_status}

    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        """扫描任务文件夹，同步图片列表"""
        task_dir = os.path.join(self.history_dir, task_id)

        if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
            return {"success": False, "error": f"任务目录不存在: {task_id}"}

        try:
            image_files = []
            for filename in os.listdir(task_dir):
                if filename.startswith("thumb_"):
                    continue
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_files.append(filename)

            image_files.sort(
                key=lambda x: int(x.split(".")[0]) if x.split(".")[0].isdigit() else 999
            )

            record = HistoryRecord.query.filter_by(task_id=task_id).first()
            if record:
                expected_count = record.page_count
                actual_count = len(image_files)

                if actual_count == 0:
                    status = RecordStatus.DRAFT
                elif actual_count >= expected_count:
                    status = RecordStatus.COMPLETED
                else:
                    status = RecordStatus.PARTIAL

                self.update_record(
                    record.id,
                    images={"task_id": task_id, "generated": image_files},
                    status=status,
                    thumbnail=image_files[0] if image_files else None,
                )

                return {
                    "success": True,
                    "record_id": record.id,
                    "task_id": task_id,
                    "images_count": len(image_files),
                    "images": image_files,
                    "status": status,
                }

            return {
                "success": True,
                "task_id": task_id,
                "images_count": len(image_files),
                "images": image_files,
                "no_record": True,
            }

        except Exception as e:
            return {"success": False, "error": f"扫描任务失败: {str(e)}"}

    def scan_all_tasks(self) -> Dict[str, Any]:
        """扫描所有任务文件夹，同步图片列表"""
        if not os.path.exists(self.history_dir):
            return {"success": False, "error": "历史记录目录不存在"}

        try:
            results = []
            for item in os.listdir(self.history_dir):
                item_path = os.path.join(self.history_dir, item)
                if os.path.isdir(item_path):
                    results.append(self.scan_and_sync_task_images(item))

            synced = sum(
                1 for r in results if r.get("success") and not r.get("no_record")
            )
            failed = sum(1 for r in results if not r.get("success"))
            orphan = [r["task_id"] for r in results if r.get("no_record")]

            return {
                "success": True,
                "total_tasks": len(results),
                "synced": synced,
                "failed": failed,
                "orphan_tasks": orphan,
                "results": results,
            }
        except Exception as e:
            return {"success": False, "error": f"扫描所有任务失败: {str(e)}"}


_service_instance = None


def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
