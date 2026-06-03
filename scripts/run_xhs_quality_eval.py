#!/usr/bin/env python3
"""
Run Xiaohongshu quality seed evaluations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.content_case_library import append_case_records, build_case_records, load_prompt_examples
from backend.services.xhs_quality_eval import (
    DEFAULT_ALLOWED_DECISIONS,
    DEFAULT_CASES_PATH,
    DEFAULT_MAX_SCORE_DROP,
    DEFAULT_MIN_OVERALL,
    apply_quality_baseline,
    case_set_metadata,
    compare_quality_trend,
    load_quality_case_set,
    load_previous_eval_results,
    run_quality_eval,
    write_jsonl_report,
    write_markdown_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Xiaohongshu quality evaluation seeds.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to quality cases JSON fixture.")
    parser.add_argument("--live", action="store_true", help="Call live ContentService and QualityService.")
    parser.add_argument("--jsonl", help="Optional path for JSONL report output.")
    parser.add_argument("--markdown", help="Optional path for Markdown report output.")
    parser.add_argument("--case-library", help="Optional JSONL content case library path to append.")
    parser.add_argument("--prompt-examples-jsonl", help="Optional JSONL prompt examples to guide live generation.")
    parser.add_argument("--prompt-examples-limit", type=int, default=3, help="Maximum prompt examples to load.")
    parser.add_argument("--run-id", help="Stable run id for reports and case library records.")
    parser.add_argument("--min-overall", type=int, default=DEFAULT_MIN_OVERALL, help="Minimum overall score.")
    parser.add_argument(
        "--compare-jsonl",
        help="Optional previous JSONL or JSON evaluation report for trend comparison.",
    )
    parser.add_argument(
        "--max-score-drop",
        type=int,
        default=DEFAULT_MAX_SCORE_DROP,
        help="Maximum allowed score drop compared with previous report.",
    )
    parser.add_argument(
        "--allow-decision",
        action="append",
        dest="allowed_decisions",
        help="Allowed quality decision. Repeat to allow multiple decisions.",
    )
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after writing reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_id = args.run_id or "xhs_quality_eval"
    case_set = load_quality_case_set(args.cases)
    cases = case_set["cases"]
    prompt_examples = []
    prompt_examples_payload = None
    if args.prompt_examples_jsonl:
        prompt_examples = load_prompt_examples(
            args.prompt_examples_jsonl,
            limit=args.prompt_examples_limit,
        )
        prompt_examples_payload = {
            "path": args.prompt_examples_jsonl,
            "loaded_count": len(prompt_examples),
            "limit": args.prompt_examples_limit,
        }

    results = run_quality_eval(
        cases,
        live=args.live,
        prompt_examples=prompt_examples,
    )
    allowed_decisions = args.allowed_decisions or list(DEFAULT_ALLOWED_DECISIONS)
    results, baseline = apply_quality_baseline(
        results,
        min_overall=args.min_overall,
        allowed_decisions=allowed_decisions,
    )
    comparison = None
    if args.compare_jsonl:
        previous_results = load_previous_eval_results(args.compare_jsonl)
        results, comparison = compare_quality_trend(
            results,
            previous_results,
            max_score_drop=args.max_score_drop,
        )

    if args.jsonl:
        write_jsonl_report(results, Path(args.jsonl))
    if args.markdown:
        write_markdown_report(results, Path(args.markdown))
    case_library = None
    if args.case_library:
        records = build_case_records(
            results,
            run_id=run_id,
            source="xhs_quality_eval",
        )
        saved_count = append_case_records(records, Path(args.case_library))
        case_library = {
            "path": args.case_library,
            "run_id": run_id,
            "saved_count": saved_count,
        }

    payload = {
        "mode": "live" if args.live else "dry-run",
        "run_id": run_id,
        "case_set": case_set_metadata(case_set),
        "case_count": len(cases),
        "success_count": sum(1 for result in results if result.get("error") is None),
        "baseline": baseline,
        "comparison": comparison,
        "case_library": case_library,
        "prompt_examples": prompt_examples_payload,
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    comparison_passed = comparison is None or comparison["passed"]
    if args.report_only or (baseline["passed"] and comparison_passed):
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
