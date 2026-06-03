#!/usr/bin/env python3
"""
Summarize a Xiaohongshu content case library.
"""

from __future__ import annotations

import argparse
import json

from backend.services.content_case_library import (
    load_case_records,
    select_prompt_examples,
    select_re_evaluated_prompt_examples,
    summarize_case_records,
    write_case_library_report,
    write_prompt_examples,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a content case JSONL library.")
    parser.add_argument("--library", required=True, help="Path to the content case JSONL library.")
    parser.add_argument("--markdown", help="Optional Markdown summary output path.")
    parser.add_argument("--examples-jsonl", help="Optional JSONL prompt examples output path.")
    parser.add_argument("--quality-examples-jsonl", help="Optional JSONL output for re-evaluated prompt examples.")
    parser.add_argument("--min-viral-potential", type=int, default=4, help="Minimum viral potential for examples.")
    parser.add_argument("--min-quality-overall", type=int, default=85, help="Minimum quality score for auto examples.")
    parser.add_argument("--min-score-delta", type=int, default=3, help="Minimum score lift for auto examples.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of prompt examples to export.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_case_records(args.library)
    summary = summarize_case_records(records)
    examples = select_prompt_examples(
        records,
        min_viral_potential=args.min_viral_potential,
        limit=args.limit,
    )
    quality_examples = select_re_evaluated_prompt_examples(
        records,
        min_overall=args.min_quality_overall,
        min_score_delta=args.min_score_delta,
        limit=args.limit,
    )

    if args.markdown:
        write_case_library_report(summary, args.markdown)
    if args.examples_jsonl:
        write_prompt_examples(examples, args.examples_jsonl)
    if args.quality_examples_jsonl:
        write_prompt_examples(quality_examples, args.quality_examples_jsonl)

    payload = {
        "library": args.library,
        "summary": summary,
        "examples_count": len(examples),
        "quality_examples_count": len(quality_examples),
        "markdown": args.markdown,
        "examples_jsonl": args.examples_jsonl,
        "quality_examples_jsonl": args.quality_examples_jsonl,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
