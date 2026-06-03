REPORT_DIR ?= reports
EVAL_CASES ?= tests/fixtures/xhs_quality_cases.json
EVAL_JSONL ?= $(REPORT_DIR)/xhs-quality-eval.jsonl
EVAL_MARKDOWN ?= $(REPORT_DIR)/xhs-quality-eval.md
EVAL_PREVIOUS ?=
EVAL_CASE_LIBRARY ?=
EVAL_RUN_ID ?= xhs_quality_eval
EVAL_MIN_OVERALL ?= 80
EVAL_MAX_SCORE_DROP ?= 3
EVAL_LIVE ?= 0
EVAL_REPORT_ONLY ?= 0
EVAL_PROMPT_EXAMPLES ?=
EVAL_PROMPT_EXAMPLES_LIMIT ?= 3
CASE_LIBRARY ?= reports/xhs-content-cases.jsonl
CASE_REPORT ?= $(REPORT_DIR)/xhs-content-case-report.md
CASE_EXAMPLES ?= $(REPORT_DIR)/xhs-prompt-examples.jsonl
CASE_QUALITY_EXAMPLES ?= $(REPORT_DIR)/xhs-quality-prompt-examples.jsonl
CASE_MIN_VIRAL ?= 4
CASE_MIN_QUALITY_OVERALL ?= 85
CASE_MIN_SCORE_DELTA ?= 3
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
REEVAL_LIBRARY ?= $(CASE_LIBRARY)
REEVAL_JSONL ?= $(REPORT_DIR)/xhs-re-evaluation.jsonl
REEVAL_MARKDOWN ?= $(REPORT_DIR)/xhs-re-evaluation.md
REEVAL_RUN_ID ?= xhs_re_evaluation
REEVAL_LIMIT ?=
REEVAL_MIN_IMPROVEMENT ?= 0
REEVAL_LIVE ?= 0
REEVAL_UPDATE_LIBRARY ?= 0
REEVAL_REPORT_ONLY ?= 0
LOOP_REPORT_DIR ?= $(REPORT_DIR)/xhs-quality-loop
LOOP_CASES ?= tests/fixtures/xhs_quality_cases.json
LOOP_CASE_LIBRARY ?= $(LOOP_REPORT_DIR)/xhs-content-cases.jsonl
LOOP_REPLAY_INDEX ?= $(LOOP_REPORT_DIR)/xhs-quality-loop-index.jsonl
LOOP_RUN_ID ?= xhs_quality_loop
LOOP_MIN_OVERALL ?= 95
LOOP_MIN_IMPROVEMENT ?= 0
LOOP_MIN_QUALITY_OVERALL ?= 85
LOOP_MIN_SCORE_DELTA ?= 3
LOOP_LIMIT ?= 20
LOOP_PROMPT_EXAMPLES ?=
LOOP_PROMPT_EXAMPLES_LIMIT ?= 3
LOOP_LIVE_CONTENT ?= 0
LOOP_LIVE_REVISION ?= 0
LOOP_LIVE_REEVAL ?= 0
LOOP_HISTORY_INDEX ?= $(LOOP_REPLAY_INDEX)
LOOP_HISTORY_MARKDOWN ?= $(LOOP_REPORT_DIR)/xhs-quality-loop-history.md
LOOP_AB_INDEX ?= $(AB_REPORT_DIR)/xhs-quality-ab-index.jsonl
LOOP_IMPROVEMENT_PLAN ?= $(LOOP_REPORT_DIR)/xhs-quality-improvement-plan.jsonl
LOOP_IMPROVEMENT_DRAFT_DIR ?= $(LOOP_REPORT_DIR)/improvement-drafts
LOOP_IMPROVEMENT_DRAFT_RUN_ID ?= xhs_improvement_drafts
LOOP_EVAL_CASE_DRAFTS ?= $(LOOP_IMPROVEMENT_DRAFT_DIR)/xhs-eval-case-drafts.jsonl
LOOP_EVAL_CASE_CANDIDATES ?= $(LOOP_REPORT_DIR)/xhs-eval-case-candidates.jsonl
LOOP_APPLY_RUN_ID ?= xhs_apply_improvements
LOOP_APPLY_APPROVED ?= 0
LOOP_PROMOTED_CASES ?= $(LOOP_REPORT_DIR)/xhs-quality-cases.next.json
LOOP_PROMOTED_VERSION_ID ?= xhs_quality_cases_next
LOOP_PROMOTE_APPROVED ?= 0
LOOP_RECOMMENDED_CASES ?= $(LOOP_REPORT_DIR)/xhs-quality-cases.recommended.json
LOOP_MARK_RECOMMENDED ?= 0
AB_REPORT_DIR ?= $(REPORT_DIR)/xhs-quality-ab
AB_BASE_CASES ?= tests/fixtures/xhs_quality_cases.json
AB_CANDIDATE_CASES ?= $(LOOP_PROMOTED_CASES)
AB_RUN_ID ?= xhs_quality_ab
AB_MIN_OVERALL ?= $(EVAL_MIN_OVERALL)
AB_MAX_SCORE_DROP ?= $(EVAL_MAX_SCORE_DROP)
AB_LIVE ?= 0
AB_REPORT_ONLY ?= 0
LOOP_HISTORY_LIMIT ?=
PYTHON ?= uv run python

