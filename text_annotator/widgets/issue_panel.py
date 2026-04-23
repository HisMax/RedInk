from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QFrame,
    QPushButton, QComboBox, QSplitter, QTextEdit,
    QSizePolicy, QMenu, QToolBar, QAction
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QIcon, QAction
from typing import List, Optional, Dict, Any
from ..models import TextIssue, IssueType, IssueSeverity


class IssueItemWidget(QWidget):
    issue_selected = Signal(str)
    issue_action = Signal(str, str)

    def __init__(self, issue: TextIssue, parent=None):
        super().__init__(parent)
        self._issue = issue
        self._issue_id = issue.id
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        severity_indicator = QLabel()
        severity_indicator.setFixedSize(8, 8)
        severity_color = self._get_severity_color()
        severity_indicator.setStyleSheet(
            f"background-color: {severity_color}; border-radius: 4px;"
        )
        header_layout.addWidget(severity_indicator)
        
        type_label = QLabel(self._get_type_display())
        type_label.setStyleSheet("color: #858585; font-size: 11px;")
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        line_label = QLabel(f"行 {self._issue.line_number}")
        line_label.setStyleSheet("color: #6e6e6e; font-size: 11px;")
        header_layout.addWidget(line_label)
        
        layout.addLayout(header_layout)
        
        message_label = QLabel(self._issue.message or "检测到问题")
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #d4d4d4; font-size: 12px;")
        layout.addWidget(message_label)
        
        if self._issue.original_text:
            text_layout = QHBoxLayout()
            text_layout.setSpacing(8)
            
            original_label = QLabel(f"原文: {self._truncate_text(self._issue.original_text)}")
            original_label.setStyleSheet("color: #f48771; font-size: 11px; font-family: Consolas;")
            text_layout.addWidget(original_label)
            
            if self._issue.suggested_text:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #6e6e6e;")
                text_layout.addWidget(arrow)
                
                suggested_label = QLabel(self._truncate_text(self._issue.suggested_text))
                suggested_label.setStyleSheet("color: #81c784; font-size: 11px; font-family: Consolas;")
                text_layout.addWidget(suggested_label)
            
            text_layout.addStretch()
            layout.addLayout(text_layout)
        
        if self._issue.is_resolved:
            status_label = QLabel("✓ 已处理" if self._issue.accepted else "✗ 已忽略")
            status_label.setStyleSheet(
                "color: #4ec9b0; font-size: 11px;" if self._issue.accepted 
                else "color: #6e6e6e; font-size: 11px;"
            )
            layout.addWidget(status_label)
        
        self.setCursor(Qt.PointingHandCursor)

    def _get_severity_color(self) -> str:
        colors = {
            IssueSeverity.ERROR: "#f48771",
            IssueSeverity.WARNING: "#cca700",
            IssueSeverity.INFO: "#3794ff"
        }
        return colors.get(self._issue.severity, "#6e6e6e")

    def _get_type_display(self) -> str:
        type_names = {
            IssueType.REGEX: "正则匹配",
            IssueType.DICTIONARY: "词库匹配",
            IssueType.REPEAT: "重复词",
            IssueType.LENGTH: "长度问题",
            IssueType.FORMAT: "格式问题",
            IssueType.SPELLING: "拼写错误"
        }
        return type_names.get(self._issue.issue_type, "未知")

    def _truncate_text(self, text: str, max_len: int = 30) -> str:
        if len(text) <= max_len:
            return repr(text)
        return repr(text[:max_len] + "...")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.issue_selected.emit(self._issue_id)
        super().mousePressEvent(event)

    def issue(self) -> TextIssue:
        return self._issue

    def issue_id(self) -> str:
        return self._issue_id


