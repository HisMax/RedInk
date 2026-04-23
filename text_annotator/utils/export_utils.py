import json
import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..models import Document, TextIssue, DiffChange


class ExportUtils:
    @staticmethod
    def export_issues_to_json(
        issues: List[TextIssue],
        file_path: str,
        include_resolved: bool = False
    ) -> bool:
        try:
            data = []
            for issue in issues:
                if not include_resolved and issue.is_resolved:
                    continue
                
                data.append({
                    'id': issue.id,
                    'issue_type': issue.issue_type.value,
                    'severity': issue.severity.value,
                    'line_number': issue.line_number,
                    'column_number': issue.column_number,
                    'start_pos': issue.start_pos,
                    'end_pos': issue.end_pos,
                    'original_text': issue.original_text,
                    'suggested_text': issue.suggested_text,
                    'message': issue.message,
                    'context': issue.context,
                    'accepted': issue.accepted,
                    'rejected': issue.rejected,
                    'metadata': issue.metadata
                })
            
            output = {
                'export_time': datetime.now().isoformat(),
                'total_issues': len(data),
                'issues': data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False

    @staticmethod
    def export_issues_to_csv(
        issues: List[TextIssue],
        file_path: str,
        include_resolved: bool = False
    ) -> bool:
        try:
            filtered = [i for i in issues if include_resolved or not i.is_resolved]
            
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'ID', '类型', '严重程度', '行号', '列号',
                    '原文', '建议修改', '消息', '状态'
                ])
                writer.writeheader()
                
                for issue in filtered:
                    status = '待处理'
                    if issue.accepted:
                        status = '已接受'
                    elif issue.rejected:
                        status = '已拒绝'
                    
                    writer.writerow({
                        'ID': issue.id[:8],
                        '类型': issue.issue_type.value,
                        '严重程度': issue.severity.value,
                        '行号': issue.line_number,
                        '列号': issue.column_number,
                        '原文': issue.original_text,
                        '建议修改': issue.suggested_text or '',
                        '消息': issue.message,
                        '状态': status
                    })
            
            return True
        except Exception:
            return False

    @staticmethod
    def export_diff_changes_to_json(
        changes: List[DiffChange],
        file_path: str,
        include_resolved: bool = False
    ) -> bool:
        try:
            data = []
            for change in changes:
                if not include_resolved and change.is_resolved:
                    continue
                
                data.append({
                    'id': change.id,
                    'change_type': change.change_type,
                    'line_number': change.line_number,
                    'original_text': change.original_text,
                    'modified_text': change.modified_text,
                    'accepted': change.accepted,
                    'rejected': change.rejected
                })
            
            output = {
                'export_time': datetime.now().isoformat(),
                'total_changes': len(data),
                'changes': data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception:
            return False

    @staticmethod
    def export_document(
        document: Document,
        file_path: str,
        export_format: str = 'txt'
    ) -> bool:
        try:
            if export_format == 'json':
                data = {
                    'id': document.id,
                    'name': document.name,
                    'file_path': document.file_path,
                    'original_content': document.original_content,
                    'current_content': document.current_content,
                    'has_changes': document.has_changes,
                    'export_time': datetime.now().isoformat()
                }
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(document.current_content)
            
            return True
        except Exception:
            return False

    @staticmethod
    def export_full_report(
        document: Document,
        output_dir: str,
        base_name: Optional[str] = None
    ) -> Dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        
        if base_name is None:
            base_name = document.name if document.name else 'document'
            base_name = os.path.splitext(base_name)[0]
        
        exported = {}
        
        text_path = os.path.join(output_dir, f'{base_name}_processed.txt')
        if ExportUtils.export_document(document, text_path):
            exported['text'] = text_path
        
        issues_json_path = os.path.join(output_dir, f'{base_name}_issues.json')
        if ExportUtils.export_issues_to_json(document.issues, issues_json_path, include_resolved=True):
            exported['issues_json'] = issues_json_path
        
        issues_csv_path = os.path.join(output_dir, f'{base_name}_issues.csv')
        if ExportUtils.export_issues_to_csv(document.issues, issues_csv_path, include_resolved=True):
            exported['issues_csv'] = issues_csv_path
        
        if document.diff_changes:
            diff_json_path = os.path.join(output_dir, f'{base_name}_diff.json')
            if ExportUtils.export_diff_changes_to_json(
                document.diff_changes, diff_json_path, include_resolved=True
            ):
                exported['diff_json'] = diff_json_path
        
        return exported
