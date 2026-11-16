import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
from config import PAGE_SIZE
from gui.dialogs import RowDialog
from gui.theme import get_palette
from gui.widgets import TreeGrid

class TablePage(tk.Frame):
    def __init__(self, parent, app, table_name):
        p = get_palette()
        super().__init__(parent, bg=p["surface"])
        self.app = app
        self.table_name = table_name
        self.page = 1
        self.order_by = None
        self.descending = False
        self.search_text = ""
        self.filter_after_id = None
        self.columns = []
        self.rows = []
        self.total_count = 0
        self.cell_font = tkfont.Font(font=("Segoe UI", 9))

        self.setup_ui()
        self.reload()

    def setup_ui(self):
        p = get_palette()

        # Top bar with subtle border
        self.top_bar = tk.Frame(
            self, bg=p["panel"], padx=8, pady=6,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.top_bar.pack(fill="x", side="top", padx=3, pady=3)

        tk.Label(self.top_bar, text="▦", font=("Segoe UI", 10), fg=p["accent"], bg=p["panel"]).pack(side="left", padx=(0, 4))
        tk.Label(self.top_bar, text=self.table_name, font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"]).pack(side="left", padx=(0, 10))

        tk.Label(self.top_bar, text="Filter:", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.filter_entry = ttk.Entry(self.top_bar, width=20)
        self.filter_entry.pack(side="left", padx=(0, 10))
        self.filter_entry.bind("<KeyRelease>", self.on_filter_changed)

        ttk.Button(self.top_bar, text="Add Row", command=self.on_add_row).pack(side="left", padx=2)
        ttk.Button(self.top_bar, text="Edit Selected", command=self.on_edit_row).pack(side="left", padx=2)
        ttk.Button(self.top_bar, text="Delete Selected", command=self.on_delete_row).pack(side="left", padx=2)

        # Bottom bar with subtle border
        self.bot_bar = tk.Frame(
            self, bg=p["panel"], padx=8, pady=6,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.bot_bar.pack(fill="x", side="bottom", padx=3, pady=3)

        self.prev_btn = ttk.Button(self.bot_bar, text="‹ Previous", command=self.on_prev_page)
        self.prev_btn.pack(side="left", padx=2)

        self.next_btn = ttk.Button(self.bot_bar, text="Next ›", command=self.on_next_page)
        self.next_btn.pack(side="left", padx=2)

        self.page_label = tk.Label(self.bot_bar, text="", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9))
        self.page_label.pack(side="left", padx=12)

        ttk.Button(
            self.bot_bar,
            text="Open table history",
            command=lambda: self.app.open_tab("history", self.table_name)
        ).pack(side="right", padx=2)

        # Center Treeview with soft 1px border
        self.grid_frame = tk.Frame(
            self, bg=p["surface"],
            highlightbackground=p["border"], highlightthickness=1
        )
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
        self.tree_grid = TreeGrid(self.tree, h_scroll, lambda: get_palette().get("grid_line", "#cbd5e1"))
        self._apply_tag_styles(p)

    def _apply_tag_styles(self, p):
        self.tree.tag_configure("even", background=p["surface"], foreground=p["text"])
        self.tree.tag_configure("odd", background=p.get("grid_alt", p["panel"]), foreground=p["text"])

    def on_filter_changed(self, event=None):
        if self.filter_after_id:
            self.after_cancel(self.filter_after_id)
        self.filter_after_id = self.after(250, self.apply_filter)

    def apply_filter(self):
        self.filter_after_id = None
        self.search_text = self.filter_entry.get().strip()
        self.page = 1
        self.reload()

    def reload(self):
        cols, rows, total = self.app.db.get_rows(
            self.table_name,
            page=self.page,
            page_size=PAGE_SIZE,
            order_by=self.order_by,
            descending=self.descending,
            search=self.search_text
        )
        self.columns, self.rows, self.total_count = cols, rows, total

        self.tree["columns"] = cols
        sample = rows[:15]
        for idx, c in enumerate(cols):
            indicator = (" ▼" if self.descending else " ▲") if c == self.order_by else ""
            self.tree.heading(c, text=f"{c}{indicator}", command=lambda col=c: self.on_sort(col))
            hw = self.cell_font.measure(f"{c}{indicator}") + 32
            cw = max((self.cell_font.measure(str(r[idx])) for r in sample if idx < len(r) and r[idx] is not None), default=0) + 24
            self.tree.column(c, width=min(max(hw, cw, 70), 380), minwidth=50)

        children = self.tree.get_children()
        if children: self.tree.delete(*children)

        for idx, r in enumerate(rows):
            display_vals = ["" if v is None else str(v) for v in r]
            tag = "odd" if idx % 2 else "even"
            self.tree.insert("", "end", values=display_vals, tags=(tag,))

        self.tree_grid.schedule_update()
        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label.config(text=f"Page {self.page} of {total_pages} ({total} rows)")
        self.prev_btn.state(["!disabled" if self.page > 1 else "disabled"])
        self.next_btn.state(["!disabled" if self.page < total_pages else "disabled"])
        self.app.update_status(table_rows=total)

    def on_sort(self, col_name):
        if self.order_by == col_name:
            self.descending = not self.descending
        else:
            self.order_by = col_name
            self.descending = False
        self.reload()

    def on_prev_page(self):
        if self.page > 1:
            self.page -= 1
            self.reload()

    def on_next_page(self):
        total_pages = max(1, (self.total_count + PAGE_SIZE - 1) // PAGE_SIZE)
        if self.page < total_pages:
            self.page += 1
            self.reload()

    def _get_pk_info(self):
        meta_cols = self.app.db.get_columns(self.table_name)
        pk_cols = [c["name"] for c in meta_cols if c["pk"]]
        if pk_cols:
            return pk_cols[0], meta_cols
        return "_rowid", meta_cols

    def on_add_row(self):
        meta_cols = self.app.db.get_columns(self.table_name)
        dlg = RowDialog(self, f"Add Row - {self.table_name}", meta_cols)
        self.wait_window(dlg)
        if dlg.result is not None:
            res = self.app.db.insert_row(self.table_name, dlg.result)
            if res.error:
                messagebox.showerror("Insert Error", res.error, parent=self)
            else:
                self.reload()
                self.app.refresh_tables()
                self.app.update_pending()

    def on_edit_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Edit Row", "Please select a row to edit.", parent=self)
            return
        vals = self.tree.item(sel[0], "values")
        data = dict(zip(self.columns, vals))

        pk_col, meta_cols = self._get_pk_info()
        pk_val = data.get(pk_col)

        dlg = RowDialog(self, f"Edit Row - {self.table_name}", meta_cols, initial_values=data)
        self.wait_window(dlg)
        if dlg.result is not None:
            update_data = {k: v for k, v in dlg.result.items() if k != "_rowid"}
            res = self.app.db.update_row(self.table_name, pk_col, pk_val, update_data)
            if res.error:
                messagebox.showerror("Update Error", res.error, parent=self)
            else:
                self.reload()
                self.app.refresh_tables()
                self.app.update_pending()

    def on_delete_row(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Delete Row", "Please select a row to delete.", parent=self)
            return
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected row?", parent=self):
            return

        vals = self.tree.item(sel[0], "values")
        data = dict(zip(self.columns, vals))
        pk_col, _ = self._get_pk_info()
        pk_val = data.get(pk_col)

        res = self.app.db.delete_row(self.table_name, pk_col, pk_val)
        if res.error:
            messagebox.showerror("Delete Error", res.error, parent=self)
        else:
            self.reload()
            self.app.refresh_tables()
            self.app.update_pending()

    def on_close(self):
        if self.filter_after_id:
            self.after_cancel(self.filter_after_id)
            self.filter_after_id = None

    def apply_theme(self, p):
        self.config(bg=p["surface"])
        self.top_bar.config(bg=p["panel"], highlightbackground=p["border"])
        for child in self.top_bar.winfo_children():
            if isinstance(child, tk.Label): child.config(bg=p["panel"], fg=p["text"] if child.cget("font") and "bold" in str(child.cget("font")) else p["muted"])
        self.bot_bar.config(bg=p["panel"], highlightbackground=p["border"])
        self.page_label.config(bg=p["panel"], fg=p["muted"])
        self.grid_frame.config(bg=p["surface"], highlightbackground=p["border"])
        self.tree_grid.apply_theme(p)
        self._apply_tag_styles(p)
