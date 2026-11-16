# Connecting LoreMemory to Hermes Agent via MCP

This guide explains how to connect **LoreMemory** as a persistent memory and database backend for **Hermes Agent** (by Nous Research) using the **Model Context Protocol (MCP)**.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│           Hermes Agent (Nous Research)                 │
│      (Autonomous reasoning, tool-calling agent)        │
└──────────────────────────┬─────────────────────────────┘
                           │ Model Context Protocol (stdio / JSON-RPC)
                           ▼
┌────────────────────────────────────────────────────────┐
│         LoreMemory MCP Server (`mcp_server.py`)        │
│  Tools: recall, remember, recent, consolidate, sql     │
└──────────────────────────┬─────────────────────────────┘
                           │ Python Engine (PRAGMA journal_mode = WAL)
                           ▼
┌────────────────────────────────────────────────────────┐
│   `data/memory.db` (Working & Episodic Memory Tables)  │
│   `data/history.db` | User SQLite Databases            │
└────────────────────────────────────────────────────────┘
```

Because LoreMemory runs SQLite in **WAL (Write-Ahead Logging)** mode, your desktop GUI application and Hermes Agent can query and update memories at the same time without database locks.

---

## Available Tools

Once connected, Hermes automatically acquires 6 tools:

| Tool | Parameters | Description |
| :--- | :--- | :--- |
| `recall` | `query: str`, `k: int = 5` | Hybrid retrieval (vector + keyword + recency + importance). Hermes calls this to retrieve relevant context before acting. |
| `remember` | `text: str`, `importance: float = 0.5`, `session: str`, `ttl_hours: float` | Saves a fact, decision, user preference, or project rule into working memory. |
| `recent` | `k: int = 10` | Returns the newest memories in reverse chronological order. |
| `consolidate` | `hours: float = 24.0` | Clusters aged working memories into long-term episodic summaries. |
| `memory_stats` | *(none)* | Returns counts of working items, unconsolidated records, and episodes. |
| `query_sql` | `sql: str`, `db_path: str` | Safely executes read-only SQL (`SELECT`, `PRAGMA`, `EXPLAIN`) against project databases. |

---

## Method 1: Hermes Agent (`~/.hermes/config.yaml`)

Hermes Agent natively loads external MCP tool servers configured in its YAML configuration file.

### Step 1: Open Hermes Config
Open your Hermes configuration file:
- **Windows:** `%USERPROFILE%\.hermes\config.yaml`
- **Linux/macOS:** `~/.hermes/config.yaml`

### Step 2: Add LoreMemory under `mcp_servers`
Add the following block to your `config.yaml`:

```yaml
mcp_servers:
  lore_memory:
    command: "python"
    args:
      - "D:/Projects/LoreMemory/mcp_server.py"
    timeout: 60
```

> **Note:** Replace `D:/Projects/LoreMemory/mcp_server.py` with your absolute path if located elsewhere.

### Step 3: Verify Tool Discovery
From your terminal, run:

```bash
hermes tools list
```

You should see:
```text
lore_memory:
  - recall
  - remember
  - recent
  - consolidate
  - memory_stats
  - query_sql
```

### Step 4: Run Hermes with Persistent Memory
Start an interactive conversation:

```bash
hermes chat
```

**Example Conversation Flow:**
1. **You:** *"Remember that the active project uses SQLite in WAL mode and the test suite has 32 tests."*
   - Hermes detects the intent and calls `remember(text="...")`.
2. **You (in a new session or later):** *"What database mode did we configure for this project?"*
   - Hermes calls `recall(query="database mode")`, retrieves the stored record, and responds accurately.

---

## Method 2: Running Nous Hermes 3 locally via Ollama + Python

If you run `hermes3` locally through Ollama or vLLM, you can bridge Hermes to `mcp_server.py` using a lightweight Python agent script:

```python
import json, subprocess, requests

class HermesLoreAgent:
    def __init__(self, mcp_script="mcp_server.py", ollama_model="hermes3"):
        self.model = ollama_model
        # Spawn LoreMemory MCP Server
        self.proc = subprocess.Popen(
            ["python", mcp_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # MCP Handshake
        self._call("initialize", {"protocolVersion": "2024-11-05"})

    def _call(self, method, params):
        req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line).get("result", {})

    def recall(self, query):
        res = self._call("tools/call", {"name": "recall", "arguments": {"query": query}})
        return res.get("content", [{}])[0].get("text", "")

    def remember(self, text, importance=0.5):
        return self._call("tools/call", {"name": "remember", "arguments": {"text": text, "importance": importance}})

    def chat(self, user_msg):
        # 1. Automatic context retrieval
        memories = self.recall(user_msg)
        system_prompt = f"You are Hermes. Relevant memories:\n{memories}\n"

        # 2. Query Ollama Hermes model
        resp = requests.post("http://localhost:11434/api/generate", json={
            "model": self.model,
            "prompt": f"{system_prompt}\nUser: {user_msg}\nAssistant:",
            "stream": False
        }).json()
        return resp.get("response", "")
```

---

## Method 3: Other MCP Clients (Claude Desktop / Cursor / Antigravity)

You can reuse the exact same `mcp_server.py` for any other tool:

### Claude Desktop (`claude_desktop_config.json`) / Cursor:
```json
{
  "mcpServers": {
    "lore-memory": {
      "command": "python",
      "args": ["D:/Projects/LoreMemory/mcp_server.py"]
    }
  }
}
```

---

## Testing the Server Standalone

You can test `mcp_server.py` at any time directly through standard input without connecting any LLM:

```powershell
py -3.13 -m pytest tests/test_mcp_server.py
```
All 4 MCP automated test cases verify handshake initialization, tool registration, memory storage, and query execution.
