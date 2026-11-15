# LoreMemory: System Reference and Developer Guide

This document serves as the comprehensive guide to LoreMemory. When modifying or extending the project in the future, you can consult this reference directly without having to reread the entire source code.

---

## 1. Architecture Overview

LoreMemory is a desktop SQLite database manager in Python (standard library + Tkinter) with a Mnemosyne-style AI memory layer for local LLMs.

The application has two distinct halves:
1. **Manual DBMS Half (User GUI):** Open/create SQLite `.db` files, run SQL with keyword highlighting and autocomplete, browse tables with paging/sorting/search, edit/add/delete rows, manage transactions (manual `Commit` and `Rollback`), and view per-table and database-wide query history across different users.
2. **AI Memory Half (LLM Terminal CLI):** A two-tier memory system (hot working memory and consolidated episodic memory) with recency decay, importance weighting, keyword scoring, optional vector embeddings, and CLI subcommands (`remember`, `recall`, `recent`, `pending`, `episode`, `consolidate`, `importance`, `stats`).

### Key Architecture Rules
- **No SQLite in GUI:** Modules inside `gui/` never import `sqlite3`. They interact solely through `Database`, `HistoryLog`, `Memory`, and `auth`.
- **Parameter Placeholders:** All value substitutions in SQL use parameter placeholders (`?`). String formatting is only used for identifiers (table/column names) properly quoted with double quotes `"{name}"`.
- **Manual Transactions:** The user database connection operates in autocommit mode (`isolation_level=None`). Modifying statements automatically issue `BEGIN` if no transaction is active. Structure changes (`CREATE`, `DROP`, `ALTER`) can be rolled back just like data changes until `Commit` is pressed.
- **Immediate History Logging:** Every executed SQL statement is logged immediately whether it succeeds, fails, or is later rolled back.

---

## 2. File and Directory Layout

```
LoreMemory/
├── main.py                  # Entry point: GUI (no args) or CLI (with args)
├── config.py                # Global constants, paths, weights, and limits
├── auth.py                  # User authentication (PBKDF2 HMAC SHA-256)
├── db.py                    # Database class: connection, execution, query logging
├── history.py               # HistoryLog class: writes and queries history.db
├── memory.py                # Memory class: working and episodic memory engine
├── cli.py                   # Terminal commands used by LLMs
├── make_sample_db.py        # Seed script for sample/school.db and demo memory
├── LOREMEMORY_REFERENCE.md  # This developer reference
├── gui/                     # Tkinter / ttk graphical interface
│   ├── __init__.py          # GUI package marker
│   ├── theme.py             # Light/dark palettes and ttk styling
│   ├── widgets.py           # Thread-safe background runner (queue + root.after)
│   ├── login.py             # LoginWindow modal form
│   ├── main_window.py       # MainWindow 3-pane layout, coordinator, and status bar
│   ├── sidebar.py           # Left navigation: DB menu, table list, theme toggle
│   ├── tabs.py              # Custom tab strip with real clickable close (×) buttons
│   ├── table_page.py        # Table grid tab (paging, sorting, debounced filter, CRUD)
│   ├── result_page.py       # Result tab showing last SELECT query output
│   ├── notepad_page.py      # Read-only notepad: HistoryPage and MemoryPage (Ctrl+F)
│   ├── dialogs.py           # Add/Edit row dialogs, New Table dialog, dangerous warnings
│   └── autocomplete.py      # Context-sensitive SQL autocomplete popup
├── tests/                   # Pytest test suite
│   ├── test_auth.py         # Authentication and hashing tests
│   ├── test_db.py           # Database CRUD, transactions, rollback, authorizer tests
│   ├── test_history.py      # History logging, multi-user view, table rename tests
│   ├── test_memory.py       # Working/episodic memory, recall abstention, TTL tests
│   ├── test_cli.py          # Terminal CLI subcommand tests
│   └── test_gui_smoke.py    # Headless GUI smoke tests
└── data/                    # App data directory (created at runtime)
    ├── users.db             # User accounts and login hashes
    ├── history.db           # Query history and touched tables
    └── memory.db           # Working and episodic AI memories (WAL mode)
```

---

## 3. Database Schemas

### 3.1 `data/users.db`
```sql
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT
);
```

