"""
Promote approved Xiaohongshu eval case candidates into versioned eval sets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

from backend.services.xhs_quality_eval import load_quality_case_set
from backend.services.xhs_quality_history import summarize_loop_history


PROMOTION_SCHEMA_VERSION = "xhs_eval_case_promotion.v1"
VERSION_SCHEMA_VERSION = "xhs_quality_cases_version.v1"
RECOMMENDED_SCHEMA_VERSION = "xhs_recommended_eval_set.v1"


def load_eval_case_candidates(path: str | Path) -> List[Dict[str, Any]]:
    """Load eval case candidate JSONL rows."""
    candidate_path = Path(path)
    if not candidate_path.exists():
        return []
    rows = []
    with candidate_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def promote_approved_eval_case_candidates(
    candidates: Iterable[Dict[str, Any]],
    *,
    base_cases_path: str | Path,
    output_path: str | Path,
    version_id: str,
    dry_run: bool = False,
    promote_approved: bool = False,
    promoted_at: str | None = None,
) -> Dict[str, Any]:
    """Write a new versioned eval case set with approved candidates appended."""
    rows = list(candidates)
    approved = [row for row in rows if row.get("status") == "approved"]
    base_cases = _load_base_cases(base_cases_path)
    promoted_cases = [_case_from_candidate(row) for row in approved]
    version_payload = _version_payload(
        base_cases,
        promoted_cases,
        base_cases_path=base_cases_path,
        candidate_count=len(rows),
        version_id=version_id,
        promoted_at=promoted_at or _utc_now(),
    )
    output = Path(output_path)
    effective_dry_run = not promote_approved or dry_run
    written_count = 0
    if not effective_dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(version_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written_count = len(version_payload["cases"])
    return {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "version_id": version_id,
        "dry_run": effective_dry_run,
        "promote_approved": bool(promote_approved),
        "base_cases": str(base_cases_path),
        "output": output,
        "candidate_count": len(rows),
        "approved_count": len(approved),
        "base_case_count": len(base_cases),
        "promoted_count": len(promoted_cases),
        "would_write_count": len(version_payload["cases"]),
        "written_count": written_count,
        "version": version_payload,
    }


def mark_recommended_eval_case_set(
    *,
    version_id: str,
    candidate_cases_path: str | Path,
    ab_index_path: str | Path,
    output_path: str | Path,
    mark_recommended: bool = False,
    dry_run: bool = False,
    recommended_at: str | None = None,
) -> Dict[str, Any]:
    """Write a recommended eval set manifest when the dashboard gate passes."""
    loop_index_path = Path(ab_index_path).with_suffix(".loop-index-missing")
    dashboard = summarize_loop_history(
        loop_index_path,
        ab_index_path=ab_index_path,
    )["eval_set_versions"]
    version = _find_dashboard_version(dashboard, version_id)
    gate = _missing_gate(version_id) if version is None else dict(version.get("recommendation_gate", {}))
    gate = _merge_gate(gate, _candidate_cases_gate(version_id, candidate_cases_path))
    output = Path(output_path)
    effective_dry_run = dry_run or not mark_recommended
    payload = {
        "schema_version": RECOMMENDED_SCHEMA_VERSION,
        "version_id": version_id,
        "candidate_cases": str(candidate_cases_path),
        "ab_index": str(ab_index_path),
        "recommended_output": str(output),
        "latest_run_id": (version or {}).get("latest_run_id"),
        "recommended_at": recommended_at or _utc_now(),
        "gate": gate,
        "dry_run": effective_dry_run,
        "mark_recommended": bool(mark_recommended),
        "written": False,
    }
    if not effective_dry_run and gate.get("eligible") is True:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        payload["written"] = True
    return payload


def _load_base_cases(path: str | Path) -> List[Dict[str, Any]]:
    base_path = Path(path)
    if not base_path.exists():
        return []
    return json.loads(base_path.read_text(encoding="utf-8"))


def _find_dashboard_version(dashboard: Dict[str, Any], version_id: str) -> Dict[str, Any] | None:
    for version in dashboard.get("versions") or []:
        if version.get("version_id") == version_id:
            return version
    return None


def _missing_gate(version_id: str) -> Dict[str, Any]:
    return {
        "eligible": False,
        "status": "blocked",
        "reasons": [f"no A/B evidence found for version {version_id}"],
        "latest_run_id": None,
    }


def _candidate_cases_gate(version_id: str, candidate_cases_path: str | Path) -> Dict[str, Any]:
    candidate_path = Path(candidate_cases_path)
    if not candidate_path.exists():
        return _blocked_gate(["candidate cases file does not exist"])
    try:
        candidate_set = load_quality_case_set(candidate_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _blocked_gate([f"candidate cases file is invalid: {exc}"])
    candidate_version_id = candidate_set.get("version_id")
    if candidate_version_id != version_id:
        return _blocked_gate([f"candidate version_id is {candidate_version_id or 'unversioned'}"])
    return {
        "eligible": True,
        "status": "passed",
        "reasons": [],
        "latest_run_id": None,
    }


def _merge_gate(gate: Dict[str, Any], candidate_gate: Dict[str, Any]) -> Dict[str, Any]:
    if candidate_gate.get("eligible") is True:
        return gate
    reasons = list(gate.get("reasons") or [])
    reasons.extend(candidate_gate.get("reasons") or [])
    return {
        "eligible": False,
        "status": "blocked",
        "reasons": reasons,
        "latest_run_id": gate.get("latest_run_id"),
    }


def _blocked_gate(reasons: List[str]) -> Dict[str, Any]:
    return {
        "eligible": False,
        "status": "blocked",
        "reasons": reasons,
        "latest_run_id": None,
    }


def _version_payload(
    base_cases: List[Dict[str, Any]],
    promoted_cases: List[Dict[str, Any]],
    *,
    base_cases_path: str | Path,
    candidate_count: int,
    version_id: str,
    promoted_at: str,
) -> Dict[str, Any]:
    return {
        "schema_version": VERSION_SCHEMA_VERSION,
        "version_id": version_id,
        "created_at": promoted_at,
        "metadata": {
            "base_cases": str(base_cases_path),
            "base_case_count": len(base_cases),
            "candidate_count": candidate_count,
            "promoted_count": len(promoted_cases),
            "total_count": len(base_cases) + len(promoted_cases),
        },
        "cases": [dict(case) for case in base_cases] + promoted_cases,
    }


def _case_from_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": _safe_id(candidate.get("candidate_id")),
        "category": candidate.get("category"),
        "topic": candidate.get("topic"),
        "outline": candidate.get("outline") or {},
        "expected_traits": candidate.get("expected_traits") or [],
        "source_candidate_id": candidate.get("candidate_id"),
        "source_task_id": candidate.get("source_task_id"),
        "source_issue_id": candidate.get("source_issue_id"),
    }


def _safe_id(value: Any) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
