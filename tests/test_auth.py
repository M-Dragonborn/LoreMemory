import sqlite3
import auth

def test_auth_full_flow():
    con = sqlite3.connect(":memory:")
    auth.init_users(con)

    # Empty inputs fail
    assert auth.register(con, "", "pass") is False
    assert auth.register(con, "alice", "") is False
    assert auth.login(con, "", "pass") is None

    # Register works
    assert auth.register(con, "alice", "secret123") is True

    # Duplicate username fails
    assert auth.register(con, "alice", "another") is False

    # Correct password logs in
    user_id = auth.login(con, "alice", "secret123")
    assert user_id is not None
    assert user_id == 1

    # Verify last_login updated
    row = con.execute("SELECT last_login FROM users WHERE user_id = 1").fetchone()
    assert row[0] is not None

    # Wrong password returns None
    assert auth.login(con, "alice", "wrong") is None

    # Unknown user returns None
    assert auth.login(con, "bob", "secret123") is None

    # No plain password is stored
    row = con.execute("SELECT password_hash, salt FROM users WHERE user_id = 1").fetchone()
    assert row[0] != "secret123"
    assert "secret123" not in row[0]
    assert len(row[1]) == 32  # 16 bytes hex

    # Change password
    assert auth.change_password(con, "alice", "new_secret456") is True
    assert auth.login(con, "alice", "secret123") is None
    assert auth.login(con, "alice", "new_secret456") == 1
    assert auth.change_password(con, "nonexistent", "pass") is False

def test_roles_and_audit_log():
    con = sqlite3.connect(":memory:")
    auth.init_users(con)

    # Create root super admin and standard users
    auth.register(con, "root_admin", "adminpass", role="super_admin")
    auth.register(con, "developer", "devpass", role="user")
    admin_id = auth.get_user_by_name(con, "root_admin")["user_id"]
    dev_id = auth.get_user_by_name(con, "developer")["user_id"]

    # Verify initial roles
    users = auth.list_users(con)
    assert len(users) == 2
    assert users[0]["role"] == "super_admin"
    assert users[1]["role"] == "user"

    # Promote developer to admin
    ok = auth.change_role(con, dev_id, "admin", admin_id, reason="Promoted to team lead")
    assert ok is True
    assert auth.get_user(con, dev_id)["role"] == "admin"

    # Verify audit log
    audit_logs = auth.list_role_audit(con)
    assert len(audit_logs) == 1
    entry = audit_logs[0]
    assert entry["target_user"] == "developer"
    assert entry["changed_by_user"] == "root_admin"
    assert entry["old_role"] == "user"
    assert entry["new_role"] == "admin"
    assert entry["reason"] == "Promoted to team lead"

    # Invalid role fails
    assert auth.change_role(con, dev_id, "invalid_role", admin_id) is False
    # Same role fails
    assert auth.change_role(con, dev_id, "admin", admin_id) is False

def test_user_active_deactivation():
    con = sqlite3.connect(":memory:")
    auth.init_users(con)

    auth.register(con, "charlie", "password123")
    c_id = auth.get_user_by_name(con, "charlie")["user_id"]
    assert auth.login(con, "charlie", "password123") == c_id

    # Deactivate account
    auth.set_active(con, c_id, False)
    u = auth.get_user(con, c_id)
    assert u["is_active"] == 0

    # Deactivated account cannot log in
    assert auth.login(con, "charlie", "password123") is None

    # Reactivate account
    auth.set_active(con, c_id, True)
    assert auth.login(con, "charlie", "password123") == c_id