EVAL_ARGS := --cases "$(EVAL_CASES)" --jsonl "$(EVAL_JSONL)" --markdown "$(EVAL_MARKDOWN)"
EVAL_ARGS += --run-id "$(EVAL_RUN_ID)"
EVAL_ARGS += --min-overall "$(EVAL_MIN_OVERALL)"
EVAL_ARGS += --max-score-drop "$(EVAL_MAX_SCORE_DROP)"

ifneq ($(strip $(EVAL_CASE_LIBRARY)),)
EVAL_ARGS += --case-library "$(EVAL_CASE_LIBRARY)"
endif

ifneq ($(strip $(EVAL_PREVIOUS)),)
EVAL_ARGS += --compare-jsonl "$(EVAL_PREVIOUS)"
endif

ifneq ($(strip $(EVAL_PROMPT_EXAMPLES)),)
EVAL_ARGS += --prompt-examples-jsonl "$(EVAL_PROMPT_EXAMPLES)" --prompt-examples-limit "$(EVAL_PROMPT_EXAMPLES_LIMIT)"
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

REEVAL_ARGS := --library "$(REEVAL_LIBRARY)" --jsonl "$(REEVAL_JSONL)" --markdown "$(REEVAL_MARKDOWN)"
REEVAL_ARGS += --run-id "$(REEVAL_RUN_ID)"
REEVAL_ARGS += --min-improvement "$(REEVAL_MIN_IMPROVEMENT)"

ifneq ($(strip $(REEVAL_LIMIT)),)
REEVAL_ARGS += --limit "$(REEVAL_LIMIT)"
endif

ifeq ($(REEVAL_LIVE),1)
REEVAL_ARGS += --live
endif

ifeq ($(REEVAL_UPDATE_LIBRARY),1)
REEVAL_ARGS += --update-case-library
endif

ifeq ($(REEVAL_REPORT_ONLY),1)
REEVAL_ARGS += --report-only
endif

LOOP_ARGS := --cases "$(LOOP_CASES)" --report-dir "$(LOOP_REPORT_DIR)" --case-library "$(LOOP_CASE_LIBRARY)"
LOOP_ARGS += --replay-index "$(LOOP_REPLAY_INDEX)"
LOOP_ARGS += --run-id "$(LOOP_RUN_ID)"
LOOP_ARGS += --min-overall "$(LOOP_MIN_OVERALL)"
LOOP_ARGS += --min-improvement "$(LOOP_MIN_IMPROVEMENT)"
LOOP_ARGS += --min-quality-overall "$(LOOP_MIN_QUALITY_OVERALL)"
LOOP_ARGS += --min-score-delta "$(LOOP_MIN_SCORE_DELTA)"
LOOP_ARGS += --limit "$(LOOP_LIMIT)"

ifneq ($(strip $(LOOP_PROMPT_EXAMPLES)),)
LOOP_ARGS += --prompt-examples-jsonl "$(LOOP_PROMPT_EXAMPLES)" --prompt-examples-limit "$(LOOP_PROMPT_EXAMPLES_LIMIT)"
endif

ifeq ($(LOOP_LIVE_CONTENT),1)
LOOP_ARGS += --live-content
endif

ifeq ($(LOOP_LIVE_REVISION),1)
LOOP_ARGS += --live-revision
endif

ifeq ($(LOOP_LIVE_REEVAL),1)
LOOP_ARGS += --live-re-evaluation
endif

LOOP_HISTORY_ARGS := --replay-index "$(LOOP_HISTORY_INDEX)" --ab-index "$(LOOP_AB_INDEX)" --markdown "$(LOOP_HISTORY_MARKDOWN)"
LOOP_HISTORY_ARGS += --improvement-plan-jsonl "$(LOOP_IMPROVEMENT_PLAN)"

ifneq ($(strip $(LOOP_HISTORY_LIMIT)),)
LOOP_HISTORY_ARGS += --limit "$(LOOP_HISTORY_LIMIT)"
endif

DRAFT_IMPROVEMENT_ARGS := --plan-jsonl "$(LOOP_IMPROVEMENT_PLAN)" --output-dir "$(LOOP_IMPROVEMENT_DRAFT_DIR)"
DRAFT_IMPROVEMENT_ARGS += --run-id "$(LOOP_IMPROVEMENT_DRAFT_RUN_ID)"

