from storage.sqlite_storage import storage


class MaterialService:
    def __init__(self):
        self.storage = storage

    def create_material(self, task_id, file_name=None, file_type=None, status=None, file_path=None, message=None, language="cn"):
        self.storage.create_material(task_id, file_name, file_type, status, file_path, message, language)

    def update_problem_by_item(self, column_name, column_value, task_id, file_name):
        self.storage.update_problem_by_item(column_name, column_value, task_id, file_name)

    def query_item_separated(self, task_id, item):
        return self.storage.query_item_separated(task_id, item)

    def update_scan_status(self, task_id, status):
        self.storage.update_material_scan_status(task_id, status)