# Eval Set Release Summary Design

## Goal

Generate a single audit artifact for each recommended XHS eval set release. The
summary should answer which eval set version is recommended, which candidate
file it points to, which A/B run supports it, and whether the release evidence is
fresh.

## Current Context

The release workflow already writes these artifacts:

- `xhs-quality-cases.next.json`: promoted candidate eval set
- `xhs-quality-ab-index.jsonl`: replayable A/B index
- `xhs-quality-loop-history.md`: history dashboard with eval set version gates
- `xhs-quality-cases.recommended.json`: recommended eval set manifest

The artifacts are valid but spread across multiple files. Operators need one
small release summary for review, handoff, and future CI integration.

## Design

Add a release summary service and CLI:

- `backend/services/xhs_eval_release.py`
- `scripts/summarize_xhs_eval_release.py`
- `make summarize-eval-release`

The service reads the recommended manifest, loads the candidate eval set, builds
the eval set version dashboard from the A/B index, and verifies that:

1. the manifest schema is `xhs_recommended_eval_set.v1`
2. the manifest gate is passed
3. the candidate file exists
4. the candidate file `version_id` matches the manifest `version_id`
5. the dashboard contains that `version_id`
6. the manifest `latest_run_id` matches the dashboard latest run
7. the dashboard recommendation gate is still passed

The CLI writes both JSON and Markdown summaries. It exits `0` when all checks
pass and `1` when any freshness or gate check fails. It still writes the summary
on failure so the reason can be inspected.

## Output Shape

JSON summary:

```json
{
  "schema_version": "xhs_eval_set_release_summary.v1",
  "status": "passed",
  "version_id": "xhs_quality_cases_next",
  "candidate_cases": "reports/xhs-quality-loop/xhs-quality-cases.next.json",
  "candidate_case_count": 6,
  "recommended_manifest": "reports/xhs-quality-loop/xhs-quality-cases.recommended.json",
  "ab_index": "reports/xhs-quality-ab/xhs-quality-ab-index.jsonl",
  "latest_run_id": "xhs_quality_ab",
  "checks": [
    {"check_id": "manifest_gate", "passed": true, "message": "recommended manifest gate passed"}
  ],
  "dashboard": {
    "risk_level": "low",
    "gate_status": "passed",
    "added_case_count": 1,
    "regression_failed_count": 0,
    "comparison_failed_count": 0
  }
}
```

Markdown summary should be compact: a short status block plus a checks table.

## Makefile Flow

Add:

```make
make summarize-eval-release
```

Then append it to:

```make
make release-eval-cases
```

The release pipeline should only generate a passed summary after the existing
recommendation gate succeeds.

## Testing

Add tests for:

- CLI writes a passed JSON/Markdown summary for fresh recommended evidence
- CLI writes a blocked summary and exits non-zero for stale `latest_run_id`
- Makefile target writes the summary
- `release-eval-cases` writes the summary on success
- failed release still does not write the recommended manifest or success summary

