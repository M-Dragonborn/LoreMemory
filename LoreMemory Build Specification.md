# LoreMemory: Build Specification

*A desktop SQLite database manager in Python and Tkinter, with a Mnemosyne-style AI memory layer. This document is the source of truth for generating the core program.*

## 1. Instructions for the code-generating LLM

Read the whole document first. Then generate the files listed in section 4, one module at a time, in the order given in section 11. Also follow the working rules in section 14 and use the packaging, threading and data rules in section 15.

- Output every file in full. No placeholders, no TODO stubs, no ellipses.
- Python 3.10 or newer. Standard library only for everything in sections 1 to 7. The only optional third-party package is sentence-transformers (embeddings, section 8), and the app must run fully without it.
- The code will be proofread by beginners. Keep every file under about 250 lines and every function short. Write plain, human-style Python: simple names, few and short comments (only where something is not obvious), and no docstring or type hints on every function. Small shortcuts are fine as long as the code stays easy to read.
- Do not add features, tables, columns or dependencies that are not in this document. If something is unclear, pick the simplest option and note it in a comment.
- Every database call must use parameter placeholders (?) for values. Never build SQL for values by string formatting.
- After each file, list in two lines what it does and how to run its tests.

## 2. Project summary

LoreMemory is a local desktop application with two halves.

- **Manual half (DBMS):** open or create SQLite .db files, run any SQL, browse tables and columns, edit rows, commit or roll back, and see a shared history of every command run per table and per database.
- **AI half (memory):** a Mnemosyne-style long-term memory of every conversation with a local LLM, kept across all sessions and time, with importance values and timestamps, plus terminal commands that the LLM uses to read and write that memory.

The app is not a web app. It needs no server and no account on the internet. The whole project is one program (one exe) with two sides: the GUI, which the user works in (started with no arguments), and terminal commands, which the LLM that uses the memory works in (started with arguments, see 6.6). The app never calls an LLM itself. It has a local login screen so that history can show who ran each command.

## 3. Priorities

1. The per-table command history and the LLM memory with its terminal commands. These are the main features and must work reliably.
2. The manual DBMS half: open a database, run SQL, browse and edit tables, Commit and Rollback.
3. Login.
4. GUI polish: dark mode, autocomplete and the New Table dialog, built only after everything above works.
5. Embeddings: the lowest priority. They may be slow. They must never crash or block the app, and the memory must still work without them.

## 4. Project layout

```
loremory/
  main.py              no arguments: login and GUI. with arguments: terminal commands (cli.py)
  config.py            constants (paths, limits, memory weights)
  auth.py              register, login and role-based access control (RBAC)
  db.py                Database class: WAL tuning, cached schema, authorizer, execution
  history.py           HistoryLog class: writes and reads history.db
  memory.py            Memory class: working and episodic memory
  mcp_server.py        stdio JSON-RPC server implementing Model Context Protocol for LLMs
  cli.py               terminal commands the LLM uses for memory
  make_sample_db.py    builds sample/school.db for demos
  gui/
    login.py           LoginWindow
    main_window.py     MainWindow: three panes, menu, status bar
    console.py         right-hand console: output, editor, button area
    sidebar.py         left navigation pane: hierarchical database tree, tables, symmetrical toolbar
    table_page.py      middle tab for one table: 2D grid, dynamic column sizing, paging, sort, filter, CRUD
    result_page.py     middle tab that shows the last SELECT result with full-height grid dividers
    tabs.py            tab strip for the middle area, with close buttons and instant switching
    dialogs.py         add or edit row form, new table form, dangerous warning prompt
    notepad_page.py    read-only notepad pages: command history and memory
    admin_page.py      user administration, role modification, account status, role audit log
    autocomplete.py    fast context-sensitive SQL popup (<0.1ms via cached schema)
    theme.py           light and dark palettes, Treeview.Row 1px border, gridline colors
    widgets.py         TreeGrid 2D vertical divider overlay, debounced geometry sync, thread helper
  tests/
    conftest.py        cross-platform Tcl/Tk library path bootstrap
    test_auth.py       authentication, salt hashing, role changes, audit log
    test_db.py         CRUD, authorizer table logging, WAL pragmas, schema cache
    test_history.py    history logging, table rename propagation, multi-user view
    test_memory.py     working/episodic memory, abstention rules, consolidation
    test_mcp_server.py MCP JSON-RPC protocol handshake, tool list, tool executions
    test_cli.py        terminal subcommands, session env tags, return codes
    test_gui_smoke.py  headless GUI window creation, TreeGrid, instant tab switching
  data/                created at runtime: users.db, history.db, memory.db
```

Rule: the gui folder never imports sqlite3. It only calls auth, db, history and memory.

## 5. Data stores and schemas

The app owns three SQLite files in data/. The user's own database files are never given any LoreMemory tables. Every connection to an app file must run `PRAGMA foreign_keys = ON` right after connecting (SQLite does not enforce foreign keys otherwise). Timestamps are stored as UTC text from CURRENT_TIMESTAMP.

