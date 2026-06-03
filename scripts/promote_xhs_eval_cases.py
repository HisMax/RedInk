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
    mark_recommended_eval_case_set,
    promote_approved_eval_case_candidates,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote approved XHS eval case candidates.")
    parser.add_argument("--candidates-jsonl", help="Path to xhs-eval-case-candidates.jsonl.")
    parser.add_argument("--base-cases", help="Base xhs quality cases JSON file.")
    parser.add_argument("--output", help="Output versioned eval set JSON file.")
    parser.add_argument("--version-id", required=True, help="Version id for the output eval set.")
    parser.add_argument("--candidate-cases", help="Candidate versioned eval set JSON file.")
    parser.add_argument("--ab-index", help="Path to xhs-quality-ab-index.jsonl.")
    parser.add_argument("--recommended-output", help="Output recommended eval set manifest JSON file.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Report what would be written without writing.")
    mode.add_argument("--promote-approved", action="store_true", help="Write a new eval set with approved candidates.")
    mode.add_argument("--mark-recommended", action="store_true", help="Write a recommended eval set manifest if gates pass.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mark_recommended or _is_recommendation_dry_run(args):
        _require_args(args, ["candidate_cases", "ab_index", "recommended_output"])
        payload = mark_recommended_eval_case_set(
            version_id=args.version_id,
            candidate_cases_path=args.candidate_cases,
            ab_index_path=args.ab_index,
            output_path=args.recommended_output,
            dry_run=args.dry_run,
            mark_recommended=args.mark_recommended,
        )
        print(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2))
        if args.dry_run or payload.get("gate", {}).get("eligible") is True:
            return 0
        return 1

    _require_args(args, ["candidates_jsonl", "base_cases", "output"])
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


def _is_recommendation_dry_run(args: argparse.Namespace) -> bool:
    return bool(args.dry_run and (args.candidate_cases or args.ab_index or args.recommended_output))


def _require_args(args: argparse.Namespace, names: list[str]) -> None:
    missing = [f"--{name.replace('_', '-')}" for name in names if not getattr(args, name)]
    if missing:
        raise SystemExit(f"missing required arguments: {', '.join(missing)}")


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
