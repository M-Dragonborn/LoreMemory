import tkinter as tk
from tkinter import ttk
from gui.theme import get_palette

SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "DROP", "CREATE", "ALTER", "TABLE", "JOIN", "ON", "ORDER",
    "BY", "GROUP", "LIMIT", "AND", "OR", "NOT", "NULL", "PRIMARY", "KEY",
    "BEGIN", "COMMIT", "ROLLBACK", "PRAGMA", "DISTINCT", "AS", "HAVING", "UNION"
]

class AutocompletePopup:
    def __init__(self, editor, get_schema_callback):
        self.editor = editor
        self.get_schema = get_schema_callback
        self.popup = None
        self.listbox = None
        self.matches = []
        self.after_id = None

        self._init_popup()

        self.editor.bind("<KeyRelease>", self.on_key_release)
        self.editor.bind("<Control-space>", self.on_ctrl_space)
        self.editor.bind("<Escape>", self.on_escape)
        self.editor.bind("<Tab>", self.on_tab)
        self.editor.bind("<Up>", self.on_arrow_up)
        self.editor.bind("<Down>", self.on_arrow_down)
        self.editor.bind("<Return>", self.on_return)
        self.editor.bind("<FocusOut>", lambda e: self.hide())

    def _init_popup(self):
        p = get_palette()
        self.popup = tk.Toplevel(self.editor)
        self.popup.wm_overrideredirect(True)
        self.listbox = tk.Listbox(
            self.popup, font=("Segoe UI", 9), selectmode="browse",
            bg=p["surface"], fg=p["text"], selectbackground=p["select_bg"],
            selectforeground=p["select_fg"], borderwidth=1, relief="solid",
            highlightbackground=p["border"], highlightthickness=1
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.on_tab(None))
        self.popup.withdraw()

    def is_visible(self):
        return self.popup.state() != "withdrawn"

    def hide(self):
        if self.after_id:
            self.editor.after_cancel(self.after_id)
            self.after_id = None
        if self.popup:
            self.popup.withdraw()

    def on_escape(self, event):
        if self.is_visible():
            self.hide()
            return "break"

    def on_return(self, event):
        if self.is_visible():
            return self.on_tab(event)

    def on_arrow_up(self, event):
        if self.is_visible():
            sel = self.listbox.curselection()
            idx = max(0, sel[0] - 1) if sel else 0
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            return "break"

    def on_arrow_down(self, event):
        if self.is_visible():
            sel = self.listbox.curselection()
            idx = min(len(self.matches) - 1, sel[0] + 1) if sel else 0
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(idx)
            self.listbox.see(idx)
            return "break"

    def on_tab(self, event):
        if self.is_visible():
            sel = self.listbox.curselection()
            idx = sel[0] if sel else 0
            if self.matches and 0 <= idx < len(self.matches):
                word, kind = self.matches[idx]
                self.insert_completion(word, kind)
            self.hide()
            return "break"

    def insert_completion(self, word, kind):
        if kind == "keyword":
            word = word.upper()
        import re
        cur_pos = self.editor.index("insert")
        line_start = f"{cur_pos.split('.')[0]}.0"
        line_text = self.editor.get(line_start, cur_pos)

        m = re.search(r"([\w\.]+)$", line_text)
        token = m.group(1) if m else ""
        if "." in token:
            _, col_part = token.split(".", 1)
            replace_len = len(col_part)
        else:
            replace_len = len(token)

        start_pos = self.editor.index(f"{cur_pos} - {replace_len} chars") if replace_len > 0 else cur_pos
        self.editor.delete(start_pos, cur_pos)
        self.editor.insert(start_pos, word)

    def on_ctrl_space(self, event):
        self.trigger_autocomplete(force=True)
        return "break"

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Escape", "Return", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        if self.after_id:
            self.editor.after_cancel(self.after_id)
        self.after_id = self.editor.after(120, lambda: self.trigger_autocomplete(force=False))

    def trigger_autocomplete(self, force=False):
        self.after_id = None
        cur_pos = self.editor.index("insert")
        line_start = f"{cur_pos.split('.')[0]}.0"
        line_text = self.editor.get(line_start, cur_pos)

        import re
        m = re.search(r"([\w\.]+)$", line_text)
        token = m.group(1) if m else ""

        if not force and len(token) < 2 and "." not in token:
            self.hide()
            return

        schema = self.get_schema() or []
        tables = [t["name"] for t in schema]
        columns_by_table = {t["name"].lower(): [c["name"] for c in t["columns"]] for t in schema}
        all_columns = []
        for cols in columns_by_table.values():
            all_columns.extend(cols)

        before = line_text[:-len(token)].strip().upper() if token else line_text.strip().upper()
        tokens_before = before.split()
        last_kw = tokens_before[-1] if tokens_before else ""

        suggestions = []
        if "." in token:
            tbl_prefix, col_prefix = token.split(".", 1)
            cols = columns_by_table.get(tbl_prefix.lower(), [])
            for c in cols:
                if c.lower().startswith(col_prefix.lower()):
                    suggestions.append((c, "column"))
        elif last_kw in ("FROM", "JOIN", "INTO", "UPDATE", "TABLE"):
            for t in tables:
                if t.lower().startswith(token.lower()):
                    suggestions.append((t, "table"))
        else:
            for kw in SQL_KEYWORDS:
                if kw.lower().startswith(token.lower()):
                    suggestions.append((kw, "keyword"))
            for t in tables:
                if t.lower().startswith(token.lower()):
                    suggestions.append((t, "table"))
            for c in set(all_columns):
                if c.lower().startswith(token.lower()):
                    suggestions.append((c, "column"))

        if not suggestions:
            self.hide()
            return

        self.matches = suggestions[:10]
        self.show_popup()

    def show_popup(self):
        p = get_palette()
        self.listbox.config(
            bg=p["surface"], fg=p["text"], selectbackground=p["select_bg"],
            selectforeground=p["select_fg"], highlightbackground=p["border"]
        )
        self.listbox.delete(0, "end")
        for word, kind in self.matches:
            self.listbox.insert("end", f"{word:<20} [{kind}]")
        self.listbox.selection_set(0)

        bbox = self.editor.bbox("insert")
        if bbox:
            x = self.editor.winfo_rootx() + bbox[0]
            y = self.editor.winfo_rooty() + bbox[1] + bbox[3] + 2
            self.popup.geometry(f"220x150+{x}+{y}")
        self.popup.deiconify()
        self.popup.lift()
