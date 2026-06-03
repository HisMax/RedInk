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
IMPROVEMENT_PLAN_SCHEMA_VERSION = "xhs_quality_improvement_plan.v1"
IMPROVEMENT_TASK_SCHEMA_VERSION = "xhs_quality_improvement_task.v1"
EVAL_SET_DASHBOARD_SCHEMA_VERSION = "xhs_eval_set_version_dashboard.v1"


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
    ab_index_path: Optional[str | Path] = None,
    limit: Optional[int] = None,
    include_reports: bool = True,
) -> Dict[str, Any]:
    """Build a compact trend summary from a quality loop replay index."""
    rows = load_loop_replay_index(index_path)
    if limit is not None:
        rows = rows[-limit:]
    ab_rows = load_loop_replay_index(ab_index_path) if ab_index_path else []
    if limit is not None:
        ab_rows = ab_rows[-limit:]

    runs = _summarize_runs(rows, include_reports=include_reports)
    ab_runs = _summarize_ab_runs(ab_rows, include_reports=include_reports)
    latest = runs[-1] if runs else {}
    summary = {
        "schema_version": SCHEMA_VERSION,
        "index_path": str(index_path),
        "ab_index_path": str(ab_index_path) if ab_index_path else None,
        "run_count": len(runs),
        "ab_run_count": len(ab_runs),
        "latest_run_id": latest.get("run_id"),
        "totals": _totals(runs),
        "runs": runs,
        "ab_runs": ab_runs,
        "eval_set_versions": _eval_set_version_dashboard(ab_runs, ab_index_path),
    }
    summary["diagnostics"] = diagnose_loop_history(summary)
    summary["improvement_plan"] = build_loop_improvement_plan(summary["diagnostics"])
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


def build_loop_improvement_plan(diagnostics: Dict[str, Any]) -> Dict[str, Any]:
    """Convert diagnostic issues into concrete prompt/revision/eval tasks."""
    tasks = []
    for issue in diagnostics.get("issue_groups") or []:
        tasks.extend(_tasks_for_issue(issue))
    for index, task in enumerate(tasks, start=1):
        task["order"] = index
    return {
        "schema_version": IMPROVEMENT_PLAN_SCHEMA_VERSION,
        "source_schema_version": diagnostics.get("schema_version"),
        "task_count": len(tasks),
        "tasks": tasks,
    }


def write_loop_history_markdown(summary: Dict[str, Any], path: str | Path) -> None:
    """Write a Markdown history report."""
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_markdown(summary), encoding="utf-8")


def write_improvement_plan_jsonl(plan: Dict[str, Any], path: str | Path) -> int:
    """Write improvement plan tasks as JSONL."""
    plan_path = Path(path)
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with plan_path.open("w", encoding="utf-8") as handle:
        for task in plan.get("tasks") or []:
            handle.write(json.dumps(task, ensure_ascii=False) + "\n")
            count += 1
    return count


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


def _summarize_ab_runs(
    rows: Iterable[Dict[str, Any]],
    *,
    include_reports: bool,
) -> List[Dict[str, Any]]:
    runs = []
    for row in rows:
        report = _load_run_report(row.get("run_report")) if include_reports else None
        summary = (report or {}).get("summary") or {}
        candidate = (report or {}).get("candidate") or {}
        candidate_case_set = candidate.get("case_set") or {}
        candidate_baseline = candidate.get("baseline") or {}
        comparison = candidate.get("comparison") or {}
        candidate_version_id = (
            candidate_case_set.get("version_id")
            or row.get("candidate_version_id")
            or "unversioned_candidate"
        )
        runs.append({
            "run_id": row.get("run_id") or (report or {}).get("run_id"),
            "created_at": row.get("created_at") or (report or {}).get("created_at"),
            "run_report": row.get("run_report"),
            "report_exists": report is not None,
            "candidate_version_id": candidate_version_id,
            "candidate_format": candidate_case_set.get("format"),
            "candidate_case_count": _summary_int(row, summary, "candidate_case_count"),
            "shared_case_count": _summary_int(row, summary, "shared_case_count"),
            "added_case_count": _summary_int(row, summary, "added_case_count"),
            "added_case_baseline_passed_count": _summary_int(row, summary, "added_case_baseline_passed_count"),
            "added_case_baseline_failed_count": _summary_int(row, summary, "added_case_baseline_failed_count"),
            "regression_failed_count": _summary_int(row, summary, "regression_failed_count"),
            "candidate_baseline_failed_count": _int(candidate_baseline.get("failed_count")),
            "candidate_baseline_passed": _optional_bool(candidate_baseline.get("passed")),
            "comparison_passed": _optional_bool(row.get("comparison_passed", summary.get("comparison_passed"))),
            "comparison_failed_count": _int(comparison.get("failed_count")),
        })
    return runs


