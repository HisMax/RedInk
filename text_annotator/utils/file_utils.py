import os
from typing import Optional, Tuple
from ..models import Document
import uuid


class FileUtils:
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.markdown'}

    @staticmethod
    def read_file(file_path: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in FileUtils.SUPPORTED_EXTENSIONS:
                return None, f"不支持的文件格式: {ext}"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content, None
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
                return content, None
            except Exception as e:
                return None, f"文件编码错误: {e}"
        except Exception as e:
            return None, f"读取文件失败: {e}"

    @staticmethod
    def write_file(file_path: str, content: str) -> Tuple[bool, Optional[str]]:
        try:
            dir_name = os.path.dirname(file_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True, None
        except Exception as e:
            return False, f"写入文件失败: {e}"

    @staticmethod
    def load_document(file_path: str) -> Tuple[Optional[Document], Optional[str]]:
        content, error = FileUtils.read_file(file_path)
        if error:
            return None, error
        
        name = os.path.basename(file_path)
        doc = Document(
            id=str(uuid.uuid4()),
            name=name,
            file_path=file_path,
            original_content=content,
            current_content=content
        )
        
        return doc, None

    @staticmethod
    def create_document_from_content(
        content: str,
        name: str = "未命名文档"
    ) -> Document:
        return Document(
            id=str(uuid.uuid4()),
            name=name,
            file_path=None,
            original_content=content,
            current_content=content
        )

    @staticmethod
    def save_document(document: Document, file_path: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        path = file_path or document.file_path
        if not path:
            return False, "未指定保存路径"
        
        success, error = FileUtils.write_file(path, document.current_content)
        if success:
            document.file_path = path
            document.name = os.path.basename(path)
        
        return success, error

    @staticmethod
    def get_file_info(file_path: str) -> dict:
        try:
            stat = os.stat(file_path)
            return {
                'exists': True,
                'size': stat.st_size,
                'modified_time': stat.st_mtime,
                'extension': os.path.splitext(file_path)[1].lower(),
                'name': os.path.basename(file_path),
                'directory': os.path.dirname(file_path)
            }
        except Exception:
            return {'exists': False}

    @staticmethod
    def is_supported_file(file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in FileUtils.SUPPORTED_EXTENSIONS
