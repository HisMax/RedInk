# Recommended Eval Set Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let evaluation and quality-loop commands consume `xhs-quality-cases.recommended.json` without manually passing `EVAL_CASES` or `LOOP_CASES`.

**Architecture:** Add a focused resolver script for recommended eval set manifests. Wire Makefile targets through the resolver so existing evaluation runners stay unchanged, then document the end-to-end promotion-to-consumption flow.

**Tech Stack:** Python 3.11, pytest, Makefile, JSON manifest artifacts.

---

## File Structure

- Create `scripts/resolve_xhs_recommended_eval_set.py`: CLI resolver for recommended manifests.
- Modify `Makefile`: add `eval-quality-recommended` and `xhs-quality-loop-recommended`.
- Modify `tests/test_xhs_quality_eval.py`: add resolver and Makefile tests.
- Modify `README.md` and `README_zh.md`: document the complete workflow.

### Task 1: Resolver CLI

**Files:**
- Create: `scripts/resolve_xhs_recommended_eval_set.py`
- Test: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Write failing resolver tests**

Add tests:

```python
def _write_recommended_manifest(path, *, candidate_path, gate=None, version_id="xhs_quality_cases_v2"):
    path.write_text(
        json.dumps({
            "schema_version": "xhs_recommended_eval_set.v1",
            "version_id": version_id,
            "candidate_cases": str(candidate_path),
            "gate": gate or {"eligible": True, "status": "passed", "reasons": []},
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def test_resolve_recommended_eval_set_cli_prints_candidate_cases(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_v2")
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    _write_recommended_manifest(manifest_path, candidate_path=candidate_path)

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/resolve_xhs_recommended_eval_set.py",
            "--recommended-manifest",
            str(manifest_path),
            "--print-cases",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == str(candidate_path)
```

Add blocked-gate and missing-candidate tests that assert non-zero return code and
JSON `resolved is False`.

- [ ] **Step 2: Run resolver tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "resolve_recommended_eval_set"
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Implement resolver script**

Create `scripts/resolve_xhs_recommended_eval_set.py` with:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

RESOLUTION_SCHEMA_VERSION = "xhs_recommended_eval_set_resolution.v1"
RECOMMENDED_SCHEMA_VERSION = "xhs_recommended_eval_set.v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve the recommended XHS eval set path.")
    parser.add_argument("--recommended-manifest", required=True)
    parser.add_argument("--print-cases", action="store_true")
    return parser.parse_args()


def resolve_recommended_eval_set(path: str | Path) -> Dict[str, Any]:
    manifest_path = Path(path)
    reasons: List[str] = []
    manifest: Dict[str, Any] = {}
    if not manifest_path.exists():
        reasons.append("recommended manifest does not exist")
    else:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            reasons.append(f"recommended manifest is invalid JSON: {exc}")
    if manifest and manifest.get("schema_version") != RECOMMENDED_SCHEMA_VERSION:
        reasons.append("recommended manifest schema_version is invalid")
    gate = manifest.get("gate") or {}
    if manifest and (gate.get("eligible") is not True or gate.get("status") != "passed"):
        reasons.append("recommended manifest gate is not passed")
    candidate_cases = manifest.get("candidate_cases") if manifest else None
    if manifest and not candidate_cases:
        reasons.append("recommended manifest candidate_cases is missing")
    if candidate_cases and not Path(candidate_cases).exists():
        reasons.append("recommended candidate cases file does not exist")
    resolved = not reasons
    return {
        "schema_version": RESOLUTION_SCHEMA_VERSION,
        "recommended_manifest": str(manifest_path),
        "candidate_cases": str(candidate_cases or ""),
        "version_id": manifest.get("version_id"),
        "gate_status": gate.get("status"),
        "resolved": resolved,
        "reasons": reasons,
    }


