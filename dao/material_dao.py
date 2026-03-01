from email import message
from config.config import STATUS_MAP, SCAN_ITEMS_MAP
from service.task_service import TaskService
from utils.db_connector import get_db_connection, close_db_connection
from glob_var import db_lock

class MaterialDao:
    def __init__(self):
        pass

    def create_material(self, task_id, file_name, file_type, status, file_path, message, language):
        # 根据 task_id 查询任务详情
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = ("INSERT INTO t_materials (task_id, file_name, file_type, status, file_path, message, language)"
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)")
                    cursor.execute(sql, (task_id, file_name, file_type, status, file_path, message, language))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def update_problem_by_item(self, column_name, column_value, task_id, file_name):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = f"UPDATE t_materials SET `{column_name}` = %s WHERE task_id = %s AND file_name = %s"
                    cursor.execute(sql, (column_value, task_id, file_name))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def query_item_separated(self, task_id, item):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = f"SELECT file_name, file_type, status, message, `{item}` FROM t_materials WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    results = cursor.fetchall()
                    if results:
                        return results
                    return None
            finally:
                close_db_connection(connection)
    
    def query_problem_count_by_material(self, task_id):
        with db_lock:
            connection = get_db_connection()
            valid_keys = [key for key in SCAN_ITEMS_MAP.keys()]
            columns_str = ", ".join(map(lambda x: f'`{x}`', valid_keys))
            try:
                with connection.cursor() as cursor:
                    sql = f"SELECT file_name, {columns_str} FROM t_materials WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    results = cursor.fetchall()
                    if results:
                        return results
                    return None
            finally:
                close_db_connection(connection)
    
    def update_scan_status(self, task_id, status):
        if status == "complete":
            results = self.query_problem_count_by_material(task_id)
            for result in results:
                file_name = result[0]
                total_count = 0
                for i in range(1, len(result)):
                    total_count += result[i]
                message = f"处理完成，发现{total_count}个问题"
                with db_lock:
                    connection = get_db_connection()
                    try:
                        with connection.cursor() as cursor:
                            sql = "UPDATE t_materials SET message = %s, status = %s WHERE task_id = %s AND file_name = %s"
                            cursor.execute(sql, (message, status, task_id, file_name))
                            connection.commit()
                    finally:
                        close_db_connection(connection)
        else:
            return