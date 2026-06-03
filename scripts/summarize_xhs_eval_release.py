#!/usr/bin/env python3
"""
Summarize the latest recommended XHS eval set release.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_eval_release import (
    summarize_eval_release,
    write_eval_release_summary_json,
    write_eval_release_summary_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a recommended XHS eval set release.")
    parser.add_argument("--recommended-manifest", required=True, help="Path to xhs-quality-cases.recommended.json.")
    parser.add_argument("--ab-index", required=True, help="Path to xhs-quality-ab-index.jsonl.")
    parser.add_argument("--json", help="Output release summary JSON path.")
    parser.add_argument("--markdown", help="Output release summary Markdown path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize_eval_release(
        recommended_manifest_path=args.recommended_manifest,
        ab_index_path=args.ab_index,
    )
    if args.json:
        write_eval_release_summary_json(summary, args.json)
    if args.markdown:
        write_eval_release_summary_markdown(summary, args.markdown)
    print(json.dumps(_jsonable(summary), ensure_ascii=False, indent=2))
    return 0 if summary.get("status") == "passed" else 1


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

