import os
import re
import sqlite3
import threading
from config import HISTORY_DB, USERS_DB

class HistoryLog:
    def __init__(self, db_path=None, users_db_path=None):
        self.db_path = str(db_path or HISTORY_DB)
        self.users_db_path = str(users_db_path or USERS_DB)
        self.lock = threading.RLock()

        parent = os.path.dirname(self.db_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        u_parent = os.path.dirname(self.users_db_path)
        if u_parent and not os.path.exists(u_parent):
            os.makedirs(u_parent, exist_ok=True)

        self.con = sqlite3.connect(
            self.db_path, isolation_level=None, check_same_thread=False, timeout=5.0
        )
        self.con.execute("PRAGMA foreign_keys = ON")
        self._init_db()

    def _init_db(self):
        with self.lock:
            self.con.execute(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    query_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    db_path       TEXT NOT NULL,
                    user_id       INTEGER NOT NULL,
                    command_type  TEXT,
                    sql_text      TEXT NOT NULL,
                    executed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    success       INTEGER NOT NULL CHECK (success IN (0,1)),
                    rows_affected INTEGER,
                    error_message TEXT
                )
                """
            )
            self.con.execute(
                """
                CREATE TABLE IF NOT EXISTS query_table (
                    query_id   INTEGER NOT NULL,
                    table_name TEXT NOT NULL,
                    PRIMARY KEY (query_id, table_name),
                    FOREIGN KEY (query_id) REFERENCES query_history(query_id) ON DELETE CASCADE
                )
                """
            )
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_history_db ON query_history (db_path, query_id)")
            self.con.execute("CREATE INDEX IF NOT EXISTS idx_table_name ON query_table (table_name, query_id)")

            # Attach users.db as u
            norm_users = os.path.normcase(os.path.realpath(self.users_db_path))
            try:
                self.con.execute(f"ATTACH DATABASE ? AS u", (norm_users,))
            except sqlite3.OperationalError:
                pass  # Already attached or in-memory

    def record(self, db_path, user_id, sql, success, rowcount, error, tables):
        with self.lock:
            norm_path = os.path.normcase(os.path.realpath(db_path)) if os.path.exists(db_path) else db_path
            clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip()
            first = clean.split()[0].upper() if clean else "SQL"

            cur = self.con.execute(
                """
                INSERT INTO query_history (db_path, user_id, command_type, sql_text, success, rows_affected, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (norm_path, user_id, first, sql, 1 if success else 0, rowcount, error)
            )
            qid = cur.lastrowid
            if success and tables:
                for t in tables:
                    try:
                        self.con.execute(
                            "INSERT INTO query_table (query_id, table_name) VALUES (?, ?)",
                            (qid, t)
                        )
                    except sqlite3.IntegrityError:
                        pass
            return qid

    def rename_table(self, db_path, old_name, new_name):
        with self.lock:
            norm_path = os.path.normcase(os.path.realpath(db_path)) if os.path.exists(db_path) else db_path
            self.con.execute(
                """
                UPDATE query_table
                SET table_name = ?
                WHERE table_name = ? AND query_id IN (
                    SELECT query_id FROM query_history WHERE db_path = ?
                )
                """,
                (new_name, old_name, norm_path)
            )

    def for_table(self, db_path, table, limit=500, offset=0):
        with self.lock:
            norm_path = os.path.normcase(os.path.realpath(db_path)) if os.path.exists(db_path) else db_path
            cur = self.con.execute(
                """
                SELECT q.executed_at, COALESCE(u.username, 'unknown'), q.command_type,
                       q.sql_text, q.success, q.error_message
                FROM query_history q
                JOIN query_table qt ON q.query_id = qt.query_id
                LEFT JOIN u.users u ON q.user_id = u.user_id
                WHERE q.db_path = ? AND qt.table_name = ?
                ORDER BY q.query_id DESC
                LIMIT ? OFFSET ?
                """,
                (norm_path, table, limit, offset)
            )
            return cur.fetchall()

    def for_database(self, db_path, limit=500, offset=0):
        with self.lock:
            norm_path = os.path.normcase(os.path.realpath(db_path)) if os.path.exists(db_path) else db_path
            cur = self.con.execute(
                """
                SELECT q.executed_at, COALESCE(u.username, 'unknown'), q.command_type,
                       q.sql_text, q.success, q.error_message
                FROM query_history q
                LEFT JOIN u.users u ON q.user_id = u.user_id
                WHERE q.db_path = ?
                ORDER BY q.query_id DESC
                LIMIT ? OFFSET ?
                """,
                (norm_path, limit, offset)
            )
            return cur.fetchall()

    def close(self):
        with self.lock:
            if self.con:
                try:
                    self.con.close()
                except Exception:
                    pass
                self.con = None
