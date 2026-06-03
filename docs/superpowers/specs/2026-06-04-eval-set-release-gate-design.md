# Eval Set Release Gate Design

## Goal

Turn the XHS eval set version dashboard into a release gate. A candidate
`xhs-quality-cases.next.json` can be marked as the current recommended eval set
only when its latest A/B evidence is low risk and every added case passed the
candidate baseline.

## Current Context

The project already has these pieces:

- `scripts/promote_xhs_eval_cases.py` writes a versioned candidate eval set from
  approved eval case candidates.
- `scripts/run_xhs_quality_ab.py` compares the base fixture with the candidate
  eval set and appends replayable rows to `xhs-quality-ab-index.jsonl`.
- `backend/services/xhs_quality_history.py` summarizes A/B rows into an eval set
  version dashboard with risk levels.
- `make promote-eval-cases`, `make eval-quality-ab`, and `make summarize-loop`
  provide the operational workflow.

## Release Gate Rules

A version is eligible for recommendation only when all conditions are true:

1. The dashboard has A/B evidence for the requested `version_id`.
2. The dashboard risk level for that version is `low`.
3. At least one added case exists in the latest evaluated candidate set.
4. All added cases passed baseline across the A/B evidence used by the
   dashboard.
5. The candidate cases file exists and its embedded `version_id` matches the
   requested recommendation version.

The gate rejects versions with shared-case regressions, failed comparison gates,
failed added-case baselines, missing A/B evidence, no added cases, missing
candidate files, or version mismatches.

## Architecture

Add a small release-gate layer on top of the existing dashboard summary instead
of duplicating A/B parsing in each caller.

- `backend/services/xhs_quality_history.py` will add a per-version
  `recommendation_gate` object to the eval set version dashboard.
- `backend/services/xhs_eval_case_promotion.py` will expose a helper that reads
  the A/B index, finds the target version in the dashboard, evaluates the gate,
  and writes a recommended-set manifest only when the gate is eligible.
- `scripts/promote_xhs_eval_cases.py` will add a CLI mode for marking an
  existing candidate eval set as recommended.
- `Makefile` will add variables and a target for the gated recommendation step.

## Data Shape

Dashboard version rows will include:

```json
{
  "recommendation_gate": {
    "eligible": true,
    "status": "passed",
    "reasons": [],
    "latest_run_id": "xhs_quality_ab"
  }
}
```

When the gate passes, the recommended-set manifest will look like:

```json
{
  "schema_version": "xhs_recommended_eval_set.v1",
  "version_id": "xhs_quality_cases_next",
  "candidate_cases": "reports/xhs-quality-loop/xhs-quality-cases.next.json",
  "ab_index": "reports/xhs-quality-ab/xhs-quality-ab-index.jsonl",
  "latest_run_id": "xhs_quality_ab",
  "recommended_at": "2026-06-04T00:00:00Z",
  "gate": {
    "eligible": true,
    "status": "passed",
    "reasons": []
  }
}
```

## Error Handling

The recommendation command exits non-zero when the gate is not eligible. It
still prints a JSON payload with the rejection reasons so automation can display
or archive the decision.

Dry runs never write the manifest but still evaluate the gate.

## Testing

Add focused tests in `tests/test_xhs_quality_eval.py`:

- Dashboard rows expose `recommendation_gate`.
- A passing low-risk version writes the recommended manifest.
- Medium or high-risk versions are rejected and do not write the manifest.
- A version with no added cases is rejected.
- Missing candidate files and candidate `version_id` mismatches are rejected.
- CLI and Makefile paths exercise the gated recommendation flow.
