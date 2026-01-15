import os
import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from backend.app import create_app
from backend.models import db, HistoryRecord
from datetime import datetime


def migrate():
    app = create_app()
    with app.app_context():
        history_dir = root_dir / "history"
        index_file = history_dir / "index.json"

        if not index_file.exists():
            print("未找到 index.json，跳过迁移。")
            return

        print(f"正在从 {index_file} 加载数据...")
        with open(index_file, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        records_to_migrate = index_data.get("records", [])
        print(f"找到 {len(records_to_migrate)} 条记录。")

        for idx_record in records_to_migrate:
            record_id = idx_record["id"]

            # 检查数据库中是否已存在
            if HistoryRecord.query.get(record_id):
                print(f"记录 {record_id} 已存在，跳过。")
                continue

            # 尝试加载详细记录文件
            record_file = history_dir / f"{record_id}.json"
            if record_file.exists():
                with open(record_file, "r", encoding="utf-8") as f:
                    detail = json.load(f)
            else:
                print(f"警告：找不到详情文件 {record_file}，使用索引数据。")
                detail = idx_record

            # 创建模型实例
            # 处理时间格式 (ISO 格式)
            def parse_date(date_str):
                try:
                    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except:
                    return datetime.utcnow()

            new_record = HistoryRecord(
                id=record_id,
                title=detail.get("title", idx_record.get("title", "无标题")),
                status=detail.get("status", idx_record.get("status", "draft")),
                created_at=parse_date(
                    detail.get("created_at", idx_record.get("created_at", ""))
                ),
                updated_at=parse_date(
                    detail.get("updated_at", idx_record.get("updated_at", ""))
                ),
                thumbnail=detail.get("thumbnail", idx_record.get("thumbnail")),
                page_count=detail.get("page_count", idx_record.get("page_count", 0)),
                task_id=detail.get("images", {}).get("task_id")
                if isinstance(detail.get("images"), dict)
                else detail.get("task_id"),
            )

            # 设置 JSON 字段
            new_record.outline = detail.get("outline", {})
            new_record.images = detail.get("images", {})

            db.session.add(new_record)
            print(f"已添加记录: {record_id} ({new_record.title})")

        db.session.commit()
        print("迁移完成！")


if __name__ == "__main__":
    migrate()
