# Eval Set Release Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mark `xhs-quality-cases.next.json` as the recommended XHS eval set only after a low-risk A/B dashboard result with all added cases passing baseline.

**Architecture:** Reuse the existing A/B index and eval set version dashboard as the source of truth. Add a per-version recommendation gate to the dashboard, then add a promotion helper and CLI mode that validates the candidate file and writes a recommended-set manifest only when the gate passes.

**Tech Stack:** Python 3.11, pytest, Makefile targets, JSON/JSONL report artifacts.

---

## File Structure

- Modify `backend/services/xhs_quality_history.py`: add `recommendation_gate` fields to dashboard version rows.
- Modify `backend/services/xhs_eval_case_promotion.py`: add gated recommendation evaluation, candidate file validation, and manifest writer.
- Modify `scripts/promote_xhs_eval_cases.py`: add CLI mode for `--mark-recommended`.
- Modify `Makefile`: add variables and `recommend-eval-cases` target.
- Modify `tests/test_xhs_quality_eval.py`: add focused dashboard, service, CLI, and Makefile tests.

### Task 1: Dashboard Recommendation Gate

**Files:**
- Modify: `backend/services/xhs_quality_history.py`
- Test: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Write the failing dashboard test**

Add assertions to `test_quality_loop_history_summarizes_ab_eval_set_versions`:

```python
    gate = version["recommendation_gate"]
    assert gate["eligible"] is False
    assert gate["status"] == "blocked"
    assert gate["latest_run_id"] == "ab_001"
    assert "risk level is high" in gate["reasons"]
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py::test_quality_loop_history_summarizes_ab_eval_set_versions -q
```

Expected: FAIL with `KeyError: 'recommendation_gate'`.

- [ ] **Step 3: Implement the minimal dashboard gate**

In `backend/services/xhs_quality_history.py`, add helper:

```python
def _recommendation_gate(version: Dict[str, Any]) -> Dict[str, Any]:
    reasons = []
    risk_level = version.get("risk_level")
    if risk_level != "low":
        reasons.append(f"risk level is {risk_level or 'unknown'}")
    if _int(version.get("added_case_count")) <= 0:
        reasons.append("no added cases were evaluated")
    if _int(version.get("added_case_baseline_failed_count")):
        reasons.append("added cases failed baseline")
    eligible = not reasons
    return {
        "eligible": eligible,
        "status": "passed" if eligible else "blocked",
        "reasons": reasons,
        "latest_run_id": version.get("latest_run_id"),
    }
```

Call it when constructing each `version` dict:

```python
        version = {
            ...
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
        }
        version["recommendation_gate"] = _recommendation_gate(version)
        versions.append(version)
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py::test_quality_loop_history_summarizes_ab_eval_set_versions -q
```

Expected: PASS.

### Task 2: Gated Recommended Manifest Service

**Files:**
- Modify: `backend/services/xhs_eval_case_promotion.py`
- Test: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Write failing service tests**

Import `mark_recommended_eval_case_set` from `backend.services.xhs_eval_case_promotion`.

Add a passing test:

```python
def test_mark_recommended_eval_case_set_writes_manifest_when_gate_passes(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    ab_index_path = tmp_path / "xhs-quality-ab-index.jsonl"
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    _write_ab_index_row(
        ab_index_path,
        version_id="xhs_quality_cases_v2",
        added_case_count=1,
        added_passed_count=1,
        added_failed_count=0,
        regression_failed_count=0,
        comparison_passed=True,
    )

    payload = mark_recommended_eval_case_set(
        version_id="xhs_quality_cases_v2",
        candidate_cases_path=candidate_path,
        ab_index_path=ab_index_path,
        output_path=manifest_path,
        mark_recommended=True,
        recommended_at="2026-06-04T12:00:00Z",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["gate"]["eligible"] is True
    assert payload["written"] is True
    assert manifest["schema_version"] == "xhs_recommended_eval_set.v1"
    assert manifest["version_id"] == "xhs_quality_cases_v2"
    assert manifest["latest_run_id"] == "ab_001"
```

Add a rejection test:

```python
def test_mark_recommended_eval_case_set_rejects_failed_added_cases(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    ab_index_path = tmp_path / "xhs-quality-ab-index.jsonl"
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    _write_ab_index_row(
        ab_index_path,
        version_id="xhs_quality_cases_v2",
        added_case_count=1,
        added_passed_count=0,
        added_failed_count=1,
        regression_failed_count=0,
        comparison_passed=True,
    )

    payload = mark_recommended_eval_case_set(
        version_id="xhs_quality_cases_v2",
        candidate_cases_path=candidate_path,
        ab_index_path=ab_index_path,
        output_path=manifest_path,
        mark_recommended=True,
    )

    assert payload["gate"]["eligible"] is False
    assert payload["written"] is False
    assert manifest_path.exists() is False
```

Add a no-added-cases rejection test with `added_case_count=0`.

Add missing-candidate and version-mismatch rejection tests:

```python
assert payload["gate"]["eligible"] is False
assert payload["written"] is False
assert manifest_path.exists() is False
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "mark_recommended_eval_case_set"
```

Expected: FAIL with import or missing function errors.

- [ ] **Step 3: Implement the service helper**

In `backend/services/xhs_eval_case_promotion.py`, import `summarize_loop_history`, add:

