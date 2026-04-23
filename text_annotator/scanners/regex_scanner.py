import re
from typing import List
from .base import BaseScanner
from ..models import TextIssue, IssueType


class RegexScanner(BaseScanner):
    def get_supported_type(self) -> IssueType:
        return IssueType.REGEX

    def scan(self, text: str) -> List[TextIssue]:
        issues = []
        for rule in self.rules:
            if not rule.enabled or not rule.pattern:
                continue
            
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            try:
                pattern = re.compile(rule.pattern, flags)
                matches = list(pattern.finditer(text))
                
                for match in matches:
                    start, end = match.span()
                    
                    suggested = rule.replacement
                    if suggested:
                        suggested = match.expand(suggested)
                    
                    issue = self.create_issue(
                        text=text,
                        start=start,
                        end=end,
                        rule=rule,
                        suggested_text=suggested
                    )
                    issues.append(issue)
            except re.error:
                continue
        
        return issues
