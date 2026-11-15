import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from db import Database
from history import HistoryLog
from memory import Memory
from config import MIN_WINDOW, HISTORY_DB, USERS_DB, MEMORY_DB
from gui.theme import apply, CURRENT_THEME, get_palette
from gui.widgets import run_in_background
from gui.tabs import TabStrip
from gui.sidebar import Sidebar
from gui.console import Console
from gui.table_page import TablePage
from gui.result_page import ResultPage
from gui.notepad_page import HistoryPage, MemoryPage
from gui.autocomplete import AutocompletePopup

class MainWindow:
    def __init__(self, root, user_id, username, on_logout=None):
        self.root = root
        self.user_id = user_id
        self.username = username
        self.on_logout_cb = on_logout

        self.root.title("LoreMemory")
        self.root.geometry(MIN_WINDOW)
        self.root.minsize(1100, 700)

        # Services
        self.history = HistoryLog(HISTORY_DB, USERS_DB)
        self.memory = Memory(MEMORY_DB)
        self.db = Database(history=self.history, user_id=self.user_id)

        self.active_table = None
        self.running_thread = None
        self.sidebar_collapsed = False

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_requested)
        self.root.bind("<Control-b>", lambda e: self.toggle_sidebar())

    def setup_ui(self):
        p = get_palette()

        # Main horizontal paned window (2 : 5 : 3 ratio)
        self.paned = ttk.Panedwindow(self.root, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        self.sidebar = Sidebar(self.paned, self)
        self.paned.add(self.sidebar, weight=2)

        # Tab strip in center
        self.tabs = TabStrip(self.paned, on_tab_close=self.on_tab_closed, on_tab_switch=self.on_tab_switched)
        self.paned.add(self.tabs.container, weight=5)

        # Console on right
        self.console = Console(self.paned, self)
        self.paned.add(self.console, weight=3)

        # Setup autocomplete on console editor
        self.autocomplete = AutocompletePopup(self.console.editor, lambda: self.db.get_table_info() if self.db.con else [])

        # Bottom Status Bar
        self.status_bar = ttk.Frame(self.root, padding=(8, 4))
        self.status_bar.pack(fill="x", side="bottom")

        self.status_user = ttk.Label(self.status_bar, text=f"User: {self.username}")
        self.status_user.pack(side="left", padx=(0, 12))

        self.status_file = ttk.Label(self.status_bar, text="No database open", style="Muted.TLabel")
        self.status_file.pack(side="left", padx=(0, 12))

        self.status_rows = ttk.Label(self.status_bar, text="", style="Muted.TLabel")
        self.status_rows.pack(side="left", padx=(0, 12))

        self.status_time = ttk.Label(self.status_bar, text="", style="Muted.TLabel")
        self.status_time.pack(side="right")

    def run_in_background(self, work, done):
        def on_done(val, err):
            self.running_thread = None
            done(val, err)
        self.running_thread = run_in_background(self.root, work, on_done)

    def toggle_sidebar(self):
        if self.sidebar_collapsed:
            self.paned.insert(0, self.sidebar, weight=2)
            self.sidebar.collapse_btn.config(text="‹")
            self.sidebar_collapsed = False
        else:
            self.paned.forget(self.sidebar)
            self.sidebar.collapse_btn.config(text="›")
            self.sidebar_collapsed = True

    def toggle_theme(self):
        new_theme = "dark" if CURRENT_THEME == "light" else "light"
        apply(self.root, new_theme)
        self.sidebar.theme_btn.config(text="☀" if new_theme == "dark" else "☾")

    def on_open_database(self):
        path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db *.sqlite"), ("All Files", "*.*")])
        if path:
            if not self.check_pending_transactions("Open Database"):
                return
            if self.db.open(path):
                self.sidebar.update_db_name(path)
                self.status_file.config(text=os.path.basename(path))
                self.refresh_tables()
                self.update_pending()

    def on_new_database(self):
        path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite Database", "*.db")])
        if path:
            if not self.check_pending_transactions("New Database"):
                return
            if self.db.open(path, create=True):
                self.sidebar.update_db_name(path)
                self.status_file.config(text=os.path.basename(path))
                self.refresh_tables()
                self.update_pending()

    def on_close_database(self):
        if not self.check_pending_transactions("Close Database"):
            return
        self.db.close()
        self.sidebar.update_db_name(None)
        self.status_file.config(text="No database open")
        self.refresh_tables()
        self.update_pending()

    def refresh_tables(self):
        if not self.db.con:
            self.sidebar.refresh_tables([])
            return
        info = self.db.get_table_info()
        self.sidebar.refresh_tables(info)

    def update_pending(self):
        has_pending = self.db.has_pending
        self.console.update_pending_status(has_pending)

    def update_status(self, table_rows=None, elapsed_ms=None):
        if table_rows is not None:
            self.status_rows.config(text=f"{table_rows} rows")
        if elapsed_ms is not None:
            self.status_time.config(text=f"{elapsed_ms:.1f} ms")

    def open_tab(self, kind, name):
        if kind == "table":
            key = f"table:{name}"
            if key not in self.tabs.tabs:
                page = TablePage(self.tabs.content_frame, self, name)
                self.tabs.add_tab(key, "table", name, page)
            else:
                self.tabs.select(key)
        elif kind == "result":
            key = "result"
            if key not in self.tabs.tabs:
                page = ResultPage(self.tabs.content_frame, self)
                self.tabs.add_tab(key, "result", "Result", page)
            else:
                self.tabs.select(key)
        elif kind == "history":
            key = f"history:{name or 'db'}"
            title = f"History: {name}" if name else "History: Database"
            if key not in self.tabs.tabs:
                ret_key = self.tabs.active_key if self.tabs.active_key != key else None
                page = HistoryPage(self.tabs.content_frame, self, table_name=name, return_tab=ret_key)
                self.tabs.add_tab(key, "history", title, page)
            else:
                self.tabs.select(key)
        elif kind == "memory":
            key = "memory"
            if key not in self.tabs.tabs:
                page = MemoryPage(self.tabs.content_frame, self)
                self.tabs.add_tab(key, "memory", "Memory", page)
            else:
                self.tabs.select(key)

    def show_select_result(self, result):
        self.open_tab("result", None)
        res_page = self.tabs.tabs["result"]["page"]
        res_page.display(result)

    def on_tab_switched(self, key, kind, page):
        if kind == "table":
            tname = key.split(":", 1)[1]
            self.active_table = tname
            self.sidebar.select_table_by_name(tname)
        else:
            self.active_table = None

    def on_tab_closed(self, key, kind):
        if kind == "table":
            tname = key.split(":", 1)[1]
            h_key = f"history:{tname}"
            if h_key in self.tabs.tabs:
                self.tabs.close_tab(h_key)

    def check_pending_transactions(self, action_name="Exit"):
        if self.running_thread and self.running_thread.is_alive():
            ans = messagebox.askyesno("Running Query", "Something is still running. Close anyway?", parent=self.root)
            if not ans:
                return False
            self.running_thread.join(timeout=2.0)

        if self.db.has_pending:
            ans = messagebox.askyesnocancel("Uncommitted Changes", "You have uncommitted changes. Commit before proceeding?", parent=self.root)
            if ans is None:
                return False
            elif ans is True:
                self.db.commit()
            else:
                self.db.rollback()
        return True

    def on_logout(self):
        if not self.check_pending_transactions("Logout"):
            return
        self.db.close()
        self.history.close()
        self.memory.close()
        for w in self.root.winfo_children():
            w.destroy()
        if self.on_logout_cb:
            self.on_logout_cb()

    def on_close_requested(self):
        if not self.check_pending_transactions("Exit"):
            return
        self.db.close()
        self.history.close()
        self.memory.close()
        self.root.destroy()