### 5.1 users.db (login & RBAC)

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('super_admin', 'admin', 'user')),
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS role_audit_log (
    audit_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    target_user     TEXT NOT NULL,
    old_role        TEXT NOT NULL,
    new_role        TEXT NOT NULL,
    changed_by_user TEXT NOT NULL,
    changed_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason          TEXT
);
```

The first registered user is automatically assigned `super_admin`. Subsequent users receive `user`. Only `super_admin` and `admin` roles have access to user management in the Admin panel. Deactivating or demoting the last `super_admin` is disallowed. Role modifications are permanently logged to `role_audit_log`.

### 5.2 history.db (manual half: command log)

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
```

One query\_history row per command. One query\_table row per table the command touched, so a JOIN across two tables gives two rows. The table name is plain text because user tables live in other files. user\_id points to users.db logically; SQLite cannot enforce a key across files. Also create two indexes so history stays fast with thousands of commands: CREATE INDEX IF NOT EXISTS idx\_history\_db ON query\_history (db\_path, query\_id) and CREATE INDEX IF NOT EXISTS idx\_table\_name ON query\_table (table\_name, query\_id).

### 5.3 memory.db (AI half: Mnemosyne-style memory)

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

One episode summarizes many working memories (1 to N). A working memory with episode\_id NULL has not been consolidated yet. Memory is shared by the whole installation and is not tied to a user account (see section 13). Open memory.db in WAL mode (PRAGMA journal\_mode = WAL), because the GUI and the terminal commands can use it at the same time.

## 6. Module contracts

### 6.1 config.py

Constants only: DATA\_DIR, file names of the three app databases, ROW\_LIMIT = 1000, PAGE\_SIZE = 100 (rows per page in the table grid), HISTORY\_BATCH = 500 (entries loaded at a time on the notepad pages), MIN\_WINDOW = 1100x700, and the memory settings in section 8 (VEC\_W 0.5, KW\_W 0.3, IMP\_W 0.2, RECENCY\_W 0.1, HALF\_LIFE\_HOURS 168, CONSOLIDATE\_HOURS 24, MIN\_SIM 0.25). There is no LLM address, because the app never calls an LLM.

### 6.2 auth.py

- `init_users(con)`: create the `users` and `role_audit_log` tables with foreign keys enabled.
- `register(con, username, password) -> bool`: False if the username exists or either field is empty. Automatically assigns the `super_admin` role to the first user created, and `user` to all subsequent accounts.
- `login(con, username, password) -> int | None`: returns user_id on success if `is_active == 1`, updates last_login, returns None otherwise.
- Hash with hashlib.pbkdf2_hmac using sha256, 100000 rounds and a random 16-byte salt stored as hex. Compare with hmac.compare_digest. Never store a plain password.
- RBAC methods: `get_user_role(con, username)`, `change_user_role(con, target_user, new_role, changed_by_user, reason)`, `set_active(con, username, is_active)`, `list_users(con)`, `list_role_audit(con, limit)`, and `change_password(con, username, new_password)`. Guard against demoting or deactivating the last remaining `super_admin`.

### 6.3 db.py: class Database

The only module that executes SQL against a user's database. It receives a HistoryLog and the current user_id, and logs every command itself.

- `open(path, create=False)` and `close()`. Normalize the path with os.path.normcase(os.path.realpath(path)) and use that form everywhere, including in history. Open the connection with isolation_level=None, so the app controls transactions itself (see the transaction rule below), and connect with timeout=5 so a locked file waits a few seconds before the readable error database is locked is shown.
- Tuning PRAGMAs at open: `journal_mode = WAL`, `synchronous = NORMAL`, `cache_size = -64000` (64MB page cache), `temp_store = MEMORY`, and `mmap_size = 268435456` (256MB memory mapping).
- Schema caching: maintains `_schema_cache` for instant lookup; invalidates on DDL; provides `get_schema_only()` for fast autocomplete (<0.1ms) without executing full-table row counts.
- `run(sql, params=()) -> Result`. Result is a small plain class with these attributes: columns, rows (at most ROW_LIMIT, using fetchmany), truncated (bool), rowcount, tables (set of names), error (text or None), elapsed_ms (how long the command took).
- Finding the tables a command touched: before executing, set a connection authorizer with con.set_authorizer(callback). The callback receives (action, arg1, arg2, dbname, source). For the actions SQLITE_READ, SQLITE_INSERT, SQLITE_UPDATE, SQLITE_DELETE, SQLITE_CREATE_TABLE and SQLITE_DROP_TABLE, add arg1 (the table name) to the set. For SQLITE_ALTER_TABLE, SQLITE_CREATE_INDEX and SQLITE_DROP_INDEX, add arg2 instead, because for those actions arg1 is the database name or the index name (for ALTER, arg1 is main, not the table). Skip empty names and names that start with sqlite_, then return sqlite3.SQLITE_OK. A new table's CREATE TABLE is therefore tagged with that table, so every table's history starts with its CREATE. After a successful ALTER TABLE x RENAME TO y (not RENAME COLUMN), call history.rename_table(db_path, x, y) so the history follows the new name. Find x and y with a regular expression on the command text, and allow the names to be quoted. Always clear the authorizer afterwards in a finally block.
- A syntax error never reaches the point where tables are known, so the failed command has no table rows. That is accepted: it appears only on the database-wide history page.
- `run` catches sqlite3.Error and returns it in Result.error. It never raises to the GUI. Transaction rule: before running INSERT, UPDATE, DELETE, REPLACE, CREATE, DROP or ALTER, run issues BEGIN if no transaction is open yet. SELECT, PRAGMA, VACUUM, ATTACH, DETACH and the transaction commands themselves get no automatic BEGIN. With this rule, structure changes (CREATE, DROP, ALTER) can be rolled back like row changes, until the user presses Commit.
- `run_script(text) -> list[Result]`: split the text into single statements using sqlite3.complete_statement and run each through `run`. Do not use executescript, because it commits silently and cannot report tables per statement.
- `get_tables()`, `get_columns(table)`: use PRAGMA table_info and PRAGMA foreign_key_list. Each column reports name, type, not-null, default, primary key flag and the foreign key target if any. Quote table names in PRAGMA calls.
- `insert_row`, `update_row`, `delete_row`: build parametrized SQL, execute through `run`, and log a readable version of the command.
- `commit()`, `rollback()`, and the property `has_pending` (connection.in_transaction).
- `is_dangerous(sql) -> str | None`: returns a warning text for DROP statements, and for DELETE or UPDATE statements that have no WHERE clause. The GUI must ask the user to confirm before running such a command, and the message says the change can be undone with Rollback until Commit.

