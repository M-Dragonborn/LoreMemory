# LoreMemory

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/sqlite-3-green.svg)](https://www.sqlite.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-zero%20external-orange.svg)](#dependencies)
[![Tests](https://img.shields.io/badge/tests-28%20passed-brightgreen.svg)](#testing)

**LoreMemory** is a high-contrast desktop **SQLite Database Management System (DBMS)** paired with an integrated **Mnemosyne-style AI Memory Engine**.

Built entirely on Python's standard library and Tkinter, it provides a fast, zero-dependency environment for browsing databases, running SQL queries, auditing user action history, and managing cognitive memory graphs for LLMs.

---

## Key Features

### 🗄️ Desktop SQLite DBMS
* **Schema Navigation:** Collapsible tree view showing tables, columns, data types, primary keys, and foreign key relationships.
* **Data Grid:** Virtual-paginated table viewer with in-place cell editing, row additions, deletions, sorting, and pagination.
* **SQL Query Console:** Responsive SQL editor featuring:
  * Debounced syntax highlighting.
  * Real-time table and column autocomplete popup.
  * Multi-result grid presentation.
  * One-click query execution plan (`EXPLAIN QUERY PLAN`).
  * Instant export to CSV and JSON.
* **Visual Tools:** Interactive schema diagram visualizer and an integrated SQL scratchpad notebook.

### 🧠 Mnemosyne AI Memory Engine
* **3-Tier Memory Architecture:**
  * **Working Memory:** Fast transient scratchpad for active context sessions.
  * **Episodic Memory:** Consolidated timeline events and summaries with session clustering.
  * **Semantic Memory:** Synthesized knowledge, entity relationships, and core preferences.
* **Hybrid Retrieval Scoring:**
  $$Score = w_{\text{vec}} \cdot Sim_{\text{vec}} + w_{\text{kw}} \cdot Sim_{\text{BM25}} + w_{\text{imp}} \cdot Imp + w_{\text{rec}} \cdot 2^{-\Delta t / t_{1/2}}$$
* **Automatic Consolidation:** Background scheduling clusters stale working memories into condensed episodic memories.

### 🔒 Authentication & Audit History
* **Cryptographic Security:** Passwords hashed with **PBKDF2-HMAC-SHA256** using 100,000 iterations and per-user 16-byte random salts.
* **Timing-Attack Protection:** Safe authentication comparison via `hmac.compare_digest`.
* **Execution History Log:** Every query, mutation, and schema alteration is automatically recorded with execution timing, row impact, and associated user IDs.

### 🎨 High-Contrast Minimalist Interface
* Designed for clarity with distinct outlines and high-contrast borders.
* Full-window compatible with responsive centered cards and split panes.
* Clean hover and active states (contrast locked to prevent text washouts).
* Fast and jitter-free—no animation lag or heavy framework overhead.

---

## Pre-Seeded Accounts

When initialized with sample data, the following local accounts are ready to use:

| User ID | Username | Password |
| :---: | :--- | :--- |
| **1** | `musfiq` | `musfiq121` |
| **2** | `rayed` | `rayed097` |
| **3** | `anower` | `anower122` |

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

Run the full automated test suite (28 unit and headless GUI smoke tests):

```bash
pytest tests/
```

All tests run headlessly in under 2 seconds.

---

## Project Structure

```
LoreMemory/
├── auth.py                  # PBKDF2 authentication & password hashing
├── cli.py                   # Command-line interface for memory engine
├── config.py                # Global limits, memory weights, and database paths
├── db.py                    # Database connection manager & metadata inspector
├── history.py               # Audit logger tracking query executions per user
├── memory.py                # Mnemosyne AI memory engine (working, episodic, semantic)
├── main.py                  # Application entry point (GUI & CLI router)
├── make_sample_db.py        # Sample school.db & memory graph seeder
├── gui/
│   ├── login.py             # Stylized minimal login & registration card
│   ├── theme.py             # High-contrast color palette & ttk styles
│   ├── main_window.py       # Full-window layout, toolbar, status bar & sidebar
│   ├── sidebar.py           # Table tree navigator with collapse handle
│   ├── tabs.py              # Notebook tab manager (data, history, console, memory)
│   ├── console.py           # SQL editor with debounced syntax highlighting
│   ├── table_page.py        # Virtual paginated data grid with inline editing
│   ├── history_page.py      # User query execution audit log viewer
│   ├── memory_page.py       # Visual memory explorer & consolidation inspector
│   ├── schema_page.py       # Interactive canvas schema diagram
│   ├── notepad_page.py      # SQL scratchpad notepad
│   └── dialogs.py           # Table creation & column editor dialogs
├── data/                    # SQLite databases (users.db, history.db, memory.db)
├── sample/                  # Demo database (school.db)
└── tests/                   # Automated pytest suite
```

---

## Architecture Principles
1. **Zero External Dependencies:** Built with pure Python standard library (`sqlite3`, `tkinter`, `hashlib`, `hmac`). Optional `sentence-transformers` can be installed for dense vector embeddings, with automatic TF-IDF fallback when absent.
2. **Modular File Sizes:** Every source file is kept clean, focused, and strictly $\le 250$ lines.
3. **Auditability:** User actions and SQL statements are tracked and linked per user ID for full observability.

---

## License
MIT License. See [LICENSE](LICENSE) for details.