### 3.2 `data/history.db`
```sql
CREATE TABLE IF NOT EXISTS query_history (
    query_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    db_path       TEXT NOT NULL,
    user_id       INTEGER NOT NULL,
    command_type  TEXT,
    sql_text      TEXT NOT NULL,
    executed_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    success       INTEGER NOT NULL CHECK (success IN (0,1)),
    rows_affected INTEGER,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS query_table (
    query_id   INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    PRIMARY KEY (query_id, table_name),
    FOREIGN KEY (query_id) REFERENCES query_history(query_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_db ON query_history (db_path, query_id);
CREATE INDEX IF NOT EXISTS idx_table_name ON query_table (table_name, query_id);
```
*Note:* At startup, `history.db` runs `ATTACH DATABASE ? AS u` pointing to `users.db` to join usernames on `user_id`.

### 3.3 `data/memory.db` (WAL Mode)
```sql
CREATE TABLE IF NOT EXISTS episodic_memory (
    episode_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    summary       TEXT NOT NULL,
    importance    REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    scope         TEXT NOT NULL DEFAULT 'global' CHECK (scope IN ('global','session')),
    source        TEXT,
    embedding     BLOB,
    period_start  TEXT,
    period_end    TEXT,
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed TEXT,
    access_count  INTEGER DEFAULT 0,
    valid_until   TEXT
);

CREATE TABLE IF NOT EXISTS working_memory (
    wm_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id INTEGER,
    session_id TEXT,
    content    TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    embedding  BLOB,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT,
    FOREIGN KEY (episode_id) REFERENCES episodic_memory(episode_id) ON DELETE SET NULL
);
```

---

## 4. Module Specifications & Major Functions

### 4.1 `config.py`
Defines operational constants:
- `BASE_DIR`: Detects `sys.frozen` (for PyInstaller executable) or resolves relative to `__file__`.
- `DATA_DIR`: Directory where app SQLite files reside.
- `USERS_DB`, `HISTORY_DB`, `MEMORY_DB`: Standard paths to internal SQLite files.
- `ROW_LIMIT = 1000`: Maximum rows fetched for interactive queries in the result view.
- `PAGE_SIZE = 100`: Table viewer grid pagination limit.
- `HISTORY_BATCH = 500`: Number of history/memory items loaded per batch.
- `MIN_WINDOW = "1100x700"`: Minimum window dimension.
- Memory scoring weights: `VEC_W = 0.5`, `KW_W = 0.3`, `IMP_W = 0.2`, `RECENCY_W = 0.1`, `HALF_LIFE_HOURS = 168`, `CONSOLIDATE_HOURS = 24`, `MIN_SIM = 0.25`.

---

### 4.2 `auth.py`
Provides password hashing and credential verification:
- `init_users(con)`: Ensures `PRAGMA foreign_keys = ON` and creates the `users` table.
- `hash_password(password, salt_hex)`: Computes PBKDF2 HMAC SHA-256 with 100,000 iterations.
- `register(con, username, password) -> bool`: Inserts a new user with a 16-byte random salt. Fails if user exists or inputs are empty.
- `login(con, username, password) -> int | None`: Validates credentials using `hmac.compare_digest`. Updates `last_login = CURRENT_TIMESTAMP` and returns `user_id` on success.
- `login_user(username, password, path=None)` / `register_user(username, password, path=None)`: Connection-managed convenience wrappers for the GUI.

---

### 4.3 `db.py`
Executes SQL against user databases with thread locking, table detection, and history recording.

#### Class `Result`
Data container returned by execution:
- Attributes: `columns` (list), `rows` (list), `truncated` (bool), `rowcount` (int), `tables` (set of touched table names), `error` (str or None), `elapsed_ms` (float).

#### Class `Database`
- `open(path, create=False) -> bool`: Normalizes path with `os.path.normcase(os.path.realpath(path))`. Opens connection with `isolation_level=None`, `check_same_thread=False`, and `timeout=5.0`. Enables `PRAGMA foreign_keys = ON`.
- `close()`: Safely closes open connection.
- `has_pending`: Property returning `bool(con and con.in_transaction)`.
- `commit()` / `rollback()`: Manually commits or rolls back pending transactions.
- `is_dangerous(sql) -> str | None`: Checks for `DROP` statements or `DELETE`/`UPDATE` without a `WHERE` clause. Returns user-facing warning or `None`.
- `run(sql, params=()) -> Result`:
  1. Issues `BEGIN` if the query is modifying (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `CREATE`, `DROP`, `ALTER`) and no transaction is active.
  2. Installs SQLite authorizer callback to record touched tables.
  3. Executes query, limits rows to `ROW_LIMIT`, measures elapsed time.
  4. Automatically intercepts `ALTER TABLE x RENAME TO y` to call `history.rename_table`.
  5. Immediately records execution in `HistoryLog`.
