#!/usr/bin/env python3
"""
Run Xiaohongshu quality seed evaluations.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.xhs_quality_eval import (
    DEFAULT_ALLOWED_DECISIONS,
    DEFAULT_CASES_PATH,
    DEFAULT_MIN_OVERALL,
    apply_quality_baseline,
    load_quality_cases,
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
    parser.add_argument("--min-overall", type=int, default=DEFAULT_MIN_OVERALL, help="Minimum overall score.")
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
    cases = load_quality_cases(args.cases)
    results = run_quality_eval(cases, live=args.live)
    allowed_decisions = args.allowed_decisions or list(DEFAULT_ALLOWED_DECISIONS)
    results, baseline = apply_quality_baseline(
        results,
        min_overall=args.min_overall,
        allowed_decisions=allowed_decisions,
    )

    if args.jsonl:
        write_jsonl_report(results, Path(args.jsonl))
    if args.markdown:
        write_markdown_report(results, Path(args.markdown))

    payload = {
        "mode": "live" if args.live else "dry-run",
        "case_count": len(cases),
        "success_count": sum(1 for result in results if result.get("error") is None),
        "baseline": baseline,
        "results": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if args.report_only or baseline["passed"]:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
