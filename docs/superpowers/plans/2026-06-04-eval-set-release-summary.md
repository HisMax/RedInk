# Eval Set Release Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate JSON and Markdown audit summaries for recommended XHS eval set releases.

**Architecture:** Add a focused backend service that validates the recommended manifest against the candidate eval set and A/B dashboard, then wrap it with a CLI and Makefile target. Append the summary step to the existing `release-eval-cases` pipeline.

**Tech Stack:** Python 3.11, pytest, GNU Make, JSON/Markdown artifacts.

---

## File Structure

- Create `backend/services/xhs_eval_release.py`: release summary validation and writers.
- Create `scripts/summarize_xhs_eval_release.py`: CLI wrapper for the service.
- Modify `Makefile`: add summary variables, target, and release pipeline step.
- Modify `tests/test_xhs_quality_eval.py`: add CLI, Makefile, and pipeline tests.
- Modify `README.md` and `README_zh.md`: document the release summary output.

### Task 1: Release Summary CLI Tests

**Files:**
- Modify: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Extend manifest helper**

Update `_write_recommended_manifest` to include `latest_run_id`:

```python
def _write_recommended_manifest(
    path,
    *,
    candidate_path,
    gate=None,
    version_id="xhs_quality_cases_v2",
    latest_run_id="ab_001",
):
    path.write_text(
        json.dumps({
            "schema_version": "xhs_recommended_eval_set.v1",
            "version_id": version_id,
            "candidate_cases": str(candidate_path),
            "latest_run_id": latest_run_id,
            "gate": gate or {"eligible": True, "status": "passed", "reasons": []},
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 2: Add failing passed-summary CLI test**

Add:

```python
def test_summarize_eval_release_cli_writes_passed_summary(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    ab_index_path = tmp_path / "xhs-quality-ab-index.jsonl"
    summary_json = tmp_path / "xhs-eval-set-release-summary.json"
    summary_md = tmp_path / "xhs-eval-set-release-summary.md"
    _write_recommended_manifest(manifest_path, candidate_path=candidate_path)
    _write_ab_index_row(ab_index_path, version_id="xhs_quality_cases_v2")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_xhs_eval_release.py",
            "--recommended-manifest",
            str(manifest_path),
            "--ab-index",
            str(ab_index_path),
            "--json",
            str(summary_json),
            "--markdown",
            str(summary_md),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    written = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["status"] == "passed"
    assert written["version_id"] == "xhs_quality_cases_v2"
    assert written["latest_run_id"] == "ab_001"
    assert summary_md.read_text(encoding="utf-8").startswith("# XHS Eval Set Release Summary")
```

- [ ] **Step 3: Add failing stale-summary CLI test**

Add:

```python
def test_summarize_eval_release_cli_blocks_stale_latest_run(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    ab_index_path = tmp_path / "xhs-quality-ab-index.jsonl"
    summary_json = tmp_path / "xhs-eval-set-release-summary.json"
    _write_recommended_manifest(manifest_path, candidate_path=candidate_path, latest_run_id="old_ab")
    _write_ab_index_row(ab_index_path, version_id="xhs_quality_cases_v2", run_id="ab_001")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_xhs_eval_release.py",
            "--recommended-manifest",
            str(manifest_path),
            "--ab-index",
            str(ab_index_path),
            "--json",
            str(summary_json),
        ],
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 1
    assert payload["status"] == "blocked"
    assert "latest_run_id does not match dashboard latest run" in payload["reasons"]
    assert summary_json.exists()
```

- [ ] **Step 4: Run CLI tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "summarize_eval_release_cli"
```

Expected: FAIL because the script does not exist.

### Task 2: Release Summary Service and Script

**Files:**
- Create: `backend/services/xhs_eval_release.py`
- Create: `scripts/summarize_xhs_eval_release.py`

- [ ] **Step 1: Implement service**

Create `backend/services/xhs_eval_release.py` with:

- `RELEASE_SUMMARY_SCHEMA_VERSION = "xhs_eval_set_release_summary.v1"`
- `summarize_eval_release(recommended_manifest_path, ab_index_path)`
- `write_eval_release_summary_json(summary, path)`
- `write_eval_release_summary_markdown(summary, path)`
- private helpers for checks, dashboard version lookup, and Markdown formatting

The summary must contain `status`, `reasons`, `version_id`, `candidate_cases`,
`candidate_case_count`, `latest_run_id`, `checks`, and `dashboard`.

- [ ] **Step 2: Implement script**

Create `scripts/summarize_xhs_eval_release.py` with args:

```bash
--recommended-manifest
--ab-index
--json
--markdown
```

The script prints JSON to stdout, writes requested files, returns `0` when
`status == "passed"` and `1` otherwise.

- [ ] **Step 3: Run CLI tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "summarize_eval_release_cli"
```

Expected: PASS.

### Task 3: Makefile Target and Pipeline Integration

**Files:**
- Modify: `Makefile`
- Modify: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Add failing Makefile target test**

Add:

```python
def test_make_summarize_eval_release_writes_summary(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    ab_index_path = tmp_path / "xhs-quality-ab-index.jsonl"
    summary_json = tmp_path / "xhs-eval-set-release-summary.json"
    summary_md = tmp_path / "xhs-eval-set-release-summary.md"
    _write_recommended_manifest(manifest_path, candidate_path=candidate_path)
    _write_ab_index_row(ab_index_path, version_id="xhs_quality_cases_v2")

    completed = subprocess.run(
        [
            "make",
            "summarize-eval-release",
            f"PYTHON={sys.executable}",
            f"LOOP_RECOMMENDED_CASES={manifest_path}",
            f"LOOP_AB_INDEX={ab_index_path}",
            f"LOOP_RELEASE_SUMMARY_JSON={summary_json}",
            f"LOOP_RELEASE_SUMMARY_MARKDOWN={summary_md}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["status"] == "passed"
    assert summary_json.exists()
    assert summary_md.exists()
```

Update `test_make_release_eval_cases_writes_recommended_manifest` to assert the
release summary JSON exists and has `status == "passed"`.

Update the failed release test to assert the release summary JSON does not exist.

- [ ] **Step 2: Run Makefile summary tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "summarize_eval_release or release_eval_cases"
```

Expected: FAIL because the Make target and pipeline step do not exist.

- [ ] **Step 3: Implement Makefile target**

Add variables:

```make
LOOP_RELEASE_SUMMARY_JSON ?= $(LOOP_REPORT_DIR)/xhs-eval-set-release-summary.json
LOOP_RELEASE_SUMMARY_MARKDOWN ?= $(LOOP_REPORT_DIR)/xhs-eval-set-release-summary.md
```

Add args:

```make
EVAL_RELEASE_SUMMARY_ARGS := --recommended-manifest "$(LOOP_RECOMMENDED_CASES)" --ab-index "$(LOOP_AB_INDEX)"
EVAL_RELEASE_SUMMARY_ARGS += --json "$(LOOP_RELEASE_SUMMARY_JSON)" --markdown "$(LOOP_RELEASE_SUMMARY_MARKDOWN)"
```

Add `.PHONY` and target:

```make
summarize-eval-release:
	@mkdir -p "$(dir $(LOOP_RELEASE_SUMMARY_JSON))"
	@$(PYTHON) scripts/summarize_xhs_eval_release.py $(EVAL_RELEASE_SUMMARY_ARGS)
```

Append to `release-eval-cases`:

```make
	@$(MAKE) summarize-eval-release
```

- [ ] **Step 4: Run Makefile summary tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "summarize_eval_release or release_eval_cases"
```

Expected: PASS.

### Task 4: README Updates

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`

- [ ] **Step 1: Document summary artifacts**

Add the generated summary paths near `make release-eval-cases`:

```text
reports/xhs-quality-loop/xhs-eval-set-release-summary.json
reports/xhs-quality-loop/xhs-eval-set-release-summary.md
```

- [ ] **Step 2: Run smoke check**

Run:

```bash
rg -n "xhs-eval-set-release-summary" README.md README_zh.md Makefile
```

Expected: both README files and Makefile mention the summary paths.

### Task 5: Full Verification

**Files:**
- No edits expected.

- [ ] **Step 1: Run quality tests**

Run:

```bash
make test-quality
```

Expected: all quality tests pass.

- [ ] **Step 2: Run full tests**

Run:

```bash
uv run --with pytest pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Check git status**

Run:

```bash
git status --short
```

Expected: only intentional tracked changes plus pre-existing untracked
`.codex-run/` and `frontend/pnpm-workspace.yaml`.

