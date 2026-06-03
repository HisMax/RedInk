#!/usr/bin/env python3
"""
Draft human-reviewed execution artifacts for XHS quality improvement tasks.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_improvement_execution import (
    build_improvement_draft_bundle,
    load_improvement_tasks,
    write_improvement_draft_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Draft XHS quality improvement execution artifacts.")
    parser.add_argument("--plan-jsonl", required=True, help="Path to xhs-quality-improvement-plan.jsonl.")
    parser.add_argument("--output-dir", required=True, help="Directory for draft artifacts.")
    parser.add_argument("--run-id", default="xhs_improvement_drafts", help="Draft bundle run id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = load_improvement_tasks(args.plan_jsonl)
    bundle = build_improvement_draft_bundle(tasks, run_id=args.run_id)
    paths = write_improvement_draft_bundle(bundle, args.output_dir)
    payload = {
        "plan_jsonl": args.plan_jsonl,
        "output_dir": args.output_dir,
        "paths": paths,
        "draft_bundle": bundle,
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
