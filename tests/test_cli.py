import os
import tempfile
import pytest
import cli
from memory import Memory

@pytest.fixture
def mem_cli(capsys):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    m = Memory(db_path=path, enable_embeddings=False)
    yield m, capsys
    m.close()
    if os.path.exists(path):
        os.remove(path)

def test_cli_remember_recall_stats(mem_cli):
    m, capsys = mem_cli

    # remember
    code = cli.run(["remember", "User prefers dark mode", "-i", "0.9", "-s", "s1"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "saved #1" in out

    # stats
    code = cli.run(["stats"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "working: 1" in out
    assert "unconsolidated: 1" in out
    assert "episodes: 0" in out

    # recall found
    code = cli.run(["recall", "dark mode"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "[working #1]" in out
    assert "User prefers dark mode" in out

    # recall nothing found
    code = cli.run(["recall", "quantum gravity"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "nothing found" in out

def test_cli_recent_and_importance(mem_cli):
    m, capsys = mem_cli
    cli.run(["remember", "Alpha beta gamma", "-i", "0.5"], mem=m)
    capsys.readouterr()

    # importance update
    code = cli.run(["importance", "1", "0.95"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "importance updated" in out

    # recent
    code = cli.run(["recent", "-k", "5"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "Alpha beta gamma" in out
    assert "imp:0.95" in out

def test_cli_episode_and_pending(mem_cli):
    m, capsys = mem_cli
    cli.run(["remember", "Note 1"], mem=m)
    cli.run(["remember", "Note 2"], mem=m)
    capsys.readouterr()

    # episode save
    code = cli.run(["episode", "--ids", "1,2", "--summary", "Two notes together"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "episode #1 saved" in out

    # stats after episode
    code = cli.run(["stats"], mem=m)
    assert code == 0
    out, _ = capsys.readouterr()
    assert "working: 2" in out
    assert "unconsolidated: 0" in out
    assert "episodes: 1" in out
