import tkinter as tk
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

        self.info_label = tk.Label(
            self.top_bar, text="", font=("Segoe UI", 9, "bold"),
            bg=p["panel"], fg=p["text"]
        )
        self.info_label.pack(side="left")

        grid_frame = tk.Frame(
            self, bg=p["surface"],
            highlightbackground=p["border"], highlightthickness=1
        )
        grid_frame.pack(fill="both", expand=True, padx=3, pady=1)

        self.tree = ttk.Treeview(grid_frame, selectmode="browse", show="headings")
        v_scroll = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        grid_frame.rowconfigure(0, weight=1)
        grid_frame.columnconfigure(0, weight=1)

    def display(self, result):
        self.result = result
        cols = result.columns or []
        rows = result.rows or []

        info_txt = f"{len(rows)} rows, {result.elapsed_ms:.1f} ms"
        if result.truncated:
            info_txt += " (Result cut at 1000 rows)"
        self.info_label.config(text=info_txt)

        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, minwidth=60)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in rows:
            display_vals = ["" if v is None else str(v) for v in r]
            self.tree.insert("", "end", values=display_vals)

        self.app.update_status(table_rows=len(rows))

    def reload(self):
        if self.result:
            self.display(self.result)

    def on_close(self):
        pass
