from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RELEASE_GATE_WORKFLOW = ROOT / ".github" / "workflows" / "xhs-eval-release-gate.yml"
RELEASE_GATE_FIXTURE = ROOT / "tests" / "fixtures" / "xhs_eval_case_candidates.approved.jsonl"


def _load_workflow(path: Path):
    assert path.exists(), f"missing workflow: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _workflow_triggers(workflow):
    return workflow.get("on", workflow.get(True, {}))


def test_xhs_eval_release_gate_runs_release_pipeline_on_pr():
    workflow = _load_workflow(RELEASE_GATE_WORKFLOW)

    triggers = _workflow_triggers(workflow)
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers
    assert set(triggers["pull_request"]["paths"]) >= {
        ".github/workflows/xhs-eval-release-gate.yml",
        "Makefile",
        "backend/services/xhs_eval_case_promotion.py",
        "backend/services/xhs_eval_release.py",
        "scripts/promote_xhs_eval_cases.py",
        "scripts/summarize_xhs_eval_release.py",
        "tests/fixtures/xhs_eval_case_candidates.approved.jsonl",
    }

    job = workflow["jobs"]["release-gate"]
    assert job["runs-on"] == "ubuntu-latest"

    uses_steps = "\n".join(str(step.get("uses", "")) for step in job["steps"])
    run_steps = "\n".join(str(step.get("run", "")) for step in job["steps"])
    assert "actions/checkout@v4" in uses_steps
    assert "astral-sh/setup-uv@" in uses_steps
    assert "make release-eval-cases" in run_steps
    assert 'REPORT_DIR="$RUNNER_TEMP/xhs-release-gate"' in run_steps
    assert "LOOP_EVAL_CASE_CANDIDATES=tests/fixtures/xhs_eval_case_candidates.approved.jsonl" in run_steps
    assert "actions/upload-artifact@v4" in uses_steps
    assert "xhs-eval-set-release-summary.json" in str(job["steps"])
    assert "xhs-eval-set-release-summary.md" in str(job["steps"])


def test_xhs_eval_release_gate_fixture_contains_approved_candidate():
    assert RELEASE_GATE_FIXTURE.exists(), f"missing fixture: {RELEASE_GATE_FIXTURE}"
    lines = [
        line
        for line in RELEASE_GATE_FIXTURE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(lines) == 1
    row = yaml.safe_load(lines[0])
    assert row["schema_version"] == "xhs_eval_case_candidate.v1"
    assert row["status"] == "approved"
    assert row["candidate_id"] == "ci_release_gate:eval_case_001"
