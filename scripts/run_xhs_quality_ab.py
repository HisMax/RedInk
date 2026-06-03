#!/usr/bin/env python3
"""
Run A/B quality evaluation between base and candidate XHS case sets.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
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
INDEX_SCHEMA_VERSION = "xhs_quality_ab_index.v1"


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
    created_at = _utc_now()
    run_report = report_dir / "runs" / _safe_id(f"{args.run_id}_{created_at}") / "xhs-quality-ab-run.json"
    ab_index = report_dir / "xhs-quality-ab-index.jsonl"
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
        created_at=created_at,
        live=args.live,
        report_dir=report_dir,
        run_report=run_report,
        ab_index=ab_index,
        max_score_drop=args.max_score_drop,
    )
    payload["replay"] = {"command": _replay_command(args)}
    _write_run_report(payload, run_report)
    _append_ab_index(payload, ab_index)
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
    created_at: str,
    live: bool,
    report_dir: Path,
    run_report: Path,
    ab_index: Path,
    max_score_drop: int,
) -> Dict[str, Any]:
    base_ids = {result.get("case_id") for result in base["results"] if result.get("case_id")}
    candidate_ids = {result.get("case_id") for result in candidate["results"] if result.get("case_id")}
    added_ids = candidate_ids - base_ids
    added_results = [
        result for result in candidate["results"]
        if result.get("case_id") in added_ids
    ]
    comparison_failures = (candidate.get("comparison") or {}).get("failures") or []
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": created_at,
        "mode": "live" if live else "dry-run",
        "run_id": run_id,
        "paths": {
            "report_dir": report_dir,
            "run_report": run_report,
            "ab_index": ab_index,
        },
        "base": _public_run_payload(base),
        "candidate": _public_run_payload(candidate),
        "summary": {
            "base_case_count": len(base_ids),
            "candidate_case_count": len(candidate_ids),
            "shared_case_count": len(base_ids & candidate_ids),
            "added_case_count": len(candidate_ids - base_ids),
            "removed_case_count": len(base_ids - candidate_ids),
            "added_case_baseline_passed_count": sum(
                1 for result in added_results
                if result.get("baseline_passed") is True
            ),
            "added_case_baseline_failed_count": sum(
                1 for result in added_results
                if result.get("baseline_passed") is False
            ),
            "added_case_error_count": sum(
                1 for result in added_results
                if result.get("error")
            ),
            "regression_failed_count": len(comparison_failures),
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


def _write_run_report(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_ab_index(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_case_set = ((payload.get("candidate") or {}).get("case_set") or {})
    summary = payload.get("summary") or {}
    paths = payload.get("paths") or {}
    row = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "run_id": payload.get("run_id"),
        "created_at": payload.get("created_at"),
        "run_report": str(paths.get("run_report") or ""),
        "candidate_version_id": candidate_case_set.get("version_id"),
        "candidate_case_count": summary.get("candidate_case_count"),
        "shared_case_count": summary.get("shared_case_count"),
        "added_case_count": summary.get("added_case_count"),
        "added_case_baseline_passed_count": summary.get("added_case_baseline_passed_count"),
        "added_case_baseline_failed_count": summary.get("added_case_baseline_failed_count"),
        "regression_failed_count": summary.get("regression_failed_count"),
        "comparison_passed": summary.get("comparison_passed"),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _replay_command(args: argparse.Namespace) -> List[str]:
    command = [
        "uv",
        "run",
        "python",
        "scripts/run_xhs_quality_ab.py",
        "--base-cases",
        args.base_cases,
        "--candidate-cases",
        args.candidate_cases,
        "--report-dir",
        args.report_dir,
        "--run-id",
        args.run_id,
        "--min-overall",
        str(args.min_overall),
        "--max-score-drop",
        str(args.max_score_drop),
    ]
    if args.prompt_examples_jsonl:
        command.extend([
            "--prompt-examples-jsonl",
            args.prompt_examples_jsonl,
            "--prompt-examples-limit",
            str(args.prompt_examples_limit),
        ])
    if args.live:
        command.append("--live")
    if args.report_only:
        command.append("--report-only")
    return command


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _safe_id(value: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
