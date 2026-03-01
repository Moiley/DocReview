class DocumentProcessingError(Exception):
    """文档处理错误基类"""
    pass


class APIError(DocumentProcessingError):
    """API调用错误"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"API调用错误: {self.message}"


class FileProcessingError(DocumentProcessingError):
    """文件处理错误"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"文件处理失败: {self.message}"      