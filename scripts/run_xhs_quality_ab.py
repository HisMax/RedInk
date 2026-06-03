#!/usr/bin/env python3
"""
Run A/B quality evaluation between base and candidate XHS case sets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.content_case_library import load_prompt_examples
from backend.services.xhs_quality_eval import (
    DEFAULT_CASES_PATH,
    DEFAULT_MAX_SCORE_DROP,
    DEFAULT_MIN_OVERALL,
    apply_quality_baseline,
    case_set_metadata,
    compare_quality_trend,
    load_quality_case_set,
    run_quality_eval,
    write_jsonl_report,
    write_markdown_report,
)


SCHEMA_VERSION = "xhs_quality_ab_comparison.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare base and candidate XHS quality case sets.")
    parser.add_argument("--base-cases", default=str(DEFAULT_CASES_PATH), help="Base quality cases JSON file.")
    parser.add_argument("--candidate-cases", required=True, help="Candidate quality cases JSON or versioned set.")
    parser.add_argument("--report-dir", default="reports/xhs-quality-ab", help="Output report directory.")
    parser.add_argument("--run-id", default="xhs_quality_ab", help="Run id prefix for A/B reports.")
    parser.add_argument("--min-overall", type=int, default=DEFAULT_MIN_OVERALL, help="Minimum overall score.")
    parser.add_argument(
        "--max-score-drop",
        type=int,
        default=DEFAULT_MAX_SCORE_DROP,
        help="Maximum allowed candidate score drop compared with base.",
    )
    parser.add_argument("--prompt-examples-jsonl", help="Optional JSONL prompt examples to guide live generation.")
    parser.add_argument("--prompt-examples-limit", type=int, default=3, help="Maximum prompt examples to load.")
    parser.add_argument("--live", action="store_true", help="Call live ContentService and QualityService.")
    parser.add_argument("--report-only", action="store_true", help="Always exit 0 after writing reports.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_dir = Path(args.report_dir)
    prompt_examples = _load_prompt_examples(args.prompt_examples_jsonl, args.prompt_examples_limit)
    base = _run_case_set(
        args.base_cases,
        output_dir=report_dir / "base",
        run_id=f"{args.run_id}_base",
        min_overall=args.min_overall,
        live=args.live,
        prompt_examples=prompt_examples,
    )
    candidate = _run_case_set(
        args.candidate_cases,
        output_dir=report_dir / "candidate",
        run_id=f"{args.run_id}_candidate",
        min_overall=args.min_overall,
        max_score_drop=args.max_score_drop,
        previous_results=base["results"],
        live=args.live,
        prompt_examples=prompt_examples,
    )
    payload = _comparison_payload(
        base,
        candidate,
        run_id=args.run_id,
        live=args.live,
        report_dir=report_dir,
        max_score_drop=args.max_score_drop,
    )
    print(json.dumps(_jsonable(payload), ensure_ascii=False, indent=2))
    gates_passed = (
        base["baseline"]["passed"]
        and candidate["baseline"]["passed"]
        and candidate["comparison"]["passed"]
    )
    if args.report_only or gates_passed:
        return 0
    return 1


def _load_prompt_examples(path: Optional[str], limit: int) -> List[Dict[str, Any]]:
    if not path:
        return []
    return load_prompt_examples(path, limit=limit)


def _run_case_set(
    cases_path: str | Path,
    *,
    output_dir: Path,
    run_id: str,
    min_overall: int,
    live: bool,
    prompt_examples: List[Dict[str, Any]],
    previous_results: Optional[List[Dict[str, Any]]] = None,
    max_score_drop: int = DEFAULT_MAX_SCORE_DROP,
) -> Dict[str, Any]:
    case_set = load_quality_case_set(cases_path)
    results = run_quality_eval(
        case_set["cases"],
        live=live,
        prompt_examples=prompt_examples,
    )
    results, baseline = apply_quality_baseline(results, min_overall=min_overall)
    comparison = {
        "passed": True,
        "previous_count": 0,
        "checked_count": len(results),
        "compared_count": 0,
        "skipped_count": len(results),
        "failed_count": 0,
        "max_score_drop": max_score_drop,
        "failures": [],
    }
    if previous_results is not None:
        results, comparison = compare_quality_trend(
            results,
            previous_results,
            max_score_drop=max_score_drop,
        )

    jsonl_path = output_dir / "xhs-quality-eval.jsonl"
    markdown_path = output_dir / "xhs-quality-eval.md"
    write_jsonl_report(results, jsonl_path)
    write_markdown_report(results, markdown_path)
    return {
        "run_id": run_id,
        "case_set": case_set_metadata(case_set),
        "case_count": len(case_set["cases"]),
        "success_count": sum(1 for result in results if result.get("error") is None),
        "baseline": baseline,
        "comparison": comparison,
        "paths": {
            "jsonl": jsonl_path,
            "markdown": markdown_path,
        },
        "results": results,
    }


def _comparison_payload(
    base: Dict[str, Any],
    candidate: Dict[str, Any],
    *,
    run_id: str,
    live: bool,
    report_dir: Path,
    max_score_drop: int,
) -> Dict[str, Any]:
    base_ids = {result.get("case_id") for result in base["results"] if result.get("case_id")}
    candidate_ids = {result.get("case_id") for result in candidate["results"] if result.get("case_id")}
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "live" if live else "dry-run",
        "run_id": run_id,
        "report_dir": report_dir,
        "base": _public_run_payload(base),
        "candidate": _public_run_payload(candidate),
        "summary": {
            "base_case_count": len(base_ids),
            "candidate_case_count": len(candidate_ids),
            "shared_case_count": len(base_ids & candidate_ids),
            "added_case_count": len(candidate_ids - base_ids),
            "removed_case_count": len(base_ids - candidate_ids),
            "base_baseline_passed": base["baseline"]["passed"],
            "candidate_baseline_passed": candidate["baseline"]["passed"],
            "comparison_passed": candidate["comparison"]["passed"],
            "max_score_drop": max_score_drop,
        },
    }


def _public_run_payload(run: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": run["run_id"],
        "case_set": run["case_set"],
        "case_count": run["case_count"],
        "success_count": run["success_count"],
        "baseline": run["baseline"],
        "comparison": run["comparison"],
        "paths": run["paths"],
    }


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
