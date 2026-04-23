import difflib
import uuid
from typing import List, Tuple, Optional
from ..models import DiffChange


class DiffComparator:
    def __init__(self):
        self._differ = difflib.Differ()

    def compare_texts(self, original: str, modified: str) -> List[DiffChange]:
        changes = []
        
        lines_original = original.splitlines(keepends=True)
        lines_modified = modified.splitlines(keepends=True)
        
        matcher = difflib.SequenceMatcher(None, lines_original, lines_modified)
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            
            original_lines = lines_original[i1:i2] if tag != 'insert' else []
            modified_lines = lines_modified[j1:j2] if tag != 'delete' else []
            
            original_text = ''.join(original_lines)
            modified_text = ''.join(modified_lines)
            
            start_pos_original = self._calculate_pos(lines_original, i1)
            end_pos_original = self._calculate_pos(lines_original, i2)
            start_pos_modified = self._calculate_pos(lines_modified, j1)
            end_pos_modified = self._calculate_pos(lines_modified, j2)
            
            change = DiffChange(
                id=str(uuid.uuid4()),
                change_type=tag,
                original_text=original_text,
                modified_text=modified_text,
                start_pos_original=start_pos_original,
                end_pos_original=end_pos_original,
                start_pos_modified=start_pos_modified,
                end_pos_modified=end_pos_modified,
                line_number=i1 + 1
            )
            changes.append(change)
        
        return changes

    def _calculate_pos(self, lines: List[str], line_index: int) -> int:
        return sum(len(line) for line in lines[:line_index])

    def generate_character_diff(
        self, 
        original: str, 
        modified: str
    ) -> List[Tuple[str, str, int, int, int, int]]:
        matcher = difflib.SequenceMatcher(None, original, modified)
        diffs = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                continue
            diffs.append((
                tag,
                original[i1:i2] if tag != 'insert' else '',
                modified[j1:j2] if tag != 'delete' else '',
                i1, i2, j1, j2
            ))
        
        return diffs

    def apply_change(self, text: str, change: DiffChange, accept: bool) -> str:
        if accept:
            if change.change_type == 'replace':
                return text[:change.start_pos_original] + change.modified_text + text[change.end_pos_original:]
            elif change.change_type == 'insert':
                return text[:change.start_pos_original] + change.modified_text + text[change.start_pos_original:]
            elif change.change_type == 'delete':
                return text[:change.start_pos_original] + text[change.end_pos_original:]
        else:
            return text

    def apply_all_changes(self, text: str, changes: List[DiffChange], accept: bool = True) -> str:
        result = text
        sorted_changes = sorted(
            [c for c in changes if not c.is_resolved],
            key=lambda x: x.start_pos_original,
            reverse=True
        )
        
        for change in sorted_changes:
            result = self.apply_change(result, change, accept)
        
        return result
