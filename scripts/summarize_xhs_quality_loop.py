#!/usr/bin/env python3
"""
Summarize Xiaohongshu quality loop replay history.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_quality_history import (
    summarize_loop_history,
    write_improvement_plan_jsonl,
    write_loop_history_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a Xiaohongshu quality loop replay index.")
    parser.add_argument("--replay-index", required=True, help="Path to xhs quality loop replay index JSONL.")
    parser.add_argument("--markdown", help="Optional Markdown history output path.")
    parser.add_argument("--improvement-plan-jsonl", help="Optional JSONL output path for improvement tasks.")
    parser.add_argument("--limit", type=int, help="Only summarize the latest N runs.")
    parser.add_argument("--no-reports", action="store_true", help="Skip reading run report JSON files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize_loop_history(
        args.replay_index,
        limit=args.limit,
        include_reports=not args.no_reports,
    )
    if args.markdown:
        write_loop_history_markdown(summary, args.markdown)
    if args.improvement_plan_jsonl:
        write_improvement_plan_jsonl(summary["improvement_plan"], args.improvement_plan_jsonl)

    payload = {
        "replay_index": args.replay_index,
        "markdown": args.markdown,
        "improvement_plan_jsonl": args.improvement_plan_jsonl,
        "summary": summary,
    }
    print(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2))
    return 0


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
