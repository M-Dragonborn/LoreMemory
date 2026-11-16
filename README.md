# LoreMemory

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/sqlite-3-green.svg)](https://www.sqlite.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero%20external-orange.svg)](#dependencies)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen.svg)](#testing)

**LoreMemory** is a high-contrast desktop **SQLite Database Management System (DBMS)** paired with an integrated **Mnemosyne-style AI Memory Engine**.

Built entirely on Python's standard library and Tkinter, it provides a fast, zero-dependency environment for browsing databases, running SQL queries, auditing user action history, and managing cognitive memory graphs for LLMs.

---

## Key Features

### 🗄️ Desktop SQLite DBMS
* **Registry-Editor Schema Navigation:** Hierarchical tree view styled like Windows Registry Editor (`🗄️ Database` → `📁 Tables` → `📄 table_name [count]` → nested `🔑` PK, `🔗` FK, `▫` columns) with double/single-click tab activation and idle action nodes.
* **Full-Grid Table Viewer:** Complete 2D spreadsheet-like grid with full-height 1px vertical column boundary dividers (`TreeGrid`) and 1px horizontal row borders:
  * Clear-cut straight thin lines flipped cleanly between Light (`#000000` solid black) and Dark (`#ffffff` solid white) modes.
  * Distinct alternating row contrast (`#f1f5f9` / `#1e293b`).
  * Dynamic column width auto-sizing based on header text and sample data content (50px to 380px).
  * In-place cell editing, pagination, multi-column sorting, and debounced text filtering.
* **High-Performance SQLite Engine:**
  * Configured with WAL journal mode (`PRAGMA journal_mode = WAL`), `synchronous = NORMAL`, 64MB cache (`cache_size = -64000`), in-memory temp store, and 256MB memory-mapped I/O (`mmap_size`).
  * In-memory schema caching (`get_schema_only()`) preventing expensive table scans and delivering instant (< 0.1ms) SQL autocomplete.
  * Fast batch row operations (`delete(*children)`) eliminating Tcl interpreter round-trips.
* **SQL Query Console:** Responsive SQL editor featuring:
  * Debounced syntax highlighting.
  * Instant table and column autocomplete popup.
  * Multi-result grid presentation with dynamic column sizing.
  * One-click query execution plan (`EXPLAIN QUERY PLAN`).
  * Instant export to CSV and JSON.
* **Visual Tools:** Interactive schema diagram visualizer and an integrated SQL scratchpad notebook.

### 🧠 Mnemosyne AI Memory Engine & MCP
* **3-Tier Memory Architecture:**
  * **Working Memory:** Fast transient scratchpad for active context sessions.
  * **Episodic Memory:** Consolidated timeline events and summaries with session clustering.
  * **Semantic Memory:** Synthesized knowledge, entity relationships, and core preferences.
* **Hybrid Retrieval Scoring:**
  $$Score = w_{\text{vec}} \cdot Sim_{\text{vec}} + w_{\text{kw}} \cdot Sim_{\text{BM25}} + w_{\text{imp}} \cdot Imp + w_{\text{rec}} \cdot 2^{-\Delta t / t_{1/2}}$$
* **Automatic Consolidation:** Background scheduling clusters stale working memories into condensed episodic memories.
* **Model Context Protocol (MCP) Server:** Standalone stdio JSON-RPC server (`mcp_server.py`) exposing `recall`, `remember`, `recent`, `consolidate`, and `query_sql` to external LLM agents (e.g. Nous Hermes, Claude, Cursor). See [Hermes MCP Guide](docs/HERMES_MCP_GUIDE.md).

### 🔒 Authentication, Roles & Audit History
* **Cryptographic Security:** Passwords hashed with **PBKDF2-HMAC-SHA256** using 100,000 iterations and per-user 16-byte random salts.
* **Timing-Attack Protection:** Safe authentication comparison via `hmac.compare_digest`.
* **Multi-Tier Role Hierarchy & Admin Panel:** Three-tier RBAC (`super_admin`, `admin`, `user`), account deactivation/activation, password resets, and immutable role audit trail in `role_audit_log`.
* **Execution History Log:** Every query, mutation, and schema alteration is automatically recorded with execution timing, row impact, and associated user IDs.

### 🎨 High-Contrast Minimalist Interface
* Designed for clarity with distinct outlines and high-contrast borders.
* Full-window compatible with responsive centered cards and split panes.
* Balanced symmetrical bottom toolbar with clean user badge and matching action buttons (`Admin`, `Logout`, `Theme`).
* Clean hover and active states (contrast locked to prevent text washouts).
* Fast, smooth, and jitter-free—debounced idle event scheduling and geometry diffing prevent layout thrashing.

---

## Pre-Seeded Accounts

When initialized with sample data, the following local accounts are ready to use:

| User ID | Username | Role | Password |
| :---: | :--- | :--- | :--- |
| **1** | `musfiq` | `super_admin` | `musfiq121` |
| **2** | `rayed` | `admin` | `rayed097` |
| **3** | `anower` | `user` | `anower122` |

---

## Quick Start

### 1. Requirements
* **Python 3.10+** (Python 3.13 recommended)
* Standard library only (Tkinter is included with standard Python on Windows and macOS).

### 2. Launch the Application
Start the desktop GUI in full window:
```bash
python main.py
```

### 3. Generate Sample Database & Memories
To reset or generate sample data (`sample/school.db` and initial memories in `data/memory.db`):
```bash
python make_sample_db.py
```

---

## CLI Usage

LoreMemory includes a command-line interface for interacting with the AI memory engine without opening the GUI:

```bash
# Store a memory
python main.py remember "User prefers dark theme for database queries" -i 0.8

# Retrieve relevant memories via hybrid search
python main.py recall "theme preference" -k 3

# View recent memory records
python main.py recent -k 5

# Inspect pending items awaiting consolidation
python main.py pending

# Run memory consolidation
python main.py consolidate --hours 24

# View memory statistics
python main.py stats
```

---

## Managing User Passwords

To update any user's password from the command line:

```bash
python -c "import auth; auth.change_password_user('musfiq', 'myNewPassword123')"
```

This automatically generates a fresh 16-byte cryptographic salt and computes the new PBKDF2-HMAC-SHA256 hash.

---

## Testing

Run the full automated test suite (35 unit and headless GUI smoke tests):

```bash
pytest tests/
```

All tests run headlessly in under 3 seconds.

---

## Project Structure

```
LoreMemory/
├── auth.py                  # PBKDF2 authentication, RBAC & password hashing
├── cli.py                   # Command-line interface for memory engine
├── config.py                # Global limits, memory weights, and database paths
├── db.py                    # Database connection manager, WAL pragmas & cached schema inspector
├── history.py               # Audit logger tracking query executions per user
├── main.py                  # Application entry point (GUI & CLI router)
├── make_sample_db.py        # Sample school.db & memory graph seeder
├── mcp_server.py            # Model Context Protocol stdio server for LLMs
├── memory.py                # Mnemosyne AI memory engine (working, episodic, semantic)
├── gui/
│   ├── admin_page.py        # User & role administration panel with audit log
│   ├── login.py             # Stylized minimal login & registration card
│   ├── theme.py             # High-contrast color palette, Treeview.Row border & ttk styles
│   ├── main_window.py       # Full-window layout, toolbar, status bar & sidebar
│   ├── sidebar.py           # Regedit-style table tree navigator with symmetrical bottom toolbar
│   ├── tabs.py              # Custom tab strip with real clickable close (×) buttons & instant switching
│   ├── console.py           # SQL editor with debounced syntax highlighting
│   ├── table_page.py        # Full-grid paginated data table with dynamic column sizing & CRUD
│   ├── result_page.py       # Query result grid with full-height dividers & auto-sizing
│   ├── notepad_page.py      # Read-only notepad: HistoryPage and MemoryPage (Ctrl+F)
│   ├── dialogs.py           # Add/Edit row dialogs, New Table dialog, dangerous warnings
│   ├── autocomplete.py      # Context-sensitive SQL autocomplete popup (<0.1ms cached)
│   └── widgets.py           # TreeGrid divider manager & thread-safe background runner
├── data/                    # SQLite databases (users.db, history.db, memory.db)
├── sample/                  # Demo database (school.db)
└── tests/                   # Automated pytest suite (35 tests)
    ├── conftest.py          # Cross-platform Tcl/Tk library path bootstrap
    ├── test_auth.py         # Authentication, salt & RBAC tests
    ├── test_cli.py          # Terminal CLI subcommand tests
    ├── test_db.py           # Database CRUD, transactions, rollback & authorizer tests
    ├── test_gui_smoke.py    # Headless GUI smoke & tab switching tests
    ├── test_history.py      # History logging, multi-user view & table rename tests
    ├── test_mcp_server.py   # MCP stdio JSON-RPC server tests
    └── test_memory.py       # Working/episodic memory, recall abstention & TTL tests
```

---

## Architecture Principles
1. **Zero External Dependencies:** Built with pure Python standard library (`sqlite3`, `tkinter`, `hashlib`, `hmac`). Optional `sentence-transformers` can be installed for dense vector embeddings, with automatic TF-IDF fallback when absent.
2. **Modular File Sizes:** Every source file is kept clean, focused, and strictly $\le 250$ lines.
3. **Auditability:** User actions and SQL statements are tracked and linked per user ID for full observability.

---

## License
MIT License. See [LICENSE](LICENSE) for details.
