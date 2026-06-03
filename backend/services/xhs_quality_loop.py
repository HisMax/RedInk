"""
One-command Xiaohongshu quality improvement loop.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.services.content_case_library import (
    build_case_records,
    load_prompt_examples,
    save_case_records,
    select_prompt_examples,
    select_re_evaluated_prompt_examples,
    summarize_case_records,
    write_case_library_report,
    write_prompt_examples,
)
from backend.services.content_revision_loop import (
    RESULT_SCHEMA_VERSION as REVISION_RESULT_SCHEMA_VERSION,
    apply_revision_results_to_case_library,
    build_revision_requests,
    run_revision_requests,
    write_revision_requests,
    write_revision_results,
)
from backend.services.xhs_quality_eval import (
    DEFAULT_ALLOWED_DECISIONS,
    DEFAULT_CASES_PATH,
    apply_quality_baseline,
    load_quality_cases,
    run_quality_eval,
    write_jsonl_report,
    write_markdown_report,
)
from backend.services.xhs_re_evaluation import (
    apply_improvement_gate,
    apply_re_evaluation_results_to_case_library,
    run_re_evaluation,
    write_re_evaluation_jsonl,
    write_re_evaluation_markdown,
)


def run_quality_loop(
    *,
    cases_path: str | Path = DEFAULT_CASES_PATH,
    report_dir: str | Path = "reports/xhs-quality-loop",
    case_library_path: Optional[str | Path] = None,
    replay_index_path: Optional[str | Path] = None,
    run_id: str = "xhs_quality_loop",
    min_overall: int = 95,
    min_improvement: int = 0,
    min_quality_overall: int = 85,
    min_score_delta: int = 3,
    limit: int = 20,
    live_content: bool = False,
    live_revision: bool = False,
    live_re_evaluation: bool = False,
    prompt_examples_path: Optional[str | Path] = None,
    prompt_examples_limit: int = 3,
) -> Dict[str, Any]:
    """Run the full evaluate-revise-re-evaluate-export loop."""
    report_path = Path(report_dir)
    report_path.mkdir(parents=True, exist_ok=True)
    case_library = Path(case_library_path) if case_library_path else report_path / "xhs-content-cases.jsonl"
    replay_index = Path(replay_index_path) if replay_index_path else report_path / "xhs-quality-loop-index.jsonl"
    created_at = _utc_now()
    run_report = report_path / "runs" / _safe_id(f"{run_id}_{created_at}") / "xhs-quality-loop-run.json"
    paths = _build_paths(report_path, case_library, replay_index, run_report)

    prompt_examples = []
    if prompt_examples_path:
        prompt_examples = load_prompt_examples(prompt_examples_path, limit=prompt_examples_limit)

    cases = load_quality_cases(cases_path)
    eval_results = run_quality_eval(
        cases,
        live=live_content,
        prompt_examples=prompt_examples,
    )
    eval_results, baseline = apply_quality_baseline(
        eval_results,
        min_overall=min_overall,
        allowed_decisions=list(DEFAULT_ALLOWED_DECISIONS),
    )
    write_jsonl_report(eval_results, paths["evaluation_jsonl"])
    write_markdown_report(eval_results, paths["evaluation_markdown"])

    records = build_case_records(
        eval_results,
        run_id=run_id,
        source="xhs_quality_loop",
    )
    save_case_records(records, case_library)

    revision_run_id = f"{run_id}_revision"
    revision_requests = build_revision_requests(records, run_id=revision_run_id)
    write_revision_requests(revision_requests, paths["revision_requests"])
    if live_revision:
        from backend.services.revision import get_revision_service

        revision_results = run_revision_requests(
            revision_requests,
            revision_service=get_revision_service(),
        )
    else:
        revision_results = build_dry_run_revision_results(revision_requests, run_id=revision_run_id)
    write_revision_results(revision_results, paths["revision_results"])

    records, revised_records = apply_revision_results_to_case_library(
        records,
        revision_results,
        run_id=revision_run_id,
    )
    save_case_records(records, case_library)

    re_eval_run_id = f"{run_id}_reeval"
    re_eval_results = run_re_evaluation(
        records,
        live=live_re_evaluation,
        run_id=re_eval_run_id,
    )
    re_eval_results, comparison = apply_improvement_gate(
        re_eval_results,
        min_improvement=min_improvement,
    )
    write_re_evaluation_jsonl(re_eval_results, paths["re_evaluation_jsonl"])
    write_re_evaluation_markdown(re_eval_results, paths["re_evaluation_markdown"])

    records, updated_count = apply_re_evaluation_results_to_case_library(records, re_eval_results)
    save_case_records(records, case_library)

    summary = summarize_case_records(records)
    manual_examples = select_prompt_examples(records, limit=limit)
    quality_examples = select_re_evaluated_prompt_examples(
        records,
        min_overall=min_quality_overall,
        min_score_delta=min_score_delta,
        limit=limit,
    )
    write_case_library_report(summary, paths["case_report"])
    write_prompt_examples(manual_examples, paths["manual_examples"])
    write_prompt_examples(quality_examples, paths["quality_examples"])

    payload = {
        "run_id": run_id,
        "mode": _mode_payload(live_content, live_revision, live_re_evaluation),
        "paths": paths,
        "prompt_examples": {
            "path": Path(prompt_examples_path) if prompt_examples_path else None,
            "loaded_count": len(prompt_examples),
            "limit": prompt_examples_limit,
        },
        "evaluation": {
            "case_count": len(cases),
            "success_count": sum(1 for result in eval_results if result.get("error") is None),
        },
        "baseline": baseline,
        "revision": {
            "request_count": len(revision_requests),
            "result_count": len(revision_results),
            "revised_case_count": len(revised_records),
        },
        "re_evaluation": {
            "candidate_count": len(re_eval_results),
            "updated_count": updated_count,
            "comparison": comparison,
        },
        "case_library": {
            "path": case_library,
            "record_count": len(records),
            "summary": summary,
        },
        "manual_examples": {
            "count": len(manual_examples),
            "path": paths["manual_examples"],
        },
        "quality_examples": {
            "count": len(quality_examples),
            "path": paths["quality_examples"],
        },
    }
    run_report = _build_run_report(
        payload,
        cases_path=cases_path,
        report_dir=report_path,
        case_library=case_library,
        replay_index=replay_index,
        run_id=run_id,
        min_overall=min_overall,
        min_improvement=min_improvement,
        min_quality_overall=min_quality_overall,
        min_score_delta=min_score_delta,
        limit=limit,
        live_content=live_content,
        live_revision=live_revision,
        live_re_evaluation=live_re_evaluation,
        prompt_examples_path=prompt_examples_path,
        prompt_examples_limit=prompt_examples_limit,
        created_at=created_at,
    )
    _write_run_report(run_report, paths["run_report"])
    _append_replay_index(run_report, paths["replay_index"])
    return payload


def build_dry_run_revision_results(
    revision_requests: Iterable[Dict[str, Any]],
    *,
    run_id: str,
    revised_at: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build deterministic revision results for local loop smoke runs."""
    timestamp = revised_at or _utc_now()
    results = []
    for request in revision_requests:
        revision_input = request.get("revision_input") or {}
        topic = revision_input.get("topic", "")
        copywriting = revision_input.get("copywriting", "")
        source_record_id = request.get("source_record_id")
        results.append({
            "schema_version": REVISION_RESULT_SCHEMA_VERSION,
            "request_id": request.get("request_id"),
            "run_id": request.get("run_id") or run_id,
            "source_record_id": source_record_id,
            "success": True,
            "trace_id": f"xhs_loop_rev_{_safe_id(source_record_id)}",
            "revised_at": timestamp,
            "revision": {
                "titles": [f"改后：{topic}"],
                "copywriting": f"改后正文：{copywriting}",
                "tags": revision_input.get("tags", []),
                "revision_summary": ["强化钩子和行动路径"],
            },
            "error": None,
        })
    return results


