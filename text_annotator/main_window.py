import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QMessageBox, QTabWidget,
    QLabel, QStatusBar, QToolBar, QMenu, QMenuBar,
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTextEdit, QFormLayout, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QKeySequence
from typing import Optional, List
from .models import Document, IssueType
from .scanners import ScannerManager
from .utils import FileUtils, ExportUtils, DiffComparator
from .widgets import HighlightEditor, IssuePanel, DiffView, RuleSettings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self._document: Optional[Document] = None
        self._scanner_manager = ScannerManager()
        self._diff_comparator = DiffComparator()
        
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_connections()
        
        self._scanner_manager.load_default_rules()

    def _setup_ui(self):
        self.setWindowTitle("红墨文本标注工具 - RedInk Text Annotator")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QMenuBar {
                background-color: #2d2d2d;
                color: #cccccc;
                border-bottom: 1px solid #3c3c3c;
            }
            QMenuBar::item {
                padding: 5px 12px;
            }
            QMenuBar::item:selected {
                background-color: #094771;
            }
            QMenu {
                background-color: #252526;
                border: 1px solid #454545;
            }
            QMenu::item {
                color: #cccccc;
                padding: 6px 24px;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QMenu::item:disabled {
                color: #6e6e6e;
            }
            QToolBar {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                padding: 4px;
                spacing: 8px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                padding: 6px 12px;
                color: #cccccc;
                border-radius: 3px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
            }
            QToolButton:pressed {
                background-color: #094771;
            }
            QStatusBar {
                background-color: #007acc;
                color: white;
                border: none;
            }
            QStatusBar QLabel {
                color: white;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #858585;
                padding: 8px 20px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QTabBar::tab:hover {
                background-color: #3c3c3c;
                color: #cccccc;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        left_panel = self._create_left_panel()
        main_splitter.addWidget(left_panel)
        
        center_panel = self._create_center_panel()
        main_splitter.addWidget(center_panel)
        
        main_splitter.setSizes([300, 1100])
        main_layout.addWidget(main_splitter)
        
        self._create_status_bar()

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        left_tabs = QTabWidget()
        left_tabs.setTabPosition(QTabWidget.West)
        
        self._issue_panel = IssuePanel()
        left_tabs.addTab(self._issue_panel, "问题")
        
        self._rule_settings = RuleSettings()
        left_tabs.addTab(self._rule_settings, "规则")
        
        layout.addWidget(left_tabs)
        
        return panel

    def _create_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self._center_tabs = QTabWidget()
        self._center_tabs.setTabsClosable(False)
        self._center_tabs.setMovable(False)
        
        self._editor_tab = QWidget()
        editor_layout = QVBoxLayout(self._editor_tab)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        self._editor = HighlightEditor()
        self._editor.setPlaceholderText("在此输入或粘贴文本，或从文件菜单导入...")
        editor_layout.addWidget(self._editor)
        
        self._center_tabs.addTab(self._editor_tab, "编辑器")
        
        self._diff_tab = QWidget()
        diff_layout = QVBoxLayout(self._diff_tab)
        diff_layout.setContentsMargins(0, 0, 0, 0)
        
        self._diff_view = DiffView()
        diff_layout.addWidget(self._diff_view)
        
        self._center_tabs.addTab(self._diff_tab, "差异对比")
        
        layout.addWidget(self._center_tabs)
        
        return panel

    def _create_status_bar(self):
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        
        self._file_label = QLabel("未打开文件")
        self._status_bar.addWidget(self._file_label)
        
        self._status_bar.addPermanentWidget(QLabel("  "))
        
        self._cursor_label = QLabel("行 1, 列 1")
        self._status_bar.addPermanentWidget(self._cursor_label)
        
        self._encoding_label = QLabel("UTF-8")
        self._status_bar.addPermanentWidget(self._encoding_label)

    def _setup_menus(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        self._new_action = QAction("新建(&N)", self)
        self._new_action.setShortcut(QKeySequence.New)
        self._new_action.triggered.connect(self._new_document)
        file_menu.addAction(self._new_action)
        
        self._open_action = QAction("打开(&O)...", self)
        self._open_action.setShortcut(QKeySequence.Open)
        self._open_action.triggered.connect(self._open_file)
        file_menu.addAction(self._open_action)
        
        file_menu.addSeparator()
        
        self._save_action = QAction("保存(&S)", self)
        self._save_action.setShortcut(QKeySequence.Save)
        self._save_action.triggered.connect(self._save_document)
        self._save_action.setEnabled(False)
        file_menu.addAction(self._save_action)
        
        self._save_as_action = QAction("另存为(&A)...", self)
        self._save_as_action.setShortcut(QKeySequence.SaveAs)
        self._save_as_action.triggered.connect(self._save_document_as)
        self._save_as_action.setEnabled(False)
        file_menu.addAction(self._save_as_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("导出(&E)")
        
        self._export_text_action = QAction("导出处理后文本...", self)
        self._export_text_action.triggered.connect(self._export_text)
        self._export_text_action.setEnabled(False)
        export_menu.addAction(self._export_text_action)
        
        self._export_json_action = QAction("导出问题报告 (JSON)...", self)
        self._export_json_action.triggered.connect(self._export_json)
        self._export_json_action.setEnabled(False)
        export_menu.addAction(self._export_json_action)
        
        self._export_csv_action = QAction("导出问题报告 (CSV)...", self)
        self._export_csv_action.triggered.connect(self._export_csv)
        self._export_csv_action.setEnabled(False)
        export_menu.addAction(self._export_csv_action)
        
        file_menu.addSeparator()
        
        self._exit_action = QAction("退出(&X)", self)
        self._exit_action.setShortcut(QKeySequence.Quit)
        self._exit_action.triggered.connect(self.close)
        file_menu.addAction(self._exit_action)
        
        edit_menu = menubar.addMenu("编辑(&E)")
        
        self._undo_action = QAction("撤销(&U)", self)
        self._undo_action.setShortcut(QKeySequence.Undo)
        self._undo_action.triggered.connect(self._editor.undo)
        edit_menu.addAction(self._undo_action)
        
        self._redo_action = QAction("重做(&R)", self)
        self._redo_action.setShortcut(QKeySequence.Redo)
        self._redo_action.triggered.connect(self._editor.redo)
        edit_menu.addAction(self._redo_action)
        
        edit_menu.addSeparator()
        
        self._cut_action = QAction("剪切(&T)", self)
        self._cut_action.setShortcut(QKeySequence.Cut)
        self._cut_action.triggered.connect(self._editor.cut)
        edit_menu.addAction(self._cut_action)
        
        self._copy_action = QAction("复制(&C)", self)
        self._copy_action.setShortcut(QKeySequence.Copy)
        self._copy_action.triggered.connect(self._editor.copy)
        edit_menu.addAction(self._copy_action)
        
        self._paste_action = QAction("粘贴(&P)", self)
        self._paste_action.setShortcut(QKeySequence.Paste)
        self._paste_action.triggered.connect(self._editor.paste)
        edit_menu.addAction(self._paste_action)
        
        edit_menu.addSeparator()
        
        self._select_all_action = QAction("全选(&A)", self)
        self._select_all_action.setShortcut(QKeySequence.SelectAll)
        self._select_all_action.triggered.connect(self._editor.selectAll)
        edit_menu.addAction(self._select_all_action)
        
        scan_menu = menubar.addMenu("扫描(&S)")
        
        self._scan_all_action = QAction("执行扫描(&S)", self)
        self._scan_all_action.setShortcut("F5")
        self._scan_all_action.triggered.connect(self._scan_text)
        scan_menu.addAction(self._scan_all_action)
        
        scan_menu.addSeparator()
        
        self._clear_issues_action = QAction("清除问题标记", self)
        self._clear_issues_action.triggered.connect(self._clear_issues)
        scan_menu.addAction(self._clear_issues_action)
        
        diff_menu = menubar.addMenu("差异(&D)")
        
        self._compare_with_original_action = QAction("与原文对比", self)
        self._compare_with_original_action.triggered.connect(self._compare_with_original)
        diff_menu.addAction(self._compare_with_original_action)
        
        self._apply_all_changes_action = QAction("接受所有差异", self)
        self._apply_all_changes_action.triggered.connect(self._apply_all_diff_changes)
        diff_menu.addAction(self._apply_all_changes_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        self._about_action = QAction("关于(&A)", self)
        self._about_action.triggered.connect(self._show_about)
        help_menu.addAction(self._about_action)

    def _setup_toolbar(self):
        toolbar = self.addToolBar("主工具栏")
        toolbar.setMovable(False)
        
        toolbar.addAction(self._new_action)
        toolbar.addAction(self._open_action)
        toolbar.addAction(self._save_action)
        toolbar.addSeparator()
        toolbar.addAction(self._scan_all_action)
        toolbar.addSeparator()
        toolbar.addAction(self._compare_with_original_action)

    def _setup_connections(self):
        self._editor.cursorPositionChanged.connect(self._update_cursor_position)
        self._editor.text_modified.connect(self._on_text_modified)
        
        self._issue_panel.issue_selected.connect(self._on_issue_selected)
        self._issue_panel.issue_accepted.connect(self._on_issue_accepted)
        self._issue_panel.issue_rejected.connect(self._on_issue_rejected)
        self._issue_panel.scan_requested.connect(self._scan_text)
        
        self._diff_view.change_accepted.connect(self._on_diff_change_accepted)
        self._diff_view.change_rejected.connect(self._on_diff_change_rejected)
        self._diff_view.all_changes_accepted.connect(self._apply_all_diff_changes)
        self._diff_view.all_changes_rejected.connect(self._reject_all_diff_changes)
        
        self._rule_settings.rules_changed.connect(self._on_rules_changed)
        
        self._center_tabs.currentChanged.connect(self._on_tab_changed)

    def _new_document(self):
        if self._document and self._document.has_changes:
            reply = QMessageBox.question(
                self, "保存更改",
                "当前文档有未保存的更改，是否保存？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                if not self._save_document():
                    return
        
        from .models import Document
        import uuid
        
        self._document = Document(
            id=str(uuid.uuid4()),
            name="未命名文档",
            file_path=None,
            original_content="",
            current_content=""
        )
        
        self._editor.setPlainText("")
        self._issue_panel.clear_issues()
        self._editor.clear_issues()
        self._diff_view.clear()
        
        self._update_title()
        self._update_file_label()
        self._enable_actions(True)

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开文件",
            "",
            "文本文件 (*.txt *.md *.markdown);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        document, error = FileUtils.load_document(file_path)
        
        if error:
            QMessageBox.critical(self, "打开文件失败", error)
            return
        
        self._document = document
        self._editor.setPlainText(document.current_content)
        self._issue_panel.clear_issues()
        self._editor.clear_issues()
        self._diff_view.clear()
        
        self._update_title()
        self._update_file_label()
        self._enable_actions(True)
        
        reply = QMessageBox.question(
            self, "自动扫描",
            "是否立即扫描文档中的问题？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._scan_text()

    def _save_document(self) -> bool:
        if not self._document:
            return False
        
        if self._document.file_path:
            self._document.current_content = self._editor.toPlainText()
            success, error = FileUtils.save_document(self._document)
            
            if not success:
                QMessageBox.critical(self, "保存失败", error)
                return False
            
            self._document.original_content = self._document.current_content
            self._update_title()
            self._status_bar.showMessage("文件已保存", 3000)
            return True
        else:
            return self._save_document_as()

    def _save_document_as(self) -> bool:
        if not self._document:
            return False
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            self._document.name,
            "文本文件 (*.txt);;Markdown 文件 (*.md);;所有文件 (*.*)"
        )
        
        if not file_path:
            return False
        
        self._document.current_content = self._editor.toPlainText()
        success, error = FileUtils.save_document(self._document, file_path)
        
        if not success:
            QMessageBox.critical(self, "保存失败", error)
            return False
        
        self._document.original_content = self._document.current_content
        self._update_title()
        self._update_file_label()
        self._status_bar.showMessage("文件已保存", 3000)
        return True

    def _scan_text(self):
        if not self._document:
            QMessageBox.information(self, "提示", "请先创建或打开一个文档")
            return
        
        text = self._editor.toPlainText()
        self._document.current_content = text
        
        rules = self._rule_settings.get_rules()
        for rule in rules:
            self._scanner_manager.add_rule(rule)
        
        issues = self._scanner_manager.scan(text)
        self._document.issues = issues
        
        self._issue_panel.set_issues(issues)
        self._editor.set_issues(issues)
        
        self._status_bar.showMessage(
            f"扫描完成，发现 {len(issues)} 个问题", 3000
        )

    def _clear_issues(self):
        self._issue_panel.clear_issues()
        self._editor.clear_issues()
        if self._document:
            self._document.issues.clear()
        self._status_bar.showMessage("已清除所有问题标记", 3000)

    def _compare_with_original(self):
        if not self._document:
            QMessageBox.information(self, "提示", "请先创建或打开一个文档")
            return
        
        original = self._document.original_content
        modified = self._editor.toPlainText()
        
        if original == modified:
            QMessageBox.information(self, "提示", "原文与修订版完全相同，没有差异")
            return
        
        self._document.current_content = modified
        
        self._diff_view.set_documents(original, modified)
        
        changes = self._diff_view.get_changes()
        self._document.diff_changes = changes
        
        self._center_tabs.setCurrentWidget(self._diff_tab)
        
        self._status_bar.showMessage(
            f"发现 {len(changes)} 处差异", 3000
        )

    def _apply_all_diff_changes(self):
        if not self._document:
            return
        
        changes = self._diff_view.get_unresolved_changes()
        if not changes:
            QMessageBox.information(self, "提示", "没有待处理的差异")
            return
        
        text = self._document.current_content
        for change in changes:
            if change.change_type == 'replace':
                text = text[:change.start_pos_modified] + change.modified_text + text[change.end_pos_modified:]
            elif change.change_type == 'insert':
                text = text[:change.start_pos_modified] + change.modified_text + text[change.start_pos_modified:]
            elif change.change_type == 'delete':
                text = text[:change.start_pos_modified] + text[change.end_pos_modified:]
            
            self._diff_view.update_change_status(change.id, accepted=True)
        
        self._document.current_content = text
        self._editor.setPlainText(text)
        
        self._status_bar.showMessage(f"已接受 {len(changes)} 处更改", 3000)

    def _reject_all_diff_changes(self):
        if not self._document:
            return
        
        changes = self._diff_view.get_unresolved_changes()
        for change in changes:
            self._diff_view.update_change_status(change.id, rejected=True)
        
        self._status_bar.showMessage(f"已拒绝 {len(changes)} 处更改", 3000)

    def _export_text(self):
        if not self._document:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出文本",
            f"{self._document.name}_processed.txt",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        self._document.current_content = self._editor.toPlainText()
        success, error = FileUtils.save_document(self._document, file_path)
        
        if success:
            self._status_bar.showMessage("文本导出成功", 3000)
        else:
            QMessageBox.critical(self, "导出失败", error)

    def _export_json(self):
        if not self._document:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 JSON 报告",
            f"{self._document.name}_issues.json",
            "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        if ExportUtils.export_issues_to_json(self._document.issues, file_path, include_resolved=True):
            self._status_bar.showMessage("JSON 报告导出成功", 3000)
        else:
            QMessageBox.critical(self, "导出失败", "导出 JSON 报告时发生错误")

    def _export_csv(self):
        if not self._document:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 CSV 报告",
            f"{self._document.name}_issues.csv",
            "CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        
        if not file_path:
            return
        
        if ExportUtils.export_issues_to_csv(self._document.issues, file_path, include_resolved=True):
            self._status_bar.showMessage("CSV 报告导出成功", 3000)
        else:
            QMessageBox.critical(self, "导出失败", "导出 CSV 报告时发生错误")

    def _update_title(self):
        if self._document:
            modified = " *" if self._document.has_changes else ""
            self.setWindowTitle(f"{self._document.name}{modified} - 红墨文本标注工具")
        else:
            self.setWindowTitle("红墨文本标注工具 - RedInk Text Annotator")

    def _update_file_label(self):
        if self._document:
            file_info = self._document.file_path if self._document.file_path else self._document.name
            self._file_label.setText(file_info)
        else:
            self._file_label.setText("未打开文件")

    def _update_cursor_position(self):
        cursor = self._editor.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self._cursor_label.setText(f"行 {line}, 列 {column}")

    def _on_text_modified(self):
        if self._document:
            self._document.current_content = self._editor.toPlainText()
            self._update_title()

    def _on_issue_selected(self, issue_id: str):
        self._editor.go_to_issue(issue_id)

    def _on_issue_accepted(self, issue_id: str):
        issue = self._issue_panel.get_issue(issue_id)
        if not issue or not issue.suggested_text:
            self._issue_panel.update_issue_status(issue_id, accepted=True)
            return
        
        cursor = self._editor.textCursor()
        cursor.setPosition(issue.start_pos)
        cursor.setPosition(issue.end_pos, cursor.KeepAnchor)
        
        if cursor.selectedText() == issue.original_text:
            cursor.insertText(issue.suggested_text)
            
            if self._document:
                self._document.current_content = self._editor.toPlainText()
        
        self._issue_panel.update_issue_status(issue_id, accepted=True)
        self._status_bar.showMessage("已接受修改", 2000)

    def _on_issue_rejected(self, issue_id: str):
        self._issue_panel.update_issue_status(issue_id, rejected=True)
        self._status_bar.showMessage("已忽略问题", 2000)

    def _on_diff_change_accepted(self, change_id: str):
        change = self._diff_view.get_change(change_id)
        if not change:
            return
        
        self._diff_view.update_change_status(change_id, accepted=True)
        
        if change.change_type == 'replace':
            cursor = self._editor.textCursor()
            cursor.setPosition(change.start_pos_modified)
            cursor.setPosition(change.end_pos_modified, cursor.KeepAnchor)
            cursor.insertText(change.modified_text)
        elif change.change_type == 'insert':
            cursor = self._editor.textCursor()
            cursor.setPosition(change.start_pos_modified)
            cursor.insertText(change.modified_text)
        elif change.change_type == 'delete':
            cursor = self._editor.textCursor()
            cursor.setPosition(change.start_pos_modified)
            cursor.setPosition(change.end_pos_modified, cursor.KeepAnchor)
            cursor.removeSelectedText()
        
        if self._document:
            self._document.current_content = self._editor.toPlainText()
        
        self._status_bar.showMessage("已接受更改", 2000)

    def _on_diff_change_rejected(self, change_id: str):
        self._diff_view.update_change_status(change_id, rejected=True)
        self._status_bar.showMessage("已拒绝更改", 2000)

    def _on_rules_changed(self):
        pass

    def _on_tab_changed(self, index):
        pass

    def _enable_actions(self, enabled: bool):
        self._save_action.setEnabled(enabled)
        self._save_as_action.setEnabled(enabled)
        self._export_text_action.setEnabled(enabled)
        self._export_json_action.setEnabled(enabled)
        self._export_csv_action.setEnabled(enabled)

    def _show_about(self):
        QMessageBox.about(
            self,
            "关于红墨文本标注工具",
            """<h3>红墨文本标注工具</h3>
            <p>版本: 1.0.0</p>
            <p>基于 Python + PySide6 开发的文本标注/审校工具</p>
            <h4>功能特性:</h4>
            <ul>
                <li>支持导入/编辑 txt、md 文件</li>
                <li>按规则（正则、词库、重复、长度、格式）扫描文本</li>
                <li>问题列表高亮显示，点击定位到原文</li>
                <li>原文/修订版差异对比视图</li>
                <li>逐条接受/拒绝修改</li>
                <li>导出处理后文本与问题报告（JSON/CSV）</li>
            </ul>
            <p>参考 RedInk 项目的文本标注/审校体验</p>"""
        )

    def closeEvent(self, event):
        if self._document and self._document.has_changes:
            reply = QMessageBox.question(
                self, "保存更改",
                "当前文档有未保存的更改，是否保存？",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            if reply == QMessageBox.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.Yes:
                if not self._save_document():
                    event.ignore()
                    return
        
        event.accept()
