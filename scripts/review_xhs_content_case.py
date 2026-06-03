#!/usr/bin/env python3
"""
Review a Xiaohongshu content case library record.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.services.content_case_library import (
    load_case_records,
    save_case_records,
    update_case_review,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update human review fields for a content case record.")
    parser.add_argument("--library", required=True, help="Path to the content case JSONL library.")
    parser.add_argument("--record-id", required=True, help="Record id to update, e.g. run_id:case_id.")
    parser.add_argument("--status", default="reviewed", help="Review status to set.")
    parser.add_argument("--publishable", choices=["true", "false"], help="Whether the case is publishable.")
    parser.add_argument("--viral-potential", type=int, help="Human viral potential score, usually 1-5.")
    parser.add_argument("--issue-type", action="append", dest="issue_types", help="Issue type tag. Repeatable.")
    parser.add_argument("--selected-title", help="Human selected title.")
    parser.add_argument("--edited-copywriting", help="Human edited copywriting text.")
    parser.add_argument("--edited-copywriting-file", help="Read edited copywriting text from a file.")
    parser.add_argument("--notes", help="Human review notes.")
    parser.add_argument("--reviewed-at", help="Stable review timestamp for reproducible runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    edited_copywriting = args.edited_copywriting
    if args.edited_copywriting_file:
        edited_copywriting = Path(args.edited_copywriting_file).read_text(encoding="utf-8")

    records = load_case_records(args.library)
    updated_records, updated = update_case_review(
        records,
        args.record_id,
        status=args.status,
        publishable=_parse_bool(args.publishable),
        viral_potential=args.viral_potential,
        issue_types=args.issue_types,
        selected_title=args.selected_title,
        edited_copywriting=edited_copywriting,
        notes=args.notes,
        reviewed_at=args.reviewed_at,
    )
    saved_count = save_case_records(updated_records, args.library)
    payload = {
        "updated": True,
        "record_id": args.record_id,
        "library": args.library,
        "saved_count": saved_count,
        "human_review": updated["human_review"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value == "true"


if __name__ == "__main__":
    raise SystemExit(main())
