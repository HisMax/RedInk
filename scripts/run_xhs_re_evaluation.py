#!/usr/bin/env python3
"""
Run re-evaluation for revised Xiaohongshu content cases.
"""

from __future__ import annotations

import argparse
import json

from backend.services.content_case_library import load_case_records, save_case_records
from backend.services.xhs_re_evaluation import (
    DEFAULT_MIN_IMPROVEMENT,
    apply_improvement_gate,
    apply_re_evaluation_results_to_case_library,
    run_re_evaluation,
    write_re_evaluation_jsonl,
    write_re_evaluation_markdown,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-evaluate revised Xiaohongshu content cases.")
    parser.add_argument("--library", required=True, help="Path to the content case JSONL library.")
    parser.add_argument("--jsonl", help="Optional JSONL report output path.")
    parser.add_argument("--markdown", help="Optional Markdown report output path.")
    parser.add_argument("--run-id", default="xhs_re_evaluation", help="Re-evaluation run id.")
    parser.add_argument("--limit", type=int, help="Maximum number of revised cases to evaluate.")
    parser.add_argument(
        "--min-improvement",
        type=int,
        default=DEFAULT_MIN_IMPROVEMENT,
        help="Minimum required score delta compared with the source case.",
    )
    parser.add_argument("--live", action="store_true", help="Call the live quality service.")
    parser.add_argument("--update-case-library", action="store_true", help="Write scores back to the case library.")
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after writing reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_case_records(args.library)
    results = run_re_evaluation(
        records,
        live=args.live,
        run_id=args.run_id,
        limit=args.limit,
    )
    results, comparison = apply_improvement_gate(results, min_improvement=args.min_improvement)

    if args.jsonl:
        write_re_evaluation_jsonl(results, args.jsonl)
    if args.markdown:
        write_re_evaluation_markdown(results, args.markdown)

    case_library = None
    if args.update_case_library:
        updated_records, updated_count = apply_re_evaluation_results_to_case_library(records, results)
        saved_count = save_case_records(updated_records, args.library)
        case_library = {
            "path": args.library,
            "updated_count": updated_count,
            "library_count": saved_count,
        }

    payload = {
        "mode": "live" if args.live else "dry-run",
        "library": args.library,
        "run_id": args.run_id,
        "candidate_count": len(results),
        "success_count": sum(1 for result in results if result.get("error") is None),
        "comparison": comparison,
        "case_library": case_library,
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.report_only or comparison["passed"]:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
