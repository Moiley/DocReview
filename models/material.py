from config.config import *

class Material:
    def __init__(self, task_id, file_name, file_type, status, file_path, message, language="cn", scan_items=None, chunks=None):
        if scan_items is None:
            scan_items = []
        if chunks is None:
            chunks = []
        self.task_id = task_id
        self.file_name = file_name
        self.file_type = file_type
        self.status = status
        self.file_path = file_path
        self.message = message
        self.language = language
        self.scan_items = scan_items
        self.chunks = chunks
    
    def check_file_type(self, file_ext):
        if file_ext not in [".xlsx", ".chm", ".docx", ".pdf", ".pptx"]:
            return False
        else:
            return True
    
    def get_task_id(self):
        return self.task_id

    def get_file_name(self):
        return self.file_name

    def get_file_type(self):
        return self.file_type

    def get_status(self):
        return self.status

    def get_file_path(self):
        return self.file_path
    
    def get_message(self):
        return self.message
    
    def get_result(self):
        return self.result

    def set_task_id(self, task_id):
        self.task_id = task_id

    def set_file_name(self, file_name):
        self.file_name = file_name

    def set_file_type(self, file_type):
        self.file_type = file_type

    def set_status(self, status):
        self.status = status

    def set_file_path(self, file_path):
        self.file_path = file_path

    def set_message(self, message):
        self.message = message
    
    def set_result(self, result):
        self.result = result
    
    def get_language(self):
        return self.language
    
    def set_language(self, language):
        self.language = language
    
    def get_chunks(self):
        return self.chunks
    
    def set_chunks(self, chunks):
        self.chunks = chunks

    def get_scan_items(self):
        return self.scan_items

    def set_scan_items(self, scan_items):
        self.scan_items = scan_items

    @staticmethod
    def get_filetype(suffix):
        return MATERIAL_TYPE_DICT[suffix]
    