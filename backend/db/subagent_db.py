"""
SUB Agent 数据库存储系统
使用 SQLite 存储 SUB agent 执行记录和事件
"""

import sqlite3
import json
import time
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager


# 数据库文件路径
DB_PATH = Path(__file__).parent / "subagent.db"


class SubAgentDB:
    """
    SUB Agent 数据库管理类

    功能：
    - 存储 SUB agent 执行记录
    - 存储执行事件
    - 提供查询接口
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径，默认使用 subagent.db
        """
        self.db_path = db_path or DB_PATH
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        获取线程本地数据库连接

        Returns:
            sqlite3.Connection: 数据库连接
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    @contextmanager
    def _get_cursor(self):
        """
        获取数据库游标上下文管理器

        Yields:
            sqlite3.Cursor: 数据库游标
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_cursor() as cursor:
            # 执行记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    subagent_type TEXT NOT NULL,
                    show_thinking INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    result TEXT,
                    error TEXT
                )
            """)

            # 事件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (execution_id) REFERENCES executions (execution_id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_execution_id
                ON events (execution_id, timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_executions_status
                ON executions (status)
            """)

    def create_execution(
        self,
        execution_id: str,
        description: str,
        subagent_type: str,
        show_thinking: bool = True
    ) -> bool:
        """
        创建执行记录

        Args:
            execution_id: 执行 ID
            description: 任务描述
            subagent_type: SUB agent 类型
            show_thinking: 是否显示思考过程

        Returns:
            是否创建成功
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO executions (
                        execution_id, description, subagent_type,
                        show_thinking, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    execution_id,
                    description,
                    subagent_type,
                    1 if show_thinking else 0,
                    'pending',
                    time.time()
                ))
                return True
        except Exception as e:
            print(f"[SubAgentDB] 创建执行记录失败: {e}")
            return False

    def update_execution_status(
        self,
        execution_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        更新执行状态

        Args:
            execution_id: 执行 ID
            status: 新状态
            result: 执行结果（可选）
            error: 错误信息（可选）

        Returns:
            是否更新成功
        """
        try:
            with self._get_cursor() as cursor:
                if status == 'running':
                    cursor.execute("""
                        UPDATE executions
                        SET status = ?, started_at = ?
                        WHERE execution_id = ?
                    """, (status, time.time(), execution_id))
                elif status in ['completed', 'error']:
                    cursor.execute("""
                        UPDATE executions
                        SET status = ?, completed_at = ?, result = ?, error = ?
                        WHERE execution_id = ?
                    """, (status, time.time(), result, error, execution_id))
                else:
                    cursor.execute("""
                        UPDATE executions
                        SET status = ?
                        WHERE execution_id = ?
                    """, (status, execution_id))
                return True
        except Exception as e:
            print(f"[SubAgentDB] 更新执行状态失败: {e}")
            return False

    def add_event(
        self,
        execution_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        timestamp: Optional[float] = None
    ) -> bool:
        """
        添加执行事件

        Args:
            execution_id: 执行 ID
            event_type: 事件类型
            event_data: 事件数据
            timestamp: 时间戳（可选，默认当前时间）

        Returns:
            是否添加成功
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    INSERT INTO events (execution_id, event_type, event_data, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (
                    execution_id,
                    event_type,
                    json.dumps(event_data, ensure_ascii=False),
                    timestamp or time.time()
                ))
                return True
        except Exception as e:
            print(f"[SubAgentDB] 添加事件失败: {e}")
            return False

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行记录

        Args:
            execution_id: 执行 ID

        Returns:
            执行记录字典，不存在则返回 None
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM executions WHERE execution_id = ?
                """, (execution_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        'execution_id': row['execution_id'],
                        'description': row['description'],
                        'subagent_type': row['subagent_type'],
                        'show_thinking': bool(row['show_thinking']),
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'started_at': row['started_at'],
                        'completed_at': row['completed_at'],
                        'result': row['result'],
                        'error': row['error']
                    }
                return None
        except Exception as e:
            print(f"[SubAgentDB] 获取执行记录失败: {e}")
            return None

    def get_events(
        self,
        execution_id: str,
        since_timestamp: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取执行事件列表

        Args:
            execution_id: 执行 ID
            since_timestamp: 起始时间戳（可选），只返回此时间之后的事件
            limit: 返回数量限制（可选）

        Returns:
            事件列表
        """
        try:
            with self._get_cursor() as cursor:
                if since_timestamp:
                    cursor.execute("""
                        SELECT * FROM events
                        WHERE execution_id = ? AND timestamp > ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    """, (execution_id, since_timestamp, limit or 1000))
                else:
                    cursor.execute("""
                        SELECT * FROM events
                        WHERE execution_id = ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    """, (execution_id, limit or 1000))

                rows = cursor.fetchall()
                events = []
                for row in rows:
                    try:
                        event_data = json.loads(row['event_data'])
                    except:
                        event_data = {}
                    events.append({
                        'id': row['id'],
                        'execution_id': row['execution_id'],
                        'type': row['event_type'],
                        'data': event_data,
                        'timestamp': row['timestamp']
                    })
                return events
        except Exception as e:
            print(f"[SubAgentDB] 获取事件列表失败: {e}")
            return []

    def get_events_count(self, execution_id: str) -> int:
        """
        获取执行事件数量

        Args:
            execution_id: 执行 ID

        Returns:
            事件数量
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) as count FROM events WHERE execution_id = ?
                """, (execution_id,))
                row = cursor.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            print(f"[SubAgentDB] 获取事件数量失败: {e}")
            return 0

    def get_latest_timestamp(self, execution_id: str) -> Optional[float]:
        """
        获取最新事件的时间戳

        Args:
            execution_id: 执行 ID

        Returns:
            最新时间戳，无事件则返回 None
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("""
                    SELECT MAX(timestamp) as max_timestamp
                    FROM events
                    WHERE execution_id = ?
                """, (execution_id,))
                row = cursor.fetchone()
                return row['max_timestamp'] if row else None
        except Exception as e:
            print(f"[SubAgentDB] 获取最新时间戳失败: {e}")
            return None

    def list_executions(
        self,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出执行记录

        Args:
            status: 状态过滤（可选）
            limit: 返回数量限制

        Returns:
            执行记录列表
        """
        try:
            with self._get_cursor() as cursor:
                if status:
                    cursor.execute("""
                        SELECT * FROM executions
                        WHERE status = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (status, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM executions
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (limit,))

                rows = cursor.fetchall()
                executions = []
                for row in rows:
                    executions.append({
                        'execution_id': row['execution_id'],
                        'description': row['description'],
                        'subagent_type': row['subagent_type'],
                        'show_thinking': bool(row['show_thinking']),
                        'status': row['status'],
                        'created_at': row['created_at'],
                        'started_at': row['started_at'],
                        'completed_at': row['completed_at'],
                        'result': row['result'],
                        'error': row['error']
                    })
                return executions
        except Exception as e:
            print(f"[SubAgentDB] 列出执行记录失败: {e}")
            return []

    def delete_execution(self, execution_id: str) -> bool:
        """
        删除执行记录及其事件

        Args:
            execution_id: 执行 ID

        Returns:
            是否删除成功
        """
        try:
            with self._get_cursor() as cursor:
                cursor.execute("DELETE FROM events WHERE execution_id = ?", (execution_id,))
                cursor.execute("DELETE FROM executions WHERE execution_id = ?", (execution_id,))
                return True
        except Exception as e:
            print(f"[SubAgentDB] 删除执行记录失败: {e}")
            return False

    def cleanup_old_executions(self, days: int = 7) -> int:
        """
        清理旧执行记录

        Args:
            days: 保留天数

        Returns:
            删除的记录数
        """
        try:
            cutoff_time = time.time() - (days * 24 * 60 * 60)
            with self._get_cursor() as cursor:
                cursor.execute("""
                    DELETE FROM events
                    WHERE execution_id IN (
                        SELECT execution_id FROM executions
                        WHERE created_at < ?
                    )
                """, (cutoff_time,))
                cursor.execute("""
                    DELETE FROM executions WHERE created_at < ?
                """, (cutoff_time,))
                return cursor.rowcount
        except Exception as e:
            print(f"[SubAgentDB] 清理旧记录失败: {e}")
            return 0

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            del self._local.connection


# 全局数据库实例
_subagent_db: Optional[SubAgentDB] = None
_db_lock = threading.Lock()


def get_subagent_db() -> SubAgentDB:
    """
    获取全局数据库实例（单例模式）

    Returns:
        SubAgentDB: 数据库实例
    """
    global _subagent_db
    if _subagent_db is None:
        with _db_lock:
            if _subagent_db is None:
                _subagent_db = SubAgentDB()
    return _subagent_db
