from typing import List, Dict, Type
from ..models import TextIssue, IssueType, ScanRule
from .base import BaseScanner
from .regex_scanner import RegexScanner
from .dictionary_scanner import DictionaryScanner
from .repeat_scanner import RepeatScanner
from .length_scanner import LengthScanner
from .format_scanner import FormatScanner


class ScannerManager:
    def __init__(self):
        self._scanners: Dict[IssueType, BaseScanner] = {}
        self._register_default_scanners()

    def _register_default_scanners(self):
        self._scanners[IssueType.REGEX] = RegexScanner()
        self._scanners[IssueType.DICTIONARY] = DictionaryScanner()
        self._scanners[IssueType.REPEAT] = RepeatScanner()
        self._scanners[IssueType.LENGTH] = LengthScanner()
        self._scanners[IssueType.FORMAT] = FormatScanner()

    def get_scanner(self, issue_type: IssueType) -> BaseScanner:
        return self._scanners.get(issue_type)

    def add_rule(self, rule: ScanRule):
        scanner = self._scanners.get(rule.rule_type)
        if scanner:
            scanner.add_rule(rule)

    def remove_rule(self, rule_id: str, issue_type: IssueType):
        scanner = self._scanners.get(issue_type)
        if scanner:
            scanner.remove_rule(rule_id)

    def scan(self, text: str, enabled_types: List[IssueType] = None) -> List[TextIssue]:
        all_issues = []
        
        if enabled_types is None:
            enabled_types = list(self._scanners.keys())
        
        for issue_type in enabled_types:
            scanner = self._scanners.get(issue_type)
            if scanner:
                issues = scanner.scan(text)
                all_issues.extend(issues)
        
        all_issues.sort(key=lambda x: x.start_pos)
        
        return all_issues

    def get_all_rules(self) -> Dict[IssueType, List[ScanRule]]:
        return {
            issue_type: scanner.rules
            for issue_type, scanner in self._scanners.items()
        }

    def load_default_rules(self):
        from ..models import IssueSeverity
        
        self.add_rule(ScanRule(
            id="regex_email",
            name="邮箱格式检测",
            rule_type=IssueType.REGEX,
            pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            description="检测文本中的邮箱地址",
            severity=IssueSeverity.INFO
        ))
        
        self.add_rule(ScanRule(
            id="regex_url",
            name="URL 检测",
            rule_type=IssueType.REGEX,
            pattern=r'https?://[^\s<>"]+|www\.[^\s<>"]+',
            description="检测文本中的 URL",
            severity=IssueSeverity.INFO
        ))
        
        self.add_rule(ScanRule(
            id="regex_phone",
            name="手机号码检测",
            rule_type=IssueType.REGEX,
            pattern=r'1[3-9]\d{9}',
            description="检测文本中的手机号码",
            severity=IssueSeverity.WARNING
        ))
