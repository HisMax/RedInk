# Eval Set Release Pipeline Design

## Goal

Provide one repeatable Makefile target that releases a promoted XHS eval set
candidate through the existing gated workflow:

1. promote approved candidates into `xhs-quality-cases.next.json`
2. run A/B against the base fixture
3. refresh the quality loop history dashboard
4. mark the candidate as recommended only if the dashboard gate passes

## Current Context

The repository already has all individual steps:

- `make promote-eval-cases LOOP_PROMOTE_APPROVED=1`
- `make eval-quality-ab`
- `make summarize-loop`
- `make recommend-eval-cases LOOP_MARK_RECOMMENDED=1`

Operators can run these manually, but the sequence is easy to mistype or skip.
The recommended manifest must remain protected by the existing gate.

## Design

Add `make release-eval-cases` as a composition target. It calls the existing
targets in order with the approval flags set inside the recipe, while preserving
the caller's path variables such as `REPORT_DIR`, `LOOP_EVAL_CASE_CANDIDATES`,
`LOOP_PROMOTED_CASES`, `AB_CANDIDATE_CASES`, `LOOP_AB_INDEX`, and
`LOOP_RECOMMENDED_CASES`.

The target should be simple shell sequencing, not a new Python orchestration
layer. Each existing target remains independently runnable for debugging.

## Failure Semantics

Make stops at the first failing step. If A/B fails or the recommendation gate is
blocked, `make release-eval-cases` exits non-zero and does not write the
recommended manifest.

## Documentation

README and README_zh should show the one-command release path and keep the
manual sequence for troubleshooting.

## Testing

Add Makefile tests for:

- success path writes a recommended manifest after promotion, A/B, summarize,
  and recommendation
- failure path does not write a recommended manifest when the candidate cannot
  pass A/B/recommendation
- README smoke check includes `release-eval-cases`