def _build_paths(
    report_dir: Path,
    case_library: Path,
    replay_index: Path,
    run_report: Path,
) -> Dict[str, Path]:
    return {
        "report_dir": report_dir,
        "case_library": case_library,
        "evaluation_jsonl": report_dir / "xhs-quality-eval.jsonl",
        "evaluation_markdown": report_dir / "xhs-quality-eval.md",
        "revision_requests": report_dir / "xhs-revision-requests.jsonl",
        "revision_results": report_dir / "xhs-revision-results.jsonl",
        "re_evaluation_jsonl": report_dir / "xhs-re-evaluation.jsonl",
        "re_evaluation_markdown": report_dir / "xhs-re-evaluation.md",
        "case_report": report_dir / "xhs-content-case-report.md",
        "manual_examples": report_dir / "xhs-prompt-examples.jsonl",
        "quality_examples": report_dir / "xhs-quality-prompt-examples.jsonl",
        "run_report": run_report,
        "replay_index": replay_index,
    }


def _build_run_report(
    payload: Dict[str, Any],
    *,
    cases_path: str | Path,
    report_dir: Path,
    case_library: Path,
    replay_index: Path,
    run_id: str,
    min_overall: int,
    min_improvement: int,
    min_quality_overall: int,
    min_score_delta: int,
    limit: int,
    live_content: bool,
    live_revision: bool,
    live_re_evaluation: bool,
    prompt_examples_path: Optional[str | Path],
    prompt_examples_limit: int,
    created_at: str,
) -> Dict[str, Any]:
    metrics = _metrics_payload(payload)
    return {
        "schema_version": "xhs_quality_loop_run.v1",
        "run_id": run_id,
        "created_at": created_at,
        "mode": payload["mode"],
        "parameters": {
            "cases_path": str(cases_path),
            "report_dir": str(report_dir),
            "case_library_path": str(case_library),
            "replay_index_path": str(replay_index),
            "run_id": run_id,
            "min_overall": min_overall,
            "min_improvement": min_improvement,
            "min_quality_overall": min_quality_overall,
            "min_score_delta": min_score_delta,
            "limit": limit,
            "live_content": live_content,
            "live_revision": live_revision,
            "live_re_evaluation": live_re_evaluation,
            "prompt_examples_path": str(prompt_examples_path) if prompt_examples_path else None,
            "prompt_examples_limit": prompt_examples_limit,
        },
        "artifacts": _artifact_payload(payload["paths"]),
        "metrics": metrics,
        "gates": {
            "baseline": payload["baseline"],
            "re_evaluation": payload["re_evaluation"]["comparison"],
        },
        "replay": {
            "command": _replay_command(
                cases_path=cases_path,
                report_dir=report_dir,
                case_library=case_library,
                replay_index=replay_index,
                run_id=run_id,
                min_overall=min_overall,
                min_improvement=min_improvement,
                min_quality_overall=min_quality_overall,
                min_score_delta=min_score_delta,
                limit=limit,
                live_content=live_content,
                live_revision=live_revision,
                live_re_evaluation=live_re_evaluation,
                prompt_examples_path=prompt_examples_path,
                prompt_examples_limit=prompt_examples_limit,
            ),
        },
    }


