from email import message
from multiprocessing import connection
import re
import time
from turtle import st

from config.config import STATUS_MAP
from utils.db_connector import get_db_connection, close_db_connection
from glob_var import db_lock

class TaskDao:
    def __init__(self):
        pass

    def get_task_by_id(self, task_id: str):
        # "根据 task_id 查询任务详情"
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = ("SELECT status, problem_count, message, create_time, complete_time, total_chunks, complete_chunks"
                        "FROM t_task WHERE task_id = %s")
                    cursor.execute(sql, (task_id,))
                    result = cursor.fetchone()
                    if result:
                        return (result[0], result[1], result[2], result[3], result[4], result[5], result[6])
                    return None
            finally:
                close_db_connection(connection)
    
    def save_task(self, task_id, status, problem_count, message, create_time, complete_time, scan_items):
        # "根据 task_id 查询任务详情"
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = ("INSERT INTO t_task (task_id, status, problem_count, message, create_time, complete_time, scan_items, total_chunks)"
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, 99999)")
                    cursor.execute(sql, (task_id, status, problem_count, message, create_time, complete_time, scan_items))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def update_total_chunks(self, task_id, total_chunks):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE t_task SET total_chunks = %s WHERE task_id = %s"
                    cursor.execute(sql, (total_chunks, task_id))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def update_complete_chunks(self, task_id, addition):
        complete_chunks = self.query_complete_chunks(task_id)
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE t_task SET complete_chunks = %s WHERE task_id = %s"
                    cursor.execute(sql, (complete_chunks + addition, task_id))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def query_complete_chunks(self, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT complete_chunks FROM t_task WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0]
                    return None
            finally:
                close_db_connection(connection)
    
    def update_problem_count(self, task_id, problem_count):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE t_task SET problem_count = %s WHERE task_id = %s"
                    cursor.execute(sql, (problem_count, task_id))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def update_scan_status(self, task_id, status):
        if status == "complete":
            scan_items, _, message, problem_count, complete_time = self.get_scan_task(task_id)
            message = f"处理完成，发现{problem_count}个问题"
        else:
            message = STATUS_MAP[status]
        complete_time = time.strftime("%Y-%m-%d %H:%M:%S")
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE t_task SET status = %s, message = %s, complete_time = %s WHERE task_id = %s"
                    cursor.execute(sql, (status, message, complete_time, task_id))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def get_scan_task(self, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT scan_items, status, message, problem_count, complete_time FROM t_task WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    result = cursor.fetchone()
                    if result:
                        return result
                    return None
            finally:
                close_db_connection(connection)
    
    def get_materials_by_id(self, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT COUNT(*) AS row_count FROM t_materials WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    result = cursor.fetchall()
                    return result[0]
            finally:
                close_db_connection(connection)
    
    def get_progress_by_id(self, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT total_chunks, complete_chunks FROM t_task WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    results = cursor.fetchone()
                    if results:
                        if results[0] == 0:
                            return 100
                        elif results[0] == 99999:
                            return 0
                        progress = int(results[1] / results[0] * 100)
                        return progress
                    return None
            finally:
                close_db_connection(connection)

    def update_material_status(self, pages, words, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "UPDATE t_task SET pages = %s, words = %s WHERE task_id = %s"
                    cursor.execute(sql, (pages, words, task_id))
                    connection.commit()
            finally:
                close_db_connection(connection)
    
    def get_status_by_id(self, task_id):
        with db_lock:
            connection = get_db_connection()
            try:
                with connection.cursor() as cursor:
                    sql = "SELECT pages, words FROM t_task WHERE task_id = %s"
                    cursor.execute(sql, (task_id,))
                    result = cursor.fetchone()
                    if result:
                        return result[0], result[1]
            finally:
                close_db_connection(connection)