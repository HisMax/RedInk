"""
Promote approved Xiaohongshu eval case candidates into versioned eval sets.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


PROMOTION_SCHEMA_VERSION = "xhs_eval_case_promotion.v1"
VERSION_SCHEMA_VERSION = "xhs_quality_cases_version.v1"


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


def _load_base_cases(path: str | Path) -> List[Dict[str, Any]]:
    base_path = Path(path)
    if not base_path.exists():
        return []
    return json.loads(base_path.read_text(encoding="utf-8"))


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
