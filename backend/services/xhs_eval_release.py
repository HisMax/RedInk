"""
Release summaries for recommended Xiaohongshu eval sets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.services.xhs_quality_eval import load_quality_case_set
from backend.services.xhs_quality_history import summarize_loop_history


RELEASE_SUMMARY_SCHEMA_VERSION = "xhs_eval_set_release_summary.v1"
RECOMMENDED_SCHEMA_VERSION = "xhs_recommended_eval_set.v1"


def summarize_eval_release(
    *,
    recommended_manifest_path: str | Path,
    ab_index_path: str | Path,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a release audit summary for a recommended eval set manifest."""
    manifest_path = Path(recommended_manifest_path)
    ab_path = Path(ab_index_path)
    manifest, manifest_error = _load_manifest(manifest_path)
    version_id = manifest.get("version_id")
    candidate_cases = manifest.get("candidate_cases")
    latest_run_id = manifest.get("latest_run_id")

    checks: List[Dict[str, Any]] = []
    checks.append(_check(
        "manifest_exists",
        manifest_error is None,
        "recommended manifest loaded" if manifest_error is None else manifest_error,
    ))
    checks.append(_check(
        "manifest_schema",
        manifest.get("schema_version") == RECOMMENDED_SCHEMA_VERSION,
        "recommended manifest schema is valid",
        f"recommended manifest schema_version is {manifest.get('schema_version') or 'missing'}",
    ))
    gate = manifest.get("gate") or {}
    checks.append(_check(
        "manifest_gate",
        gate.get("eligible") is True and gate.get("status") == "passed",
        "recommended manifest gate passed",
        "recommended manifest gate is not passed",
    ))

    candidate_set = None
    candidate_error = None
    if candidate_cases:
        try:
            candidate_set = load_quality_case_set(candidate_cases)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            candidate_error = f"candidate cases file is invalid: {exc}"
    checks.append(_check(
        "candidate_cases",
        bool(candidate_cases) and candidate_error is None,
        "candidate cases file loaded",
        candidate_error or "recommended manifest candidate_cases is missing",
    ))
    checks.append(_check(
        "candidate_version",
        bool(candidate_set) and candidate_set.get("version_id") == version_id,
        "candidate version_id matches manifest",
        f"candidate version_id is {(candidate_set or {}).get('version_id') or 'missing'}",
    ))

    dashboard = summarize_loop_history(
        ab_path.with_suffix(".loop-index-missing"),
        ab_index_path=ab_path,
    )["eval_set_versions"]
    dashboard_version = _find_dashboard_version(dashboard, version_id)
    checks.append(_check(
        "dashboard_version",
        dashboard_version is not None,
        "dashboard contains recommended version",
        f"dashboard has no version {version_id or 'missing'}",
    ))
    dashboard_latest_run_id = (dashboard_version or {}).get("latest_run_id")
    checks.append(_check(
        "latest_run",
        bool(latest_run_id) and latest_run_id == dashboard_latest_run_id,
        "latest_run_id matches dashboard latest run",
        "latest_run_id does not match dashboard latest run",
    ))
    dashboard_gate = (dashboard_version or {}).get("recommendation_gate") or {}
    checks.append(_check(
        "dashboard_gate",
        dashboard_gate.get("eligible") is True and dashboard_gate.get("status") == "passed",
        "dashboard recommendation gate passed",
        "dashboard recommendation gate is not passed",
    ))

    reasons = [check["message"] for check in checks if check["passed"] is False]
    status = "passed" if not reasons else "blocked"
    summary = {
        "schema_version": RELEASE_SUMMARY_SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now(),
        "status": status,
        "reasons": reasons,
        "recommended_manifest": str(manifest_path),
        "ab_index": str(ab_path),
        "version_id": version_id,
        "candidate_cases": str(candidate_cases or ""),
        "candidate_case_count": (candidate_set or {}).get("case_count"),
        "latest_run_id": latest_run_id,
        "checks": checks,
        "dashboard": _dashboard_payload(dashboard_version),
    }
    return summary


def write_eval_release_summary_json(summary: Dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_eval_release_summary_markdown(summary: Dict[str, Any], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_markdown(summary), encoding="utf-8")


def _load_manifest(path: Path) -> tuple[Dict[str, Any], Optional[str]]:
    if not path.exists():
        return {}, "recommended manifest does not exist"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"recommended manifest is invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return {}, "recommended manifest must be a JSON object"
    return payload, None


def _find_dashboard_version(dashboard: Dict[str, Any], version_id: Any) -> Dict[str, Any] | None:
    for version in dashboard.get("versions") or []:
        if version.get("version_id") == version_id:
            return version
    return None


def _check(
    check_id: str,
    passed: bool,
    passed_message: str,
    failed_message: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "message": passed_message if passed else (failed_message or passed_message),
    }


def _dashboard_payload(version: Dict[str, Any] | None) -> Dict[str, Any]:
    if not version:
        return {}
    gate = version.get("recommendation_gate") or {}
    return {
        "version_id": version.get("version_id"),
        "risk_level": version.get("risk_level"),
        "gate_status": gate.get("status"),
        "gate_eligible": gate.get("eligible"),
        "ab_run_count": version.get("ab_run_count"),
        "latest_run_id": version.get("latest_run_id"),
        "candidate_case_count": version.get("candidate_case_count"),
        "added_case_count": version.get("added_case_count"),
        "added_case_baseline_failed_count": version.get("added_case_baseline_failed_count"),
        "regression_failed_count": version.get("regression_failed_count"),
        "comparison_failed_count": version.get("comparison_failed_count"),
    }


def _markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# XHS Eval Set Release Summary",
        "",
        f"- Status: `{summary.get('status')}`",
        f"- Version: `{summary.get('version_id') or ''}`",
        f"- Candidate cases: `{summary.get('candidate_cases') or ''}`",
        f"- Latest A/B run: `{summary.get('latest_run_id') or ''}`",
        f"- Recommended manifest: `{summary.get('recommended_manifest') or ''}`",
        f"- A/B index: `{summary.get('ab_index') or ''}`",
        "",
        "| Check | Passed | Message |",
        "| --- | --- | --- |",
    ]
    for check in summary.get("checks") or []:
        lines.append(
            "| {check_id} | {passed} | {message} |".format(
                check_id=check.get("check_id") or "",
                passed="yes" if check.get("passed") else "no",
                message=check.get("message") or "",
            )
        )
    return "\n".join(lines) + "\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