```python
RECOMMENDED_SCHEMA_VERSION = "xhs_recommended_eval_set.v1"

def mark_recommended_eval_case_set(
    *,
    version_id: str,
    candidate_cases_path: str | Path,
    ab_index_path: str | Path,
    output_path: str | Path,
    mark_recommended: bool = False,
    dry_run: bool = False,
    recommended_at: str | None = None,
) -> Dict[str, Any]:
    dashboard = summarize_loop_history(Path(ab_index_path).with_suffix(".loop-index-missing"), ab_index_path=ab_index_path)["eval_set_versions"]
    version = _find_dashboard_version(dashboard, version_id)
    gate = _missing_gate(version_id) if version is None else version.get("recommendation_gate", {})
    payload = {
        "schema_version": RECOMMENDED_SCHEMA_VERSION,
        "version_id": version_id,
        "candidate_cases": str(candidate_cases_path),
        "ab_index": str(ab_index_path),
        "latest_run_id": (version or {}).get("latest_run_id"),
        "recommended_at": recommended_at or _utc_now(),
        "gate": gate,
        "dry_run": bool(dry_run or not mark_recommended),
        "mark_recommended": bool(mark_recommended),
        "written": False,
    }
    if mark_recommended and not dry_run and gate.get("eligible") is True:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        payload["written"] = True
    return payload
```

Add private helpers `_find_dashboard_version`, `_missing_gate`,
`_candidate_cases_gate`, `_merge_gate`, and `_blocked_gate`.

- [ ] **Step 4: Run the service tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "mark_recommended_eval_case_set"
```

Expected: PASS.

### Task 3: CLI and Makefile Gate

**Files:**
- Modify: `scripts/promote_xhs_eval_cases.py`
- Modify: `Makefile`
- Test: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Write failing CLI and Makefile tests**

Add CLI test invoking:

```bash
python scripts/promote_xhs_eval_cases.py \
  --version-id xhs_quality_cases_v2 \
  --candidate-cases /tmp/xhs_quality_cases_v2.json \
  --ab-index /tmp/xhs-quality-ab-index.jsonl \
  --recommended-output /tmp/xhs-quality-cases.recommended.json \
  --mark-recommended
```

Assert return code `0`, `written is True`, and manifest exists.

Add Makefile test invoking:

```bash
make recommend-eval-cases \
  PYTHON=/usr/bin/python3 \
  LOOP_PROMOTED_VERSION_ID=xhs_quality_cases_v2 \
  LOOP_PROMOTED_CASES=/tmp/xhs_quality_cases_v2.json \
  LOOP_AB_INDEX=/tmp/xhs-quality-ab-index.jsonl \
  LOOP_RECOMMENDED_CASES=/tmp/xhs-quality-cases.recommended.json \
  LOOP_MARK_RECOMMENDED=1
```

Assert return code `0` and manifest exists.

- [ ] **Step 2: Run the new CLI/Makefile tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "recommended_eval_case_set_cli or make_recommend"
```

Expected: FAIL because CLI args and Make target do not exist.

- [ ] **Step 3: Implement CLI mode**

In `scripts/promote_xhs_eval_cases.py`:

- Import `mark_recommended_eval_case_set`.
- Add parser arguments `--candidate-cases`, `--ab-index`, `--recommended-output`.
- Add mutually exclusive mode `--mark-recommended`.
- In `main`, call `mark_recommended_eval_case_set` when `args.mark_recommended` is true.
- Return `0` when `payload["gate"]["eligible"] is True` or dry-run, otherwise return `1`.

- [ ] **Step 4: Implement Makefile target**

Add variables:

```make
LOOP_RECOMMENDED_CASES ?= $(LOOP_REPORT_DIR)/xhs-quality-cases.recommended.json
LOOP_MARK_RECOMMENDED ?= 0
```

Add args:

```make
RECOMMEND_EVAL_CASE_ARGS := --version-id "$(LOOP_PROMOTED_VERSION_ID)"
RECOMMEND_EVAL_CASE_ARGS += --candidate-cases "$(LOOP_PROMOTED_CASES)" --ab-index "$(LOOP_AB_INDEX)"
RECOMMEND_EVAL_CASE_ARGS += --recommended-output "$(LOOP_RECOMMENDED_CASES)"
```

Add mode and target:

```make
ifeq ($(LOOP_MARK_RECOMMENDED),1)
RECOMMEND_EVAL_CASE_ARGS += --mark-recommended
else
RECOMMEND_EVAL_CASE_ARGS += --dry-run
endif

recommend-eval-cases:
	@mkdir -p "$(dir $(LOOP_RECOMMENDED_CASES))"
	@$(PYTHON) scripts/promote_xhs_eval_cases.py $(RECOMMEND_EVAL_CASE_ARGS)
```

- [ ] **Step 5: Run focused CLI/Makefile tests**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "recommended_eval_case_set_cli or make_recommend"
```

Expected: PASS.

### Task 4: Full Verification

**Files:**
- No edits expected.

- [ ] **Step 1: Run quality tests**

Run:

```bash
make test-quality
```

Expected: all tests pass.

- [ ] **Step 2: Run full test suite**

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

Expected: only intentional tracked changes plus pre-existing untracked `.codex-run/` and `frontend/pnpm-workspace.yaml`.
