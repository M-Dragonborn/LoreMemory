import tkinter as tk
from tkinter import ttk
from config import HISTORY_BATCH
from gui.theme import get_palette

class NotepadPage(tk.Frame):
    def __init__(self, parent, app, title="Notepad"):
        p = get_palette()
        super().__init__(parent, bg=p["surface"])
        self.app = app
        self.title_str = title
        self.offset, self.has_more, self.loading = 0, True, False
        self.find_matches, self.find_index = [], -1

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()
        self.top_bar = tk.Frame(
            self, bg=p["panel"], padx=8, pady=6,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.top_bar.pack(fill="x", side="top", padx=3, pady=3)

        self.find_bar = tk.Frame(
            self, bg=p["panel"], padx=6, pady=4,
            highlightbackground=p["accent"], highlightthickness=1
        )
        self.find_entry = ttk.Entry(self.find_bar, width=20)
        self.find_entry.pack(side="left", padx=2)
        self.find_entry.bind("<KeyRelease>", lambda e: self.do_find())
        ttk.Button(self.find_bar, text="‹", width=2, command=self.find_prev).pack(side="left", padx=2)
        ttk.Button(self.find_bar, text="›", width=2, command=self.find_next).pack(side="left", padx=2)
        ttk.Button(self.find_bar, text="×", width=2, command=self.hide_find_bar).pack(side="left", padx=2)
        self.find_lbl = tk.Label(self.find_bar, text="", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.find_lbl.pack(side="left", padx=4)

        text_frame = tk.Frame(
            self, bg=p["surface"],
            highlightbackground=p["border"], highlightthickness=1
        )
        text_frame.pack(fill="both", expand=True, padx=3, pady=1)

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

        self.text.tag_configure("header", foreground=p["muted"], font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("failed", foreground=p["danger"], font=("Segoe UI", 9, "bold"))
        self.text.tag_configure("error_msg", foreground=p["danger"], font=("Consolas", 9, "bold"))
        self.text.tag_configure("sql", foreground=p["text"], font=("Consolas", 10))
        self.text.tag_configure("find_match", background="#fef08a", foreground="#000000")
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
        self.find_bar.pack(fill="x", side="top", before=self.text.master, padx=3, pady=2)
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
        self.table_name, self.return_tab = table_name, return_tab
        p = get_palette()

        ttk.Button(self.top_bar, text="‹ Back", width=6, command=self.go_back).pack(side="left", padx=(0, 6))
        tk.Label(self.top_bar, text="⏱", font=("Segoe UI", 10), fg=p["accent"], bg=p["panel"]).pack(side="left", padx=(0, 4))
        tk.Label(self.top_bar, text="Query History", font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"]).pack(side="left", padx=(0, 6))

        target_str = f"[{self.table_name}]" if self.table_name else "[Whole Database]"
        self.scope_lbl = tk.Label(self.top_bar, text=target_str, bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.scope_lbl.pack(side="left", padx=(0, 10))

        if self.table_name:
            self.switch_link = tk.Label(
                self.top_bar, text="Switch to whole database",
                fg=p["accent"], bg=p["panel"], cursor="hand2", font=("Segoe UI", 9, "bold", "underline")
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
        self.offset, self.has_more = 0, True
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
        p = get_palette()
        tk.Label(self.top_bar, text="🧠", font=("Segoe UI", 10), fg=p["accent"], bg=p["panel"]).pack(side="left", padx=(0, 4))
        tk.Label(self.top_bar, text="AI Memory", font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"]).pack(side="left", padx=(0, 6))
        tk.Label(self.top_bar, text="[Mnemosyne Cognitive Graph]", font=("Segoe UI", 9), fg=p["muted"], bg=p["panel"]).pack(side="left")
        self.reload()

    def reload(self):
        self.offset, self.has_more = 0, True
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
