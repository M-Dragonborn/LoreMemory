import os
import re
import sqlite3
import threading
import time
from config import ROW_LIMIT

def _v_str(v):
    return "NULL" if v is None else (str(v) if isinstance(v, (int, float)) else "'" + str(v).replace("'", "''") + "'")

class Result:
    def __init__(self, columns=None, rows=None, truncated=False, rowcount=0, tables=None, error=None, elapsed_ms=0.0):
        self.columns, self.rows, self.truncated = columns or [], rows or [], truncated
        self.rowcount, self.tables = rowcount, set(tables or [])
        self.error, self.elapsed_ms = error, elapsed_ms

class Database:
    def __init__(self, history=None, user_id=1):
        self.history, self.user_id, self.con = history, user_id, None
        self.path, self.lock, self._schema_cache = None, threading.RLock(), None

    def open(self, path, create=False):
        with self.lock:
            self.close()
            real_path = os.path.normcase(os.path.realpath(path))
            if not create and not os.path.exists(real_path): return False
            parent = os.path.dirname(real_path)
            if parent and not os.path.exists(parent): os.makedirs(parent, exist_ok=True)
            self.path = real_path
            try:
                self.con = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False, timeout=10.0)
                for prg in ("foreign_keys = ON", "journal_mode = WAL", "synchronous = NORMAL",
                            "cache_size = -64000", "temp_store = MEMORY", "mmap_size = 268435456"):
                    try: self.con.execute(f"PRAGMA {prg}")
                    except Exception: pass
                return True
            except Exception:
                self.close(); return False

    def close(self):
        with self.lock:
            self._schema_cache = None
            if self.con:
                try: self.con.close()
                except Exception: pass
            self.con, self.path = None, None

    @property
    def has_pending(self):
        with self.lock:
            return bool(self.con and self.con.in_transaction)

    def commit(self):
        with self.lock:
            if self.con and self.con.in_transaction: self.con.execute("COMMIT")
            self._schema_cache = None

    def rollback(self):
        with self.lock:
            if self.con and self.con.in_transaction: self.con.execute("ROLLBACK")
            self._schema_cache = None

    def is_dangerous(self, sql):
        clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip()
        u = clean.upper()
        if u.startswith("DROP"):
            return "This DROP statement will permanently remove an object. Undoable until Commit."
        if u.startswith("DELETE") and not re.search(r"\bWHERE\b", u):
            return "DELETE without WHERE will delete all rows. Undoable until Commit."
        if u.startswith("UPDATE") and not re.search(r"\bWHERE\b", u):
            return "UPDATE without WHERE will modify all rows. Undoable until Commit."
        return None

    def run(self, sql, params=(), display_sql=None):
        with self.lock:
            if not self.con: return Result(error="No open database")
            clean = re.sub(r"--.*$", "", sql, flags=re.MULTILINE).strip()
            first_word = clean.split()[0].upper() if clean else ""

            # Transaction rule: auto BEGIN for modifying statements (including CTEs)
            is_modifying = first_word in {"INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER"} or (
                first_word == "WITH" and bool(re.search(r"\b(INSERT|UPDATE|DELETE|REPLACE)\b", clean, re.I))
            )
            if is_modifying:
                if first_word in {"CREATE", "DROP", "ALTER"} or "CREATE" in clean.upper(): self._schema_cache = None
                if not self.con.in_transaction: self.con.execute("BEGIN")

            touched = set()
            def authorizer(action, a1, a2, dbname, source):
                if action in (sqlite3.SQLITE_READ, sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE,
                              sqlite3.SQLITE_DELETE, sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE):
                    target = a1
                elif action in (sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX):
                    target = a2
                else:
                    target = None
                if target and not target.startswith("sqlite_"): touched.add(target)
                return sqlite3.SQLITE_OK

            error, columns, rows, truncated, rowcount = None, [], [], False, 0
            t0 = time.perf_counter()
            self.con.set_authorizer(authorizer)
            try:
                cur = self.con.execute(sql, params)
                if cur.description:
                    columns = [d[0] for d in cur.description]
                    fetched = cur.fetchmany(ROW_LIMIT + 1)
                    if len(fetched) > ROW_LIMIT:
                        truncated = True
                        rows = fetched[:ROW_LIMIT]
                    else:
                        rows = fetched
                    rowcount = len(rows)
                else:
                    rowcount = cur.rowcount
            except sqlite3.Error as e:
                error = str(e)
            finally:
                self.con.set_authorizer(None)

            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

            # Logging rule: log immediately whether success or fail
            if self.history and self.path:
                self.history.record(self.path, self.user_id, display_sql or sql, 0 if error else 1,
                                    rowcount, error, touched)

            # Check table rename to update history
            if not error and first_word == "ALTER":
                m = re.search(r"ALTER\s+TABLE\s+[\"'`]?(\w+)[\"'`]?\s+RENAME\s+TO\s+[\"'`]?(\w+)[\"'`]?", sql, re.I)
                if m and self.history:
                    self.history.rename_table(self.path, m.group(1), m.group(2))

            return Result(columns, rows, truncated, rowcount, touched, error, elapsed_ms)

    def run_script(self, text):
        results = []
        buf = ""
        in_quote = None
        for i, c in enumerate(text):
            buf += c
            if c in ("'", '"') and (i == 0 or text[i - 1] != "\\"):
                if in_quote == c:
                    in_quote = None
                elif in_quote is None:
                    in_quote = c
            elif c == ";" and in_quote is None:
                if sqlite3.complete_statement(buf):
                    stmt = buf.strip()
                    if stmt:
                        res = self.run(stmt)
                        results.append(res)
                        if res.error:
                            return results
                    buf = ""
        if buf.strip():
            res = self.run(buf.strip())
            results.append(res)
        return results

    def get_tables(self):
        with self.lock:
            if not self.con:
                return []
            cur = self.con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            return [r[0] for r in cur.fetchall()]

    def get_columns(self, table):
        with self.lock:
            if not self.con: return []
            try:
                safe_t = str(table).replace('"', '""')
                cur = self.con.execute(f'PRAGMA table_info("{safe_t}")')
                cols = [{"name": r[1], "type": (r[2] or "TEXT").upper(), "notnull": bool(r[3]), "default": r[4], "pk": bool(r[5]), "fk": None} for r in cur.fetchall()]
                fk_cur = self.con.execute(f'PRAGMA foreign_key_list("{safe_t}")')
                for fk in fk_cur.fetchall():
                    for c in cols:
                        if c["name"] == fk[3]: c["fk"] = f"{fk[2]}({fk[4]})"
                return cols
            except Exception: return []

    def get_schema_only(self):
        with self.lock:
            if not self.con: return []
            if self._schema_cache is not None: return self._schema_cache
            self._schema_cache = [{"name": t, "columns": self.get_columns(t)} for t in self.get_tables()]
            return self._schema_cache

    def get_table_info(self):
        with self.lock:
            schema = self.get_schema_only()
            info = []
            for item in schema:
                t, cols = item["name"], item["columns"]
                safe_t = str(t).replace('"', '""')
                try: cnt = self.con.execute(f'SELECT COUNT(*) FROM "{safe_t}"').fetchone()[0]
                except Exception: cnt = 0
                info.append({"name": t, "columns": cols, "row_count": cnt})
            return info

    def get_rows(self, table, page, page_size=100, order_by=None, descending=False, search=""):
        with self.lock:
            if not self.con: return [], [], 0
            try:
                def q(s): return str(s).replace('"', '""')
                safe_t = q(table)
                cols = self.get_columns(table)
                col_names = [c["name"] for c in cols]
                has_pk = any(c["pk"] for c in cols)
                select_cols = [f'"{q(c)}"' for c in col_names]
                if not has_pk:
                    select_cols.insert(0, "rowid AS _rowid")
                    col_names.insert(0, "_rowid")
                where_parts, params = [], []
                if search and cols:
                    sub = " OR ".join([f'CAST("{q(c["name"])}" AS TEXT) LIKE ?' for c in cols])
                    where_parts.append(f"({sub})")
                    params.extend([f"%{search}%"] * len(cols))
                where_str = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
                count_sql = f'SELECT COUNT(*) FROM "{safe_t}"{where_str}'
                total_count = self.con.execute(count_sql, params).fetchone()[0]
                order_str = ""
                if order_by and order_by in col_names:
                    direction = "DESC" if descending else "ASC"
                    order_str = f' ORDER BY "{q(order_by)}" {direction}'
                offset = max(0, (page - 1) * page_size)
                query_sql = f'SELECT {", ".join(select_cols)} FROM "{safe_t}"{where_str}{order_str} LIMIT ? OFFSET ?'
                cur = self.con.execute(query_sql, list(params) + [page_size, offset])
                return col_names, cur.fetchall(), total_count
            except Exception: return [], [], 0

    def insert_row(self, table, data_dict):
        cols = list(data_dict.keys())
        p_str, c_str = ", ".join(["?"] * len(cols)), ", ".join([f'"{c}"' for c in cols])
        disp = f'INSERT INTO "{table}" ({c_str}) VALUES ({", ".join(_v_str(v) for v in data_dict.values())})'
        return self.run(f'INSERT INTO "{table}" ({c_str}) VALUES ({p_str})', tuple(data_dict.values()), display_sql=disp)

    def update_row(self, table, pk_col, pk_val, data_dict):
        set_parts = [f'"{c}" = ?' for c in data_dict.keys()]
        sql = f'UPDATE "{table}" SET {", ".join(set_parts)} WHERE "{pk_col}" = ?'
        disp_sets = [f'"{c}" = {_v_str(v)}' for c, v in data_dict.items()]
        disp = f'UPDATE "{table}" SET {", ".join(disp_sets)} WHERE "{pk_col}" = {_v_str(pk_val)}'
        return self.run(sql, tuple(data_dict.values()) + (pk_val,), display_sql=disp)

    def delete_row(self, table, pk_col, pk_val):
        disp = f'DELETE FROM "{table}" WHERE "{pk_col}" = {_v_str(pk_val)}'
        return self.run(f'DELETE FROM "{table}" WHERE "{pk_col}" = ?', (pk_val,), display_sql=disp)