Logging rule: every command is logged immediately, whether it succeeds or fails, and whether it is later rolled back. History is a record of what was run.

### 6.4 history.py: class HistoryLog

- Opens history.db with foreign keys on, creates the tables, and runs `ATTACH DATABASE` for users.db as `u` once at start-up (ATTACH fails inside an open transaction, so do it first and commit after every write).
- `record(db_path, user_id, sql, success, rowcount, error, tables)`: insert one query\_history row and one query\_table row per table, then commit. Also rename\_table(db\_path, old, new): change table\_name from old to new in the query\_table rows whose query belongs to that db\_path, so a renamed table keeps its history.
- `for_table(db_path, table, limit=500, offset=0)`: join query\_history, query\_table and u.users with a LEFT JOIN. Return executed\_at, username, command\_type, sql\_text, success, error\_message, newest first. The offset lets the GUI load the next batch of entries.
- `for_database(db_path, limit=500, offset=0)`: the same without the table filter and without the query\_table join, so failed commands are included.
- Visibility rule: history is shared. Anyone who can open a database file in the app can see all history for it, regardless of who ran each command.

### 6.5 memory.py: class Memory

See section 8 for the behavior. The terminal commands in 6.6 and the GUI Memory page both call these methods. Public methods:

- `remember(text, importance=0.5, session=None, ttl_hours=None)`: returns the new id
- `recall(query, k=5)`: a list of dicts with source, id, text, importance, created, session (the session label, empty for episodes) and score
- `recent(k=10, offset=0)`: the newest memories, same dict shape. The offset lets the Memory page load older batches
- `pending(hours=None)`: unconsolidated working memories older than the cutoff
- `save_episode(ids, summary, importance=None)`: one episode for those working memories, with a summary the caller supplies. Importance defaults to the highest among them. Returns the episode id, or None if none of the ids is still unconsolidated
- `consolidate(hours=None)`: the plain automatic version, one episode per session. Returns the number of episodes created
- `set_importance(item_id, value, source='working')`: source is working or episodic
- `stats()`: counts of working memories, unconsolidated ones, episodes and rows with embeddings

### 6.6 cli.py: terminal commands for the LLM

- Entry point: main.py with no arguments starts the GUI. With any arguments it passes them to cli.run(argv) and exits with its return code. The LLM that uses the memory works only through these commands, because it has a terminal. The app never calls an LLM. Use argparse from the standard library. Output is plain text that is easy for an LLM to read.
- `remember TEXT [-i importance] [-s session] [--ttl hours]`: save a working memory and print `saved #ID`. The session defaults to the LOREMEMORY\_SESSION environment variable, else terminal.
- `recall QUERY [-k 5]`: print the best matches, each as a header line with source, id, importance, time and score, then the text on the next line. Print `nothing found` when nothing qualifies.
- `recent [-k 10]`: the newest memories, same format.
- `pending [--hours N]`: working memories not yet summarized and older than N hours (default CONSOLIDATE\_HOURS).
- `episode --ids 1,2,3 --summary TEXT [-i importance]`: save a summary written by the LLM itself as one episode and link those working memories to it.
- `consolidate [--hours N]`: the plain automatic version (section 8). Prints how many episodes were created.
- `importance ID VALUE [--episode]`: set importance from 0 to 1 on a working memory, or on an episode with --episode.
- `stats`: counts of working memories, unconsolidated ones, episodes and rows with embeddings.

### 6.7 mcp_server.py: Model Context Protocol (MCP) Server for LLMs

- Standard stdio JSON-RPC 2.0 transport implementing the Model Context Protocol (MCP).
- Invoked via `python mcp_server.py` or configured inside desktop AI clients (such as Claude Desktop or Cursor).
- Tools exposed to LLMs:
  - `recall`: Hybrid retrieval from episodic and working memory.
  - `remember`: Save new working memory items with importance and optional session tags.
  - `recent`: Retrieve newest memories across both tiers.
  - `consolidate`: Fold pending working memories into summarized episodes.
  - `query_sql`: Execute arbitrary SQL commands with safety checks and automatic audit logging.

## 7. Behavior rules

