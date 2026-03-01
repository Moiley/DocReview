import os.path
import time
from asyncio import Lock

from config.config import TEMP_DIR
from models.material import Material
from service.material_service import MaterialService
from utils.common import check_lang, scan_item_by_lang


class Task:
    """
    任务模型
    
    策略参数 (strategy):
        - baseline-naive: PyPDF2 原始提取 + 纯滑动窗口（外部基线）
        - ours-fixed: PrecisionPDFProcessor + 优化固定分块（系统基础版）
        - ours-adaptive: MinerU 解析 + 结构感知分块（系统增强版）
    
    Agent模式 (agent_mode):
        - detector-only: 仅使用 Detector Agent
        - dual-agent: 使用 Detector Agent + Reviewer Agent
    """
    
    # 有效的策略和Agent模式
    VALID_STRATEGIES = ["baseline-naive", "ours-fixed", "ours-adaptive"]
    VALID_AGENT_MODES = ["detector-only", "dual-agent"]
    
    def __init__(self, task_id, status=None, problem_count=0, message=None, create_time=None,
                scan_items=None, materials=None, complete_time=None, total_chunks=0, complete_chunks=0,
                sensitive_words=None, words=0, pages=0, adaptive_chunk=True,
                strategy="ours-adaptive", agent_mode="dual-agent"):
        if sensitive_words is None:
            sensitive_words = []
        if materials is None:
            materials = []
        if scan_items is None:
            scan_items = []
        self.task_id = task_id
        self.status = status
        self.problem_count = problem_count
        self.message = message
        self.create_time = create_time
        self.scan_items = scan_items
        self.materials = materials
        self.complete_time = complete_time
        self.total_chunks = total_chunks
        self.complete_chunks = complete_chunks
        self.sensitive_words = sensitive_words
        self.words = words
        self.pages = pages
        self.adaptive_chunk = adaptive_chunk
        
        # 新增参数
        self.strategy = strategy.lower() if strategy else "ours-adaptive"
        self.agent_mode = agent_mode.lower() if agent_mode else "dual-agent"
        
        # 兼容旧的 adaptive_chunk 参数
        if not adaptive_chunk and self.strategy == "ours-adaptive":
            self.strategy = "ours-fixed"
    
    def get_strategy(self):
        """获取分块策略"""
        return self.strategy
    
    def get_agent_mode(self):
        """获取Agent模式"""
        return self.agent_mode
    
    def is_dual_agent(self):
        """是否使用双Agent模式"""
        return self.agent_mode == "dual-agent"

    @staticmethod
    def get_file_locks():
        file_locks = {}
        return file_locks
    
    @staticmethod
    def get_lock():
        return Lock()
    
    def get_task_id(self):
        return self.task_id
    
    def get_status(self):
        return self.status
    
    def get_problem_count(self):
        return self.problem_count
    
    def get_file_name(self):
        return self.file_name

    def get_file_type(self):
        return self.file_type

    def get_message(self):
        return self.message
    
    def get_timestamp(self):
        return self.timestamp
    
    def set_task_id(self, task_id):
        self.task_id = task_id
    
    def set_status(self, status):
        self.status = status
    
    def set_problem_count(self, problem_count):
        self.problem_count = problem_count
    
    def set_file_name(self, file_name):
        self.file_name = file_name

    def set_file_type(self, file_type):
        self.file_type = file_type

    def set_message(self, message):
        self.message = message

    def set_timestamp(self, timestamp):
        self.timestamp = timestamp

    def get_materials(self):
        return self.materials
    
    def set_materials(self, materials):
        self.materials = materials
    
    def get_total_chunks(self):
        return self.total_chunks
    
    def get_complete_chunks(self):
        return self.complete_chunks
    
    def set_total_chunks(self, total_chunks):
        self.total_chunks = total_chunks
    
    def set_complete_chunks(self, complete_chunks):
        self.complete_chunks = complete_chunks
    
    def get_task_directory(self) -> str:
        return os.path.join(TEMP_DIR, self.task_id)

    def create_task_directory(self):
        task_dir = self.get_task_directory()
        if not os.path.exists(task_dir):
            os.makedirs(task_dir)
        return task_dir
    
    def init_task(self, files, scan_items, sensitive_words):
        self.create_task_directory()
        task_dir = self.get_task_directory()
        for file in files:
            file_name = file.filename
            if file_name == '':
                continue
            
            file_path = os.path.join(task_dir, file_name)
            file_suffix = file_name.split('.')[-1]
            file_type = Material.get_filetype(file_suffix)
            
            language = check_lang(file_name)
            scan_item = scan_item_by_lang(language, scan_items)
            material = Material(self.task_id, file_name, file_type, "processing", file_path, "等待处理", language, scan_items)
            
            # 数据库中插入新增扫描资料
            MaterialService().create_material(self.task_id, file_name, file_type, "processing", file_path, "等待处理", language)
            self.materials.append(material)
        
        self.status = "processing"
        self.message = "任务处理中"
        self.create_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.complete_time = None
        self.scan_items = scan_items
        self.problem_count = 0
        self.sensitive_words = sensitive_words