def _metrics_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    baseline = payload["baseline"]
    comparison = payload["re_evaluation"]["comparison"]
    return {
        "evaluation_case_count": payload["evaluation"]["case_count"],
        "evaluation_success_count": payload["evaluation"]["success_count"],
        "baseline_failed_count": baseline.get("failed_count", 0),
        "revision_request_count": payload["revision"]["request_count"],
        "revision_result_count": payload["revision"]["result_count"],
        "revised_case_count": payload["revision"]["revised_case_count"],
        "re_evaluation_candidate_count": payload["re_evaluation"]["candidate_count"],
        "re_evaluation_updated_count": payload["re_evaluation"]["updated_count"],
        "re_evaluation_improved_count": comparison.get("improved_count", 0),
        "case_library_record_count": payload["case_library"]["record_count"],
        "manual_examples_count": payload["manual_examples"]["count"],
        "quality_examples_count": payload["quality_examples"]["count"],
    }


def _artifact_payload(paths: Dict[str, Path]) -> Dict[str, str]:
    return {key: str(path) for key, path in paths.items()}


def _replay_command(
    *,
    cases_path: str | Path,
    report_dir: Path,
    case_library: Path,
    replay_index: Path,
    run_id: str,
    min_overall: int,
    min_improvement: int,
    min_quality_overall: int,
    min_score_delta: int,
    limit: int,
    live_content: bool,
    live_revision: bool,
    live_re_evaluation: bool,
    prompt_examples_path: Optional[str | Path],
    prompt_examples_limit: int,
) -> List[str]:
    command = [
        "uv",
        "run",
        "python",
        "scripts/run_xhs_quality_loop.py",
        "--cases",
        str(cases_path),
        "--report-dir",
        str(report_dir),
        "--case-library",
        str(case_library),
        "--replay-index",
        str(replay_index),
        "--run-id",
        run_id,
        "--min-overall",
        str(min_overall),
        "--min-improvement",
        str(min_improvement),
        "--min-quality-overall",
        str(min_quality_overall),
        "--min-score-delta",
        str(min_score_delta),
        "--limit",
        str(limit),
    ]
    if prompt_examples_path:
        command.extend([
            "--prompt-examples-jsonl",
            str(prompt_examples_path),
            "--prompt-examples-limit",
            str(prompt_examples_limit),
        ])
    if live_content:
        command.append("--live-content")
    if live_revision:
        command.append("--live-revision")
    if live_re_evaluation:
        command.append("--live-re-evaluation")
    return command


def _write_run_report(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _append_replay_index(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "schema_version": "xhs_quality_loop_index.v1",
        "run_id": report["run_id"],
        "created_at": report["created_at"],
        "run_report": report["artifacts"]["run_report"],
        "evaluation_case_count": report["metrics"]["evaluation_case_count"],
        "baseline_failed_count": report["metrics"]["baseline_failed_count"],
        "revision_request_count": report["metrics"]["revision_request_count"],
        "re_evaluation_candidate_count": report["metrics"]["re_evaluation_candidate_count"],
        "quality_examples_count": report["metrics"]["quality_examples_count"],
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _mode_payload(
    live_content: bool,
    live_revision: bool,
    live_re_evaluation: bool,
) -> Dict[str, bool]:
    return {
        "live_content": live_content,
        "live_revision": live_revision,
        "live_re_evaluation": live_re_evaluation,
    }


def _safe_id(value: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value))


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
