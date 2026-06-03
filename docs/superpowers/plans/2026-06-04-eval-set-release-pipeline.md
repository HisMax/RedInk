# Eval Set Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `make release-eval-cases` to run promotion, A/B, history summarization, and gated recommendation as one repeatable release workflow.

**Architecture:** Compose existing Makefile targets instead of adding a new orchestration script. The new target passes approval flags only to the steps that need them and keeps all path/config variables overridable by callers.

**Tech Stack:** GNU Make, Python 3.11, pytest, JSON/JSONL artifacts.

---

## File Structure

- Modify `Makefile`: add `.PHONY` entry and `release-eval-cases` target.
- Modify `tests/test_xhs_quality_eval.py`: add success and failure Makefile tests.
- Modify `README.md` and `README_zh.md`: document the one-command release workflow.

### Task 1: Release Pipeline Tests

**Files:**
- Modify: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Add candidate fixture helper**

Add helper near the existing eval candidate tests:

```python
def _write_eval_case_candidates(path, *, approved=True):
    row = {
        "schema_version": "xhs_eval_case_candidate.v1",
        "candidate_id": "release_001:eval_case_001",
        "source_draft_id": "eval_case_001",
        "source_task_id": "eval_task_001",
        "source_issue_id": "baseline_overall_below_threshold",
        "status": "approved" if approved else "candidate",
        "category": "quality_regression",
        "topic": "标题钩子和信息密度验证",
        "outline": {"goal": "验证标题和正文是否更具体"},
        "expected_traits": ["标题钩子", "可执行细节"],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
```

- [ ] **Step 2: Add failing success-path test**

Add:

```python
def test_make_release_eval_cases_writes_recommended_manifest(tmp_path):
    report_dir = tmp_path / "reports"
    loop_dir = report_dir / "xhs-quality-loop"
    ab_dir = report_dir / "xhs-quality-ab"
    candidates_path = loop_dir / "xhs-eval-case-candidates.jsonl"
    promoted_path = loop_dir / "xhs-quality-cases.next.json"
    recommended_path = loop_dir / "xhs-quality-cases.recommended.json"
    _write_eval_case_candidates(candidates_path)

    completed = subprocess.run(
        [
            "make",
            "release-eval-cases",
            f"PYTHON={sys.executable}",
            f"REPORT_DIR={report_dir}",
            f"LOOP_EVAL_CASE_CANDIDATES={candidates_path}",
            f"LOOP_PROMOTED_CASES={promoted_path}",
            f"AB_REPORT_DIR={ab_dir}",
            f"AB_CANDIDATE_CASES={promoted_path}",
            f"LOOP_AB_INDEX={ab_dir / 'xhs-quality-ab-index.jsonl'}",
            f"LOOP_RECOMMENDED_CASES={recommended_path}",
            "AB_MIN_OVERALL=80",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(recommended_path.read_text(encoding="utf-8"))
    assert completed.returncode == 0
    assert promoted_path.exists()
    assert manifest["gate"]["eligible"] is True
    assert manifest["candidate_cases"] == str(promoted_path)
```

- [ ] **Step 3: Add failing blocked-path test**

Add:

```python
def test_make_release_eval_cases_stops_before_recommendation_when_no_approved_cases(tmp_path):
    report_dir = tmp_path / "reports"
    loop_dir = report_dir / "xhs-quality-loop"
    ab_dir = report_dir / "xhs-quality-ab"
    candidates_path = loop_dir / "xhs-eval-case-candidates.jsonl"
    promoted_path = loop_dir / "xhs-quality-cases.next.json"
    recommended_path = loop_dir / "xhs-quality-cases.recommended.json"
    _write_eval_case_candidates(candidates_path, approved=False)

    completed = subprocess.run(
        [
            "make",
            "release-eval-cases",
            f"PYTHON={sys.executable}",
            f"REPORT_DIR={report_dir}",
            f"LOOP_EVAL_CASE_CANDIDATES={candidates_path}",
            f"LOOP_PROMOTED_CASES={promoted_path}",
            f"AB_REPORT_DIR={ab_dir}",
            f"AB_CANDIDATE_CASES={promoted_path}",
            f"LOOP_AB_INDEX={ab_dir / 'xhs-quality-ab-index.jsonl'}",
            f"LOOP_RECOMMENDED_CASES={recommended_path}",
            "AB_MIN_OVERALL=80",
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert promoted_path.exists()
    assert recommended_path.exists() is False
```

- [ ] **Step 4: Run release tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "release_eval_cases"
```

Expected: FAIL because the Make target does not exist.

### Task 2: Makefile Target

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Add `release-eval-cases` target**

Add `release-eval-cases` to `.PHONY`.

Add recipe:

```make
release-eval-cases:
	@$(MAKE) promote-eval-cases LOOP_PROMOTE_APPROVED=1
	@$(MAKE) eval-quality-ab
	@$(MAKE) summarize-loop
	@$(MAKE) recommend-eval-cases LOOP_MARK_RECOMMENDED=1
```

- [ ] **Step 2: Run release tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "release_eval_cases"
```

Expected: PASS.

### Task 3: README Updates

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`

- [ ] **Step 1: Update English README**

Add after the manual sequence:

```markdown
Run the complete release sequence as one gated pipeline:

```bash
make release-eval-cases
```
```

- [ ] **Step 2: Update Chinese README**

Add equivalent Chinese text and command.

- [ ] **Step 3: Run README smoke check**

Run:

```bash
rg -n "release-eval-cases" README.md README_zh.md Makefile
```

Expected: command appears in both READMEs and Makefile.

### Task 4: Full Verification

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