def _eval_set_version_dashboard(
    ab_runs: Iterable[Dict[str, Any]],
    ab_index_path: Optional[str | Path],
) -> Dict[str, Any]:
    versions = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for run in ab_runs:
        grouped.setdefault(run.get("candidate_version_id") or "unversioned_candidate", []).append(run)

    for version_id, runs in sorted(grouped.items()):
        latest = runs[-1]
        regression_failed_count = sum(_int(run.get("regression_failed_count")) for run in runs)
        added_failed_count = sum(_int(run.get("added_case_baseline_failed_count")) for run in runs)
        comparison_failed_count = sum(1 for run in runs if run.get("comparison_passed") is False)
        risk_level, risk_reasons = _eval_set_risk(
            regression_failed_count=regression_failed_count,
            added_failed_count=added_failed_count,
            comparison_failed_count=comparison_failed_count,
        )
        versions.append({
            "version_id": version_id,
            "candidate_format": latest.get("candidate_format"),
            "ab_run_count": len(runs),
            "latest_run_id": latest.get("run_id"),
            "latest_created_at": latest.get("created_at"),
            "candidate_case_count": _int(latest.get("candidate_case_count")),
            "shared_case_count": _int(latest.get("shared_case_count")),
            "added_case_count": _int(latest.get("added_case_count")),
            "added_case_baseline_passed_count": sum(
                _int(run.get("added_case_baseline_passed_count")) for run in runs
            ),
            "added_case_baseline_failed_count": added_failed_count,
            "regression_failed_count": regression_failed_count,
            "comparison_passed_count": sum(1 for run in runs if run.get("comparison_passed") is True),
            "comparison_failed_count": comparison_failed_count,
            "ab_run_ids": [run.get("run_id") for run in runs if run.get("run_id")],
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
        })
    return {
        "schema_version": EVAL_SET_DASHBOARD_SCHEMA_VERSION,
        "ab_index_path": str(ab_index_path) if ab_index_path else None,
        "version_count": len(versions),
        "versions": versions,
    }


def _eval_set_risk(
    *,
    regression_failed_count: int,
    added_failed_count: int,
    comparison_failed_count: int,
) -> tuple[str, List[str]]:
    reasons = []
    if regression_failed_count:
        reasons.append(f"{regression_failed_count} shared cases regressed beyond threshold")
    if added_failed_count:
        reasons.append(f"{added_failed_count} added cases failed baseline")
    if comparison_failed_count:
        reasons.append(f"{comparison_failed_count} A/B runs failed comparison gate")
    if regression_failed_count:
        return "high", reasons
    if added_failed_count or comparison_failed_count:
        return "medium", reasons
    return "low", reasons


def _summary_int(row: Dict[str, Any], summary: Dict[str, Any], key: str) -> int:
    return _int(summary.get(key) if summary.get(key) is not None else row.get(key))


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


def _tasks_for_issue(issue: Dict[str, Any]) -> List[Dict[str, Any]]:
    issue_id = issue.get("issue_id")
    if issue_id == "missing_run_report":
        return [_task(
            issue,
            stage="monitoring",
            task_type="artifact_recovery",
            title="恢复质量闭环运行报告",
            action="恢复缺失的 run report，或使用 replay command 重跑对应 run 后重新生成 history。",
            config_targets=["LOOP_REPLAY_INDEX", "LOOP_HISTORY_INDEX", "xhs-quality-loop-run.json"],
            acceptance_check="make summarize-loop 不再出现 missing_run_report 诊断。",
        )]
    if issue_id in ("baseline_overall_below_threshold", "baseline_gate_failed"):
        return [
            _task(
                issue,
                stage="prompt",
                task_type="generation_prompt_update",
                title="强化首轮内容生成 prompt",
                action="把 baseline 失败样本中的高频问题补进内容生成 prompt，重点约束标题钩子、正文结构、信息密度和收藏理由。",
                config_targets=["EVAL_PROMPT_EXAMPLES", "LOOP_PROMPT_EXAMPLES", "xhs-quality-prompt-examples.jsonl"],
                acceptance_check="下一轮 make xhs-quality-loop 的 baseline_failed_count 下降。",
            ),
            _task(
                issue,
                stage="eval",
                task_type="quality_gate_review",
                title="复核首轮质量门禁和评测集",
                action="检查 LOOP_MIN_OVERALL/EVAL_MIN_OVERALL 是否符合当前 MVP 阶段，并补充能暴露标题、正文、标签问题的评测案例。",
                config_targets=["LOOP_MIN_OVERALL", "EVAL_MIN_OVERALL", "tests/fixtures/xhs_quality_cases.json"],
                acceptance_check="门禁阈值、评测案例和目标内容质量之间有明确记录，且趋势报告可比较。",
            ),
        ]
    if issue_id == "baseline_decision_not_allowed":
        return [_task(
            issue,
            stage="eval",
            task_type="decision_gate_review",
            title="复核质量决策门禁",
            action="检查 allowed decisions 和 QualityService 返回决策，确认 reject/revise 的具体触发原因。",
            config_targets=["DEFAULT_ALLOWED_DECISIONS", "EVAL_REPORT_ONLY", "LOOP_MIN_OVERALL"],
            acceptance_check="下一轮诊断能区分分数不足和决策不允许两类失败。",
        )]
    if issue_id == "re_evaluation_not_improved":
        return [_task(
            issue,
            stage="revision",
            task_type="revision_prompt_update",
            title="收紧二次改稿 prompt",
            action="要求 revision 明确引用 baseline 失败原因，并输出逐项修复摘要，避免只做表层润色。",
            config_targets=["REVISION_LIVE", "LOOP_LIVE_REVISION", "LOOP_MIN_IMPROVEMENT"],
            acceptance_check="下一轮 re_evaluation_failure_count 下降，re_evaluation_improved_count 上升。",
        )]
    if issue_id == "quality_examples_missing":
        return [_task(
            issue,
            stage="prompt",
            task_type="prompt_example_supply",
            title="补齐可复用优质样本",
            action="降低样本导出门槛或补充人工 review 后的优质样本，保证下一轮生成能引用稳定示例。",
            config_targets=["LOOP_MIN_QUALITY_OVERALL", "LOOP_MIN_SCORE_DELTA", "CASE_QUALITY_EXAMPLES"],
            acceptance_check="xhs-quality-prompt-examples.jsonl 至少导出 1 条样本。",
        )]
    if issue_id == "quality_examples_declined":
        return [_task(
            issue,
            stage="eval",
            task_type="quality_example_regression_check",
            title="排查优质样本产出下滑",
            action="对比下滑 run 和前一轮 run report，确认是门禁变严、输入案例变化，还是生成质量下降。",
            config_targets=["LOOP_MIN_QUALITY_OVERALL", "LOOP_MIN_SCORE_DELTA", "LOOP_HISTORY_LIMIT"],
            acceptance_check="重放后能解释 quality_examples_delta 为负的原因，并记录修复动作。",
        )]
    return [_task(
        issue,
        stage="eval",
        task_type="diagnostic_review",
        title=f"复盘诊断问题 {issue_id}",
        action=issue.get("action") or "复盘诊断问题并记录改进动作。",
        config_targets=["LOOP_HISTORY_MARKDOWN"],
        acceptance_check="问题有明确 owner、配置目标和下一轮验证指标。",
    )]


