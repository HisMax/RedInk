"""
Summaries for Xiaohongshu quality loop replay history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "xhs_quality_loop_history.v1"


def load_loop_replay_index(path: str | Path) -> List[Dict[str, Any]]:
    """Load replay index JSONL rows."""
    index_path = Path(path)
    if not index_path.exists():
        return []
    rows = []
    with index_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def summarize_loop_history(
    index_path: str | Path,
    *,
    limit: Optional[int] = None,
    include_reports: bool = True,
) -> Dict[str, Any]:
    """Build a compact trend summary from a quality loop replay index."""
    rows = load_loop_replay_index(index_path)
    if limit is not None:
        rows = rows[-limit:]

    runs = _summarize_runs(rows, include_reports=include_reports)
    latest = runs[-1] if runs else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "index_path": str(index_path),
        "run_count": len(runs),
        "latest_run_id": latest.get("run_id"),
        "totals": _totals(runs),
        "runs": runs,
    }


def write_loop_history_markdown(summary: Dict[str, Any], path: str | Path) -> None:
    """Write a Markdown history report."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_markdown(summary), encoding="utf-8")


def _summarize_runs(
    rows: Iterable[Dict[str, Any]],
    *,
    include_reports: bool,
) -> List[Dict[str, Any]]:
    runs = []
    previous_quality_examples = None
    previous_baseline_failed = None

    for row in rows:
        report = _load_run_report(row.get("run_report")) if include_reports else None
        metrics = _merge_metrics(row, report)
        quality_examples_count = _int(metrics.get("quality_examples_count"))
        baseline_failed_count = _int(metrics.get("baseline_failed_count"))
        run = {
            "run_id": row.get("run_id"),
            "created_at": row.get("created_at"),
            "run_report": row.get("run_report"),
            "report_exists": report is not None,
            "evaluation_case_count": _int(metrics.get("evaluation_case_count")),
            "baseline_failed_count": baseline_failed_count,
            "baseline_failed_delta": _delta(baseline_failed_count, previous_baseline_failed),
            "revision_request_count": _int(metrics.get("revision_request_count")),
            "re_evaluation_candidate_count": _int(metrics.get("re_evaluation_candidate_count")),
            "re_evaluation_improved_count": _optional_int(metrics.get("re_evaluation_improved_count")),
            "case_library_record_count": _optional_int(metrics.get("case_library_record_count")),
            "manual_examples_count": _optional_int(metrics.get("manual_examples_count")),
            "quality_examples_count": quality_examples_count,
            "quality_examples_delta": _delta(quality_examples_count, previous_quality_examples),
            "replay_command": _replay_command(report),
        }
        previous_quality_examples = quality_examples_count
        previous_baseline_failed = baseline_failed_count
        runs.append(run)

    return runs


def _merge_metrics(row: Dict[str, Any], report: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = {}
    if report:
        metrics.update(report.get("metrics") or {})
    for key in (
        "evaluation_case_count",
        "baseline_failed_count",
        "revision_request_count",
        "re_evaluation_candidate_count",
        "quality_examples_count",
    ):
        if row.get(key) is not None:
            metrics[key] = row.get(key)
    return metrics


def _load_run_report(path: Any) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    report_path = Path(path)
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def _totals(runs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    rows = list(runs)
    return {
        "evaluation_case_count": sum(_int(row.get("evaluation_case_count")) for row in rows),
        "baseline_failed_count": sum(_int(row.get("baseline_failed_count")) for row in rows),
        "revision_request_count": sum(_int(row.get("revision_request_count")) for row in rows),
        "re_evaluation_candidate_count": sum(_int(row.get("re_evaluation_candidate_count")) for row in rows),
        "quality_examples_count": sum(_int(row.get("quality_examples_count")) for row in rows),
    }


def _markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# Xiaohongshu Quality Loop History",
        "",
        f"- Schema: `{summary.get('schema_version')}`",
        f"- Index: `{summary.get('index_path')}`",
        f"- Runs: {summary.get('run_count', 0)}",
        f"- Latest run: `{summary.get('latest_run_id') or ''}`",
        "",
        "| Run ID | Created At | Cases | Baseline Failed | Revisions | Re-eval | Improved | Quality Examples | Delta | Report |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in summary.get("runs") or []:
        lines.append(
            "| {run_id} | {created_at} | {cases} | {failed} | {revisions} | {reeval} | {improved} | {examples} | {delta} | {report} |".format(
                run_id=run.get("run_id") or "",
                created_at=run.get("created_at") or "",
                cases=_display_number(run.get("evaluation_case_count")),
                failed=_display_number(run.get("baseline_failed_count")),
                revisions=_display_number(run.get("revision_request_count")),
                reeval=_display_number(run.get("re_evaluation_candidate_count")),
                improved=_display_number(run.get("re_evaluation_improved_count")),
                examples=_display_number(run.get("quality_examples_count")),
                delta=_display_delta(run.get("quality_examples_delta")),
                report=_display_report(run),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _replay_command(report: Optional[Dict[str, Any]]) -> Optional[List[str]]:
    if not report:
        return None
    command = (report.get("replay") or {}).get("command")
    return command if isinstance(command, list) else None


def _delta(current: int, previous: Optional[int]) -> Optional[int]:
    if previous is None:
        return None
    return current - previous


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _optional_int(value: Any) -> Optional[int]:
    return value if isinstance(value, int) else None


def _display_number(value: Any) -> str:
    return "" if value is None else str(value)


def _display_delta(value: Any) -> str:
    if value is None:
        return ""
    return f"+{value}" if value > 0 else str(value)


def _display_report(run: Dict[str, Any]) -> str:
    report = run.get("run_report") or ""
    if not report:
        return ""
    return report if run.get("report_exists") else f"missing: {report}"
