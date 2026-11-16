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
        self.root, self.user_id, self.username, self.on_logout_cb = root, user_id, username, on_logout
        self.root.title("LoreMemory")
        try: self.root.state("zoomed")
        except Exception: self.root.geometry(MIN_WINDOW)

        self.role = "user"
        try:
            import auth
            con = auth.get_connection(USERS_DB)
            u = auth.get_user(con, self.user_id); con.close()
            if u: self.role = u.get("role", "user")
        except Exception: pass

        self.history = HistoryLog(HISTORY_DB, USERS_DB)
        self.memory = Memory(MEMORY_DB)
        self.db = Database(history=self.history, user_id=self.user_id)
        self.active_table, self.running_thread, self.sidebar_collapsed = None, None, False

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_requested)
        self.root.bind("<Control-b>", lambda e: self.toggle_sidebar())

    def setup_ui(self):
        p = get_palette()

        self.main_container = tk.Frame(self.root, bg=p["bg"])
        self.main_container.pack(fill="both", expand=True)

        # Persistent Expand bar visible only when sidebar is shrunk
        self.expand_bar = tk.Frame(
            self.main_container, bg=p["panel"], width=28,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.expand_btn = tk.Button(
            self.expand_bar, text="›", font=("Segoe UI", 11, "bold"),
            relief="flat", bg=p["surface"], fg=p["text"],
            activebackground=p["select_bg"], command=self.toggle_sidebar,
            cursor="hand2", bd=0, padx=4, pady=6
        )
        self.expand_btn.pack(side="top", pady=6)

        # Paned Window (2 : 5 : 3)
        self.paned = ttk.Panedwindow(self.main_container, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        self.sidebar = Sidebar(self.paned, self)
        self.paned.add(self.sidebar, weight=2)

        self.tabs = TabStrip(self.paned, on_tab_close=self.on_tab_closed, on_tab_switch=self.on_tab_switched)
        self.paned.add(self.tabs.container, weight=5)

        self.console = Console(self.paned, self)
        self.paned.add(self.console, weight=3)

        self.autocomplete = AutocompletePopup(self.console.editor, lambda: self.db.get_table_info() if self.db.con else [])

        # Bottom Status Bar with soft 1px border
        self.status_bar = tk.Frame(self.root, bg=p["panel"], padx=10, pady=5, highlightbackground=p["border"], highlightthickness=1)
        self.status_bar.pack(fill="x", side="bottom")
        role_tag = f" ({self.role})" if self.role != "user" else ""
        self.status_user = tk.Label(self.status_bar, text=f"User: {self.username}{role_tag}", bg=p["panel"], fg=p["text"], font=("Segoe UI", 9, "bold"))
        self.status_user.pack(side="left", padx=(0, 14))
        self.status_file = tk.Label(self.status_bar, text="No database open", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.status_file.pack(side="left", padx=(0, 14))
        self.status_rows = tk.Label(self.status_bar, text="", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.status_rows.pack(side="left", padx=(0, 14))
        self.status_time = tk.Label(self.status_bar, text="", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.status_time.pack(side="right")

    def run_in_background(self, work, done):
        def on_done(val, err):
            self.running_thread = None
            done(val, err)
        self.running_thread = run_in_background(self.root, work, on_done)

    def toggle_sidebar(self):
        if self.sidebar_collapsed:
            self.expand_bar.pack_forget()
            self.paned.insert(0, self.sidebar, weight=2)
            self.sidebar_collapsed = False
        else:
            self.paned.forget(self.sidebar)
            self.expand_bar.pack(side="left", fill="y", before=self.paned)
            self.sidebar_collapsed = True

    def toggle_theme(self):
        import gui.theme as theme
        new_theme = "light" if theme.CURRENT_THEME == "dark" else "dark"
        p = theme.apply(self.root, new_theme)
        self.sidebar.theme_btn.config(text="☀" if new_theme == "dark" else "☾")
        self.main_container.config(bg=p["bg"])
        self.status_bar.config(bg=p["panel"], highlightbackground=p["border"])
        self.expand_bar.config(bg=p["panel"], highlightbackground=p["border"])
        self.expand_btn.config(bg=p["surface"], fg=p["text"])
        for child in self.status_bar.winfo_children():
            if isinstance(child, tk.Label): child.config(bg=p["panel"], fg=p["text"])
        self.sidebar.apply_theme(p); self.tabs.apply_theme(p); self.console.apply_theme(p)

    def on_open_database(self):
        self.root.after(100, self._do_open_database)

    def _do_open_database(self):
        try:
            d = os.path.dirname(self.db.path) if self.db.path else os.getcwd()
            p = filedialog.askopenfilename(parent=self.root, title="Open SQLite Database", initialdir=d,
                                           filetypes=[("SQLite Database", "*.db"), ("SQLite Database", "*.sqlite"), ("All Files", "*.*")])
            if p and self.check_pending_transactions("Open Database"):
                self.close_table_tabs()
                if self.db.open(p):
                    self.sidebar.update_db_name(p); self.status_file.config(text=os.path.basename(p))
                    self.refresh_tables(); self.update_pending()
                else: messagebox.showerror("Error", f"Failed to open database:\n{p}", parent=self.root)
        except Exception as e: messagebox.showerror("Database Error", f"Could not open database:\n{e}", parent=self.root)

    def on_new_database(self):
        self.root.after(100, self._do_new_database)

    def _do_new_database(self):
        try:
            d = os.path.dirname(self.db.path) if self.db.path else os.getcwd()
            p = filedialog.asksaveasfilename(parent=self.root, title="New SQLite Database", initialdir=d,
                                             defaultextension=".db", filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")])
            if p and self.check_pending_transactions("New Database"):
                self.close_table_tabs()
                if self.db.open(p, create=True):
                    self.sidebar.update_db_name(p); self.status_file.config(text=os.path.basename(p))
                    self.refresh_tables(); self.update_pending()
                else: messagebox.showerror("Error", f"Failed to create database:\n{p}", parent=self.root)
        except Exception as e: messagebox.showerror("Database Error", f"Could not create database:\n{e}", parent=self.root)

    def on_close_database(self):
        if self.check_pending_transactions("Close Database"):
            self.close_table_tabs(); self.db.close()
            self.sidebar.update_db_name(None); self.status_file.config(text="No database open")
            self.refresh_tables(); self.update_pending()

    def close_table_tabs(self):
        self.sidebar.selected_table, self.active_table = None, None
        for k in list(self.tabs.tabs.keys()):
            if k.startswith("table:") or k.startswith("history:"):
                info = self.tabs.tabs.pop(k, None)
                if info:
                    if hasattr(info["page"], "on_close"):
                        try: info["page"].on_close()
                        except Exception: pass
                    info["header"].destroy(); info["page"].destroy()
        if self.tabs.tabs: self.tabs.select(list(self.tabs.tabs.keys())[-1])
        else:
            self.tabs.active_key = None
            p = get_palette()
            self.tabs.empty_label.config(bg=p["surface"], fg=p["muted"])
            self.tabs.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def refresh_tables(self):
        if not self.db.con: self.sidebar.refresh_tables([]); return
        try: self.sidebar.refresh_tables(self.db.get_table_info())
        except Exception: self.sidebar.refresh_tables([])

    def update_pending(self):
        self.console.update_pending_status(self.db.has_pending)

    def update_status(self, table_rows=None, elapsed_ms=None):
        if table_rows is not None: self.status_rows.config(text=f"{table_rows} rows")
        if elapsed_ms is not None: self.status_time.config(text=f"{elapsed_ms:.1f} ms")

    def open_tab(self, kind, name):
        try:
            if kind == "table":
                key, title, fn = f"table:{name}", name, lambda: TablePage(self.tabs.content_frame, self, name)
            elif kind == "result":
                key, title, fn = "result", "Result", lambda: ResultPage(self.tabs.content_frame, self)
            elif kind == "history":
                key = f"history:{name or 'db'}"
                title = f"History: {name}" if name else "History: Database"
                ret = self.tabs.active_key if self.tabs.active_key != key else None
                fn = lambda: HistoryPage(self.tabs.content_frame, self, table_name=name, return_tab=ret)
            elif kind == "memory":
                key, title, fn = "memory", "Memory", lambda: MemoryPage(self.tabs.content_frame, self)
            elif kind == "admin":
                from gui.admin_page import AdminPage
                key, title, fn = "admin", "Admin Panel", lambda: AdminPage(self.tabs.content_frame, self)
            else: return
            if key not in self.tabs.tabs: self.tabs.add_tab(key, kind, title, fn())
            else: self.tabs.select(key)
        except Exception as e:
            try:
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"open_tab({kind}) error: {e}\n")
            except Exception: pass
            messagebox.showerror("Error Opening Tab", f"Failed to open {kind} tab:\n{e}", parent=self.root)

    def show_select_result(self, result):
        self.open_tab("result", None)
        self.tabs.tabs["result"]["page"].display(result)

    def on_tab_switched(self, key, kind, page):
        if kind == "table":
            tname = key.split(":", 1)[1]
            self.active_table = tname
            self.sidebar.select_table_by_name(tname)
        else: self.active_table = None

    def on_tab_closed(self, key, kind):
        if kind == "table":
            tname = key.split(":", 1)[1]
            h_key = f"history:{tname}"
            if h_key in self.tabs.tabs: self.tabs.close_tab(h_key)

    def check_pending_transactions(self, action_name="Exit"):
        if self.running_thread and self.running_thread.is_alive():
            if not messagebox.askyesno("Running Query", "Something is still running. Close anyway?", parent=self.root): return False
            self.running_thread.join(timeout=2.0)
        if self.db.has_pending:
            ans = messagebox.askyesnocancel("Uncommitted Changes", "You have uncommitted changes. Commit before proceeding?", parent=self.root)
            if ans is None: return False
            elif ans is True: self.db.commit()
            else: self.db.rollback()
        return True

    def on_logout(self):
        if not self.check_pending_transactions("Logout"): return
        self.db.close(); self.history.close(); self.memory.close()
        for w in self.root.winfo_children(): w.destroy()
        if self.on_logout_cb: self.on_logout_cb()

    def on_close_requested(self):
        if not self.check_pending_transactions("Exit"): return
        self.db.close(); self.history.close(); self.memory.close()
        self.root.destroy()
