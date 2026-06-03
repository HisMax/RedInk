"""
Draft execution artifacts for Xiaohongshu quality improvement plans.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


BUNDLE_SCHEMA_VERSION = "xhs_quality_improvement_draft_bundle.v1"
PROMPT_PATCH_SCHEMA_VERSION = "xhs_prompt_patch_draft.v1"
EVAL_CASE_SCHEMA_VERSION = "xhs_eval_case_draft.v1"
REVISION_PATCH_SCHEMA_VERSION = "xhs_revision_prompt_patch_draft.v1"


def load_improvement_tasks(path: str | Path) -> List[Dict[str, Any]]:
    """Load improvement tasks from JSONL."""
    task_path = Path(path)
    if not task_path.exists():
        return []
    tasks = []
    with task_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                tasks.append(json.loads(line))
    return tasks


def build_improvement_draft_bundle(
    tasks: Iterable[Dict[str, Any]],
    *,
    run_id: str = "xhs_improvement_drafts",
    created_at: str | None = None,
) -> Dict[str, Any]:
    """Build prompt, revision, eval, and checklist drafts from improvement tasks."""
    rows = list(tasks)
    prompt_drafts = [_prompt_patch_draft(task) for task in rows if _is_prompt_task(task)]
    eval_drafts = [_eval_case_draft(task) for task in rows if _is_eval_task(task)]
    revision_drafts = [_revision_prompt_draft(task) for task in rows if _is_revision_task(task)]
    checklist = [_checklist_item(task) for task in rows]
    return {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": created_at or _utc_now(),
        "requires_human_approval": True,
        "task_count": len(rows),
        "draft_counts": {
            "prompt_patch_drafts": len(prompt_drafts),
            "eval_case_drafts": len(eval_drafts),
            "revision_prompt_drafts": len(revision_drafts),
            "execution_checklist_items": len(checklist),
        },
        "prompt_patch_drafts": prompt_drafts,
        "eval_case_drafts": eval_drafts,
        "revision_prompt_drafts": revision_drafts,
        "execution_checklist": checklist,
    }


def write_improvement_draft_bundle(bundle: Dict[str, Any], output_dir: str | Path) -> Dict[str, Path]:
    """Write an improvement draft bundle and return artifact paths."""
    draft_dir = Path(output_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": draft_dir / "xhs-improvement-draft-manifest.json",
        "prompt_patch_drafts": draft_dir / "xhs-prompt-patch-drafts.md",
        "eval_case_drafts": draft_dir / "xhs-eval-case-drafts.jsonl",
        "revision_prompt_drafts": draft_dir / "xhs-revision-prompt-drafts.md",
        "execution_checklist": draft_dir / "xhs-improvement-execution-checklist.md",
    }
    paths["manifest"].write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    paths["prompt_patch_drafts"].write_text(_prompt_patch_markdown(bundle), encoding="utf-8")
    paths["eval_case_drafts"].write_text(_eval_case_jsonl(bundle), encoding="utf-8")
    paths["revision_prompt_drafts"].write_text(_revision_patch_markdown(bundle), encoding="utf-8")
    paths["execution_checklist"].write_text(_checklist_markdown(bundle), encoding="utf-8")
    return paths


def _is_prompt_task(task: Dict[str, Any]) -> bool:
    return task.get("stage") == "prompt"


def _is_eval_task(task: Dict[str, Any]) -> bool:
    return task.get("stage") == "eval"


def _is_revision_task(task: Dict[str, Any]) -> bool:
    return task.get("stage") == "revision"


def _prompt_patch_draft(task: Dict[str, Any]) -> Dict[str, Any]:
    issue_id = task.get("source_issue_id") or "unknown_issue"
    return {
        "schema_version": PROMPT_PATCH_SCHEMA_VERSION,
        "draft_id": f"prompt_patch_{task.get('task_id')}",
        "source_task_id": task.get("task_id"),
        "source_issue_id": issue_id,
        "status": "draft",
        "requires_human_approval": True,
        "target": "content_generation_prompt",
        "config_targets": task.get("config_targets") or [],
        "patch_notes": [
            "强化标题钩子：标题需要给出明确人群、场景或结果承诺。",
            "强化正文结构：开头给痛点，中段给步骤，结尾给收藏或行动理由。",
            "强化信息密度：每段至少包含一个可执行细节，避免泛泛表达。",
            "生成前优先引用已验证的 xhs-quality-prompt-examples.jsonl 样本。",
        ],
        "acceptance_check": task.get("acceptance_check"),
    }


def _eval_case_draft(task: Dict[str, Any]) -> Dict[str, Any]:
    issue_id = task.get("source_issue_id") or "unknown_issue"
    return {
        "schema_version": EVAL_CASE_SCHEMA_VERSION,
        "draft_id": f"eval_case_{task.get('task_id')}",
        "source_task_id": task.get("task_id"),
        "source_issue_id": issue_id,
        "status": "draft",
        "requires_human_approval": True,
        "category": "quality_regression",
        "topic": "待补充：高频 baseline 失败主题",
        "outline": {
            "audience": "小红书目标用户",
            "scenario": "从历史质量诊断中抽样出的失败场景",
            "goal": "验证标题钩子、正文结构、可执行信息密度和收藏理由是否改善",
        },
        "expected_focus": [
            "标题钩子",
            "正文结构",
            "可执行细节",
            "收藏理由",
            "标签匹配",
        ],
        "config_targets": task.get("config_targets") or [],
        "acceptance_check": task.get("acceptance_check"),
    }


def _revision_prompt_draft(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": REVISION_PATCH_SCHEMA_VERSION,
        "draft_id": f"revision_patch_{task.get('task_id')}",
        "source_task_id": task.get("task_id"),
        "source_issue_id": task.get("source_issue_id"),
        "status": "draft",
        "requires_human_approval": True,
        "target": "revision_prompt",
        "config_targets": task.get("config_targets") or [],
        "patch_notes": [
            "改稿必须逐项引用 baseline 失败原因。",
            "输出 revision_summary 时说明每一处修改解决了什么问题。",
            "避免只做措辞润色，必须改变标题、开头或结构中的至少一项。",
        ],
        "acceptance_check": task.get("acceptance_check"),
    }


def _checklist_item(task: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "stage": task.get("stage"),
        "title": task.get("title"),
        "action": task.get("action"),
        "config_targets": task.get("config_targets") or [],
        "acceptance_check": task.get("acceptance_check"),
        "status": "needs_human_approval",
    }


def _prompt_patch_markdown(bundle: Dict[str, Any]) -> str:
    lines = [
        "# XHS Prompt Patch Drafts",
        "",
        "这些草案需要人工确认后再应用到真实 prompt 或配置。",
        "",
    ]
    for draft in bundle.get("prompt_patch_drafts") or []:
        lines.extend([
            f"## {draft.get('source_task_id')}",
            "",
            f"- Source issue: `{draft.get('source_issue_id')}`",
            f"- Target: `{draft.get('target')}`",
            f"- Acceptance: {draft.get('acceptance_check') or ''}",
            "",
        ])
        for note in draft.get("patch_notes") or []:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def _eval_case_jsonl(bundle: Dict[str, Any]) -> str:
    rows = bundle.get("eval_case_drafts") or []
    if not rows:
        return ""
    return "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"


def _revision_patch_markdown(bundle: Dict[str, Any]) -> str:
    lines = [
        "# XHS Revision Prompt Drafts",
        "",
        "这些草案需要人工确认后再应用到真实 revision prompt。",
        "",
    ]
    for draft in bundle.get("revision_prompt_drafts") or []:
        lines.extend([
            f"## {draft.get('source_task_id')}",
            "",
            f"- Source issue: `{draft.get('source_issue_id')}`",
            f"- Target: `{draft.get('target')}`",
            f"- Acceptance: {draft.get('acceptance_check') or ''}",
            "",
        ])
        for note in draft.get("patch_notes") or []:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def _checklist_markdown(bundle: Dict[str, Any]) -> str:
    lines = [
        "# XHS Improvement Execution Checklist",
        "",
        "所有任务默认需要人工确认后再应用。",
        "",
        "| Order | Stage | Task | Status | Acceptance Check |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(bundle.get("execution_checklist") or [], start=1):
        lines.append(
            "| {order} | {stage} | {task_id} | {status} | {check} |".format(
                order=index,
                stage=item.get("stage") or "",
                task_id=item.get("task_id") or "",
                status=item.get("status") or "",
                check=item.get("acceptance_check") or "",
            )
        )
    lines.append("")
    return "\n".join(lines)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
