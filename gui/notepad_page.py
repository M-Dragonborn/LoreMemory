import tkinter as tk
from tkinter import ttk
from config import HISTORY_BATCH
from gui.theme import get_palette

class NotepadPage(ttk.Frame):
    def __init__(self, parent, app, title="Notepad"):
        super().__init__(parent)
        self.app = app
        self.title_str = title
        self.offset = 0
        self.has_more = True
        self.loading = False
        self.find_matches = []
        self.find_index = -1

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()
        self.top_bar = ttk.Frame(self, padding=(8, 4))
        self.top_bar.pack(fill="x", side="top")

        # Find bar (toggleable via Ctrl+F)
        self.find_bar = ttk.Frame(self, padding=(8, 2))
        self.find_entry = ttk.Entry(self.find_bar, width=20)
        self.find_entry.pack(side="left", padx=2)
        self.find_entry.bind("<KeyRelease>", lambda e: self.do_find())
        ttk.Button(self.find_bar, text="‹", width=2, command=self.find_prev).pack(side="left", padx=2)
        ttk.Button(self.find_bar, text="›", width=2, command=self.find_next).pack(side="left", padx=2)
        ttk.Button(self.find_bar, text="×", width=2, command=self.hide_find_bar).pack(side="left", padx=2)
        self.find_lbl = ttk.Label(self.find_bar, text="", style="Muted.TLabel")
        self.find_lbl.pack(side="left", padx=4)

        # Main text area
        text_frame = ttk.Frame(self)
        text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            text_frame, wrap="word", font=("Consolas", 10),
            bg=p["surface"], fg=p["text"], padx=10, pady=10,
            borderwidth=0, highlightthickness=0
        )
        scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.on_scroll_cmd)
        self.text.configure(yscrollcommand=self.on_text_scroll)

        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.v_scroll = scroll

        # Tags
        self.text.tag_configure("header", foreground=p["muted"], font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("failed", foreground=p["danger"], font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("error_msg", foreground=p["danger"])
        self.text.tag_configure("sql", foreground=p["text"], font=("Consolas", 10))
        self.text.tag_configure("find_match", background="#fff3a8", foreground="#000000")
        self.text.tag_configure("find_curr", background=p["accent"], foreground=p["accent_text"])

        self.text.bind("<Control-f>", lambda e: self.show_find_bar())
        self.bind("<Control-f>", lambda e: self.show_find_bar())

    def on_scroll_cmd(self, *args):
        self.text.yview(*args)
        self.check_bottom()

    def on_text_scroll(self, first, last):
        self.v_scroll.set(first, last)
        if float(last) >= 0.98 and self.has_more and not self.loading:
            self.load_more()

    def check_bottom(self):
        _, last = self.text.yview()
        if float(last) >= 0.98 and self.has_more and not self.loading:
            self.load_more()

    def show_find_bar(self):
        self.find_bar.pack(fill="x", side="top", before=self.text.master)
        self.find_entry.focus()

    def hide_find_bar(self):
        self.find_bar.pack_forget()
        self.text.tag_remove("find_match", "1.0", "end")
        self.text.tag_remove("find_curr", "1.0", "end")

    def do_find(self):
        self.text.tag_remove("find_match", "1.0", "end")
        self.text.tag_remove("find_curr", "1.0", "end")
        q = self.find_entry.get()
        if not q:
            self.find_lbl.config(text="")
            self.find_matches = []
            return
        idx = "1.0"
        self.find_matches = []
        while True:
            idx = self.text.search(q, idx, nocase=True, stopindex="end")
            if not idx:
                break
            end_idx = f"{idx}+{len(q)}c"
            self.find_matches.append((idx, end_idx))
            self.text.tag_add("find_match", idx, end_idx)
            idx = end_idx
        self.find_lbl.config(text=f"{len(self.find_matches)} matches")
        if self.find_matches:
            self.find_index = 0
            self.highlight_current_match()

    def highlight_current_match(self):
        self.text.tag_remove("find_curr", "1.0", "end")
        if 0 <= self.find_index < len(self.find_matches):
            s, e = self.find_matches[self.find_index]
            self.text.tag_add("find_curr", s, e)
            self.text.see(s)

    def find_next(self):
        if self.find_matches:
            self.find_index = (self.find_index + 1) % len(self.find_matches)
            self.highlight_current_match()

    def find_prev(self):
        if self.find_matches:
            self.find_index = (self.find_index - 1 + len(self.find_matches)) % len(self.find_matches)
            self.highlight_current_match()

    def load_more(self):
        pass

    def reload(self):
        pass

    def on_close(self):
        pass

class HistoryPage(NotepadPage):
    def __init__(self, parent, app, table_name=None, return_tab=None):
        super().__init__(parent, app, title=f"History: {table_name or 'Database'}")
        self.table_name = table_name
        self.return_tab = return_tab

        # Back arrow
        ttk.Button(self.top_bar, text="‹ Back", width=6, command=self.go_back).pack(side="left", padx=(0, 8))

        # Filter mode text & toggle link
        target_str = self.table_name if self.table_name else "whole database"
        self.scope_lbl = ttk.Label(self.top_bar, text=f"Showing: {target_str}", font=("Segoe UI", 9))
        self.scope_lbl.pack(side="left", padx=(0, 8))

        if self.table_name:
            self.switch_link = tk.Label(
                self.top_bar, text="Switch to whole database",
                fg=get_palette()["accent"], cursor="hand2", font=("Segoe UI", 9, "underline")
            )
            self.switch_link.pack(side="left")
            self.switch_link.bind("<Button-1>", lambda e: self.switch_scope())

        self.reload()

    def switch_scope(self):
        if self.table_name:
            self.app.open_tab("history", None)

    def go_back(self):
        self.app.tabs.close_tab(self.app.tabs.active_key)
        if self.return_tab:
            self.app.tabs.select(self.return_tab)

    def reload(self):
        self.offset = 0
        self.has_more = True
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")
        self.load_more()

    def load_more(self):
        if self.loading or not self.has_more or not self.app.db.path:
            return
        self.loading = True
        if self.table_name:
            rows = self.app.history.for_table(self.app.db.path, self.table_name, limit=HISTORY_BATCH, offset=self.offset)
        else:
            rows = self.app.history.for_database(self.app.db.path, limit=HISTORY_BATCH, offset=self.offset)

        if len(rows) < HISTORY_BATCH:
            self.has_more = False
        self.offset += len(rows)

        self.text.config(state="normal")
        for exec_at, user, cmd_type, sql, success, err in rows:
            status_tag = "header" if success else "failed"
            status_txt = "OK" if success else "FAILED"
            hdr = f"{exec_at}  user:{user}  [{cmd_type}]  {status_txt}\n"
            self.text.insert("end", hdr, status_tag)
            self.text.insert("end", f"{sql}\n", "sql")
            if err:
                self.text.insert("end", f"Error: {err}\n", "error_msg")
            self.text.insert("end", "\n")
        self.text.config(state="disabled")
        self.loading = False

class MemoryPage(NotepadPage):
    def __init__(self, parent, app):
        super().__init__(parent, app, title="Memory")
        self.lbl = ttk.Label(self.top_bar, text="AI Memory (Mnemosyne-style)", font=("Segoe UI", 9, "bold"))
        self.lbl.pack(side="left")
        self.reload()

    def reload(self):
        self.offset = 0
        self.has_more = True
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")
        self.load_more()

    def load_more(self):
        if self.loading or not self.has_more:
            return
        self.loading = True
        items = self.app.memory.recent(k=HISTORY_BATCH, offset=self.offset)
        if len(items) < HISTORY_BATCH:
            self.has_more = False
        self.offset += len(items)

        self.text.config(state="normal")
        for it in items:
            kind_txt = "episode [summary]" if it["source"] == "episodic" else f"session:{it['session'] or 'terminal'}"
            hdr = f"{it['created']}  imp:{it['importance']:.2f}  {kind_txt}\n"
            self.text.insert("end", hdr, "header")
            self.text.insert("end", f"{it['text']}\n\n", "sql")
        self.text.config(state="disabled")
        self.loading = False
