import re
from typing import List, Set
from .base import BaseScanner
from ..models import TextIssue, IssueType


class DictionaryScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        self._dictionary: Set[str] = set()

    def get_supported_type(self) -> IssueType:
        return IssueType.DICTIONARY

    def load_dictionary(self, words: List[str]):
        self._dictionary = set(words)

    def add_words(self, words: List[str]):
        self._dictionary.update(words)

    def scan(self, text: str) -> List[TextIssue]:
        issues = []
        
        if not self._dictionary:
            return issues
        
        pattern = r'\b\w+\b'
        words = re.finditer(pattern, text)
        
        word_set = {w.lower() for w in self._dictionary}
        
        for match in words:
            word = match.group()
            if word.lower() not in word_set:
                continue
            
            start, end = match.span()
            
            for rule in self.rules:
                if not rule.enabled:
                    continue
                if rule.pattern and rule.pattern.lower() != word.lower():
                    continue
                
                issue = self.create_issue(
                    text=text,
                    start=start,
                    end=end,
                    rule=rule,
                    suggested_text=rule.replacement
                )
                issues.append(issue)
        
        return issues