- The user's connection keeps its transaction open until the user presses Commit or Rollback. Do not commit after each command. The same holds for CREATE, DROP and ALTER: they stay undoable until Commit (see 6.3). When closing a database or logging out with pending changes, ask the user to commit, roll back or cancel.
- The history connection is separate and commits after each record, so logging never interferes with the user's transaction.
- Results show at most ROW\_LIMIT rows. If more exist, show a note that the result is truncated.
- Long operations (embeddings, consolidation, large queries) run in a background thread and post results to the GUI through a queue that the main thread polls with root.after, so the window never freezes.
- Wrong password, SQL errors and missing files must all produce readable messages, never a traceback. A bad terminal command prints a short message and exits with a non-zero code.

## 8. AI memory design (Mnemosyne reference)

Reference project: https://github.com/mnemosyne-oss/mnemosyne (MIT license). It is a local-first, SQLite-backed memory layer built around two tiers: a working memory for hot context and an episodic memory for long-term storage, with a consolidation step that folds old working items into summaries. LoreMemory borrows the ideas only, in a much smaller form. Do not copy its code. If any of its code is ever copied, the MIT notice must be kept and the use disclosed. Credit the project in the README and the report.

Ideas borrowed:

- **Two tiers.** Raw items go to working\_memory. Consolidation turns old unconsolidated items into one episodic\_memory row and sets their episode\_id.
- **Importance.** A number from 0 to 1 on every item. Default 0.5. An item can be marked important (1.0) with the importance terminal command.
- **Scope.** global means visible in every future conversation. session means only that conversation. Default global for episodes.
- **Expiry.** Optional expires\_at on working items (ttl\_hours) and valid\_until on episodes. Expired rows are ignored by recall.
- **Recall scoring.** Mnemosyne weights vector similarity 50 percent, keyword rank 30 percent and importance 20 percent, with a recency half-life of 168 hours. Use the same weights from config.py:
  - similarity: cosine similarity of embeddings, or 0 if either side has no embedding
  - keyword: fraction of the query's words found in the content (simple substitute for full-text rank)
  - recency: 0.5 \*\* (age\_in\_hours / HALF\_LIFE\_HOURS), added as a small bonus of 0.1 times recency
  - final score = 0.5 \* similarity + 0.3 \* keyword + 0.2 \* importance + 0.1 \* recency
- **Abstention.** A memory is only returned if it shares at least one keyword with the query or its similarity is at least MIN\_SIM; if nothing qualifies, return an empty list. Do not invent memories.

Search both tables in recall. Return dicts with source (working or episodic), id, text (the content or the summary), importance, created, session (empty for episodes) and score. Update last\_accessed and access\_count on episodic rows that are returned.

**Embeddings (optional, lowest priority).** Use sentence-transformers with the model all-MiniLM-L6-v2, loaded lazily on first use. Store vectors as float32 bytes in the embedding BLOB. Wrap every embedding call in try/except for ImportError, OSError, RuntimeError and ValueError. On failure store the row with embedding NULL and continue. If sentence-transformers is not installed, recall uses the keyword and importance parts only. The app must work and pass its tests with no embedding model present.

**Consolidation.** Take working rows with episode\_id NULL older than CONSOLIDATE\_HOURS, group them by session\_id, join the texts of each group into one summary of at most 1000 characters (the plain version needs no LLM), and insert one episodic row per group: importance is the highest importance in the group, period\_start and period\_end are the earliest and latest created\_at, source is consolidation. Then set episode\_id on the source rows. Run it only through the consolidate command in the terminal (there is no consolidate button in the GUI). An LLM can write a better summary: it runs pending, writes the summary itself, and saves it with the episode command, which does the same insert and linking.

**LLM flow (terminal).** The app never calls an LLM. An LLM agent with terminal access first runs recall with the user's message and uses the results as background, then after answering runs remember for anything worth keeping, with importance 0.5 by default and higher for things the user says matter. The session label comes from the LOREMEMORY\_SESSION environment variable (default terminal).

## 9. GUI specification (Tkinter with ttk)

### 9.1 Principles

The GUI is for the user. It must stay minimal and clean, because it is shown to a non-technical audience, and fewer screens means fewer things that can break.

- One accent color (blue), used only for the selected item and the Run button. Everything else is grey on white, or the dark equivalent.
- Whitespace and one thin separator line between panes. No boxes inside boxes.
- Two button styles only: a filled one (Run) and plain flat ones.
- One font (Segoe UI) in regular and bold, muted grey for secondary text, and a monospace font (Consolas) for SQL and memory text.
- No icons. Only the small glyphs ‹ › × ▾ ▲ ▼ and ☾.
- The history pages and the memory page are read-only.
- Nothing in gui/ runs SQL itself. Pages reach the database only through the main window (see 9.10).
- Implementation: ttk with the clam base theme and one palette dict each for light and dark (background, surface, text, muted text, accent, border, danger, success) in gui/theme.py, with apply(root, mode). Style Treeview, buttons, entries and the tk.Text widgets from the palette. Only built-in Tkinter and ttk. No third-party theme packages.

### 9.2 Login window

A small, plain window. The wordmark LoreMemory as text (no image file), a Username box, a Password box (masked), a Login button and a Create account link that registers the typed username and password. An error line under the boxes shows one of: Enter a username and a password; Wrong username or password; That username already exists. Enter submits the form. On success the login window closes and the main window opens with the user\_id and username.

### 9.3 Main window layout