def _task(
    issue: Dict[str, Any],
    *,
    stage: str,
    task_type: str,
    title: str,
    action: str,
    config_targets: List[str],
    acceptance_check: str,
) -> Dict[str, Any]:
    return {
        "schema_version": IMPROVEMENT_TASK_SCHEMA_VERSION,
        "task_id": f"{stage}_{issue.get('issue_id')}",
        "source_issue_id": issue.get("issue_id"),
        "source_priority": issue.get("priority"),
        "severity": issue.get("severity"),
        "stage": stage,
        "task_type": task_type,
        "title": title,
        "action": action,
        "config_targets": config_targets,
        "affected_run_ids": issue.get("affected_run_ids") or [],
        "acceptance_check": acceptance_check,
        "status": "proposed",
    }


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
    dashboard = summary.get("eval_set_versions") or {}
    lines.extend([
        "",
        "## Eval Set Versions",
        "",
        f"- Schema: `{dashboard.get('schema_version') or ''}`",
        f"- A/B index: `{dashboard.get('ab_index_path') or ''}`",
        f"- Versions: {dashboard.get('version_count', 0)}",
        "",
        "| Version | Runs | Latest Run | Cases | Added | Added Pass | Added Fail | Regressions | Comparison Fail | Risk |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for version in dashboard.get("versions") or []:
        lines.append(
            "| {version_id} | {runs} | {latest} | {cases} | {added} | {added_pass} | {added_fail} | {regressions} | {comparison_fail} | {risk} |".format(
                version_id=version.get("version_id") or "",
                runs=_display_number(version.get("ab_run_count")),
                latest=version.get("latest_run_id") or "",
                cases=_display_number(version.get("candidate_case_count")),
                added=_display_number(version.get("added_case_count")),
                added_pass=_display_number(version.get("added_case_baseline_passed_count")),
                added_fail=_display_number(version.get("added_case_baseline_failed_count")),
                regressions=_display_number(version.get("regression_failed_count")),
                comparison_fail=_display_number(version.get("comparison_failed_count")),
                risk=version.get("risk_level") or "",
            )
        )
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
    improvement_plan = summary.get("improvement_plan") or {}
    lines.extend([
        "",
        "## Improvement Plan",
        "",
        f"- Schema: `{improvement_plan.get('schema_version') or ''}`",
        f"- Tasks: {improvement_plan.get('task_count', 0)}",
        "",
        "| Order | Stage | Task | Source Issue | Config Targets | Acceptance Check |",
        "| ---: | --- | --- | --- | --- | --- |",
    ])
    for task in improvement_plan.get("tasks") or []:
        lines.append(
            "| {order} | {stage} | {task_id} | {issue_id} | {targets} | {check} |".format(
                order=task.get("order"),
                stage=task.get("stage") or "",
                task_id=task.get("task_id") or "",
                issue_id=task.get("source_issue_id") or "",
                targets=", ".join(task.get("config_targets") or []),
                check=task.get("acceptance_check") or "",
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


def _optional_bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


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
