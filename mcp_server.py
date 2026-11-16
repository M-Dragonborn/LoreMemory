"""LoreMemory Model Context Protocol (MCP) Server.
Standard library stdio JSON-RPC 2.0 implementation (compatible with MCP 2024-11-05).
Zero external dependencies required.
"""
import json, os, re, sys, sqlite3, traceback
from memory import Memory
from config import MEMORY_DB

TOOLS = [
    {
        "name": "recall",
        "description": "Search working and episodic memories using hybrid retrieval (keyword + recency + semantic).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query or concept to recall."},
                "k": {"type": "integer", "description": "Max results to return (default 5).", "default": 5}
            },
            "required": ["query"]
        }
    },
    {
        "name": "remember",
        "description": "Store a new memory (fact, user preference, instruction, decision) in working memory.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "The memory content to store."},
                "importance": {"type": "number", "description": "Importance score between 0.0 and 1.0 (default 0.5).", "default": 0.5},
                "session": {"type": "string", "description": "Optional session identifier."},
                "ttl_hours": {"type": "number", "description": "Optional time-to-live in hours before auto-expiry."}
            },
            "required": ["text"]
        }
    },
    {
        "name": "recent",
        "description": "Retrieve recent memories in reverse chronological order.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "k": {"type": "integer", "description": "Number of memories to return (default 10).", "default": 10}
            }
        }
    },
    {
        "name": "consolidate",
        "description": "Consolidate aged working memories into structured episodic memory summaries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hours": {"type": "number", "description": "Hours threshold for consolidation (default 24.0).", "default": 24.0}
            }
        }
    },
    {
        "name": "memory_stats",
        "description": "Get current memory statistics (working, unconsolidated, episodes counts).",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "query_sql",
        "description": "Run a read-only SELECT query against the memory database or another SQLite database file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "Read-only SQL query (SELECT, PRAGMA, EXPLAIN)."},
                "db_path": {"type": "string", "description": "Path to SQLite database file (defaults to data/memory.db)."}
            },
            "required": ["sql"]
        }
    }
]

class MCPServer:
    def __init__(self, db_path=None):
        self.mem = Memory(db_path=db_path or MEMORY_DB)

    def log(self, msg):
        sys.stderr.write(f"[LoreMemory-MCP] {msg}\n")
        sys.stderr.flush()

    def handle_call(self, name, args):
        args = args or {}
        if name == "recall":
            q = str(args.get("query", ""))
            k = int(args.get("k", 5))
            res = self.mem.recall(q, k=k)
            return json.dumps(res, indent=2)
        elif name == "remember":
            text = str(args.get("text", ""))
            imp = float(args.get("importance", 0.5))
            sess = args.get("session")
            ttl = args.get("ttl_hours")
            rowid = self.mem.remember(text, importance=imp, session=sess, ttl_hours=ttl)
            return json.dumps({"status": "stored", "wm_id": rowid, "text": text})
        elif name == "recent":
            k = int(args.get("k", 10))
            return json.dumps(self.mem.recent(k=k), indent=2)
        elif name == "consolidate":
            h = args.get("hours", 24.0)
            cnt = self.mem.consolidate(hours=h)
            return json.dumps({"consolidated_episodes": cnt})
        elif name == "memory_stats":
            return json.dumps(self.mem.stats(), indent=2)
        elif name == "query_sql":
            sql = str(args.get("sql", "")).strip()
            if not re.match(r"^(SELECT|PRAGMA|EXPLAIN)\b", sql, re.IGNORECASE):
                raise ValueError("Only read-only queries (SELECT, PRAGMA, EXPLAIN) are permitted.")
            path = args.get("db_path") or self.mem.db_path
            con = sqlite3.connect(path, timeout=5.0)
            try:
                cur = con.execute(sql)
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = [dict(zip(cols, r)) for r in cur.fetchmany(100)]
                return json.dumps({"columns": cols, "rows": rows, "count": len(rows)}, indent=2)
            finally:
                con.close()
        raise ValueError(f"Unknown tool: {name}")

    def dispatch(self, req):
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if req_id is None:
            if method == "notifications/initialized":
                self.log("Client completed handshake.")
            return None

        if method == "initialize":
            res = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "lore-memory", "version": "1.0.0"}
            }
            return {"jsonrpc": "2.0", "id": req_id, "result": res}
        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            try:
                out_text = self.handle_call(tool_name, tool_args)
                res = {"content": [{"type": "text", "text": out_text}], "isError": False}
            except Exception as e:
                res = {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
            return {"jsonrpc": "2.0", "id": req_id, "result": res}
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        else:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}

    def run(self):
        self.log("Server initialized on stdio. Awaiting JSON-RPC requests...")
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception as e:
                self.log(f"Invalid JSON: {e}")
                continue
            resp = self.dispatch(req)
            if resp:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    server = MCPServer()
    try:
        server.run()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.mem.close()
