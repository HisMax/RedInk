from .models import (
    TextIssue, ScanRule, DiffChange, Document,
    IssueType, IssueSeverity
)
from .scanners import ScannerManager
from .utils import DiffComparator, ExportUtils, FileUtils

__version__ = "1.0.0"
__all__ = [
    'TextIssue',
    'ScanRule',
    'DiffChange',
    'Document',
    'IssueType',
    'IssueSeverity',
    'ScannerManager',
    'DiffComparator',
    'ExportUtils',
    'FileUtils',
]

try:
    from .widgets import (
        HighlightEditor, IssuePanel, DiffView, RuleSettings
    )
    __all__.extend([
        'HighlightEditor',
        'IssuePanel',
        'DiffView',
        'RuleSettings',
    ])
except ImportError:
    pass
