import re
from typing import List
from .base import BaseScanner
from ..models import TextIssue, ScanRule, IssueType, IssueSeverity


class RepeatScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        default_rule = ScanRule(
            id="repeat_default",
            name="重复词检测",
            rule_type=IssueType.REPEAT,
            description="检测重复出现的词语",
            severity=IssueSeverity.WARNING
        )
        self.rules.append(default_rule)

    def get_supported_type(self) -> IssueType:
        return IssueType.REPEAT

    def scan(self, text: str) -> List[TextIssue]:
        issues = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            pattern = r'\b(\w+)\s+\1\b'
            if rule.pattern:
                pattern = rule.pattern
            
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
                matches = list(regex.finditer(text))
                
                for match in matches:
                    start, end = match.span()
                    word = match.group(1)
                    
                    suggested_text = rule.replacement if rule.replacement else word
                    
                    issue = self.create_issue(
                        text=text,
                        start=start,
                        end=end,
                        rule=rule,
                        suggested_text=suggested_text
                    )
                    issue.message = f"检测到重复词: '{word}'"
                    issue.original_text = match.group(0)
                    issue.suggested_text = word
                    issues.append(issue)
            except re.error:
                continue
        
        return issues