Three panes side by side, separated by thin draggable dividers (ttk.PanedWindow): the navigation pane on the left, the tabbed middle area, and the console on the right. They start at roughly 2 : 5 : 3 of the window width, and the console keeps at least 300 px. Minimum window size 1100 by 700, centered, titled LoreMemory. A thin status bar at the bottom shows the logged-in user, the open file name, the row count of the active table and how long the last command took in milliseconds.

### 9.4 Navigation pane (left)

- Top: the open database's file name in bold with a ▾ that opens a small menu: Open database, New database, Close database.
- Registry Editor style hierarchy: under the header, an interactive Treeview displays Databases in bold, Tables in regular weight, and expandable columns with branch icons (`▾` / `▸`). Live row counts are shown next to each table. A small + next to the header opens the New Table dialog.
- Symmetrical bottom toolbar:
  - User identity row: `👤 <username>` on the left with `[ ROLE ]` pill badge on the right (`SUPER_ADMIN`, `ADMIN`, `USER`).
  - Symmetrical 3-button action grid: `[ ⚙ Admin ]`, `[ ⎋ Logout ]`, and `[ ☾ / ☀ ]` sharing equal height, padding, and 1px borders.
- A small ‹ handle on the pane's edge collapses it, and Ctrl+B does the same. The middle area takes the freed width, and a › handle brings the pane back.
- Clicking a table opens it in a tab in the middle area, or switches to its tab if it is already open. Redundant clicks on the currently active table are debounced without re-querying the database.
- The list reloads after any command that changes data or structure, so counts and new or dropped tables are always current.

### 9.5 Middle area: tabs

A row of small tab labels with a × on each, like a browser. Build the strip from labels and a stack of frames raised with tkraise, not with ttk.Notebook, so that the × is a real clickable widget (tabs.py). There are five kinds of tab:

- **Table tab**, one per open table (9.6).
- **Result tab**, only one. It shows the last SELECT result, and every new SELECT replaces what it shows. It uses the same grid as the table page, read-only, with no paging (at most ROW_LIMIT rows).
- **History tab**, titled History: students (9.8).
- **Memory tab**, only one (9.8).
- **Admin tab**, opened via the Admin button in the sidebar (9.13).

Instant tab switching: clicking a tab calls `select()` to raise the page frame without re-querying the database, eliminating switching stutter. Closing a table tab also closes its history tab. If a table is dropped, its tab and its history tab close. If a table is renamed, both take the new name. When nothing is open, the area shows a muted hint: Open a table from the left.

### 9.6 Table page

- A 2D grid (`TreeGrid` in `gui/widgets.py` wrapping `ttk.Treeview`) featuring 1px horizontal row borders (`Treeview.Row` `bordercolor`) and dynamic full-height vertical dividers (`ttk.Separator`, `relheight=1.0`). Line colors flip between clear-cut straight black (`#000000`) and white (`#ffffff`).
- Dynamic column auto-sizing: column widths are calculated from the max text width of the header and first 15 sample rows using cached font measurement (clamped between 50px and 380px).
- Debounced geometry updates: geometry adjustments are scheduled via `root.after_idle` to prevent layout thrashing and jitter during resizing.
- 100 rows per page, Previous and Next buttons, and a label such as Page 2 of 7 (640 rows).
- Clicking a column header sorts by it, and clicking again reverses the order (▲ or ▼ next to the name).
- A filter box above the grid filters the rows live across all columns, waiting about 300 ms after typing stops.
- Buttons: Add Row, Edit Selected, Delete Selected. Add and Edit open a modal form with one field per column, chosen by the declared type (integer entry, number entry, text entry; BLOB columns are skipped). A blank field on insert lets the default apply. A blank field on edit stores NULL, or shows an error if the column is not null. Delete asks for confirmation. Batch row deletion (`delete(*children)`) prevents GUI freezes during large refreshes. All three go through Database.run and are logged, and afterwards the page, the table list counts and the pending indicator refresh.
- Browsing (paging, sorting, filtering) is not logged.
- At the bottom of the page an Open table history button opens the History tab for this table (9.8).
- Column names and types are visible in the grid headers. There is no separate structure view: structure is changed from the console.

### 9.7 Console (right pane)

From top to bottom:

- **Output area:** read-only text. It shows each command that was run, then one grey outcome line, and errors in red. It starts empty every time the user logs in, like a terminal in VS Code. History is the permanent record.
- **Editor:** a multi-line input in the monospace font. Keywords are highlighted in the accent color: SELECT, FROM, WHERE, INSERT, INTO, VALUES, UPDATE, SET, DELETE, DROP, CREATE, ALTER, TABLE, JOIN, ON, ORDER, BY, GROUP, LIMIT, AND, OR, NOT, NULL, PRIMARY, KEY. Case-insensitive, refreshed after each key release.
- **Button area:** the bottom quarter of the console, with a draggable divider above it. It holds a pending-changes line (Uncommitted changes or No pending changes), then the buttons Run (filled), Commit and Rollback, and below them Table history, Memory, Copy last command and Clear (Clear empties the output area, not the editor).

Keys and behavior:

