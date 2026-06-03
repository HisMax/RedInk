# Recommended Eval Set Consumption Design

## Goal

Make the recommended eval set manifest produced by the release gate directly
usable by evaluation and loop commands. Operators should not need to manually
copy `EVAL_CASES=reports/xhs-quality-loop/xhs-quality-cases.next.json` after a
candidate eval set has been marked recommended.

## Current Context

The previous release-gate step writes
`reports/xhs-quality-loop/xhs-quality-cases.recommended.json` with:

- `schema_version`: `xhs_recommended_eval_set.v1`
- `candidate_cases`: path to the recommended versioned eval case set
- `gate`: a passed recommendation gate
- `version_id`: the recommended eval set version

`make eval-quality` and `make xhs-quality-loop` still default to
`tests/fixtures/xhs_quality_cases.json`, so the manifest is not consumed by the
main workflow yet.

## Design

Add a small resolver script that reads a recommended eval set manifest, validates
that the manifest gate is still passed, validates that the referenced candidate
case file exists, and prints the candidate case path.

Then add two Make targets that use that resolver:

- `make eval-quality-recommended`
- `make xhs-quality-loop-recommended`

Both targets use the same report paths and options as the existing commands but
derive `--cases` from `LOOP_RECOMMENDED_CASES`.

## Resolver Rules

The resolver accepts `--recommended-manifest <path>` and prints a compact JSON
payload:

```json
{
  "schema_version": "xhs_recommended_eval_set_resolution.v1",
  "recommended_manifest": "reports/xhs-quality-loop/xhs-quality-cases.recommended.json",
  "candidate_cases": "reports/xhs-quality-loop/xhs-quality-cases.next.json",
  "version_id": "xhs_quality_cases_next",
  "gate_status": "passed",
  "resolved": true
}
```

The resolver exits non-zero when:

- the manifest file is missing
- the manifest schema is not `xhs_recommended_eval_set.v1`
- `gate.eligible` is not true or `gate.status` is not `passed`
- `candidate_cases` is missing
- the referenced candidate file does not exist

It still prints a JSON payload with `resolved=false` and `reasons` so automation
can show the failure cleanly.

## Makefile Flow

The recommended targets use shell-local resolution:

```make
cases="$$(python scripts/resolve_xhs_recommended_eval_set.py --recommended-manifest "$(LOOP_RECOMMENDED_CASES)" --print-cases)"
python scripts/run_xhs_quality_eval.py --cases "$$cases" ...
```

This keeps the existing Python runners unchanged and avoids duplicating manifest
parsing inside every script.

## Documentation

Update English and Chinese README workflow sections so the complete flow is:

1. `make promote-eval-cases LOOP_PROMOTE_APPROVED=1`
2. `make eval-quality-ab`
3. `make summarize-loop`
4. `make recommend-eval-cases LOOP_MARK_RECOMMENDED=1`
5. `make eval-quality-recommended` or `make xhs-quality-loop-recommended`

## Testing

Add tests in `tests/test_xhs_quality_eval.py` for:

- resolver returns the candidate case path for a passed manifest
- resolver rejects blocked gates and missing candidate files
- CLI `--print-cases` outputs only the path for shell use
- `make eval-quality-recommended` evaluates the versioned set from the manifest
- `make xhs-quality-loop-recommended` starts the loop with the versioned set from
  the manifest

