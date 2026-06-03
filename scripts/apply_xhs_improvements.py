#!/usr/bin/env python3
"""
Safely apply approved XHS improvement drafts to candidate artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_improvement_apply import (
    apply_approved_eval_case_drafts,
    load_eval_case_drafts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply approved XHS improvement drafts safely.")
    parser.add_argument("--eval-case-drafts", required=True, help="Path to xhs-eval-case-drafts.jsonl.")
    parser.add_argument("--candidate-jsonl", required=True, help="Output JSONL for approved eval case candidates.")
    parser.add_argument("--run-id", default="xhs_apply_improvements", help="Apply run id.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report what would be appended without writing.")
    mode.add_argument("--apply-approved", action="store_true", help="Append only rows with status=approved.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    drafts = load_eval_case_drafts(args.eval_case_drafts)
    payload = apply_approved_eval_case_drafts(
        drafts,
        args.candidate_jsonl,
        run_id=args.run_id,
        dry_run=args.dry_run,
        apply_approved=args.apply_approved,
    )
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
