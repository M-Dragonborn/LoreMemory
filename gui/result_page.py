import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from gui.theme import get_palette

class ResultPage(tk.Frame):
    def __init__(self, parent, app):
        p = get_palette()
        super().__init__(parent, bg=p["surface"])
        self.app = app
        self.result = None
        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        self.top_bar = tk.Frame(
            self, bg=p["panel"], padx=8, pady=6,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.top_bar.pack(fill="x", side="top", padx=3, pady=3)

        tk.Label(self.top_bar, text="📊", font=("Segoe UI", 10), fg=p["accent"], bg=p["panel"]).pack(side="left", padx=(0, 4))
        tk.Label(self.top_bar, text="Query Results", font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"]).pack(side="left", padx=(0, 8))

        self.info_label = tk.Label(self.top_bar, text="", font=("Segoe UI", 9), bg=p["panel"], fg=p["muted"])
        self.info_label.pack(side="left")

        self.grid_frame = tk.Frame(self, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        self.grid_frame.pack(fill="both", expand=True, padx=3, pady=1)

        self.tree = ttk.Treeview(self.grid_frame, selectmode="browse", show="headings")
        v_scroll = ttk.Scrollbar(self.grid_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(self.grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.grid_frame.rowconfigure(0, weight=1)
        self.grid_frame.columnconfigure(0, weight=1)
        self._apply_tag_styles(p)

    def _apply_tag_styles(self, p):
        self.tree.tag_configure("even", background=p["surface"], foreground=p["text"])
        self.tree.tag_configure("odd", background=p.get("grid_alt", p["panel"]), foreground=p["text"])

    def display(self, result):
        self.result = result
        cols = result.columns or []
        rows = result.rows or []

        info_txt = f"{len(rows)} rows, {result.elapsed_ms:.1f} ms"
        if result.truncated: info_txt += " (Result cut at 1000 rows)"
        self.info_label.config(text=info_txt)

        self.tree["columns"] = cols
        f = tkfont.Font(font=("Segoe UI", 9))
        sample = rows[:50]
        for idx, c in enumerate(cols):
            self.tree.heading(c, text=c)
            hw = f.measure(str(c)) + 32
            cw = max((f.measure(str(r[idx])) for r in sample if idx < len(r) and r[idx] is not None), default=0) + 24
            self.tree.column(c, width=min(max(hw, cw, 70), 380), minwidth=50)

        children = self.tree.get_children()
        if children: self.tree.delete(*children)

        for idx, r in enumerate(rows):
            display_vals = ["" if v is None else str(v) for v in r]
            tag = "odd" if idx % 2 else "even"
            self.tree.insert("", "end", values=display_vals, tags=(tag,))

        self.app.update_status(table_rows=len(rows))

    def reload(self):
        if self.result: self.display(self.result)

    def on_close(self):
        pass

    def apply_theme(self, p):
        self.config(bg=p["surface"])
        self.top_bar.config(bg=p["panel"], highlightbackground=p["border"])
        for child in self.top_bar.winfo_children():
            if isinstance(child, tk.Label): child.config(bg=p["panel"], fg=p["text"])
        self.info_label.config(bg=p["panel"], fg=p["muted"])
        self.grid_frame.config(bg=p["surface"], highlightbackground=p["border"])
        self._apply_tag_styles(p)
