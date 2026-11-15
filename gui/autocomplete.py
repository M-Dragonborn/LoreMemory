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
        self.current_prefix = ""
        self.replace_start = None

        self.editor.bind("<KeyRelease>", self.on_key_release)
        self.editor.bind("<Control-space>", self.on_ctrl_space)
        self.editor.bind("<Escape>", self.on_escape)
        self.editor.bind("<Tab>", self.on_tab)
        self.editor.bind("<Up>", self.on_arrow_up)
        self.editor.bind("<Down>", self.on_arrow_down)
        self.editor.bind("<Return>", self.on_return)

    def is_visible(self):
        return self.popup is not None and self.popup.winfo_exists()

    def hide(self):
        if self.popup:
            self.popup.destroy()
            self.popup = None

    def on_escape(self, event):
        if self.is_visible():
            self.hide()
            return "break"

    def on_return(self, event):
        if self.is_visible():
            self.hide()

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
            if sel:
                word, kind = self.matches[sel[0]]
                self.insert_completion(word, kind)
                self.hide()
                return "break"

    def insert_completion(self, word, kind):
        if kind == "keyword":
            word = word.upper()
        cur_pos = self.editor.index("insert")
        if self.replace_start:
            self.editor.delete(self.replace_start, cur_pos)
            self.editor.insert(self.replace_start, word)
        else:
            self.editor.insert("insert", word)

    def on_ctrl_space(self, event):
        self.trigger_autocomplete(force=True)
        return "break"

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Escape", "Return", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        self.trigger_autocomplete(force=False)

    def trigger_autocomplete(self, force=False):
        cur_pos = self.editor.index("insert")
        line_start = f"{cur_pos.split('.')[0]}.0"
        line_text = self.editor.get(line_start, cur_pos)

        # Find word boundary
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

        # Context detection
        before = line_text[:-len(token)].strip().upper() if token else line_text.strip().upper()
        tokens_before = before.split()
        last_kw = tokens_before[-1] if tokens_before else ""

        suggestions = []
        if "." in token:
            tbl_prefix, col_prefix = token.split(".", 1)
            tbl_key = tbl_prefix.lower()
            cols = columns_by_table.get(tbl_key, [])
            for c in cols:
                if c.lower().startswith(col_prefix.lower()):
                    suggestions.append((c, "column"))
            self.current_prefix = col_prefix
            self.replace_start = f"{cur_pos}-{len(col_prefix)}c"
        elif last_kw in ("FROM", "JOIN", "INTO", "UPDATE", "TABLE"):
            for t in tables:
                if t.lower().startswith(token.lower()):
                    suggestions.append((t, "table"))
            self.current_prefix = token
            self.replace_start = f"{cur_pos}-{len(token)}c"
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
            self.current_prefix = token
            self.replace_start = f"{cur_pos}-{len(token)}c"

        if not suggestions:
            self.hide()
            return

        self.matches = suggestions[:12]
        self.show_popup()

    def show_popup(self):
        p = get_palette()
        if not self.popup:
            self.popup = tk.Toplevel(self.editor)
            self.popup.wm_overrideredirect(True)
            self.listbox = tk.Listbox(
                self.popup, font=("Segoe UI", 9), selectmode="browse",
                bg=p["surface"], fg=p["text"], selectbackground=p["select_bg"],
                selectforeground=p["select_fg"], borderwidth=1, relief="solid"
            )
            self.listbox.pack(fill="both", expand=True)
            self.listbox.bind("<Double-Button-1>", lambda e: self.on_tab(None))

        self.listbox.delete(0, "end")
        for word, kind in self.matches:
            self.listbox.insert("end", f"{word:<20} [{kind}]")
        self.listbox.selection_set(0)

        # Position popup under text cursor
        bbox = self.editor.bbox("insert")
        if bbox:
            x = self.editor.winfo_rootx() + bbox[0]
            y = self.editor.winfo_rooty() + bbox[1] + bbox[3]
            self.popup.geometry(f"220x160+{x}+{y}")
            self.popup.lift()

