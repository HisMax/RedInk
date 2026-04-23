from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class IssueType(Enum):
    REGEX = "regex"
    DICTIONARY = "dictionary"
    REPEAT = "repeat"
    LENGTH = "length"
    FORMAT = "format"
    SPELLING = "spelling"


class IssueSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class TextIssue:
    id: str
    issue_type: IssueType
    severity: IssueSeverity
    start_pos: int
    end_pos: int
    original_text: str
    suggested_text: Optional[str] = None
    message: str = ""
    context: str = ""
    line_number: int = 0
    column_number: int = 0
    accepted: bool = False
    rejected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_resolved(self) -> bool:
        return self.accepted or self.rejected


@dataclass
class ScanRule:
    id: str
    name: str
    rule_type: IssueType
    enabled: bool = True
    pattern: str = ""
    replacement: str = ""
    description: str = ""
    severity: IssueSeverity = IssueSeverity.WARNING
    case_sensitive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffChange:
    id: str
    change_type: str
    original_text: str
    modified_text: str
    start_pos_original: int
    end_pos_original: int
    start_pos_modified: int
    end_pos_modified: int
    line_number: int
    accepted: bool = False
    rejected: bool = False

    @property
    def is_resolved(self) -> bool:
        return self.accepted or self.rejected


@dataclass
class Document:
    id: str
    name: str
    file_path: Optional[str] = None
    original_content: str = ""
    current_content: str = ""
    issues: List[TextIssue] = field(default_factory=list)
    diff_changes: List[DiffChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_changes(self) -> bool:
        return self.original_content != self.current_content

    @property
    def unresolved_issues(self) -> List[TextIssue]:
        return [i for i in self.issues if not i.is_resolved]

    @property
    def unresolved_diff_changes(self) -> List[DiffChange]:
        return [c for c in self.diff_changes if not c.is_resolved]