- Ctrl+Enter runs. Enter adds a new line. If text is selected, only the selection runs.
- The Up and Down arrows recall earlier commands from this login when the cursor is on the first or last line of the editor. Ctrl+Up and Ctrl+Down always recall.
- After a successful run the editor clears. After an error it keeps the text so it can be fixed.
- Several statements run one after another through Database.run\_script and stop at the first error. The console prints one outcome line per statement.
- Outcome lines: a SELECT prints a line such as 6 rows, 0.9 ms (plus a note that the result was cut at 1000 rows when it is truncated), and its full grid opens in the Result tab. INSERT, UPDATE and DELETE print 1 row affected. CREATE, DROP and ALTER print OK. Every line ends with the time in ms.
- Before running a dangerous command (is\_dangerous) the app asks for confirmation. The message says the change can be undone with Rollback until Commit.
- Commit and Rollback call Database.commit and Database.rollback. The pending line and the status bar update straight away.
- Table history opens the History tab of the active table. If the active tab is not a table (the Result tab, the Memory tab, or none) it opens the whole-database history instead. Memory opens the Memory tab. Copy last command puts the text of the last command on the clipboard.
- Closing the window, choosing Exit or logging out always asks first when anything is going on. If a command or other background work is still running, a prompt says Something is still running. Close anyway? with Yes and No. On Yes the app waits for the running command to finish and then goes on to the next check. If there are uncommitted changes, a second prompt asks to commit, roll back or cancel. With nothing running and nothing uncommitted, the window closes without a prompt.

### 9.8 Notepad pages (history and memory)

One shared read-only component, gui/notepad\_page.py, is used for both pages. It is a text area that the user can select and copy from but not edit. The newest entry comes first, and each entry is a small grey header line, then the text, then a blank line. It first loads HISTORY\_BATCH (500) entries and loads the next batch automatically when the user scrolls to the bottom. Ctrl+F opens a find bar (matches highlighted, Next and Previous). It is built last, and the pages work without it because the user can simply scroll.

- **History tab:** titled History: students, with a back arrow ‹ at the top left that closes the tab and returns to that table's tab exactly as it was (same page, sort and filter). A history tab opened for the whole database returns to the tab that was active before it. A line at the top reads Showing students, with a link to switch to the whole database. Each entry header shows the time (UTC), the user, the command type and OK or FAILED, and the entry text is the SQL. A failed command also shows its error in red. It lists the commands of every user, because history is shared. The oldest entry of a table's history is the CREATE command that made it, when the table was created inside the app. A table that already existed in an opened file starts with the first command run on it in the app. Every table gets its own history automatically, because a table's history is a filter on the command log, so nothing has to be set up when a table is created.
- **Memory tab:** one page with the LLM's memories, newest first (Memory.recent with an offset). Each entry header shows the date, the importance and the session, plus the word summary for episodes, and the entry text is the memory itself. It reloads every time the tab is selected, because the LLM adds memories from the terminal while the app is open. It is read-only: no search box, no mark-important button and no consolidate button (the terminal commands do those).

### 9.9 Build order for the GUI

Each step must run before the next one starts.

1. theme.py and widgets.py (colors, fonts, the background-thread helper).
2. The login window.
3. The main window: three panes, status bar, empty tab strip.
4. The navigation pane with the table list.
5. The tab strip and the Table page.
6. The console: editor, Run, outcome lines, Commit and Rollback.
7. The Result tab.
8. notepad\_page.py, the History tab and both Table history buttons.
9. The Memory tab and the Memory button.
10. Last, in this order, and only after everything above works: autocomplete, dark mode, the New Table dialog, Ctrl+F.

### 9.10 Contract between the main window and its pages

- The main window owns db (the Database), history, memory, user\_id, username, active\_table, and the helper run\_in\_background(work, done), which runs work() in a thread and calls done(value, error) on the GUI thread.
- It offers open\_tab(kind, name) (kind is table, result, history or memory), close\_tab(tab), refresh\_tables() (re-reads the table list and counts; call it after any command that changed anything) and update\_pending() (refreshes the pending indicators).
- Every page class has a title, reload() and on\_close(). A Table page is created with (app, table\_name).
- Pages reach the database only through app.db, app.history and app.memory. Background threads never touch widgets.

### 9.11 Autocomplete (built last)

- The names come from Database.get\_table\_info when a database opens and are refreshed after any structure change, so typing never queries the database.
- A small popup appears under the cursor after two typed letters, or with Ctrl+Space. Matching is case-insensitive from the start of the word.
- After FROM, JOIN, INTO, UPDATE or TABLE it offers only tables. After a name followed by a dot (a table name or an alias) it offers only that table's columns. Elsewhere it offers keywords, tables and columns. Each suggestion has a small label: table, column or keyword.
- Up and Down move through the list, Tab accepts, Esc closes. Enter closes the popup and adds a new line. Keywords are inserted in uppercase.
- The code goes in gui/autocomplete.py.

### 9.12 Click-through test checklist

Do these by hand after each build step, because pytest cannot check windows.

