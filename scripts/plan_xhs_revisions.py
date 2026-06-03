#!/usr/bin/env python3
"""
Plan or run Xiaohongshu content revisions from a case library.
"""

from __future__ import annotations

import argparse
import json

from backend.services.content_case_library import load_case_records, save_case_records
from backend.services.content_revision_loop import (
    apply_revision_results_to_case_library,
    build_revision_requests,
    load_revision_results,
    run_revision_requests,
    write_revision_requests,
    write_revision_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build revision requests from a content case library.")
    parser.add_argument("--library", required=True, help="Path to the content case JSONL library.")
    parser.add_argument("--requests-jsonl", help="Optional JSONL path for planned revision requests.")
    parser.add_argument("--results-jsonl", help="Optional JSONL path for live revision results.")
    parser.add_argument("--apply-results-jsonl", help="Load existing revision results and apply them to cases.")
    parser.add_argument(
        "--append-revised-cases",
        action="store_true",
        help="Upsert revised case records into the case library.",
    )
    parser.add_argument(
        "--revised-case-library",
        help="Optional output case library path for revised records. Defaults to --library.",
    )
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

    applied_results = []
    if args.apply_results_jsonl:
        applied_results = load_revision_results(args.apply_results_jsonl)
    elif args.append_revised_cases and results is not None:
        applied_results = results

    revised_case_library = None
    if args.append_revised_cases:
        output_library = args.revised_case_library or args.library
        updated_records, revised_records = apply_revision_results_to_case_library(
            records,
            applied_results,
            run_id=args.run_id,
        )
        saved_total = save_case_records(updated_records, output_library)
        revised_case_library = {
            "path": output_library,
            "saved_count": len(revised_records),
            "library_count": saved_total,
        }

    payload = {
        "library": args.library,
        "run_id": args.run_id,
        "candidate_count": len(requests),
        "requests_jsonl": args.requests_jsonl,
        "live": args.live,
        "results_count": len(results) if results is not None else 0,
        "results_jsonl": args.results_jsonl,
        "applied_results_count": len(applied_results),
        "revised_case_library": revised_case_library,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
