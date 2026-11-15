import os
import tempfile
import pytest
from db import Database

@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database()
    db.open(path, create=True)
    yield db, path
    db.close()
    if os.path.exists(path):
        os.remove(path)

def test_db_basic_crud(tmp_db):
    db, _ = tmp_db
    # CREATE
    r = db.run("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    assert r.error is None
    assert "users" in r.tables
    db.commit()

    # INSERT
    r = db.run("INSERT INTO users (name) VALUES (?)", ("Alice",))
    assert r.error is None
    assert r.rowcount == 1
    assert "users" in r.tables
    db.commit()

    # SELECT
    r = db.run("SELECT * FROM users")
    assert r.error is None
    assert len(r.rows) == 1
    assert r.rows[0][1] == "Alice"
    assert "users" in r.tables

    # UPDATE
    r = db.run("UPDATE users SET name = ? WHERE id = ?", ("Bob", 1))
    assert r.error is None
    assert r.rowcount == 1
    db.commit()

    # DROP
    r = db.run("DROP TABLE users")
    assert r.error is None
    assert "users" in r.tables
    db.commit()

def test_db_join_tables(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE t1 (id INT, v TEXT)")
    db.run("CREATE TABLE t2 (id INT, v TEXT)")
    db.commit()
    r = db.run("SELECT * FROM t1 JOIN t2 ON t1.id = t2.id")
    assert r.error is None
    assert r.tables == {"t1", "t2"}

def test_db_syntax_error(tmp_db):
    db, _ = tmp_db
    r = db.run("SELEC FROM nowhere")
    assert r.error is not None
    assert len(r.tables) == 0

def test_db_rollback(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE test (id INT)")
    db.commit()

    # Rollback uncommitted insert
    db.run("INSERT INTO test VALUES (10)")
    assert db.has_pending is True
    db.rollback()
    assert db.has_pending is False
    r = db.run("SELECT * FROM test")
    assert len(r.rows) == 0

    # Rollback DROP TABLE
    db.run("DROP TABLE test")
    assert db.has_pending is True
    db.rollback()
    assert "test" in db.get_tables()

    # Rollback ALTER TABLE
    db.run("ALTER TABLE test ADD COLUMN extra TEXT")
    assert db.has_pending is True
    db.rollback()
    cols = [c["name"] for c in db.get_columns("test")]
    assert "extra" not in cols

def test_db_alter_and_indexes_tagged(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE items (id INT, name TEXT)")
    db.commit()

    r1 = db.run("ALTER TABLE items ADD COLUMN price REAL")
    assert "items" in r1.tables
    db.commit()

    r2 = db.run("CREATE INDEX idx_name ON items(name)")
    assert "items" in r2.tables
    db.commit()

    r3 = db.run("DROP INDEX idx_name")
    assert "items" in r3.tables
    db.commit()

def test_db_get_rows_paging_sorting_search(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, grade INT)")
    for i in range(1, 151):
        db.run("INSERT INTO students (id, name, grade) VALUES (?, ?, ?)",
               (i, f"Student_{i:03d}", i % 10))
    db.commit()

    # Paging: 100 rows on page 1, 50 on page 2
    cols, rows, total = db.get_rows("students", page=1, page_size=100)
    assert total == 150
    assert len(rows) == 100
    assert rows[0][1] == "Student_001"

    cols, rows2, total2 = db.get_rows("students", page=2, page_size=100)
    assert total2 == 150
    assert len(rows2) == 50

    # Sorting
    _, desc_rows, _ = db.get_rows("students", page=1, page_size=5, order_by="id", descending=True)
    assert desc_rows[0][0] == 150

    # Search
    _, search_rows, s_total = db.get_rows("students", page=1, search="042")
    assert s_total == 1
    assert search_rows[0][1] == "Student_042"

def test_db_get_table_info(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE a (id INT)")
    db.run("CREATE TABLE b (id INT, val TEXT)")
    db.run("INSERT INTO a VALUES (1)")
    db.run("INSERT INTO a VALUES (2)")
    db.commit()

    info = db.get_table_info()
    table_names = [t["name"] for t in info]
    assert "a" in table_names and "b" in table_names
    a_info = next(t for t in info if t["name"] == "a")
    assert a_info["row_count"] == 2
    b_info = next(t for t in info if t["name"] == "b")
    assert b_info["row_count"] == 0

def test_db_foreign_keys_enforced(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
    db.run("CREATE TABLE child (id INTEGER PRIMARY KEY, pid INT REFERENCES parent(id))")
    db.commit()

    # Violating FK fails
    r = db.run("INSERT INTO child (id, pid) VALUES (1, 999)")
    assert r.error is not None
    assert "FOREIGN KEY" in r.error.upper()

def test_db_row_limit_truncation(tmp_db):
    db, _ = tmp_db
    db.run("CREATE TABLE many (id INT)")
    # Insert 1005 rows
    stmts = ["INSERT INTO many VALUES (1)"] * 1005
    db.run_script("; ".join(stmts))
    db.commit()

    r = db.run("SELECT * FROM many")
    assert r.truncated is True
    assert len(r.rows) == 1000

def test_db_is_dangerous():
    db = Database()
    assert db.is_dangerous("DROP TABLE users") is not None
    assert db.is_dangerous("DELETE FROM users") is not None
    assert db.is_dangerous("UPDATE users SET a = 1") is not None
    assert db.is_dangerous("DELETE FROM users WHERE id = 1") is None
    assert db.is_dangerous("UPDATE users SET a = 1 WHERE id = 1") is None
    assert db.is_dangerous("SELECT * FROM users") is None

