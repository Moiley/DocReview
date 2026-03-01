from dataclasses import dataclass
from pathlib import Path
from typing import Optional

class TextChunk:
    def __init__(self, file_path: str, text: str, length: int, language="cn", file_name="", scan_items=[], metadata=None):
        # 封装每个文本段的数据类
        self.file_path = file_path # 源文件路径
        self.text = text # 段落内容
        self.length = length # 段落长度
        self.language = language 
        self.file_name = file_name 
        self.scan_items = scan_items 
        self.metadata = metadata if metadata else {} # 新增元数据

    def get_metadata(self):
        return self.metadata
    
    def get_strategy(self):
        return self.metadata.get('strategy', 'baseline_fixed') 

    def get_file_path(self):
        return self.file_path
    
    def set_file_path(self, file_path):
        self.file_path = file_path

    def get_text(self):
        return self.text

    def get_length(self):
        return self.length

    def get_page_num(self):
        return self.page_num

    def get_language(self):
        return self.language

    def set_language(self, language):
        self.language = language
    
    def get_filename(self):
        return self.file_name
    
    def get_scan_items(self):
        return self.scan_items
    