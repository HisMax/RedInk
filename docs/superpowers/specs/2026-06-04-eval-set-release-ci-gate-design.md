# XHS Eval Set Release CI Gate Design

## Goal

Add a GitHub Actions PR gate that runs the existing `make release-eval-cases`
pipeline, so the recommended eval set release path is verified automatically.

## Context

The repository has a Docker publish workflow, but no PR workflow for the XHS eval
release path. The release pipeline already exists locally:

1. promote approved eval case candidates
2. run eval set A/B
3. summarize loop history
4. mark the candidate as recommended only when the gate passes
5. write a release summary JSON/Markdown audit artifact

The default release inputs live under `reports/`, and `reports/` is ignored by
git. A PR workflow therefore cannot rely on local generated report files being
present in the checkout.

## Design

Create `.github/workflows/xhs-eval-release-gate.yml` with two triggers:

- `pull_request`, scoped to files that affect the release gate implementation,
  the Make target, the CI fixture, and the workflow itself.
- `workflow_dispatch`, so maintainers can run the gate manually.

The workflow uses a tracked fixture,
`tests/fixtures/xhs_eval_case_candidates.approved.jsonl`, as a deterministic
approved candidate input. It runs `make release-eval-cases` with `REPORT_DIR`
pointing at `$RUNNER_TEMP/xhs-release-gate`, so CI does not write generated
artifacts into the repository checkout.

This verifies the full release mechanism on every relevant PR. Actual local
release runs can still pass their real `LOOP_EVAL_CASE_CANDIDATES` and output
paths through Make variables.

## Artifacts

The workflow uploads the generated release outputs even when the job fails:

- `xhs-quality-loop/xhs-quality-cases.next.json`
- `xhs-quality-loop/xhs-quality-cases.recommended.json`
- `xhs-quality-loop/xhs-eval-set-release-summary.json`
- `xhs-quality-loop/xhs-eval-set-release-summary.md`
- `xhs-quality-ab/xhs-quality-ab-index.jsonl`

These artifacts make a blocked PR gate diagnosable without copying full logs into
the PR discussion.

## Testing

Add focused CI workflow tests in `tests/test_ci_workflows.py`:

- parse the workflow YAML and assert it has `pull_request` and
  `workflow_dispatch` triggers
- assert the PR path filter includes the release gate implementation files
- assert the job checks out the repo, sets up `uv`, runs `make release-eval-cases`
  against the tracked fixture and temp report directory, and uploads summary
  artifacts
- assert the tracked candidate fixture contains one approved candidate row

Keep the existing quality tests as the behavior-level verification for the Make
pipeline itself.
