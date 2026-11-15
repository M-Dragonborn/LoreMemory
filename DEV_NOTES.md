# LoreMemory: Development Notes

## Status and Verification
- **Test Suite**: 27 unit and smoke tests passing across 6 test modules (`test_auth`, `test_db`, `test_history`, `test_memory`, `test_cli`, `test_gui_smoke`).
- **File Lengths**: All source files adhere strictly to the rule of staying under ~250 lines and contain short, readable, human-style Python functions.
- **Dependencies**: 100% standard library (Python 3.10+ / 3.13) + Tkinter. Optional `sentence-transformers` for embeddings is supported lazily with full fallback to keyword+importance scoring when not installed.

## Decisions Made
1. **Transaction Management**: In user databases, isolation level is `None`. Modifying statements (`INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `CREATE`, `DROP`, `ALTER`) automatically initiate a transaction (`BEGIN`) if one is not already open, enabling rollbacks for structure changes until `Commit` is triggered.
2. **Authorizer Table Tracking**: SQLite authorizer callback intercepts touched tables dynamically, tagging `CREATE TABLE` and `ALTER TABLE ... RENAME TO` properly.
3. **Database-Wide vs Table History**: Failed commands (e.g. syntax errors) do not reach the authorizer and are recorded in the database-wide query log. Successful commands and table modifications are recorded in both database and per-table logs.
4. **Console Window on Windows**: `main.py` checks `kernel32.GetConsoleProcessList`. If double-clicked (count == 1), it hides the console window; if run from a terminal or command prompt by an LLM, the console remains active for text input and output.
5. **No SQLite in GUI**: All GUI modules interact exclusively via the abstraction layers (`Database`, `HistoryLog`, `Memory`, `auth`), maintaining modular separation.