- `run_script(text) -> list[Result]`: Parses multiple statements across semicolons and runs each through `run()`. Halts execution on the first error.
- `get_tables() -> list[str]`: Returns table names from `sqlite_master` excluding internal `sqlite_%` tables.
- `get_columns(table) -> list[dict]`: Queries `PRAGMA table_info` and `PRAGMA foreign_key_list`. Returns column metadata dicts: `name`, `type`, `notnull`, `default`, `pk`, `fk`.
- `get_table_info() -> list[dict]`: Returns list of dicts with `name`, `columns`, and `row_count` (`SELECT COUNT(*)`). Used for the sidebar and autocomplete.
- `get_rows(table, page, page_size=100, order_by=None, descending=False, search="") -> (cols, rows, total)`: Paginated fetch with search across columns using `LIKE ?`. If table has no primary key, automatically prepends `rowid AS _rowid`. Browsing queries are not logged to history.
- `insert_row(table, data_dict)`: Builds parametrized `INSERT` statement and runs via `run()`.
- `update_row(table, pk_col, pk_val, data_dict)`: Builds parametrized `UPDATE` statement and runs via `run()`.
- `delete_row(table, pk_col, pk_val)`: Builds parametrized `DELETE` statement and runs via `run()`.

---

### 4.4 `history.py`
Shared, database-agnostic query history tracker.

#### Class `HistoryLog`
- `__init__(db_path=None, users_db_path=None)`: Connects to `history.db`, initializes tables/indexes, and runs `ATTACH DATABASE users.db AS u`.
- `record(db_path, user_id, sql, success, rowcount, error, tables) -> query_id`: Inserts row into `query_history` and child entries into `query_table`.
- `rename_table(db_path, old_name, new_name)`: Updates `query_table` records matching `db_path` so historical records follow table renames.
- `for_table(db_path, table, limit=500, offset=0) -> list[tuple]`: Queries history joined with `query_table` and `u.users`.
- `for_database(db_path, limit=500, offset=0) -> list[tuple]`: Queries whole-database history including failed commands (which do not have associated table rows).

---

### 4.5 `memory.py`
Mnemosyne-style two-tier AI memory layer.

#### Class `Memory`
- `remember(text, importance=0.5, session=None, ttl_hours=None) -> int`: Stores raw content in `working_memory`. Computes vector embedding if enabled.
- `recall(query, k=5) -> list[dict]`:
  - Formula: `Score = 0.5 * similarity + 0.3 * keyword + 0.2 * importance + 0.1 * recency`
  - Keyword: Fraction of query terms present in text.
  - Recency: `0.5 ** (age_hours / 168.0)`.
  - Abstention Rule: Memories are omitted unless they match at least one keyword or have cosine similarity $\ge 0.25$.
  - Increments `access_count` and updates `last_accessed` on returned episodic memories.
- `recent(k=10, offset=0) -> list[dict]`: Fetches newest memories across both working and episodic tables.
- `pending(hours=None) -> list[dict]`: Fetches unconsolidated working memories (`episode_id IS NULL`) older than threshold (default 24 hours).
- `save_episode(ids, summary, importance=None) -> int | None`: Consolidates specified working memory IDs into an `episodic_memory` record, setting their `episode_id`. Returns `None` if IDs are already consolidated.
- `consolidate(hours=None) -> int`: Plain automatic consolidation. Groups pending memories by `session_id`, concatenates text up to 1000 characters, creates episodic rows, and links working memories. Returns count of created episodes.
- `set_importance(item_id, value, source="working")`: Adjusts importance (0.0 to 1.0) on working or episodic items.
- `stats() -> dict`: Returns counts of working, unconsolidated, episodes, and embedded rows.

---