class IssuePanel(QWidget):
    issue_selected = Signal(str)
    issue_accepted = Signal(str)
    issue_rejected = Signal(str)
    scan_requested = Signal()
    filter_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._issues: Dict[str, TextIssue] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        stats_bar = self._create_stats_bar()
        layout.addWidget(stats_bar)
        
        self._issue_list = QListWidget()
        self._issue_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: none;
                border-top: 1px solid #3c3c3c;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                margin: 0px;
                padding: 0px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
        """)
        self._issue_list.setSpacing(0)
        self._issue_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._issue_list)
        
        self._context_menu = self._create_context_menu()
        self._issue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._issue_list.customContextMenuRequested.connect(self._show_context_menu)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #2d2d2d; border-bottom: 1px solid #3c3c3c;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        title_label = QLabel("问题列表")
        title_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 13px;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self._type_combo = QComboBox()
        self._type_combo.addItems(["全部类型", "正则", "词库", "重复词", "长度", "格式"])
        self._type_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 8px;
                min-width: 80px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self._type_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._type_combo)
        
        self._severity_combo = QComboBox()
        self._severity_combo.addItems(["全部严重程度", "错误", "警告", "信息"])
        self._severity_combo.setStyleSheet(self._type_combo.styleSheet())
        self._severity_combo.currentIndexChanged.connect(self._on_filter_changed)
        layout.addWidget(self._severity_combo)
        
        scan_btn = QPushButton("扫描")
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
        """)
        scan_btn.clicked.connect(self.scan_requested.emit)
        layout.addWidget(scan_btn)
        
        return toolbar

    def _create_stats_bar(self) -> QWidget:
        stats_bar = QFrame()
        stats_bar.setStyleSheet("background-color: #252526;")
        layout = QHBoxLayout(stats_bar)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(16)
        
        self._total_label = QLabel("总计: 0")
        self._total_label.setStyleSheet("color: #858585; font-size: 11px;")
        layout.addWidget(self._total_label)
        
        self._error_label = QLabel("错误: 0")
        self._error_label.setStyleSheet("color: #f48771; font-size: 11px;")
        layout.addWidget(self._error_label)
        
        self._warning_label = QLabel("警告: 0")
        self._warning_label.setStyleSheet("color: #cca700; font-size: 11px;")
        layout.addWidget(self._warning_label)
        
        self._info_label = QLabel("信息: 0")
        self._info_label.setStyleSheet("color: #3794ff; font-size: 11px;")
        layout.addWidget(self._info_label)
        
        layout.addStretch()
        
        self._resolved_label = QLabel("已处理: 0")
        self._resolved_label.setStyleSheet("color: #4ec9b0; font-size: 11px;")
        layout.addWidget(self._resolved_label)
        
        return stats_bar

    def _create_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.setStyleSheet("""
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
        """)
        
        accept_action = menu.addAction("接受修改")
        accept_action.triggered.connect(self._accept_current_issue)
        
        reject_action = menu.addAction("忽略此问题")
        reject_action.triggered.connect(self._reject_current_issue)
        
        menu.addSeparator()
        
        accept_all_action = menu.addAction("接受所有修改")
        accept_all_action.triggered.connect(self._accept_all_issues)
        
        reject_all_action = menu.addAction("忽略所有问题")
        reject_all_action.triggered.connect(self._reject_all_issues)
        
        return menu

    def set_issues(self, issues: List[TextIssue]):
        self._issues = {i.id: i for i in issues}
        self._refresh_display()
        self._update_stats()

    def add_issue(self, issue: TextIssue):
        self._issues[issue.id] = issue
        self._refresh_display()
        self._update_stats()

    def clear_issues(self):
        self._issues.clear()
        self._issue_list.clear()
        self._update_stats()

    def update_issue_status(self, issue_id: str, accepted: bool = None, rejected: bool = None):
        if issue_id not in self._issues:
            return
        
        issue = self._issues[issue_id]
        if accepted is not None:
            issue.accepted = accepted
        if rejected is not None:
            issue.rejected = rejected
        
        self._refresh_display()
        self._update_stats()

    def _refresh_display(self):
        self._issue_list.clear()
        
        type_filter = self._type_combo.currentIndex()
        severity_filter = self._severity_combo.currentIndex()
        
        type_map = {
            1: IssueType.REGEX,
            2: IssueType.DICTIONARY,
            3: IssueType.REPEAT,
            4: IssueType.LENGTH,
            5: IssueType.FORMAT
        }
        
        severity_map = {
            1: IssueSeverity.ERROR,
            2: IssueSeverity.WARNING,
            3: IssueSeverity.INFO
        }
        
        for issue in sorted(self._issues.values(), key=lambda x: x.start_pos):
            if type_filter > 0 and issue.issue_type != type_map.get(type_filter):
                continue
            if severity_filter > 0 and issue.severity != severity_map.get(severity_filter):
                continue
            
            item_widget = IssueItemWidget(issue)
            item_widget.issue_selected.connect(self._on_issue_selected)
            
            item = QListWidgetItem(self._issue_list)
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.UserRole, issue.id)
            
            self._issue_list.addItem(item)
            self._issue_list.setItemWidget(item, item_widget)

    def _update_stats(self):
        total = len(self._issues)
        errors = sum(1 for i in self._issues.values() if i.severity == IssueSeverity.ERROR)
        warnings = sum(1 for i in self._issues.values() if i.severity == IssueSeverity.WARNING)
        infos = sum(1 for i in self._issues.values() if i.severity == IssueSeverity.INFO)
        resolved = sum(1 for i in self._issues.values() if i.is_resolved)
        
        self._total_label.setText(f"总计: {total}")
        self._error_label.setText(f"错误: {errors}")
        self._warning_label.setText(f"警告: {warnings}")
        self._info_label.setText(f"信息: {infos}")
        self._resolved_label.setText(f"已处理: {resolved}")

    def _on_item_clicked(self, item: QListWidgetItem):
        issue_id = item.data(Qt.UserRole)
        self.issue_selected.emit(issue_id)

    def _on_issue_selected(self, issue_id: str):
        self.issue_selected.emit(issue_id)

    def _on_filter_changed(self):
        self._refresh_display()
        self.filter_changed.emit({
            "type_filter": self._type_combo.currentIndex(),
            "severity_filter": self._severity_combo.currentIndex()
        })

    def _show_context_menu(self, pos):
        item = self._issue_list.itemAt(pos)
        if item:
            self._context_menu.exec(self._issue_list.mapToGlobal(pos))

    def _accept_current_issue(self):
        current_item = self._issue_list.currentItem()
        if current_item:
            issue_id = current_item.data(Qt.UserRole)
            self.issue_accepted.emit(issue_id)

    def _reject_current_issue(self):
        current_item = self._issue_list.currentItem()
        if current_item:
            issue_id = current_item.data(Qt.UserRole)
            self.issue_rejected.emit(issue_id)

    def _accept_all_issues(self):
        for issue_id in list(self._issues.keys()):
            self.issue_accepted.emit(issue_id)

    def _reject_all_issues(self):
        for issue_id in list(self._issues.keys()):
            self.issue_rejected.emit(issue_id)

    def get_issues(self) -> List[TextIssue]:
        return list(self._issues.values())

    def get_issue(self, issue_id: str) -> Optional[TextIssue]:
        return self._issues.get(issue_id)
