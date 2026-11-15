import os
import sqlite3
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from memory import Memory

@pytest.fixture
def mem():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    m = Memory(db_path=path, enable_embeddings=False)
    yield m, path
    m.close()
    if os.path.exists(path):
        os.remove(path)

def test_memory_fk_rejects_missing_episode(mem):
    m, _ = mem
    # Attempting to insert working memory with non-existent episode_id should fail FK check
    with pytest.raises(sqlite3.IntegrityError):
        m.con.execute(
            "INSERT INTO working_memory (content, episode_id) VALUES ('test', 9999)"
        )

def test_memory_consolidation(mem):
    m, _ = mem
    # Insert working memories created in the past (e.g. 30 hours ago)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S")
    m.con.execute(
        "INSERT INTO working_memory (session_id, content, importance, created_at) VALUES ('sess1', 'Hello world', 0.8, ?)",
        (old_time,)
    )
    m.con.execute(
        "INSERT INTO working_memory (session_id, content, importance, created_at) VALUES ('sess1', 'More info', 0.6, ?)",
        (old_time,)
    )

    created_episodes = m.consolidate(hours=24)
    assert created_episodes == 1

    # Check episodic memory created
    eps = m.con.execute("SELECT episode_id, summary, importance, source FROM episodic_memory").fetchall()
    assert len(eps) == 1
    assert "Hello world" in eps[0][1]
    assert eps[0][2] == 0.8
    assert eps[0][3] == "consolidation"

    # Check working memory linked
    wms = m.con.execute("SELECT episode_id FROM working_memory").fetchall()
    assert len(wms) == 2
    assert wms[0][0] == eps[0][0]
    assert wms[1][0] == eps[0][0]

def test_memory_delete_episode_sets_null(mem):
    m, _ = mem
    ep_id = m.con.execute("INSERT INTO episodic_memory (summary) VALUES ('summary')").lastrowid
    wm_id = m.con.execute("INSERT INTO working_memory (content, episode_id) VALUES ('item', ?)", (ep_id,)).lastrowid

    # Delete episode
    m.con.execute("DELETE FROM episodic_memory WHERE episode_id = ?", (ep_id,))

    # wm should have episode_id set to NULL
    row = m.con.execute("SELECT episode_id FROM working_memory WHERE wm_id = ?", (wm_id,)).fetchone()
    assert row[0] is None

def test_memory_recall_abstention(mem):
    m, _ = mem
    m.remember("The capital of France is Paris")
    m.remember("Python is a programming language")

    # Query with no keyword match and no embeddings
    res = m.recall("Quantum physics cosmology")
    assert res == []

    # Query with keyword match
    res_match = m.recall("capital France")
    assert len(res_match) >= 1
    assert "Paris" in res_match[0]["text"]

def test_memory_save_episode(mem):
    m, _ = mem
    id1 = m.remember("Fact A", importance=0.4)
    id2 = m.remember("Fact B", importance=0.9)

    ep_id = m.save_episode([id1, id2], "Summary of A and B")
    assert ep_id is not None

    # Check importance took the highest
    row = m.con.execute("SELECT importance FROM episodic_memory WHERE episode_id = ?", (ep_id,)).fetchone()
    assert row[0] == 0.9

    # Try saving episode again with same ids - should refuse and return None
    res_again = m.save_episode([id1, id2], "Duplicate attempt")
    assert res_again is None

def test_memory_expired_never_recalled(mem):
    m, _ = mem
    # Expired memory
    past = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    m.con.execute(
        "INSERT INTO working_memory (content, expires_at) VALUES ('Temporary secret code', ?)",
        (past,)
    )
    # Active memory
    m.remember("Permanent secret code")

    res = m.recall("secret code")
    assert len(res) == 1
    assert "Permanent" in res[0]["text"]