APPLY_IMPROVEMENT_ARGS := --eval-case-drafts "$(LOOP_EVAL_CASE_DRAFTS)" --candidate-jsonl "$(LOOP_EVAL_CASE_CANDIDATES)"
APPLY_IMPROVEMENT_ARGS += --run-id "$(LOOP_APPLY_RUN_ID)"

ifeq ($(LOOP_APPLY_APPROVED),1)
APPLY_IMPROVEMENT_ARGS += --apply-approved
else
APPLY_IMPROVEMENT_ARGS += --dry-run
endif

PROMOTE_EVAL_CASE_ARGS := --candidates-jsonl "$(LOOP_EVAL_CASE_CANDIDATES)" --base-cases "tests/fixtures/xhs_quality_cases.json"
PROMOTE_EVAL_CASE_ARGS += --output "$(LOOP_PROMOTED_CASES)" --version-id "$(LOOP_PROMOTED_VERSION_ID)"

ifeq ($(LOOP_PROMOTE_APPROVED),1)
PROMOTE_EVAL_CASE_ARGS += --promote-approved
else
PROMOTE_EVAL_CASE_ARGS += --dry-run
endif

RECOMMEND_EVAL_CASE_ARGS := --version-id "$(LOOP_PROMOTED_VERSION_ID)"
RECOMMEND_EVAL_CASE_ARGS += --candidate-cases "$(LOOP_PROMOTED_CASES)" --ab-index "$(LOOP_AB_INDEX)"
RECOMMEND_EVAL_CASE_ARGS += --recommended-output "$(LOOP_RECOMMENDED_CASES)"

ifeq ($(LOOP_MARK_RECOMMENDED),1)
RECOMMEND_EVAL_CASE_ARGS += --mark-recommended
else
RECOMMEND_EVAL_CASE_ARGS += --dry-run
endif

AB_ARGS := --base-cases "$(AB_BASE_CASES)" --candidate-cases "$(AB_CANDIDATE_CASES)"
AB_ARGS += --report-dir "$(AB_REPORT_DIR)" --run-id "$(AB_RUN_ID)"
AB_ARGS += --min-overall "$(AB_MIN_OVERALL)" --max-score-drop "$(AB_MAX_SCORE_DROP)"

ifeq ($(AB_LIVE),1)
AB_ARGS += --live
endif

ifeq ($(AB_REPORT_ONLY),1)
AB_ARGS += --report-only
endif

.PHONY: eval-quality eval-quality-ab summarize-cases plan-revisions re-eval-revisions xhs-quality-loop summarize-loop draft-improvements apply-improvements promote-eval-cases recommend-eval-cases test-quality

eval-quality:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_quality_eval.py $(EVAL_ARGS)

eval-quality-ab:
	@mkdir -p "$(AB_REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_quality_ab.py $(AB_ARGS)

summarize-cases:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/summarize_xhs_content_cases.py --library "$(CASE_LIBRARY)" --markdown "$(CASE_REPORT)" --examples-jsonl "$(CASE_EXAMPLES)" --quality-examples-jsonl "$(CASE_QUALITY_EXAMPLES)" --min-viral-potential "$(CASE_MIN_VIRAL)" --min-quality-overall "$(CASE_MIN_QUALITY_OVERALL)" --min-score-delta "$(CASE_MIN_SCORE_DELTA)" --limit "$(CASE_LIMIT)"

plan-revisions:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/plan_xhs_revisions.py $(REVISION_ARGS)

re-eval-revisions:
	@mkdir -p "$(REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_re_evaluation.py $(REEVAL_ARGS)

xhs-quality-loop:
	@mkdir -p "$(LOOP_REPORT_DIR)"
	@$(PYTHON) scripts/run_xhs_quality_loop.py $(LOOP_ARGS)

summarize-loop:
	@mkdir -p "$(LOOP_REPORT_DIR)"
	@$(PYTHON) scripts/summarize_xhs_quality_loop.py $(LOOP_HISTORY_ARGS)

draft-improvements:
	@mkdir -p "$(LOOP_IMPROVEMENT_DRAFT_DIR)"
	@$(PYTHON) scripts/draft_xhs_improvements.py $(DRAFT_IMPROVEMENT_ARGS)

apply-improvements:
	@mkdir -p "$(dir $(LOOP_EVAL_CASE_CANDIDATES))"
	@$(PYTHON) scripts/apply_xhs_improvements.py $(APPLY_IMPROVEMENT_ARGS)

promote-eval-cases:
	@mkdir -p "$(dir $(LOOP_PROMOTED_CASES))"
	@$(PYTHON) scripts/promote_xhs_eval_cases.py $(PROMOTE_EVAL_CASE_ARGS)

recommend-eval-cases:
	@mkdir -p "$(dir $(LOOP_RECOMMENDED_CASES))"
	@$(PYTHON) scripts/promote_xhs_eval_cases.py $(RECOMMEND_EVAL_CASE_ARGS)

test-quality:
	@uv run --with pytest pytest tests/test_xhs_quality_eval.py -q