- Login: empty fields, wrong password, duplicate username, the Enter key.
- Open the sample database: the tables and counts appear. Open a table: sort, filter, page, add, edit and delete a row, and watch the counts change.
- Console: Ctrl+Enter runs, Enter adds a line, Up recalls, a SELECT prints one line and fills the Result tab, a bad command shows red text and keeps the text, a DROP asks for confirmation, Rollback brings the table back, Commit makes it permanent, and closing with uncommitted changes asks.
- History: a new table's history starts with its CREATE, commands from two different users both appear, a failed command appears only in the whole-database view, scrolling loads older entries, and the back arrow returns to the same table page.
- Memory: run LoreMemory.exe remember with some text in a terminal, open the Memory tab, and the new memory is there.
- Layout: collapse the navigation pane with the handle and with Ctrl+B, close tabs with the ×, resize the window, and close the window while a query is running (it must ask first) and with uncommitted changes (it must ask to commit, roll back or cancel).

### 9.13 Admin page (gui/admin_page.py)

Accessible to `super_admin` and `admin` roles via the symmetrical Admin button in the bottom-left sidebar toolbar:
- User table: displays username, role, active status, creation timestamp, and last login.
- Action controls: role change dropdown (`super_admin`, `admin`, `user`), account activate/deactivate toggle, and password change modal.
- Safety guards: prohibits demoting or deactivating the last remaining `super_admin`.
- Role audit trail: displays chronological events from `role_audit_log` (target user, old role, new role, changed by, timestamp, reason).

## 10. Tests (pytest)

The test suite contains 35 passing automated tests across 7 test modules:

- **test_auth:** register works, duplicate username fails, correct password logs in, wrong password and unknown user return None, no plain password is stored; first user gets `super_admin`; role changes, audit logging, and account deactivation are verified; demoting or deactivating the last `super_admin` is rejected.
- **test_db:** run a SELECT, INSERT, UPDATE, CREATE and DROP in a temporary database; the tables set is right for a JOIN; a syntax error returns Result.error and does not raise; rollback undoes an uncommitted insert, a DROP TABLE and an ALTER TABLE; ALTER TABLE, CREATE INDEX and DROP INDEX are tagged with the right table; get_rows paging, sorting and search work; get_table_info returns row counts; foreign keys are enforced on the user's database; the 1000-row limit sets truncated; is_dangerous flags DROP and DELETE without WHERE only; WAL pragmas and schema caching are verified.
- **test_history:** a JOIN logs two table rows, the history for a table includes commands from two different users, a failed command appears in the database-wide view but not in a table view, a new table's history starts with its CREATE command, renaming a table moves its history to the new name, and the offset returns the next batch of entries.
- **test_memory:** foreign key rejects a working memory pointing at a missing episode, consolidation sets episode_id and creates one episode, deleting an episode sets episode_id back to NULL, recall returns an empty list when nothing matches, save_episode links the given working memories to one episode and refuses ones already consolidated, an expired memory is never recalled, and everything passes with embeddings disabled.
- **test_cli:** terminal commands (memory file in a temporary folder, embeddings off) runs remember, recall and stats through cli.run and checks the output and the exit codes.
- **test_mcp_server:** tests Model Context Protocol stdio JSON-RPC initialization handshake, tool enumeration, and tool execution (`recall`, `remember`, `recent`, `consolidate`, `query_sql`).
- **test_gui_smoke:** verifies headless creation of all GUI frames and dialogs, `TreeGrid` 2D vertical divider placement, and instant tab switching without data reload.

## 11. Build order and acceptance

1. config.py and auth.py with test\_auth.
2. db.py with test\_db.
3. history.py with test\_history, then connect Database to HistoryLog.
4. memory.py and cli.py with test\_memory and test\_cli (embeddings off).
5. make\_sample\_db.py: a small school database (students, courses, enrollments) and a few seeded memories.
6. GUI, in the order given in section 9.9.
7. Embeddings last.

Accepted when: a user can register, log in, open the sample database, run SQL, commit and roll back, edit rows, and two different users see each other's commands in the history of the same table; and an LLM can save and recall memories through the terminal commands, with the Memory page showing them, across app restarts.

## 12. Out of scope

Web or server versions, any call to an LLM from the app (the LLM uses the terminal commands instead), accounts on the internet, per-database permissions, a knowledge-graph table, scheduled consolidation, binary vector compression, memory sync, encryption, third-party theme packages, exports of any kind (no CSV), a structure view for tables, a copy of the user's database file, a consolidate button or a memory search box in the GUI, and multiple databases open at once.

## 13. Assumptions to confirm

- Memory is shared by the whole installation and has no user\_id column. Add one to episodic\_memory and working\_memory only if accounts should have private memories.
- Access to a database means being able to open its file in the app. There is no permissions table.
- The LLM that uses the memory can run terminal commands and call the program with arguments. It needs no API.
- Renaming a table moves its history to the new name. A dropped table keeps its history in the log, reachable from the whole-database history page, and a new table with the same name continues it.
- The tested building blocks (hashing and login, the authorizer-based table detection, the history join with ATTACH, the foreign key behavior and the terminal commands) were verified in a prototype. Embeddings and the Windows exe build are untested.

Decisions already made, so the generator does not reopen them:

- Commands that are rolled back stay in the history log, with no special mark.
- Two people working on one file: the second waits up to 5 seconds, then sees the readable message database is locked. There is no merging and no live sync.
- Dark mode is not remembered between sessions.
- The console output and the list of recalled commands live in memory only and start empty at every login.
- Ctrl+F on the notepad pages is optional and built last.
- The history and memory pages have no search box and no buttons that change anything. The user scrolls.

## 14. Vibe-coding rules

These rules keep AI-generated code correct and readable by the team that has to explain it.

