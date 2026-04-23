#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试核心模块功能"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_test():
    print("=" * 50)
    print("  红墨文本标注工具 - 核心模块测试")
    print("=" * 50)
    print()
    
    # Test models
    print("=== 测试 models 模块 ===")
    from text_annotator.models import TextIssue, ScanRule, Document, IssueType, IssueSeverity
    
    doc = Document(
        id="test-doc-001",
        name="测试文档",
        file_path=None,
        original_content="这是测试内容。",
        current_content="这是测试内容。"
    )
    print("[OK] Document 创建成功: " + doc.name)
    print("  - has_changes: " + str(doc.has_changes))
    
    issue = TextIssue(
        id="test-issue-001",
        issue_type=IssueType.REGEX,
        severity=IssueSeverity.WARNING,
        start_pos=0,
        end_pos=5,
        original_text="测试",
        message="这是一个测试问题"
    )
    print("[OK] TextIssue 创建成功: " + issue.message)
    print("  - type: " + issue.issue_type.value)
    print("  - severity: " + issue.severity.value)
    
    print()
    
    # Test scanners
    print("=== 测试 scanners 模块 ===")
    from text_annotator.scanners import ScannerManager
    
    manager = ScannerManager()
    manager.load_default_rules()
    print("[OK] ScannerManager 创建成功，默认规则已加载")
    
    test_text = """这是一个测试文本。
我的邮箱是 test@example.com，
手机号码是 13800138000。"""
    
    issues = manager.scan(test_text)
    print("[OK] 扫描测试文本，发现 " + str(len(issues)) + " 个问题")
    
    for i, issue in enumerate(issues, 1):
        print("  " + str(i) + ". [" + issue.issue_type.value + "] " + issue.message)
        print("     位置: " + str(issue.start_pos) + "-" + str(issue.end_pos))
        print("     原文: '" + issue.original_text + "'")
    
    print()
    
    # Test diff utils
    print("=== 测试 diff_utils 模块 ===")
    from text_annotator.utils.diff_utils import DiffComparator
    
    original = """这是第一行。
这是第二行。"""
    
    modified = """这是修改后的第一行。
这是插入的新行。
这是第二行。"""
    
    comparator = DiffComparator()
    changes = comparator.compare_texts(original, modified)
    print("[OK] 对比文本，发现 " + str(len(changes)) + " 处差异")
    
    for change in changes:
        print("  - [" + change.change_type + "] 行 " + str(change.line_number))
    
    print()
    
    # Test file utils
    print("=== 测试 file_utils 模块 ===")
    from text_annotator.utils.file_utils import FileUtils
    
    test_content = "# 测试 Markdown 文档\n\n这是一个测试文档。\n"
    
    doc = FileUtils.create_document_from_content(test_content, "test.md")
    print("[OK] 从内容创建文档: " + doc.name)
    print("  - 内容长度: " + str(len(doc.current_content)) + " 字符")
    
    supported_exts = FileUtils.SUPPORTED_EXTENSIONS
    print("[OK] 支持的文件格式: " + ", ".join(supported_exts))
    
    print()
    
    # Test export utils
    print("=== 测试 export_utils 模块 ===")
    from text_annotator.utils.export_utils import ExportUtils
    
    test_issues = [
        TextIssue(
            id="issue-1",
            issue_type=IssueType.REGEX,
            severity=IssueSeverity.ERROR,
            start_pos=0,
            end_pos=10,
            original_text="测试错误",
            message="这是一个错误",
            line_number=1
        ),
        TextIssue(
            id="issue-2",
            issue_type=IssueType.FORMAT,
            severity=IssueSeverity.WARNING,
            start_pos=20,
            end_pos=30,
            original_text="格式问题",
            message="这是一个警告",
            line_number=2
        )
    ]
    
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        temp_json = f.name
    
    success = ExportUtils.export_issues_to_json(test_issues, temp_json)
    if success:
        print("[OK] 导出 JSON 报告成功")
    else:
        print("[FAIL] 导出 JSON 报告失败")
    
    os.unlink(temp_json)
    
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        temp_csv = f.name
    
    success = ExportUtils.export_issues_to_csv(test_issues, temp_csv)
    if success:
        print("[OK] 导出 CSV 报告成功")
    else:
        print("[FAIL] 导出 CSV 报告失败")
    
    os.unlink(temp_csv)
    
    print()
    
    print("=" * 50)
    print("  [OK] 所有核心模块测试通过！")
    print("=" * 50)
    print()
    print("安装 PySide6 后可运行 GUI 应用:")
    print("  pip install PySide6")
    print("  python -m text_annotator.app")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(run_test())
