from PySide6.QtWidgets import (
    QTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect, QSize
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QColor, QFont,
    QPainter, QTextFormat, QBrush, QPen
)
from typing import List, Optional, Dict
from ..models import TextIssue, IssueSeverity


class LineNumberArea(QWidget):
    def __init__(self, editor: 'HighlightEditor'):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


class HighlightEditor(QTextEdit):
    issue_clicked = Signal(str)
    text_modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._issues: Dict[str, TextIssue] = {}
        self._highlight_formats: Dict[str, QTextCharFormat] = {}
        self._line_number_area = LineNumberArea(self)
        
        self._setup_ui()
        self._create_formats()
        
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self.textChanged.connect(self._on_text_changed)
        
        self._update_line_number_area_width(0)

    def _setup_ui(self):
        font = QFont("Consolas", 11)
        self.setFont(font)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setTabStopDistance(40)
        
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: none;
                padding: 4px;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 14px;
                border-radius: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #4a4a4a;
                min-height: 30px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5a5a5a;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #2d2d2d;
                height: 14px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4a4a4a;
                min-width: 30px;
                border-radius: 7px;
            }
        """)

    def _create_formats(self):
        error_format = QTextCharFormat()
        error_format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        error_format.setUnderlineColor(QColor("#f48771"))
        error_format.setBackground(QColor("#3c1f1f"))
        self._highlight_formats["error"] = error_format
        
        warning_format = QTextCharFormat()
        warning_format.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        warning_format.setUnderlineColor(QColor("#cca700"))
        warning_format.setBackground(QColor("#3c3c1f"))
        self._highlight_formats["warning"] = warning_format
        
        info_format = QTextCharFormat()
        info_format.setUnderlineStyle(QTextCharFormat.DashUnderline)
        info_format.setUnderlineColor(QColor("#3794ff"))
        info_format.setBackground(QColor("#1f3c3c"))
        self._highlight_formats["info"] = info_format
        
        added_format = QTextCharFormat()
        added_format.setBackground(QColor("#1a472a"))
        added_format.setForeground(QColor("#81c784"))
        self._highlight_formats["added"] = added_format
        
        removed_format = QTextCharFormat()
        removed_format.setBackground(QColor("#471a1a"))
        removed_format.setForeground(QColor("#e57373"))
        self._highlight_formats["removed"] = removed_format
        
        current_line_format = QTextCharFormat()
        current_line_format.setBackground(QColor("#2a2d2e"))
        self._highlight_formats["current_line"] = current_line_format

    def _update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect, dy):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def line_number_area_width(self) -> int:
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#252526"))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        painter.setPen(QColor("#858585"))
        font = self.font()
        font.setPointSize(font.pointSize() - 1)
        painter.setFont(font)
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, top,
                    self._line_number_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )
            
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def _highlight_current_line(self):
        extra_selections = []
        
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#2a2d2e")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        
        self.setExtraSelections(extra_selections)

    def _on_text_changed(self):
        self.text_modified.emit()

    def set_issues(self, issues: List[TextIssue]):
        self._issues = {i.id: i for i in issues}
        self._apply_highlights()

    def add_issue(self, issue: TextIssue):
        self._issues[issue.id] = issue
        self._apply_highlights()

    def clear_issues(self):
        self._issues.clear()
        self._apply_highlights()

    def _apply_highlights(self):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        
        cursor.select(QTextCursor.Document)
        cursor.setCharFormat(QTextCharFormat())
        cursor.clearSelection()
        
        for issue in self._issues.values():
            if issue.is_resolved:
                continue
            
            highlight_cursor = QTextCursor(self.document())
            highlight_cursor.setPosition(issue.start_pos)
            highlight_cursor.setPosition(issue.end_pos, QTextCursor.KeepAnchor)
            
            format_key = issue.severity.value
            if format_key in self._highlight_formats:
                highlight_cursor.mergeCharFormat(self._highlight_formats[format_key])
        
        cursor.endEditBlock()

    def go_to_issue(self, issue_id: str) -> bool:
        issue = self._issues.get(issue_id)
        if not issue:
            return False
        
        cursor = QTextCursor(self.document())
        cursor.setPosition(issue.start_pos)
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 
                           issue.end_pos - issue.start_pos)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()
        
        return True

    def go_to_line(self, line_number: int) -> bool:
        cursor = QTextCursor(self.document())
        block = self.document().findBlockByLineNumber(line_number - 1)
        
        if not block.isValid():
            return False
        
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.setFocus()
        
        return True

    def get_selected_text(self) -> str:
        return self.textCursor().selectedText()

    def replace_selected_text(self, new_text: str):
        cursor = self.textCursor()
        cursor.insertText(new_text)

    def get_line_count(self) -> int:
        return self.document().blockCount()

    def get_line_text(self, line_number: int) -> str:
        block = self.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            return block.text()
        return ""

    def highlight_diff(
        self,
        added_ranges: List[tuple],
        removed_ranges: List[tuple]
    ):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        
        for start, end in added_ranges:
            diff_cursor = QTextCursor(self.document())
            diff_cursor.setPosition(start)
            diff_cursor.setPosition(end, QTextCursor.KeepAnchor)
            diff_cursor.mergeCharFormat(self._highlight_formats["added"])
        
        for start, end in removed_ranges:
            diff_cursor = QTextCursor(self.document())
            diff_cursor.setPosition(start)
            diff_cursor.setPosition(end, QTextCursor.KeepAnchor)
            diff_cursor.mergeCharFormat(self._highlight_formats["removed"])
        
        cursor.endEditBlock()
