from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSplitter, QFrame, QPushButton, QScrollBar,
    QToolBar, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QTextCursor
from typing import List, Optional, Dict
from ..models import DiffChange, Document
from ..utils.diff_utils import DiffComparator
from .highlight_editor import HighlightEditor


class DiffChangeItem(QWidget):
    change_selected = Signal(str)
    change_accepted = Signal(str)
    change_rejected = Signal(str)

    def __init__(self, change: DiffChange, parent=None):
        super().__init__(parent)
        self._change = change
        self._change_id = change.id
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        type_indicator = QLabel()
        type_indicator.setFixedSize(12, 12)
        type_color = self._get_type_color()
        type_symbol = self._get_type_symbol()
        type_indicator.setStyleSheet(
            f"background-color: {type_color}; border-radius: 2px; "
            f"color: white; font-size: 10px; font-weight: bold;"
        )
        type_indicator.setAlignment(Qt.AlignCenter)
        type_indicator.setText(type_symbol)
        header_layout.addWidget(type_indicator)
        
        type_label = QLabel(self._get_type_display())
        type_label.setStyleSheet("color: #858585; font-size: 11px;")
        header_layout.addWidget(type_label)
        
        header_layout.addStretch()
        
        line_label = QLabel(f"行 {self._change.line_number}")
        line_label.setStyleSheet("color: #6e6e6e; font-size: 11px;")
        header_layout.addWidget(line_label)
        
        layout.addLayout(header_layout)
        
        if self._change.change_type in ['replace', 'delete']:
            original_label = QLabel("原文:")
            original_label.setStyleSheet("color: #858585; font-size: 11px;")
            layout.addWidget(original_label)
            
            original_text = QLabel(self._truncate_text(self._change.original_text))
            original_text.setStyleSheet(
                "color: #e57373; font-size: 12px; font-family: Consolas; "
                "text-decoration: line-through;"
            )
            original_text.setWordWrap(True)
            layout.addWidget(original_text)
        
        if self._change.change_type in ['replace', 'insert']:
            modified_label = QLabel("修改:")
            modified_label.setStyleSheet("color: #858585; font-size: 11px;")
            layout.addWidget(modified_label)
            
            modified_text = QLabel(self._truncate_text(self._change.modified_text))
            modified_text.setStyleSheet(
                "color: #81c784; font-size: 12px; font-family: Consolas;"
            )
            modified_text.setWordWrap(True)
            layout.addWidget(modified_text)
        
        if not self._change.is_resolved:
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)
            
            accept_btn = QPushButton("接受")
            accept_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2d632f;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #3d733f;
                }
            """)
            accept_btn.clicked.connect(self._on_accept)
            button_layout.addWidget(accept_btn)
            
            reject_btn = QPushButton("拒绝")
            reject_btn.setStyleSheet("""
                QPushButton {
                    background-color: #632d2d;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 3px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #733d3d;
                }
            """)
            reject_btn.clicked.connect(self._on_reject)
            button_layout.addWidget(reject_btn)
            
            button_layout.addStretch()
            layout.addLayout(button_layout)
        else:
            status_label = QLabel(
                "✓ 已接受" if self._change.accepted else "✗ 已拒绝"
            )
            status_label.setStyleSheet(
                "color: #4ec9b0; font-size: 11px;" if self._change.accepted
                else "color: #6e6e6e; font-size: 11px;"
            )
            layout.addWidget(status_label)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QWidget {
                background-color: #2d2d2d;
                border-bottom: 1px solid #3c3c3c;
            }
            QWidget:hover {
                background-color: #353535;
            }
        """)

    def _get_type_color(self) -> str:
        colors = {
            'insert': '#2d632f',
            'delete': '#632d2d',
            'replace': '#635d2d'
        }
        return colors.get(self._change.change_type, '#3c3c3c')

    def _get_type_symbol(self) -> str:
        symbols = {
            'insert': '+',
            'delete': '-',
            'replace': '~'
        }
        return symbols.get(self._change.change_type, '?')

    def _get_type_display(self) -> str:
        displays = {
            'insert': '插入',
            'delete': '删除',
            'replace': '替换'
        }
        return displays.get(self._change.change_type, '未知')

    def _truncate_text(self, text: str, max_len: int = 50) -> str:
        text = text.replace('\n', '↵ ')
        if len(text) <= max_len:
            return repr(text)[1:-1]
        return repr(text[:max_len] + "...")[1:-1]

    def _on_accept(self):
        self.change_accepted.emit(self._change_id)

    def _on_reject(self):
        self.change_rejected.emit(self._change_id)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_selected.emit(self._change_id)
        super().mousePressEvent(event)

    def change(self) -> DiffChange:
        return self._change

    def change_id(self) -> str:
        return self._change_id


