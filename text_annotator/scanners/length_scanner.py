import re
from typing import List
from .base import BaseScanner
from ..models import TextIssue, ScanRule, IssueType, IssueSeverity


class LengthScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        default_rule = ScanRule(
            id="length_default",
            name="句子长度检测",
            rule_type=IssueType.LENGTH,
            description="检测过长或过短的句子",
            severity=IssueSeverity.INFO
        )
        self.rules.append(default_rule)

    def get_supported_type(self) -> IssueType:
        return IssueType.LENGTH

    def scan(self, text: str) -> List[TextIssue]:
        issues = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            min_length = rule.metadata.get("min_length", 0)
            max_length = rule.metadata.get("max_length", 100)
            check_type = rule.metadata.get("check_type", "sentence")
            
            if check_type == "sentence":
                issues.extend(self._scan_sentences(text, rule, min_length, max_length))
            elif check_type == "word":
                issues.extend(self._scan_words(text, rule, min_length, max_length))
            elif check_type == "paragraph":
                issues.extend(self._scan_paragraphs(text, rule, min_length, max_length))
        
        return issues

    def _scan_sentences(self, text: str, rule: ScanRule, min_len: int, max_len: int) -> List[TextIssue]:
        issues = []
        sentence_pattern = r'[^。！？.!?]+[。！？.!?]+'
        
        for match in re.finditer(sentence_pattern, text):
            sentence = match.group().strip()
            start, end = match.span()
            length = len(sentence)
            
            if length == 0:
                continue
            
            if min_len > 0 and length < min_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"句子过短 ({length} 字符，最小 {min_len})"
                issues.append(issue)
            elif max_len > 0 and length > max_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"句子过长 ({length} 字符，最大 {max_len})"
                issues.append(issue)
        
        return issues

    def _scan_words(self, text: str, rule: ScanRule, min_len: int, max_len: int) -> List[TextIssue]:
        issues = []
        word_pattern = r'\b\w+\b'
        
        for match in re.finditer(word_pattern, text):
            word = match.group()
            start, end = match.span()
            length = len(word)
            
            if min_len > 0 and length < min_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"单词过短 ({length} 字符，最小 {min_len})"
                issues.append(issue)
            elif max_len > 0 and length > max_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"单词过长 ({length} 字符，最大 {max_len})"
                issues.append(issue)
        
        return issues

    def _scan_paragraphs(self, text: str, rule: ScanRule, min_len: int, max_len: int) -> List[TextIssue]:
        issues = []
        paragraphs = re.split(r'\n\n+', text)
        pos = 0
        
        for para in paragraphs:
            if not para.strip():
                pos += len(para) + 2
                continue
            
            length = len(para.strip())
            start = pos + text[pos:].find(para)
            end = start + len(para)
            
            if min_len > 0 and length < min_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"段落过短 ({length} 字符，最小 {min_len})"
                issues.append(issue)
            elif max_len > 0 and length > max_len:
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"段落过长 ({length} 字符，最大 {max_len})"
                issues.append(issue)
            
            pos = end + 2
        
        return issues
