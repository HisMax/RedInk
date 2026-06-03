#!/usr/bin/env python3
"""
Run the full Xiaohongshu content quality improvement loop.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.services.xhs_quality_loop import run_quality_loop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Xiaohongshu quality improvement loop.")
    parser.add_argument("--cases", default="tests/fixtures/xhs_quality_cases.json", help="Path to quality cases JSON.")
    parser.add_argument("--report-dir", default="reports/xhs-quality-loop", help="Output report directory.")
    parser.add_argument("--case-library", help="Optional case library JSONL path. Defaults under --report-dir.")
    parser.add_argument("--run-id", default="xhs_quality_loop", help="Loop run id.")
    parser.add_argument("--min-overall", type=int, default=95, help="Minimum first-pass overall score.")
    parser.add_argument("--min-improvement", type=int, default=0, help="Minimum re-evaluation score lift.")
    parser.add_argument("--min-quality-overall", type=int, default=85, help="Minimum score for exported quality examples.")
    parser.add_argument("--min-score-delta", type=int, default=3, help="Minimum score lift for exported quality examples.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum prompt examples to export.")
    parser.add_argument("--prompt-examples-jsonl", help="Optional prompt examples to guide live content generation.")
    parser.add_argument("--prompt-examples-limit", type=int, default=3, help="Maximum prompt examples to load.")
    parser.add_argument("--live-content", action="store_true", help="Use live ContentService for first-pass generation.")
    parser.add_argument("--live-revision", action="store_true", help="Use live RevisionService for second-pass rewriting.")
    parser.add_argument("--live-re-evaluation", action="store_true", help="Use live QualityService for re-evaluation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run_quality_loop(
        cases_path=args.cases,
        report_dir=args.report_dir,
        case_library_path=args.case_library,
        run_id=args.run_id,
        min_overall=args.min_overall,
        min_improvement=args.min_improvement,
        min_quality_overall=args.min_quality_overall,
        min_score_delta=args.min_score_delta,
        limit=args.limit,
        live_content=args.live_content,
        live_revision=args.live_revision,
        live_re_evaluation=args.live_re_evaluation,
        prompt_examples_path=args.prompt_examples_jsonl,
        prompt_examples_limit=args.prompt_examples_limit,
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
