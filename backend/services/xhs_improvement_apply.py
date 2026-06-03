"""
Safe application helpers for approved Xiaohongshu improvement drafts.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


APPLY_SCHEMA_VERSION = "xhs_quality_improvement_apply.v1"
CANDIDATE_SCHEMA_VERSION = "xhs_eval_case_candidate.v1"


def load_eval_case_drafts(path: str | Path) -> List[Dict[str, Any]]:
    """Load eval case draft JSONL rows."""
    draft_path = Path(path)
    if not draft_path.exists():
        return []
    rows = []
    with draft_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def apply_approved_eval_case_drafts(
    drafts: Iterable[Dict[str, Any]],
    candidate_path: str | Path,
    *,
    run_id: str = "xhs_apply_improvements",
    dry_run: bool = False,
    apply_approved: bool = False,
    applied_at: str | None = None,
) -> Dict[str, Any]:
    """Append approved eval case drafts to a candidate JSONL file."""
    rows = list(drafts)
    approved = [row for row in rows if row.get("status") == "approved"]
    timestamp = applied_at or _utc_now()
    candidates = [
        _candidate_from_draft(row, run_id=run_id, applied_at=timestamp)
        for row in approved
    ]
    output_path = Path(candidate_path)
    target_exists = output_path.exists()
    effective_dry_run = not apply_approved or dry_run
    appended_count = 0
    if not effective_dry_run and candidates:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            for candidate in candidates:
                handle.write(json.dumps(candidate, ensure_ascii=False) + "\n")
                appended_count += 1

    return {
        "schema_version": APPLY_SCHEMA_VERSION,
        "run_id": run_id,
        "dry_run": effective_dry_run,
        "apply_approved": bool(apply_approved),
        "candidate_jsonl": output_path,
        "target_exists": target_exists,
        "draft_count": len(rows),
        "approved_count": len(approved),
        "would_append_count": len(candidates),
        "appended_count": appended_count,
        "candidates": candidates,
    }


def _candidate_from_draft(
    draft: Dict[str, Any],
    *,
    run_id: str,
    applied_at: str,
) -> Dict[str, Any]:
    return {
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "candidate_id": f"{run_id}:{draft.get('draft_id')}",
        "run_id": run_id,
        "source_draft_id": draft.get("draft_id"),
        "source_task_id": draft.get("source_task_id"),
        "source_issue_id": draft.get("source_issue_id"),
        "created_at": applied_at,
        "status": "candidate",
        "category": draft.get("category"),
        "topic": draft.get("topic"),
        "outline": draft.get("outline") or {},
        "expected_traits": draft.get("expected_focus") or [],
        "config_targets": draft.get("config_targets") or [],
        "acceptance_check": draft.get("acceptance_check"),
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
