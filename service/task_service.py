from storage.sqlite_storage import storage


class TaskService:
    def __init__(self):
        self.storage = storage
    
    def save_task(self, task_id, status=None, problem_count=0, message=None, create_time=None, complete_time=None, scan_items=None):
        self.storage.save_task(task_id, status, problem_count, message, create_time, complete_time, scan_items or [])

    def get_task_by_id(self, task_id):
        return self.storage.get_task_by_id(task_id)
    
    def update_total_chunks(self, task_id, total_chunks):
        self.storage.update_total_chunks(task_id, total_chunks)
    
    def update_complete_chunks(self, task_id, addition):
        self.storage.update_complete_chunks(task_id, addition)
    
    def update_problem_count(self, task_id, problem_count):
        self.storage.update_problem_count(task_id, problem_count)
    
    def update_scan_status(self, task_id, status):
        self.storage.update_scan_status(task_id, status)
    
    def get_scan_task(self, task_id):
        return self.storage.get_scan_task(task_id)

    def get_materials_by_id(self, task_id):
        return self.storage.get_materials_by_id(task_id)

    def get_progress_by_id(self, task_id):
        return self.storage.get_progress_by_id(task_id)
    
    def update_material_status(self, pages, words, task_id):
        self.storage.update_material_status(pages, words, task_id)

    def get_status_by_id(self, task_id):
        return self.storage.get_status_by_id(task_id)