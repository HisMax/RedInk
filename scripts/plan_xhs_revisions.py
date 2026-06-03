#!/usr/bin/env python3
"""
Plan or run Xiaohongshu content revisions from a case library.
"""

from __future__ import annotations

import argparse
import json

from backend.services.content_case_library import load_case_records
from backend.services.content_revision_loop import (
    build_revision_requests,
    run_revision_requests,
    write_revision_requests,
    write_revision_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build revision requests from a content case library.")
    parser.add_argument("--library", required=True, help="Path to the content case JSONL library.")
    parser.add_argument("--requests-jsonl", help="Optional JSONL path for planned revision requests.")
    parser.add_argument("--results-jsonl", help="Optional JSONL path for live revision results.")
    parser.add_argument("--run-id", default="xhs_revision_loop", help="Revision run id.")
    parser.add_argument("--limit", type=int, help="Maximum number of revision requests to plan.")
    parser.add_argument("--live", action="store_true", help="Call the live revision advisor service.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_case_records(args.library)
    requests = build_revision_requests(records, run_id=args.run_id, limit=args.limit)

    if args.requests_jsonl:
        write_revision_requests(requests, args.requests_jsonl)

    results = None
    if args.live:
        from backend.services.revision import get_revision_service

        results = run_revision_requests(requests, revision_service=get_revision_service())
        if args.results_jsonl:
            write_revision_results(results, args.results_jsonl)

    payload = {
        "library": args.library,
        "run_id": args.run_id,
        "candidate_count": len(requests),
        "requests_jsonl": args.requests_jsonl,
        "live": args.live,
        "results_count": len(results) if results is not None else 0,
        "results_jsonl": args.results_jsonl,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
