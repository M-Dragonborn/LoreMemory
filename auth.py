import hashlib
import hmac
import secrets

def init_users(con):
    con.execute("PRAGMA foreign_keys = ON")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt          TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login    TEXT
        )
        """
    )
    con.commit()

def hash_password(password, salt_hex):
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return dk.hex()

def register(con, username, password):
    if not username or not password:
        return False
    username = username.strip()
    if not username:
        return False

    salt_hex = secrets.token_hex(16)
    p_hash = hash_password(password, salt_hex)
    try:
        con.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, p_hash, salt_hex)
        )
        con.commit()
        return True
    except Exception:
        return False

def login(con, username, password):
    if not username or not password:
        return None
    username = username.strip()
    cur = con.execute(
        "SELECT user_id, password_hash, salt FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    if not row:
        return None

    user_id, stored_hash, salt_hex = row
    calc_hash = hash_password(password, salt_hex)
    if not hmac.compare_digest(stored_hash, calc_hash):
        return None

    con.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?",
        (user_id,)
    )
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
    try:
        return login(con, username, password)
    finally:
        con.close()

def register_user(username, password, path=None):
    con = get_connection(path)
    try:
        return register(con, username, password)
    finally:
        con.close()

def change_password(con, username, new_password):
    if not username or not new_password:
        return False
    username = username.strip()
    salt_hex = secrets.token_hex(16)
    p_hash = hash_password(new_password, salt_hex)
    cur = con.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (p_hash, salt_hex, username)
    )
    con.commit()
    return cur.rowcount > 0

def change_password_user(username, new_password, path=None):
    con = get_connection(path)
    try:
        return change_password(con, username, new_password)
    finally:
        con.close()
