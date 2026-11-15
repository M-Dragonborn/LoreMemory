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

