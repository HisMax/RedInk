import re
from typing import List
from .base import BaseScanner
from ..models import TextIssue, ScanRule, IssueType, IssueSeverity


class FormatScanner(BaseScanner):
    def __init__(self):
        super().__init__()
        default_rule = ScanRule(
            id="format_default",
            name="格式检测",
            rule_type=IssueType.FORMAT,
            description="检测文本格式问题",
            severity=IssueSeverity.WARNING
        )
        self.rules.append(default_rule)

    def get_supported_type(self) -> IssueType:
        return IssueType.FORMAT

    def scan(self, text: str) -> List[TextIssue]:
        issues = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            format_type = rule.metadata.get("format_type", "all")
            
            if format_type == "all" or format_type == "whitespace":
                issues.extend(self._scan_whitespace(text, rule))
            if format_type == "all" or format_type == "punctuation":
                issues.extend(self._scan_punctuation(text, rule))
            if format_type == "all" or format_type == "casing":
                issues.extend(self._scan_casing(text, rule))
            if format_type == "all" or format_type == "numbers":
                issues.extend(self._scan_numbers(text, rule))
        
        return issues

    def _scan_whitespace(self, text: str, rule: ScanRule) -> List[TextIssue]:
        issues = []
        
        patterns = [
            (r'  +', "多余空格"),
            (r'\t', "制表符"),
            (r' +\n', "行尾空格"),
            (r'\n{3,}', "过多空行"),
        ]
        
        for pattern, desc in patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"{desc}: '{match.group()!r}'"
                issues.append(issue)
        
        return issues

    def _scan_punctuation(self, text: str, rule: ScanRule) -> List[TextIssue]:
        issues = []
        
        patterns = [
            (r'([，。！？；：、])\1+', "重复标点"),
            (r'([,.!?;:])\1+', "重复英文标点"),
            (r'\b(\w+)(,)(\w)', "英文逗号后无空格"),
        ]
        
        for pattern, desc in patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                issue = self.create_issue(text, start, end, rule)
                issue.message = f"{desc}: '{match.group()}'"
                issues.append(issue)
        
        return issues

    def _scan_casing(self, text: str, rule: ScanRule) -> List[TextIssue]:
        issues = []
        
        sentence_start_pattern = r'(?<=[。！？.!?]\s)([a-z])'
        for match in re.finditer(sentence_start_pattern, text):
            start = match.start()
            end = match.end()
            issue = self.create_issue(text, start, end, rule)
            issue.message = f"句子开头应该大写: '{match.group()}'"
            issue.suggested_text = match.group().upper()
            issues.append(issue)
        
        return issues

    def _scan_numbers(self, text: str, rule: ScanRule) -> List[TextIssue]:
        issues = []
        
        cn_num_pattern = r'[一二三四五六七八九十百千万亿]+'
        for match in re.finditer(cn_num_pattern, text):
            if self._is_valid_chinese_number(match.group()):
                continue
            start, end = match.span()
            issue = self.create_issue(text, start, end, rule)
            issue.message = f"中文数字格式可能有误: '{match.group()}'"
            issues.append(issue)
        
        return issues

    def _is_valid_chinese_number(self, s: str) -> bool:
        valid_units = {'零', '一', '二', '三', '四', '五', '六', '七', '八', '九', 
                       '十', '百', '千', '万', '亿'}
        return all(c in valid_units for c in s)
