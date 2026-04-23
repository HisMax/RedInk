from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QCheckBox,
    QGroupBox, QFormLayout, QSpinBox, QDialog,
    QDialogButtonBox, QMessageBox, QSplitter, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from typing import List, Optional, Dict, Any
from ..models import ScanRule, IssueType, IssueSeverity


class RuleEditDialog(QDialog):
    def __init__(self, rule: Optional[ScanRule] = None, parent=None):
        super().__init__(parent)
        self._rule = rule
        self._setup_ui()
        
        if rule:
            self._load_rule(rule)

    def _setup_ui(self):
        self.setWindowTitle("编辑规则" if self._rule else "新建规则")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("规则名称")
        form_layout.addRow("名称:", self._name_edit)
        
        self._type_combo = QComboBox()
        self._type_combo.addItems([
            "正则表达式", "词库匹配", "重复词检测", "长度检查", "格式检查"
        ])
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form_layout.addRow("类型:", self._type_combo)
        
        self._severity_combo = QComboBox()
        self._severity_combo.addItems(["错误", "警告", "信息"])
        form_layout.addRow("严重程度:", self._severity_combo)
        
        self._enabled_check = QCheckBox("启用规则")
        self._enabled_check.setChecked(True)
        form_layout.addRow(self._enabled_check)
        
        layout.addLayout(form_layout)
        
        self._pattern_group = QGroupBox("匹配规则")
        pattern_layout = QVBoxLayout(self._pattern_group)
        
        pattern_form = QFormLayout()
        
        self._pattern_edit = QTextEdit()
        self._pattern_edit.setPlaceholderText("输入正则表达式或匹配模式...")
        self._pattern_edit.setMaximumHeight(80)
        pattern_form.addRow("匹配模式:", self._pattern_edit)
        
        self._replacement_edit = QLineEdit()
        self._replacement_edit.setPlaceholderText("建议的替换文本（可选）")
        pattern_form.addRow("替换文本:", self._replacement_edit)
        
        self._description_edit = QTextEdit()
        self._description_edit.setPlaceholderText("规则描述...")
        self._description_edit.setMaximumHeight(60)
        pattern_form.addRow("描述:", self._description_edit)
        
        pattern_layout.addLayout(pattern_form)
        layout.addWidget(self._pattern_group)
        
        self._advanced_group = QGroupBox("高级选项")
        advanced_layout = QFormLayout(self._advanced_group)
        
        self._case_sensitive_check = QCheckBox("区分大小写")
        self._case_sensitive_check.setChecked(True)
        advanced_layout.addRow(self._case_sensitive_check)
        
        self._min_length_spin = QSpinBox()
        self._min_length_spin.setRange(0, 10000)
        self._min_length_spin.setValue(0)
        advanced_layout.addRow("最小长度:", self._min_length_spin)
        
        self._max_length_spin = QSpinBox()
        self._max_length_spin.setRange(0, 10000)
        self._max_length_spin.setValue(100)
        advanced_layout.addRow("最大长度:", self._max_length_spin)
        
        self._check_type_combo = QComboBox()
        self._check_type_combo.addItems(["句子", "单词", "段落"])
        advanced_layout.addRow("检查对象:", self._check_type_combo)
        
        layout.addWidget(self._advanced_group)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accepted)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self._style_dialog()

    def _style_dialog(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
            }
            QLabel {
                color: #cccccc;
            }
            QLineEdit, QTextEdit, QSpinBox {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 4px;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border-color: #094771;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 4px 8px;
            }
            QCheckBox {
                color: #cccccc;
            }
            QGroupBox {
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0c517c;
            }
        """)

    def _on_type_changed(self, index):
        show_length = index == 3
        show_format = index == 4
        
        self._min_length_spin.setVisible(show_length)
        self._max_length_spin.setVisible(show_length)
        self._check_type_combo.setVisible(show_length)
        
        if index == 3:
            self._pattern_edit.setPlaceholderText("留空使用默认设置，或输入自定义匹配模式...")
        elif index == 2:
            self._pattern_edit.setPlaceholderText("自定义重复词检测正则（可选），默认检测 \\b(\\w+)\\s+\\1\\b")
        else:
            self._pattern_edit.setPlaceholderText("输入正则表达式或匹配模式...")

    def _load_rule(self, rule: ScanRule):
        self._name_edit.setText(rule.name)
        self._replacement_edit.setText(rule.replacement)
        self._description_edit.setPlainText(rule.description)
        self._enabled_check.setChecked(rule.enabled)
        self._case_sensitive_check.setChecked(rule.case_sensitive)
        
        type_map = {
            IssueType.REGEX: 0,
            IssueType.DICTIONARY: 1,
            IssueType.REPEAT: 2,
            IssueType.LENGTH: 3,
            IssueType.FORMAT: 4
        }
        self._type_combo.setCurrentIndex(type_map.get(rule.rule_type, 0))
        
        severity_map = {
            IssueSeverity.ERROR: 0,
            IssueSeverity.WARNING: 1,
            IssueSeverity.INFO: 2
        }
        self._severity_combo.setCurrentIndex(severity_map.get(rule.severity, 1))
        
        self._pattern_edit.setPlainText(rule.pattern)
        
        self._min_length_spin.setValue(rule.metadata.get("min_length", 0))
        self._max_length_spin.setValue(rule.metadata.get("max_length", 100))
        
        check_type_map = {"sentence": 0, "word": 1, "paragraph": 2}
        check_type = rule.metadata.get("check_type", "sentence")
        self._check_type_combo.setCurrentIndex(check_type_map.get(check_type, 0))

    def _on_accepted(self):
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "警告", "请输入规则名称")
            return
        
        if self._type_combo.currentIndex() in [0, 1]:
            if not self._pattern_edit.toPlainText().strip():
                QMessageBox.warning(self, "警告", "请输入匹配模式")
                return
        
        self.accept()

    def get_rule(self) -> ScanRule:
        type_map = [
            IssueType.REGEX,
            IssueType.DICTIONARY,
            IssueType.REPEAT,
            IssueType.LENGTH,
            IssueType.FORMAT
        ]
        rule_type = type_map[self._type_combo.currentIndex()]
        
        severity_map = [IssueSeverity.ERROR, IssueSeverity.WARNING, IssueSeverity.INFO]
        severity = severity_map[self._severity_combo.currentIndex()]
        
        metadata = {}
        if rule_type == IssueType.LENGTH:
            metadata["min_length"] = self._min_length_spin.value()
            metadata["max_length"] = self._max_length_spin.value()
            check_type_map = ["sentence", "word", "paragraph"]
            metadata["check_type"] = check_type_map[self._check_type_combo.currentIndex()]
        
        return ScanRule(
            id=self._rule.id if self._rule else "",
            name=self._name_edit.text().strip(),
            rule_type=rule_type,
            enabled=self._enabled_check.isChecked(),
            pattern=self._pattern_edit.toPlainText().strip(),
            replacement=self._replacement_edit.text().strip(),
            description=self._description_edit.toPlainText().strip(),
            severity=severity,
            case_sensitive=self._case_sensitive_check.isChecked(),
            metadata=metadata
        )


class RuleSettings(QWidget):
    rule_added = Signal(ScanRule)
    rule_removed = Signal(str, IssueType)
    rule_updated = Signal(ScanRule)
    rules_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: Dict[str, ScanRule] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        header_layout = QHBoxLayout()
        
        title_label = QLabel("扫描规则")
        title_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("+ 新建规则")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d632f;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d733f;
            }
        """)
        add_btn.clicked.connect(self._add_rule)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        self._rule_list = QListWidget()
        self._rule_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
            }
            QListWidget::item {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #094771;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        self._rule_list.itemDoubleClicked.connect(self._edit_rule)
        layout.addWidget(self._rule_list)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._edit_rule)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #632d2d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 5px 12px;
            }
            QPushButton:hover {
                background-color: #733d3d;
            }
        """)
        delete_btn.clicked.connect(self._delete_rule)
        button_layout.addWidget(delete_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)

    def set_rules(self, rules: List[ScanRule]):
        self._rules = {r.id: r for r in rules}
        self._refresh_display()

    def add_rule(self, rule: ScanRule):
        if not rule.id:
            import uuid
            rule.id = str(uuid.uuid4())
        
        self._rules[rule.id] = rule
        self._refresh_display()
        self.rule_added.emit(rule)
        self.rules_changed.emit()

    def get_rules(self) -> List[ScanRule]:
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[ScanRule]:
        return self._rules.get(rule_id)

    def _refresh_display(self):
        self._rule_list.clear()
        
        type_names = {
            IssueType.REGEX: "正则",
            IssueType.DICTIONARY: "词库",
            IssueType.REPEAT: "重复",
            IssueType.LENGTH: "长度",
            IssueType.FORMAT: "格式"
        }
        
        severity_colors = {
            IssueSeverity.ERROR: "#f48771",
            IssueSeverity.WARNING: "#cca700",
            IssueSeverity.INFO: "#3794ff"
        }
        
        for rule in sorted(self._rules.values(), key=lambda r: r.name):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, rule.id)
            
            status = "✓" if rule.enabled else "✗"
            type_name = type_names.get(rule.rule_type, "未知")
            color = severity_colors.get(rule.severity, "#6e6e6e")
            
            item.setText(f"{status} [{type_name}] {rule.name}")
            item.setForeground(Qt.GlobalColor.gray if not rule.enabled else Qt.GlobalColor.white)
            
            self._rule_list.addItem(item)

    def _add_rule(self):
        dialog = RuleEditDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            rule = dialog.get_rule()
            self.add_rule(rule)

    def _edit_rule(self):
        current_item = self._rule_list.currentItem()
        if not current_item:
            return
        
        rule_id = current_item.data(Qt.UserRole)
        rule = self._rules.get(rule_id)
        if not rule:
            return
        
        dialog = RuleEditDialog(rule, parent=self)
        if dialog.exec() == QDialog.Accepted:
            updated_rule = dialog.get_rule()
            updated_rule.id = rule.id
            self._rules[rule.id] = updated_rule
            self._refresh_display()
            self.rule_updated.emit(updated_rule)
            self.rules_changed.emit()

    def _delete_rule(self):
        current_item = self._rule_list.currentItem()
        if not current_item:
            return
        
        rule_id = current_item.data(Qt.UserRole)
        rule = self._rules.get(rule_id)
        if not rule:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除规则 '{rule.name}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self._rules[rule_id]
            self._refresh_display()
            self.rule_removed.emit(rule_id, rule.rule_type)
            self.rules_changed.emit()
