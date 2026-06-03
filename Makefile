REPORT_DIR ?= reports
EVAL_JSONL ?= $(REPORT_DIR)/xhs-quality-eval.jsonl
EVAL_MARKDOWN ?= $(REPORT_DIR)/xhs-quality-eval.md
EVAL_PREVIOUS ?=
EVAL_MIN_OVERALL ?= 80
EVAL_MAX_SCORE_DROP ?= 3
EVAL_LIVE ?= 0
EVAL_REPORT_ONLY ?= 0
PYTHON ?= uv run python

EVAL_ARGS := --jsonl "$(EVAL_JSONL)" --markdown "$(EVAL_MARKDOWN)"
EVAL_ARGS += --min-overall "$(EVAL_MIN_OVERALL)"
EVAL_ARGS += --max-score-drop "$(EVAL_MAX_SCORE_DROP)"

ifneq ($(strip $(EVAL_PREVIOUS)),)
EVAL_ARGS += --compare-jsonl "$(EVAL_PREVIOUS)"
endif

ifeq ($(EVAL_LIVE),1)
EVAL_ARGS += --live
endif

ifeq ($(EVAL_REPORT_ONLY),1)
EVAL_ARGS += --report-only
endif

.PHONY: eval-quality test-quality

eval-quality:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_quality_eval.py $(EVAL_ARGS)

test-quality:
	@uv run --with pytest pytest tests/test_xhs_quality_eval.py -q
