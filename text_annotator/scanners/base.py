import re
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import TextIssue, ScanRule, IssueType, IssueSeverity


class BaseScanner(ABC):
    def __init__(self):
        self.rules: List[ScanRule] = []

    @abstractmethod
    def scan(self, text: str) -> List[TextIssue]:
        pass

    @abstractmethod
    def get_supported_type(self) -> IssueType:
        pass

    def add_rule(self, rule: ScanRule):
        if rule.rule_type == self.get_supported_type():
            self.rules.append(rule)

    def remove_rule(self, rule_id: str):
        self.rules = [r for r in self.rules if r.id != rule_id]

    def get_line_column(self, text: str, pos: int) -> tuple:
        line = text[:pos].count('\n') + 1
        last_newline = text.rfind('\n', 0, pos)
        column = pos - last_newline
        return line, column

    def get_context(self, text: str, start: int, end: int, context_chars: int = 30) -> str:
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        return text[context_start:context_end]

    def create_issue(
        self,
        text: str,
        start: int,
        end: int,
        rule: ScanRule,
        suggested_text: Optional[str] = None
    ) -> TextIssue:
        line, column = self.get_line_column(text, start)
        context = self.get_context(text, start, end)
        
        return TextIssue(
            id=str(uuid.uuid4()),
            issue_type=rule.rule_type,
            severity=rule.severity,
            start_pos=start,
            end_pos=end,
            original_text=text[start:end],
            suggested_text=suggested_text or rule.replacement,
            message=rule.description,
            context=context,
            line_number=line,
            column_number=column,
            metadata={"rule_id": rule.id, "rule_name": rule.name}
        )