### 14.1 Working method for the team

1. Prompt one module at a time. Paste section 1, the module's contract from section 6, the schemas from section 5, the signatures of any module it calls, and for GUI files the parts of sections 9 and 15 about that tab. Nothing else.
2. Run before you move on. Run the module's pytest file first, then try the module by hand.
3. Commit to Git after every working step with a clear message. Never commit code that fails its tests. Use one branch per teammate and merge often.
4. If you cannot read a function, ask the LLM to explain it in plain words, then to rewrite it more simply. Do not keep code that nobody on the team understands.
5. Report each bug in its own prompt: the full error traceback, the file name, what you did, and what you expected.
6. Ask for the smallest fix: only the changed function and its file name. Do not accept a whole-file rewrite unless you asked for one.
7. The spec is the contract. Never let the LLM change a schema, a function signature or the file layout on its own. Edit this document first, then regenerate the affected modules.
8. Never delete or weaken a failing test to make it pass.
9. Use a virtual environment and write requirements.txt after the first working run.
10. Keep a short DEV\_NOTES.md: what works, known bugs, decisions made.
11. When a chat gets long or the LLM starts forgetting rules, open a new chat and paste the spec again.
12. Check your university's rules on AI-assisted work and state the AI use in the report.

### 14.2 Review checklist before accepting any generated file

- Every SQL statement that takes values uses ? placeholders.
- PRAGMA foreign\_keys = ON on every connection, including the user's database.
- Commit and rollback happen only where the spec says. No with-block on the user's connection.
- No widget is touched from a background thread.
- Errors become readable messages, never tracebacks on screen.
- No new library, file, table or column that is not in this document.
- You can explain every function in your own words.
- Try to break it: wrong password, bad SQL, empty table, huge SELECT, missing file, a terminal command with a missing argument.

### 14.3 Rules for the code-generating LLM

- Follow the spec exactly. When something is unclear, take the simplest option and leave a one-line comment starting with ASSUMPTION.
- Do not add features, libraries, tables or columns.
- No placeholder code, no pseudocode, and no phrases like rest unchanged.
- Plain, human-style Python: short functions, clear names, few and short comments, and no docstring or type hints on every function. No metaclasses, no async, no decorators. Small shortcuts are fine if the code stays easy to read.
- Never use a bare except. Catch specific exceptions and show short readable messages.
- No global mutable state except the constants in config.py. No stray debug print calls (cli.py prints its output on purpose).
- Use pathlib or os.path so paths work on Windows.
- When fixing a bug, return only the changed functions with the file name and a one-line reason, unless the whole file is asked for.
- When the spec lists tests for a module, deliver them with it.
- End every answer with three lines: what was built, how to run it, and what is untested.

## 15. Packaging, threading and data access

This section covers packaging, the threading rules and the data helpers the GUI needs. Where it differs from an earlier section, this section wins.

### 15.1 Packaging (Windows .exe)

- Target: a standalone Windows desktop program built with PyInstaller, on Python 3.10 or newer.
- Build command, run from the project folder inside the virtual environment:

```
pyinstaller --onefile --clean --name LoreMemory main.py
```

- The result is dist/LoreMemory.exe. Do not use --noconsole, because the terminal commands need a console to print to. When the exe is double-clicked, main.py hides its console window on Windows, but only if that console was created for this process (GetConsoleProcessList returns 1), so it never hides a terminal the user started it from.
- Paths: a one-file build unpacks to a temporary folder on every start. config.py must define DATA\_DIR as the folder that contains the .exe when sys.frozen is set, and as the project folder otherwise. Never store data in the temporary folder.
- Build the exe without sentence-transformers. Embeddings (section 8) stay optional, and bundling PyTorch makes the file huge and unreliable. Without them, recall uses the keyword and importance parts only.

### 15.2 Architecture and threading

- Keep the names in section 4: db.py, history.py, memory.py and the gui package. Do not rename them to database.py or app.py, and do not add a separate controller layer. The Database, HistoryLog and Memory classes are the logic layer and the GUI calls them directly.
- Use with-blocks for short operations on the app's own files: with con: commits or rolls back by itself. Never use a with-block on the user's database connection, because leaving it commits and would bypass the Commit and Rollback buttons.
- Queries run in background threads, so open the user's connection with check\_same\_thread=False and guard every use with one threading.RLock (re-entrant, because some Database methods call others) inside Database. The same applies to any other connection used from a thread. Background threads never touch widgets: pass results back with root.after or a queue.
- Database also runs PRAGMA foreign\_keys = ON on the user's connection, so foreign keys in the user's tables are enforced while editing.

### 15.3 Data helpers for the table page (extends section 6.3)

- `Database.get_table_info()` reads sqlite\_master and returns, for each table except names starting with sqlite\_, its name, its columns and its row count (SELECT COUNT(\*)). The navigation pane and the autocomplete use it.
- `Database.get_rows(table, page, page_size=100, order_by=None, descending=False, search='')` returns the column names, the rows of that page and the total row count. The order\_by column must be checked against get\_columns before it is put in the SQL. The search text filters across all columns with LIKE and ? placeholders. For tables without a primary key, also select rowid so rows can be edited and deleted.
- Logging: browsing reads (paging, sorting, filtering, metadata) are not logged. Add, Edit and Delete go through run and are logged.
