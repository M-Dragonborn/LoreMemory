import os
import sqlite3
import tempfile
import pytest
import auth
from history import HistoryLog
from db import Database

@pytest.fixture
def env():
    td = tempfile.mkdtemp()
    hist_path = os.path.join(td, "test_hist.db")
    users_path = os.path.join(td, "test_users.db")
    db_path = os.path.join(td, "test_user_db.db")

    # init users
    u_con = sqlite3.connect(users_path)
    auth.init_users(u_con)
    auth.register(u_con, "alice", "p1")
    auth.register(u_con, "bob", "p2")
    u_con.close()

    hist = HistoryLog(hist_path, users_path)
    db = Database(history=hist, user_id=1)
    db.open(db_path, create=True)

    yield hist, db, db_path, hist_path

    db.close()
    hist.close()

def test_history_join_logs_two_tables(env):
    hist, db, db_path, hist_path = env
    db.run("CREATE TABLE t1 (id INT)")
    db.run("CREATE TABLE t2 (id INT)")
    db.commit()

    r = db.run("SELECT * FROM t1 JOIN t2 ON t1.id = t2.id")
    assert r.error is None
    assert r.tables == {"t1", "t2"}

    # Check query_table has 2 rows for this query
    h_con = sqlite3.connect(hist_path)
    rows = h_con.execute(
        "SELECT table_name FROM query_table WHERE query_id = (SELECT MAX(query_id) FROM query_history)"
    ).fetchall()
    h_con.close()
    tables = {row[0] for row in rows}
    assert tables == {"t1", "t2"}

def test_history_multi_user(env):
    hist, db, db_path, _ = env
    db.user_id = 1  # Alice
    db.run("CREATE TABLE items (id INT)")
    db.run("INSERT INTO items VALUES (1)")
    db.commit()

    db.user_id = 2  # Bob
    db.run("INSERT INTO items VALUES (2)")
    db.commit()

    entries = hist.for_table(db_path, "items")
    users = [e[1] for e in entries]
    assert "alice" in users
    assert "bob" in users

def test_history_failed_command_view(env):
    hist, db, db_path, _ = env
    db.run("CREATE TABLE pets (id INT)")
    db.commit()

    # Syntax error command
    db.run("SELEC * FROM pets")

    # Should be in database-wide history
    db_hist = hist.for_database(db_path)
    assert any("SELEC" in e[3] and e[4] == 0 for e in db_hist)

    # Should NOT be in table history (no table associated)
    table_hist = hist.for_table(db_path, "pets")
    assert not any("SELEC" in e[3] for e in table_hist)

def test_history_starts_with_create(env):
    hist, db, db_path, _ = env
    db.run("CREATE TABLE cars (model TEXT)")
    db.run("INSERT INTO cars VALUES ('Civic')")
    db.commit()

    entries = hist.for_table(db_path, "cars")
    # Newest first, so oldest is at end
    oldest = entries[-1]
    assert oldest[2] == "CREATE"
    assert "CREATE TABLE cars" in oldest[3]

def test_history_rename_table(env):
    hist, db, db_path, _ = env
    db.run("CREATE TABLE old_books (title TEXT)")
    db.run("INSERT INTO old_books VALUES ('Hamlet')")
    db.commit()

    # Rename
    db.run("ALTER TABLE old_books RENAME TO new_books")
    db.commit()

    # Old name should have 0 entries now
    assert len(hist.for_table(db_path, "old_books")) == 0
    # New name has the history
    new_entries = hist.for_table(db_path, "new_books")
    assert len(new_entries) >= 2
    assert any("CREATE TABLE old_books" in e[3] for e in new_entries)

def test_history_offset_pagination(env):
    hist, db, db_path, _ = env
    db.run("CREATE TABLE logs (num INT)")
    for i in range(10):
        db.run(f"INSERT INTO logs VALUES ({i})")
    db.commit()

    batch1 = hist.for_table(db_path, "logs", limit=5, offset=0)
    batch2 = hist.for_table(db_path, "logs", limit=5, offset=5)
    assert len(batch1) == 5
    assert len(batch2) == 5
    # Distinct entries
    sql1 = [e[3] for e in batch1]
    sql2 = [e[3] for e in batch2]
    assert not set(sql1).intersection(set(sql2))
