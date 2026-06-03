# XHS Eval Set Release CI Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions PR gate that runs `make release-eval-cases` with deterministic approved candidate input.

**Architecture:** Keep business release behavior in the existing Make/Python pipeline. Add one workflow file that invokes the pipeline in a temporary report directory and one tracked candidate fixture used only by CI.

**Tech Stack:** GitHub Actions, GNU Make, Python 3.11, uv, pytest, PyYAML.

---

### Task 1: Workflow Contract Tests

**Files:**
- Create: `tests/test_ci_workflows.py`

- [ ] **Step 1: Write the failing tests**

Create tests that parse `.github/workflows/xhs-eval-release-gate.yml` and assert
the PR trigger, manual trigger, `make release-eval-cases` command, temp
`REPORT_DIR`, candidate fixture path, and artifact upload are present. Add a
second test that asserts the candidate fixture contains exactly one approved row.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run --with pytest pytest tests/test_ci_workflows.py -q
```

Expected: fail because `.github/workflows/xhs-eval-release-gate.yml` and the
candidate fixture do not exist yet.

### Task 2: CI Fixture

**Files:**
- Create: `tests/fixtures/xhs_eval_case_candidates.approved.jsonl`

- [ ] **Step 1: Add a deterministic approved candidate**

Write one JSONL row:

```json
{"schema_version":"xhs_eval_case_candidate.v1","candidate_id":"ci_release_gate:eval_case_001","source_draft_id":"eval_case_001","source_task_id":"eval_task_001","source_issue_id":"ci_release_gate","status":"approved","category":"quality_regression","topic":"标题钩子和信息密度验证","outline":{"goal":"验证标题和正文是否更具体"},"expected_traits":["标题钩子","可执行细节"]}
```

- [ ] **Step 2: Run the tests and verify the remaining failure**

Run:

```bash
uv run --with pytest pytest tests/test_ci_workflows.py -q
```

Expected: fixture test passes; workflow test still fails because the workflow
does not exist.

### Task 3: GitHub Actions Release Gate

**Files:**
- Create: `.github/workflows/xhs-eval-release-gate.yml`

- [ ] **Step 1: Add the workflow**

Create a workflow named `XHS Eval Release Gate` with quoted `"on"` key, PR path
filters for the release gate files, and a `release-gate` job on
`ubuntu-latest`. Steps:

1. `actions/checkout@v4`
2. `astral-sh/setup-uv@v5`
3. run `make release-eval-cases` with:
   - `REPORT_DIR="$RUNNER_TEMP/xhs-release-gate"`
   - `LOOP_EVAL_CASE_CANDIDATES=tests/fixtures/xhs_eval_case_candidates.approved.jsonl`
4. upload release outputs with `actions/upload-artifact@v4` and `if: always()`

- [ ] **Step 2: Run workflow tests and verify GREEN**

Run:

```bash
uv run --with pytest pytest tests/test_ci_workflows.py -q
```

Expected: all workflow tests pass.

### Task 4: Documentation

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`
- Modify: `.github/pull_request_template.md`

- [ ] **Step 1: Document the PR gate**

Add a short note near the eval release workflow section explaining that relevant
PRs run the XHS eval release gate in GitHub Actions, using the tracked approved
candidate fixture and uploading release summary artifacts.

- [ ] **Step 2: Update PR checklist**

Add a checklist item for the XHS eval release gate when touching eval release
logic or candidate inputs.

- [ ] **Step 3: Smoke check docs**

Run:

```bash
rg -n "XHS Eval Release Gate|xhs-eval-release-gate|release-eval-cases" README.md README_zh.md .github/pull_request_template.md
```

Expected: the workflow and release gate are mentioned in both READMEs and the PR
template.

### Task 5: Final Verification And Commit

**Files:**
- All changed files

- [ ] **Step 1: Run focused tests**

```bash
uv run --with pytest pytest tests/test_ci_workflows.py -q
```

Expected: all CI workflow tests pass.

- [ ] **Step 2: Run quality tests**

```bash
make test-quality
```

Expected: all quality tests pass.

- [ ] **Step 3: Run full pytest**

```bash
uv run --with pytest pytest -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit only scoped files**

```bash
git add .github/workflows/xhs-eval-release-gate.yml .github/pull_request_template.md README.md README_zh.md tests/test_ci_workflows.py tests/fixtures/xhs_eval_case_candidates.approved.jsonl docs/superpowers/specs/2026-06-04-eval-set-release-ci-gate-design.md docs/superpowers/plans/2026-06-04-eval-set-release-ci-gate.md
git commit -m "ci: gate xhs eval set releases"
```