### 4.6 `cli.py`
Terminal interface for local LLMs:
- `remember TEXT [-i importance] [-s session] [--ttl hours]` $\rightarrow$ `saved #ID`
- `recall QUERY [-k 5]` $\rightarrow$ Formatted match headers + text or `nothing found`
- `recent [-k 10]` $\rightarrow$ Newest memories
- `pending [--hours N]` $\rightarrow$ Working memories awaiting consolidation
- `episode --ids 1,2,3 --summary TEXT [-i importance]` $\rightarrow$ Creates summary episode
- `consolidate [--hours N]` $\rightarrow$ Auto-consolidates expired working memories
- `importance ID VALUE [--episode]` $\rightarrow$ Updates memory importance
- `stats` $\rightarrow$ Prints item counts

---

### 4.7 GUI Modules (`gui/`)

- **`theme.py`**:
  - `apply(root, mode)`: Configures ttk clam theme with Segoe UI and Consolas fonts. Palettes define background, surface, text, muted, accent (blue), border, and status colors.
- **`widgets.py`**:
  - `run_in_background(root, work, done)`: Executes `work()` in a thread, sends `(result, error)` through a `queue.Queue`, and polls with `root.after` to execute `done()` safely on the main GUI thread.
- **`login.py` (`LoginWindow`)**:
  - Wordmark, Username, Password (masked), Login button, Create account link, and real-time validation error messaging.
- **`main_window.py` (`MainWindow`)**:
  - 3-pane layout (`PanedWindow`), status bar, safe closing/logout prompts (checks running threads and uncommitted transactions).
- **`sidebar.py` (`Sidebar`)**:
  - Database dropdown menu (Open, New, Close), `TABLES` list with live row counts, `+` button for New Table dialog, `‹`/`›` collapse handle (`Ctrl+B`), user label, Logout, and `☾` dark mode toggle.
- **`tabs.py` (`TabStrip`)**:
  - Browser-style tab strip with clickable close `×` buttons. Manages Table, Result, History, and Memory tabs.
- **`table_page.py` (`TablePage`)**:
  - Interactive grid (`Treeview`), 100-row paging, sort column toggle (▲/▼), debounced live filter (300 ms), Add/Edit/Delete row modal buttons, and table history button.
- **`result_page.py` (`ResultPage`)**:
  - Read-only grid displaying SELECT query results with row counts, execution time, and truncation notes.
- **`notepad_page.py` (`NotepadPage`, `HistoryPage`, `MemoryPage`)**:
  - Read-only scrollable console. Auto-loads `HISTORY_BATCH` (500) items with infinite scroll on reach bottom. Features built-in `Ctrl+F` find bar with Next/Previous highlighting.
- **`dialogs.py`**:
  - `RowDialog`: Auto-detects column types for adding/editing records.
  - `NewTableDialog`: Form for table creation (`CREATE TABLE`).
  - `confirm_dangerous`: Confirmation prompt for dangerous SQL.
- **`autocomplete.py` (`AutocompletePopup`)**:
  - Contextual SQL suggestions (keywords, table names after `FROM`/`JOIN`, columns after `table.`). Navigable via `Up`/`Down`, accepted via `Tab`.

---

## 5. Modifying and Extending the Project

### How to Add a New CLI Command
1. In `cli.py`:
   - Add a new subparser in `build_parser()`.
   - Add the handler branch in `run()`.
2. In `tests/test_cli.py`:
   - Add a test verifying output and return code.

### How to Add a New Table Column or Schema Field
1. Update schema definitions in `auth.py`, `history.py`, or `memory.py`.
2. Update corresponding `test_*.py` files.
3. If modifying user database operations, check `db.py` to ensure parameter bindings match.

### How to Add a New GUI Tab
1. Create your page frame class extending `ttk.Frame` (provide `reload()` and `on_close()` methods).
2. In `main_window.py`, extend `open_tab(kind, name)` to instantiate your page and call `self.tabs.add_tab(key, kind, title, page)`.

---

## 6. Testing & Building

### Running Unit Tests
Run pytest from the project root:
```bash
py -3.13 -m pytest tests/
```

### Packaging Windows Standalone Executable
Build with PyInstaller:
```bash
pyinstaller --onefile --clean --name LoreMemory main.py
```
- The output executable is placed in `dist/LoreMemory.exe`.
- Do not use `--noconsole`: `main.py` detects when double-clicked and hides the console window on Windows automatically, while preserving terminal access when invoked with CLI arguments by an LLM.

