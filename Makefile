REPORT_DIR ?= reports
EVAL_JSONL ?= $(REPORT_DIR)/xhs-quality-eval.jsonl
EVAL_MARKDOWN ?= $(REPORT_DIR)/xhs-quality-eval.md
EVAL_PREVIOUS ?=
EVAL_CASE_LIBRARY ?=
EVAL_RUN_ID ?= xhs_quality_eval
EVAL_MIN_OVERALL ?= 80
EVAL_MAX_SCORE_DROP ?= 3
EVAL_LIVE ?= 0
EVAL_REPORT_ONLY ?= 0
CASE_LIBRARY ?= reports/xhs-content-cases.jsonl
CASE_REPORT ?= $(REPORT_DIR)/xhs-content-case-report.md
CASE_EXAMPLES ?= $(REPORT_DIR)/xhs-prompt-examples.jsonl
CASE_MIN_VIRAL ?= 4
CASE_LIMIT ?= 20
REVISION_LIBRARY ?= $(CASE_LIBRARY)
REVISION_REQUESTS ?= $(REPORT_DIR)/xhs-revision-requests.jsonl
REVISION_RESULTS ?= $(REPORT_DIR)/xhs-revision-results.jsonl
REVISION_RUN_ID ?= xhs_revision_loop
REVISION_LIMIT ?=
REVISION_LIVE ?= 0
REVISION_APPLY_RESULTS ?=
REVISION_APPEND_CASES ?= 0
REVISION_REVISED_LIBRARY ?= $(REVISION_LIBRARY)
PYTHON ?= uv run python

EVAL_ARGS := --jsonl "$(EVAL_JSONL)" --markdown "$(EVAL_MARKDOWN)"
EVAL_ARGS += --run-id "$(EVAL_RUN_ID)"
EVAL_ARGS += --min-overall "$(EVAL_MIN_OVERALL)"
EVAL_ARGS += --max-score-drop "$(EVAL_MAX_SCORE_DROP)"

ifneq ($(strip $(EVAL_CASE_LIBRARY)),)
EVAL_ARGS += --case-library "$(EVAL_CASE_LIBRARY)"
endif

ifneq ($(strip $(EVAL_PREVIOUS)),)
EVAL_ARGS += --compare-jsonl "$(EVAL_PREVIOUS)"
endif

ifeq ($(EVAL_LIVE),1)
EVAL_ARGS += --live
endif

ifeq ($(EVAL_REPORT_ONLY),1)
EVAL_ARGS += --report-only
endif

REVISION_ARGS := --library "$(REVISION_LIBRARY)" --requests-jsonl "$(REVISION_REQUESTS)" --run-id "$(REVISION_RUN_ID)"

ifneq ($(strip $(REVISION_LIMIT)),)
REVISION_ARGS += --limit "$(REVISION_LIMIT)"
endif

ifeq ($(REVISION_LIVE),1)
REVISION_ARGS += --live --results-jsonl "$(REVISION_RESULTS)"
endif

ifneq ($(strip $(REVISION_APPLY_RESULTS)),)
REVISION_ARGS += --apply-results-jsonl "$(REVISION_APPLY_RESULTS)"
endif

ifeq ($(REVISION_APPEND_CASES),1)
REVISION_ARGS += --append-revised-cases --revised-case-library "$(REVISION_REVISED_LIBRARY)"
endif

.PHONY: eval-quality summarize-cases plan-revisions test-quality

eval-quality:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_quality_eval.py $(EVAL_ARGS)

summarize-cases:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/summarize_xhs_content_cases.py --library "$(CASE_LIBRARY)" --markdown "$(CASE_REPORT)" --examples-jsonl "$(CASE_EXAMPLES)" --min-viral-potential "$(CASE_MIN_VIRAL)" --limit "$(CASE_LIMIT)"

plan-revisions:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/plan_xhs_revisions.py $(REVISION_ARGS)

test-quality:
	@uv run --with pytest pytest tests/test_xhs_quality_eval.py -q
