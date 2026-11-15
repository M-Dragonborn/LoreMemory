import tkinter as tk
from tkinter import ttk, messagebox
from config import PAGE_SIZE
from gui.dialogs import RowDialog
from gui.theme import get_palette

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

        self.setup_ui()
        self.reload()

    def setup_ui(self):
        p = get_palette()

        # Top bar: Filter and Action buttons with border
        top_bar = tk.Frame(
            self, bg=p["panel"], padx=10, pady=8,
            highlightbackground=p["border"], highlightthickness=1
        )
        top_bar.pack(fill="x", side="top", padx=4, pady=4)

        tk.Label(top_bar, text="Filter:", bg=p["panel"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 6))
        self.filter_entry = ttk.Entry(top_bar, width=24)
        self.filter_entry.pack(side="left", padx=(0, 16))
        self.filter_entry.bind("<KeyRelease>", self.on_filter_changed)

        ttk.Button(top_bar, text="Add Row", command=self.on_add_row).pack(side="left", padx=3)
        ttk.Button(top_bar, text="Edit Selected", command=self.on_edit_row).pack(side="left", padx=3)
        ttk.Button(top_bar, text="Delete Selected", command=self.on_delete_row).pack(side="left", padx=3)

        # Bottom bar: Paging & Table History with border
        bot_bar = tk.Frame(
            self, bg=p["panel"], padx=10, pady=8,
            highlightbackground=p["border"], highlightthickness=1
        )
        bot_bar.pack(fill="x", side="bottom", padx=4, pady=4)

        self.prev_btn = ttk.Button(bot_bar, text="‹ Previous", command=self.on_prev_page)
        self.prev_btn.pack(side="left", padx=3)

        self.next_btn = ttk.Button(bot_bar, text="Next ›", command=self.on_next_page)
        self.next_btn.pack(side="left", padx=3)

        self.page_label = tk.Label(bot_bar, text="", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9, "bold"))
        self.page_label.pack(side="left", padx=16)

        ttk.Button(
            bot_bar,
            text="Open table history",
            command=lambda: self.app.open_tab("history", self.table_name)
        ).pack(side="right", padx=3)

        # Center: Treeview Grid enclosed in distinct outline
        grid_frame = tk.Frame(
            self, bg=p["surface"],
            highlightbackground=p["border_dark"], highlightthickness=1
        )
        grid_frame.pack(fill="both", expand=True, padx=4, pady=2)

        self.tree = ttk.Treeview(grid_frame, selectmode="browse", show="headings")
        v_scroll = ttk.Scrollbar(grid_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(grid_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        grid_frame.rowconfigure(0, weight=1)
        grid_frame.columnconfigure(0, weight=1)

    def on_filter_changed(self, event=None):
        if self.filter_after_id:
            self.after_cancel(self.filter_after_id)
        self.filter_after_id = self.after(300, self.apply_filter)

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
        self.columns = cols
        self.rows = rows
        self.total_count = total

        self.tree["columns"] = cols
        for c in cols:
            indicator = ""
            if c == self.order_by:
                indicator = " ▼" if self.descending else " ▲"
            self.tree.heading(c, text=f"{c}{indicator}", command=lambda col=c: self.on_sort(col))
            self.tree.column(c, width=120, minwidth=60)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in rows:
            display_vals = ["" if v is None else str(v) for v in r]
            self.tree.insert("", "end", values=display_vals)

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
