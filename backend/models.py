from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
import json

db = SQLAlchemy()


class HistoryRecord(db.Model):
    """历史记录模型"""

    __tablename__ = "history_records"
    __table_args__ = (
        Index("idx_history_records_status", "status"),
        Index("idx_history_records_created_at", "created_at"),
        Index("idx_history_records_task_id", "task_id"),
        Index("idx_history_records_status_created_at", "status", "created_at"),
    )

    id = db.Column(db.String(36), primary_key=True)  # 使用 UUID
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # 存储 JSON 数据为 TEXT
    _outline_json = db.Column("outline", db.Text, nullable=True)
    _images_json = db.Column("images", db.Text, nullable=True)

    thumbnail = db.Column(db.String(255), nullable=True)
    page_count = db.Column(db.Integer, default=0)
    task_id = db.Column(db.String(100), nullable=True)

    @property
    def outline(self):
        if self._outline_json:
            try:
                return json.loads(self._outline_json)
            except Exception:
                return {}
        return {}

    @outline.setter
    def outline(self, value):
        self._outline_json = json.dumps(value, ensure_ascii=False)

    @property
    def images(self):
        if self._images_json:
            try:
                return json.loads(self._images_json)
            except Exception:
                return {"task_id": self.task_id, "generated": []}
        return {"task_id": self.task_id, "generated": []}

    @images.setter
    def images(self, value):
        self._images_json = json.dumps(value, ensure_ascii=False)

    def to_dict(self):
        """转为字典供 API 返回"""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "outline": self.outline,
            "images": self.images,
            "thumbnail": self.thumbnail,
            "page_count": self.page_count,
            "task_id": self.task_id,
        }

    def to_index_dict(self):
        """转为简要字典供列表 API 返回"""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "thumbnail": self.thumbnail,
            "page_count": self.page_count,
            "task_id": self.task_id,
        }
