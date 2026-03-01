import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.config import SQLITE_DB_PATH, STATUS_MAP


class SQLiteStorage:
    """轻量级 SQLite 存储，实现任务与资料的持久化管理。"""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT,
                    problem_count INTEGER DEFAULT 0,
                    message TEXT,
                    create_time TEXT,
                    complete_time TEXT,
                    scan_items TEXT,
                    total_chunks INTEGER DEFAULT 0,
                    complete_chunks INTEGER DEFAULT 0,
                    pages INTEGER DEFAULT 0,
                    words INTEGER DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_type TEXT,
                    status TEXT,
                    file_path TEXT,
                    message TEXT,
                    language TEXT,
                    problem_counts TEXT DEFAULT '{}',
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_material_task ON materials(task_id)"
            )

    # ---------------------- Task 操作 ---------------------- #
    def save_task(
        self,
        task_id: str,
        status: Optional[str],
        problem_count: int,
        message: Optional[str],
        create_time: Optional[str],
        complete_time: Optional[str],
        scan_items: Sequence[str],
    ):
        scan_items_str = (
            ",".join(scan_items) if isinstance(scan_items, (list, tuple)) else scan_items
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, status, problem_count, message, create_time, complete_time, scan_items, total_chunks, complete_chunks, pages, words)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0)
                """,
                (
                    task_id,
                    status,
                    problem_count,
                    message,
                    create_time,
                    complete_time,
                    scan_items_str or "",
                ),
            )

    def get_task_by_id(self, task_id: str):
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT status, problem_count, message, create_time, complete_time, total_chunks, complete_chunks
                FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row:
                return (
                    row["status"],
                    row["problem_count"],
                    row["message"],
                    row["create_time"],
                    row["complete_time"],
                    row["total_chunks"],
                    row["complete_chunks"],
                )
            return None

    def update_total_chunks(self, task_id: str, total_chunks: int):
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET total_chunks = ? WHERE task_id = ?",
                (total_chunks, task_id),
            )

    def query_complete_chunks(self, task_id: str) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT complete_chunks FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return row["complete_chunks"] if row else 0

    def update_complete_chunks(self, task_id: str, addition: int):
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET complete_chunks = complete_chunks + ? WHERE task_id = ?",
                (addition, task_id),
            )

    def update_problem_count(self, task_id: str, problem_count: int):
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET problem_count = ? WHERE task_id = ?",
                (problem_count, task_id),
            )

    def update_scan_status(self, task_id: str, status: str):
        with self._lock, self._connect() as conn:
            if status == "complete":
                row = conn.execute(
                    "SELECT problem_count FROM tasks WHERE task_id = ?", (task_id,)
                ).fetchone()
                problem_count = row["problem_count"] if row else 0
                message = f"处理完成，发现{problem_count}个问题"
            else:
                message = STATUS_MAP.get(status, status)
            complete_time = time.strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                UPDATE tasks SET status = ?, message = ?, complete_time = ?
                WHERE task_id = ?
                """,
                (status, message, complete_time, task_id),
            )

    def get_scan_task(self, task_id: str):
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT scan_items, status, message, problem_count, complete_time
                FROM tasks WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            if row:
                return (
                    row["scan_items"],
                    row["status"],
                    row["message"],
                    row["problem_count"],
                    row["complete_time"],
                )
            return None

    def get_materials_by_id(self, task_id: str) -> int:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM materials WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            return row["cnt"] if row else 0

    def get_progress_by_id(self, task_id: str) -> Optional[int]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT total_chunks, complete_chunks FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if not row:
                return None
            total = row["total_chunks"]
            complete = row["complete_chunks"]
            if total == 0:
                return 100
            if total == 99999:
                return 0
            return int(complete / total * 100)

    def update_material_status(self, pages: int, words: int, task_id: str):
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET pages = ?, words = ? WHERE task_id = ?",
                (pages, words, task_id),
            )

    def get_status_by_id(self, task_id: str):
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT pages, words FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            if row:
                return row["pages"], row["words"]
            return None, None

    # ---------------------- Material 操作 ---------------------- #
    def create_material(
        self,
        task_id: str,
        file_name: str,
        file_type: str,
        status: str,
        file_path: str,
        message: str,
        language: str,
    ):
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO materials (task_id, file_name, file_type, status, file_path, message, language, problem_counts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    file_name,
                    file_type,
                    status,
                    file_path,
                    message,
                    language,
                    json.dumps({}),
                ),
            )

    def _get_problem_counts(self, row: sqlite3.Row) -> Dict[str, int]:
        try:
            return json.loads(row["problem_counts"]) if row["problem_counts"] else {}
        except json.JSONDecodeError:
            return {}

    def update_problem_by_item(
        self, item_key: str, count: int, task_id: str, file_name: str
    ):
        with self._lock, self._connect() as conn:
            row = conn.execute(
                """
                SELECT problem_counts FROM materials
                WHERE task_id = ? AND file_name = ?
                """,
                (task_id, file_name),
            ).fetchone()
            if not row:
                return
            problem_counts = self._get_problem_counts(row)
            problem_counts[item_key] = count
            conn.execute(
                """
                UPDATE materials SET problem_counts = ?
                WHERE task_id = ? AND file_name = ?
                """,
                (json.dumps(problem_counts, ensure_ascii=False), task_id, file_name),
            )

    def query_item_separated(
        self, task_id: str, item_key: str
    ) -> Optional[List[Tuple[str, str, str, str, int]]]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT file_name, file_type, status, message, problem_counts
                FROM materials WHERE task_id = ?
                """,
                (task_id,),
            ).fetchall()
        if not rows:
            return None
        results = []
        for row in rows:
            counts = self._get_problem_counts(row)
            results.append(
                (
                    row["file_name"],
                    row["file_type"],
                    row["status"],
                    row["message"],
                    counts.get(item_key, 0),
                )
            )
        return results

    def update_material_scan_status(self, task_id: str, status: str):
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, problem_counts FROM materials
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchall()
            for row in rows:
                counts = self._get_problem_counts(row)
                total = sum(counts.values())
                message = f"处理完成，发现{total}个问题" if status == "complete" else STATUS_MAP.get(
                    status, status
                )
                conn.execute(
                    "UPDATE materials SET status = ?, message = ? WHERE id = ?",
                    (status, message, row["id"]),
                )

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务列表，按创建时间倒序"""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, status, problem_count, message,
                       create_time, complete_time, scan_items,
                       total_chunks, complete_chunks, pages, words
                FROM tasks
                ORDER BY create_time DESC
                """
            ).fetchall()
            tasks = []
            for row in rows:
                tasks.append({
                    "task_id": row["task_id"],
                    "status": row["status"],
                    "problem_count": row["problem_count"],
                    "message": row["message"],
                    "create_time": row["create_time"],
                    "complete_time": row["complete_time"],
                    "scan_items": row["scan_items"],
                    "total_chunks": row["total_chunks"],
                    "complete_chunks": row["complete_chunks"],
                    "pages": row["pages"],
                    "words": row["words"],
                })
            return tasks


storage = SQLiteStorage(SQLITE_DB_PATH)