class DiffView(QWidget):
    change_selected = Signal(str)
    change_accepted = Signal(str)
    change_rejected = Signal(str)
    all_changes_accepted = Signal()
    all_changes_rejected = Signal()
    compare_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._changes: Dict[str, DiffChange] = {}
        self._original_text = ""
        self._modified_text = ""
        self._comparator = DiffComparator()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3c3c;
            }
            QSplitter::handle:horizontal {
                width: 3px;
            }
        """)
        
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        left_header = self._create_header_label("原文 (Original)", "#f48771")
        left_layout.addWidget(left_header)
        
        self._original_editor = HighlightEditor()
        self._original_editor.setReadOnly(True)
        left_layout.addWidget(self._original_editor)
        
        main_splitter.addWidget(left_container)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        right_header = self._create_header_label("修订版 (Modified)", "#81c784")
        right_layout.addWidget(right_header)
        
        self._modified_editor = HighlightEditor()
        self._modified_editor.setReadOnly(True)
        right_layout.addWidget(self._modified_editor)
        
        main_splitter.addWidget(right_container)
        
        main_splitter.setSizes([400, 400])
        layout.addWidget(main_splitter)
        
        self._sync_scroll_bars()

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #2d2d2d; border-bottom: 1px solid #3c3c3c;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        title_label = QLabel("差异对比")
        title_label.setStyleSheet("color: #cccccc; font-weight: bold; font-size: 13px;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        self._view_combo = QComboBox()
        self._view_combo.addItems(["并排视图", "合并视图", "仅显示差异"])
        self._view_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 8px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        layout.addWidget(self._view_combo)
        
        accept_all_btn = QPushButton("接受全部")
        accept_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d632f;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d733f;
            }
        """)
        accept_all_btn.clicked.connect(self.all_changes_accepted.emit)
        layout.addWidget(accept_all_btn)
        
        reject_all_btn = QPushButton("拒绝全部")
        reject_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #632d2d;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #733d3d;
            }
        """)
        reject_all_btn.clicked.connect(self.all_changes_rejected.emit)
        layout.addWidget(reject_all_btn)
        
        return toolbar

    def _create_header_label(self, text: str, color: str) -> QLabel:
        header = QLabel(text)
        header.setStyleSheet(
            f"background-color: #252526; color: {color}; "
            f"padding: 4px 8px; font-weight: bold; border-bottom: 1px solid #3c3c3c;"
        )
        return header

    def _sync_scroll_bars(self):
        original_vbar = self._original_editor.verticalScrollBar()
        modified_vbar = self._modified_editor.verticalScrollBar()
        
        original_vbar.valueChanged.connect(modified_vbar.setValue)
        modified_vbar.valueChanged.connect(original_vbar.setValue)
        
        original_hbar = self._original_editor.horizontalScrollBar()
        modified_hbar = self._modified_editor.horizontalScrollBar()
        
        original_hbar.valueChanged.connect(modified_hbar.setValue)
        modified_hbar.valueChanged.connect(original_hbar.setValue)

    def set_documents(self, original: str, modified: str):
        self._original_text = original
        self._modified_text = modified
        
        self._original_editor.setPlainText(original)
        self._modified_editor.setPlainText(modified)
        
        self._changes.clear()
        changes = self._comparator.compare_texts(original, modified)
        self._changes = {c.id: c for c in changes}
        
        self._apply_diff_highlights()

    def set_changes(self, changes: List[DiffChange]):
        self._changes = {c.id: c for c in changes}
        self._apply_diff_highlights()

    def update_change_status(self, change_id: str, accepted: bool = None, rejected: bool = None):
        if change_id not in self._changes:
            return
        
        change = self._changes[change_id]
        if accepted is not None:
            change.accepted = accepted
        if rejected is not None:
            change.rejected = rejected

    def _apply_diff_highlights(self):
        added_ranges_original = []
        removed_ranges_original = []
        added_ranges_modified = []
        removed_ranges_modified = []
        
        for change in self._changes.values():
            if change.is_resolved:
                continue
            
            if change.change_type == 'insert':
                added_ranges_modified.append((
                    change.start_pos_modified, change.end_pos_modified
                ))
            elif change.change_type == 'delete':
                removed_ranges_original.append((
                    change.start_pos_original, change.end_pos_original
                ))
            elif change.change_type == 'replace':
                removed_ranges_original.append((
                    change.start_pos_original, change.end_pos_original
                ))
                added_ranges_modified.append((
                    change.start_pos_modified, change.end_pos_modified
                ))
        
        self._original_editor.highlight_diff(added_ranges_original, removed_ranges_original)
        self._modified_editor.highlight_diff(added_ranges_modified, removed_ranges_modified)

    def go_to_change(self, change_id: str) -> bool:
        change = self._changes.get(change_id)
        if not change:
            return False
        
        if change.change_type != 'insert':
            self._original_editor.go_to_line(change.line_number)
        
        if change.change_type != 'delete':
            self._modified_editor.go_to_line(change.line_number)
        
        return True

    def get_changes(self) -> List[DiffChange]:
        return list(self._changes.values())

    def get_change(self, change_id: str) -> Optional[DiffChange]:
        return self._changes.get(change_id)

    def get_unresolved_changes(self) -> List[DiffChange]:
        return [c for c in self._changes.values() if not c.is_resolved]

    def _on_view_changed(self, index):
        pass

    def clear(self):
        self._changes.clear()
        self._original_text = ""
        self._modified_text = ""
        self._original_editor.setPlainText("")
        self._modified_editor.setPlainText("")