def main() -> int:
    args = parse_args()
    payload = resolve_recommended_eval_set(args.recommended_manifest)
    if args.print_cases and payload["resolved"]:
        print(payload["candidate_cases"])
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["resolved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run resolver tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "resolve_recommended_eval_set"
```

Expected: PASS.

### Task 2: Recommended Make Targets

**Files:**
- Modify: `Makefile`
- Test: `tests/test_xhs_quality_eval.py`

- [ ] **Step 1: Write failing Makefile tests**

Add tests:

```python
def test_make_eval_quality_recommended_uses_manifest_cases(tmp_path):
    candidate_path = _versioned_quality_cases_path(tmp_path, version_id="xhs_quality_cases_make_recommended_v2")
    manifest_path = tmp_path / "xhs-quality-cases.recommended.json"
    report_dir = tmp_path / "reports"
    _write_recommended_manifest(manifest_path, candidate_path=candidate_path, version_id="xhs_quality_cases_make_recommended_v2")

    completed = subprocess.run(
        [
            "make",
            "eval-quality-recommended",
            f"REPORT_DIR={report_dir}",
            f"PYTHON={sys.executable}",
            f"LOOP_RECOMMENDED_CASES={manifest_path}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    assert payload["case_set"]["version_id"] == "xhs_quality_cases_make_recommended_v2"
```

Add `test_make_xhs_quality_loop_recommended_uses_manifest_cases` and assert
`payload["case_set"]["version_id"]` matches the manifest candidate.

- [ ] **Step 2: Run Makefile tests to verify they fail**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "eval_quality_recommended or quality_loop_recommended"
```

Expected: FAIL because the targets do not exist.

- [ ] **Step 3: Implement Makefile targets**

Add:

```make
RESOLVE_RECOMMENDED_CASES = $(PYTHON) scripts/resolve_xhs_recommended_eval_set.py --recommended-manifest "$(LOOP_RECOMMENDED_CASES)" --print-cases

eval-quality-recommended:
	@mkdir -p "$(REPORT_DIR)"
	@cases="$$( $(RESOLVE_RECOMMENDED_CASES) )"; \
	$(PYTHON) scripts/run_xhs_quality_eval.py --cases "$$cases" --jsonl "$(EVAL_JSONL)" --markdown "$(EVAL_MARKDOWN)" --run-id "$(EVAL_RUN_ID)" --min-overall "$(EVAL_MIN_OVERALL)" --max-score-drop "$(EVAL_MAX_SCORE_DROP)"

xhs-quality-loop-recommended:
	@mkdir -p "$(LOOP_REPORT_DIR)"
	@cases="$$( $(RESOLVE_RECOMMENDED_CASES) )"; \
	$(PYTHON) scripts/run_xhs_quality_loop.py --cases "$$cases" --report-dir "$(LOOP_REPORT_DIR)" --case-library "$(LOOP_CASE_LIBRARY)" --replay-index "$(LOOP_REPLAY_INDEX)" --run-id "$(LOOP_RUN_ID)" --min-overall "$(LOOP_MIN_OVERALL)" --min-improvement "$(LOOP_MIN_IMPROVEMENT)" --min-quality-overall "$(LOOP_MIN_QUALITY_OVERALL)" --min-score-delta "$(LOOP_MIN_SCORE_DELTA)" --limit "$(LOOP_LIMIT)"
```

Include both new targets in `.PHONY`.

- [ ] **Step 4: Run Makefile tests to verify they pass**

Run:

```bash
uv run --with pytest pytest tests/test_xhs_quality_eval.py -q -k "eval_quality_recommended or quality_loop_recommended"
```

Expected: PASS.

### Task 3: README Workflow

**Files:**
- Modify: `README.md`
- Modify: `README_zh.md`

- [ ] **Step 1: Update English workflow**

In the XHS eval set section, add:

```markdown
Mark the candidate as the current recommended eval set only after A/B and the
history dashboard gate are low risk:

```bash
make recommend-eval-cases LOOP_MARK_RECOMMENDED=1
```

Use the recommended eval set without manually copying the candidate path:

```bash
make eval-quality-recommended
make xhs-quality-loop-recommended
```
```

- [ ] **Step 2: Update Chinese workflow**

Add the equivalent Chinese text and commands to `README_zh.md`.

- [ ] **Step 3: Run README smoke check**

Run:

```bash
rg -n "eval-quality-recommended|xhs-quality-loop-recommended|recommend-eval-cases" README.md README_zh.md
```

Expected: all three commands appear in both READMEs.

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

