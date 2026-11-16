import hashlib
import hmac
import secrets

def init_users(con):
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
            is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            created_by    INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login    TEXT
        )
    """)
    cur = con.execute("PRAGMA table_info(users)")
    cols = {r[1] for r in cur.fetchall()}
    if "role" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if "is_active" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    if "created_by" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN created_by INTEGER REFERENCES users(user_id) ON DELETE SET NULL")

    con.execute("""
        CREATE TABLE IF NOT EXISTS role_audit_log (
            audit_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user  INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            changed_by   INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
            old_role     TEXT NOT NULL,
            new_role     TEXT NOT NULL,
            changed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reason       TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_role_audit_target ON role_audit_log(target_user)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_role_audit_changed ON role_audit_log(changed_by)")

    # Seed initial super_admin if none exists
    cnt = con.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'").fetchone()[0]
    if cnt == 0:
        con.execute("UPDATE users SET role = 'super_admin' WHERE username = 'musfiq' OR user_id = 1")
        con.execute("UPDATE users SET role = 'admin' WHERE username = 'rayed'")
    con.commit()

def hash_password(password, salt_hex):
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return dk.hex()

def register(con, username, password, role="user", created_by=None):
    if not username or not password: return False
    username = username.strip()
    if not username: return False
    if role not in ("user", "admin", "super_admin"): role = "user"
    salt_hex = secrets.token_hex(16)
    p_hash = hash_password(password, salt_hex)
    try:
        con.execute(
            "INSERT INTO users (username, password_hash, salt, role, is_active, created_by) VALUES (?, ?, ?, ?, 1, ?)",
            (username, p_hash, salt_hex, role, created_by)
        )
        con.commit()
        return True
    except Exception:
        return False

def login(con, username, password):
    if not username or not password: return None
    username = username.strip()
    cur = con.execute("SELECT user_id, password_hash, salt, is_active FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row or row[3] == 0: return None
    user_id, stored_hash, salt_hex, _ = row
    calc_hash = hash_password(password, salt_hex)
    if not hmac.compare_digest(stored_hash, calc_hash): return None
    con.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
    con.commit()
    return user_id

def get_connection(path=None):
    import sqlite3
    from config import USERS_DB
    p = str(path or USERS_DB)
    con = sqlite3.connect(p, timeout=5.0)
    init_users(con)
    return con

def login_user(username, password, path=None):
    con = get_connection(path)
    try: return login(con, username, password)
    finally: con.close()

def register_user(username, password, role="user", created_by=None, path=None):
    con = get_connection(path)
    try: return register(con, username, password, role=role, created_by=created_by)
    finally: con.close()

def change_password(con, username, new_password):
    if not username or not new_password: return False
    username = username.strip()
    salt_hex = secrets.token_hex(16)
    p_hash = hash_password(new_password, salt_hex)
    cur = con.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = ?", (p_hash, salt_hex, username))
    con.commit()
    return cur.rowcount > 0

def change_password_user(username, new_password, path=None):
    con = get_connection(path)
    try: return change_password(con, username, new_password)
    finally: con.close()

def get_user(con, user_id):
    cur = con.execute("SELECT user_id, username, role, is_active, created_at, last_login, created_by FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row: return None
    return {"user_id": row[0], "username": row[1], "role": row[2], "is_active": row[3], "created_at": row[4], "last_login": row[5], "created_by": row[6]}

def get_user_by_name(con, username):
    cur = con.execute("SELECT user_id FROM users WHERE username = ?", (username.strip(),))
    row = cur.fetchone()
    return get_user(con, row[0]) if row else None

def list_users(con):
    cur = con.execute("SELECT user_id, username, role, is_active, created_at, last_login, created_by FROM users ORDER BY user_id ASC")
    return [{"user_id": r[0], "username": r[1], "role": r[2], "is_active": r[3], "created_at": r[4], "last_login": r[5], "created_by": r[6]} for r in cur.fetchall()]

def change_role(con, target_user_id, new_role, changed_by_id, reason=""):
    if new_role not in ("user", "admin", "super_admin"): return False
    u = get_user(con, target_user_id)
    if not u or u["role"] == new_role: return False
    old_role = u["role"]
    con.execute(
        "INSERT INTO role_audit_log (target_user, changed_by, old_role, new_role, reason) VALUES (?, ?, ?, ?, ?)",
        (target_user_id, changed_by_id, old_role, new_role, reason)
    )
    con.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, target_user_id))
    con.commit()
    return True

def set_active(con, target_user_id, is_active):
    act = 1 if is_active else 0
    cur = con.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (act, target_user_id))
    con.commit()
    return cur.rowcount > 0

def list_role_audit(con, target_user_id=None):
    sql = """SELECT a.audit_id, a.target_user, u1.username, a.changed_by, u2.username,
                    a.old_role, a.new_role, a.changed_at, a.reason
             FROM role_audit_log a
             LEFT JOIN users u1 ON a.target_user = u1.user_id
             LEFT JOIN users u2 ON a.changed_by = u2.user_id"""
    params = (target_user_id,) if target_user_id else ()
    if target_user_id: sql += " WHERE a.target_user = ?"
    sql += " ORDER BY a.audit_id DESC"
    cur = con.execute(sql, params)
    return [{
        "audit_id": r[0], "target_id": r[1], "target_user": r[2] or f"User #{r[1]}",
        "changed_by_id": r[3], "changed_by_user": r[4] or f"User #{r[3]}",
        "old_role": r[5], "new_role": r[6], "changed_at": r[7], "reason": r[8] or ""
    } for r in cur.fetchall()]
