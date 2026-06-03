#!/usr/bin/env python3
"""
Promote approved XHS eval case candidates into a versioned eval set.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_eval_case_promotion import (
    load_eval_case_candidates,
    promote_approved_eval_case_candidates,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote approved XHS eval case candidates.")
    parser.add_argument("--candidates-jsonl", required=True, help="Path to xhs-eval-case-candidates.jsonl.")
    parser.add_argument("--base-cases", required=True, help="Base xhs quality cases JSON file.")
    parser.add_argument("--output", required=True, help="Output versioned eval set JSON file.")
    parser.add_argument("--version-id", required=True, help="Version id for the output eval set.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report what would be written without writing.")
    mode.add_argument("--promote-approved", action="store_true", help="Write a new eval set with approved candidates.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    candidates = load_eval_case_candidates(args.candidates_jsonl)
    payload = promote_approved_eval_case_candidates(
        candidates,
        base_cases_path=args.base_cases,
        output_path=args.output,
        version_id=args.version_id,
        dry_run=args.dry_run,
        promote_approved=args.promote_approved,
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
