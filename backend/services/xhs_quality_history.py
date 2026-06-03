"""
Summaries for Xiaohongshu quality loop replay history.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "xhs_quality_loop_history.v1"
DIAGNOSTICS_SCHEMA_VERSION = "xhs_quality_loop_diagnostics.v1"


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
    summary = {
        "schema_version": SCHEMA_VERSION,
        "index_path": str(index_path),
        "run_count": len(runs),
        "latest_run_id": latest.get("run_id"),
        "totals": _totals(runs),
        "runs": runs,
    }
    summary["diagnostics"] = diagnose_loop_history(summary)
    return summary


def diagnose_loop_history(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Build prioritized diagnostic issue groups from a loop history summary."""
    runs = list(summary.get("runs") or [])
    issue_groups = []
    issue_groups.extend(_missing_report_issues(runs))
    issue_groups.extend(_baseline_issues(runs))
    issue_groups.extend(_re_evaluation_issues(runs))
    issue_groups.extend(_quality_example_issues(runs))
    issue_groups.sort(key=lambda issue: (issue["priority"], issue["issue_id"]))
    return {
        "schema_version": DIAGNOSTICS_SCHEMA_VERSION,
        "issue_count": len(issue_groups),
        "issue_groups": issue_groups,
        "next_actions": _next_actions(issue_groups),
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
        baseline_reasons = _baseline_failure_reasons(report)
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
            "re_evaluation_failure_count": _re_evaluation_failure_count(report),
            "case_library_record_count": _optional_int(metrics.get("case_library_record_count")),
            "manual_examples_count": _optional_int(metrics.get("manual_examples_count")),
            "quality_examples_count": quality_examples_count,
            "quality_examples_delta": _delta(quality_examples_count, previous_quality_examples),
            "baseline_failure_reasons": baseline_reasons,
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


def _missing_report_issues(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    affected = [run for run in runs if not run.get("report_exists")]
    if not affected:
        return []
    return [_issue(
        issue_id="missing_run_report",
        severity="high",
        priority=1,
        count=len(affected),
        affected_runs=affected,
        evidence=[f"{len(affected)} run reports are missing from replay index references."],
        recommendation="恢复或重跑缺失的 run report，保证索引里的回放入口可以追溯。",
        action="恢复或重跑缺失的 run report，然后重新执行 make summarize-loop。",
    )]


def _baseline_issues(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    affected = [run for run in runs if _int(run.get("baseline_failed_count")) > 0]
    if not affected:
        return []

    reason_counts = Counter()
    for run in affected:
        for reason, count in (run.get("baseline_failure_reasons") or {}).items():
            reason_counts[reason] += count
    issue_id = reason_counts.most_common(1)[0][0] if reason_counts else "baseline_gate_failed"
    latest = affected[-1]
    latest_failed = _int(latest.get("baseline_failed_count"))
    latest_cases = _int(latest.get("evaluation_case_count"))
    failure_rate = latest_failed / latest_cases if latest_cases else 0
    return [_issue(
        issue_id=issue_id,
        severity="high" if failure_rate >= 0.5 else "medium",
        priority=1 if failure_rate >= 0.5 else 2,
        count=sum(_int(run.get("baseline_failed_count")) for run in affected),
        affected_runs=affected,
        evidence=[
            f"{len(affected)} runs have baseline failures.",
            f"Latest run failed {latest_failed}/{latest_cases} cases.",
        ],
        recommendation="优先加强首轮内容生成的结构、标题钩子和可执行信息密度，降低进入改稿环节的比例。",
        action="复盘 baseline 失败样本，把高频问题补进生成 prompt 和优质样本库。",
    )]


def _re_evaluation_issues(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    affected = [run for run in runs if _int(run.get("re_evaluation_failure_count")) > 0]
    if not affected:
        return []
    return [_issue(
        issue_id="re_evaluation_not_improved",
        severity="high",
        priority=2,
        count=sum(_int(run.get("re_evaluation_failure_count")) for run in affected),
        affected_runs=affected,
        evidence=[f"{len(affected)} runs have revised cases that did not improve enough."],
        recommendation="收紧改稿指令，要求 revision 明确解决 baseline 失败原因，并输出可验证的修改摘要。",
        action="抽样复盘未提升改稿结果，更新 revision prompt 的改写约束。",
    )]


def _quality_example_issues(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not runs:
        return []
    issues = []
    latest = runs[-1]
    if _int(latest.get("quality_examples_count")) == 0:
        issues.append(_issue(
            issue_id="quality_examples_missing",
            severity="high",
            priority=2,
            count=1,
            affected_runs=[latest],
            evidence=["Latest run exported 0 verified quality examples."],
            recommendation="先保证至少产出一批可复用的优质样本，再进入 live 扩量生成。",
            action="降低样本导出门槛或补充人工优质样本，重新生成 prompt examples。",
        ))

    declined = [run for run in runs if (run.get("quality_examples_delta") or 0) < 0]
    if declined:
        issues.append(_issue(
            issue_id="quality_examples_declined",
            severity="medium",
            priority=3,
            count=len(declined),
            affected_runs=declined,
            evidence=[f"{len(declined)} runs exported fewer quality examples than the previous run."],
            recommendation="对比下滑 run 的评测门禁和输入案例，确认是否门槛变严或内容质量退化。",
            action="用 replay command 重放下滑 run，并对比前一轮报告。",
        ))
    return issues


def _issue(
    *,
    issue_id: str,
    severity: str,
    priority: int,
    count: int,
    affected_runs: List[Dict[str, Any]],
    evidence: List[str],
    recommendation: str,
    action: str,
) -> Dict[str, Any]:
    return {
        "issue_id": issue_id,
        "severity": severity,
        "priority": priority,
        "count": count,
        "affected_run_ids": [run.get("run_id") for run in affected_runs if run.get("run_id")],
        "evidence": evidence,
        "recommendation": recommendation,
        "action": action,
    }


def _next_actions(issue_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "priority": issue["priority"],
            "issue_id": issue["issue_id"],
            "action": issue["action"],
        }
        for issue in issue_groups[:5]
    ]


def _baseline_failure_reasons(report: Optional[Dict[str, Any]]) -> Dict[str, int]:
    if not report:
        return {}
    failures = ((report.get("gates") or {}).get("baseline") or {}).get("failures") or []
    reasons = Counter()
    for failure in failures:
        reasons[_normalize_baseline_reason(failure.get("reason"))] += 1
    return dict(reasons)


def _normalize_baseline_reason(reason: Any) -> str:
    text = str(reason or "").lower()
    if "overall" in text and "below" in text:
        return "baseline_overall_below_threshold"
    if "decision" in text:
        return "baseline_decision_not_allowed"
    return "baseline_gate_failed"


def _re_evaluation_failure_count(report: Optional[Dict[str, Any]]) -> int:
    if not report:
        return 0
    comparison = ((report.get("gates") or {}).get("re_evaluation") or {})
    failures = comparison.get("failures") or []
    return len(failures)


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
    diagnostics = summary.get("diagnostics") or {}
    lines.extend([
        "",
        "## Diagnostics",
        "",
        f"- Schema: `{diagnostics.get('schema_version') or ''}`",
        f"- Issues: {diagnostics.get('issue_count', 0)}",
        "",
        "| Priority | Severity | Issue | Count | Affected Runs | Recommendation |",
        "| ---: | --- | --- | ---: | --- | --- |",
    ])
    for issue in diagnostics.get("issue_groups") or []:
        lines.append(
            "| {priority} | {severity} | {issue_id} | {count} | {runs} | {recommendation} |".format(
                priority=issue.get("priority"),
                severity=issue.get("severity") or "",
                issue_id=issue.get("issue_id") or "",
                count=_display_number(issue.get("count")),
                runs=", ".join(issue.get("affected_run_ids") or []),
                recommendation=issue.get("recommendation") or "",
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
