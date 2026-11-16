import json, pytest
from mcp_server import MCPServer

@pytest.fixture
def mcp(tmp_path):
    db_file = tmp_path / "test_mcp.db"
    srv = MCPServer(db_path=str(db_file))
    yield srv
    srv.mem.close()

def test_mcp_initialize(mcp):
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    res = mcp.dispatch(req)
    assert res["id"] == 1
    assert res["result"]["serverInfo"]["name"] == "lore-memory"
    assert "tools" in res["result"]["capabilities"]

def test_mcp_tools_list(mcp):
    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    res = mcp.dispatch(req)
    tools = res["result"]["tools"]
    names = [t["name"] for t in tools]
    assert "recall" in names
    assert "remember" in names
    assert "recent" in names
    assert "query_sql" in names

def test_mcp_remember_and_recall(mcp):
    # Store a memory
    req_store = {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {
            "name": "remember",
            "arguments": {"text": "Project LoreMemory uses SQLite with WAL mode.", "importance": 0.9}
        }
    }
    res_store = mcp.dispatch(req_store)
    assert res_store["result"]["isError"] is False
    stored = json.loads(res_store["result"]["content"][0]["text"])
    assert stored["status"] == "stored"

    # Recall it
    req_recall = {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "recall", "arguments": {"query": "WAL mode", "k": 3}}
    }
    res_recall = mcp.dispatch(req_recall)
    assert res_recall["result"]["isError"] is False
    recalls = json.loads(res_recall["result"]["content"][0]["text"])
    assert len(recalls) > 0
    assert "WAL mode" in recalls[0]["text"]

def test_mcp_query_sql(mcp):
    req = {
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "query_sql", "arguments": {"sql": "SELECT COUNT(*) AS total FROM working_memory"}}
    }
    res = mcp.dispatch(req)
    assert res["result"]["isError"] is False
    data = json.loads(res["result"]["content"][0]["text"])
    assert "rows" in data
