import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from gui.dialogs import NewTableDialog
from gui.theme import get_palette

class Sidebar(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.collapsed = False
        self.selected_table = None
        self.table_items = {}

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        # Database Header & Menu
        top_frame = ttk.Frame(self, padding=(10, 10, 10, 6))
        top_frame.pack(fill="x", side="top")

        self.db_menu_btn = tk.Menubutton(
            top_frame,
            text="No Database ▾",
            font=("Segoe UI", 10, "bold"),
            bg=p["bg"],
            fg=p["text"],
            relief="flat",
            cursor="hand2"
        )
        self.db_menu = tk.Menu(self.db_menu_btn, tearoff=0)
        self.db_menu.add_command(label="Open database...", command=self.app.on_open_database)
        self.db_menu.add_command(label="New database...", command=self.app.on_new_database)
        self.db_menu.add_command(label="Close database", command=self.app.on_close_database)
        self.db_menu_btn.config(menu=self.db_menu)
        self.db_menu_btn.pack(side="left")

        # Collapse handle button
        self.collapse_btn = ttk.Button(top_frame, text="‹", width=2, command=self.toggle_collapse)
        self.collapse_btn.pack(side="right")

        # Tables Section Header
        tables_hdr = ttk.Frame(self, padding=(10, 8, 10, 4))
        tables_hdr.pack(fill="x", side="top")

        ttk.Label(tables_hdr, text="TABLES", style="Muted.TLabel", font=("Segoe UI", 8, "bold")).pack(side="left")
        self.new_tbl_btn = tk.Label(
            tables_hdr, text="+", font=("Segoe UI", 11, "bold"),
            fg=p["accent"], bg=p["bg"], cursor="hand2"
        )
        self.new_tbl_btn.pack(side="right")
        self.new_tbl_btn.bind("<Button-1>", lambda e: self.open_new_table_dialog())

        # Tables list area (using Canvas or Treeview / Listbox)
        # A Treeview without headings provides clean two-column display: table name and count
        list_frame = ttk.Frame(self, padding=(6, 0))
        list_frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(list_frame, columns=("name", "count"), show="", selectmode="browse")
        self.tree.column("name", width=140, anchor="w")
        self.tree.column("count", width=50, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_table_selected)

        # Bottom Bar: User, Logout, Dark Mode toggle
        bottom_frame = ttk.Frame(self, padding=(10, 10))
        bottom_frame.pack(fill="x", side="bottom")

        self.user_lbl = ttk.Label(bottom_frame, text=self.app.username, style="Bold.TLabel")
        self.user_lbl.pack(side="left")

        self.logout_lbl = tk.Label(
            bottom_frame, text="Log out", fg=p["accent"],
            bg=p["bg"], cursor="hand2", font=("Segoe UI", 9, "underline")
        )
        self.logout_lbl.pack(side="left", padx=(10, 0))
        self.logout_lbl.bind("<Button-1>", lambda e: self.app.on_logout())

        self.theme_btn = tk.Label(
            bottom_frame, text="☾", font=("Segoe UI", 11),
            fg=p["text"], bg=p["bg"], cursor="hand2"
        )
        self.theme_btn.pack(side="right")
        self.theme_btn.bind("<Button-1>", lambda e: self.app.toggle_theme())

    def update_db_name(self, path):
        if path:
            name = os.path.basename(path)
            self.db_menu_btn.config(text=f"{name} ▾")
        else:
            self.db_menu_btn.config(text="No Database ▾")

    def refresh_tables(self, tables_info):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.table_items = {}

        for t in tables_info:
            tname = t["name"]
            cnt = t["row_count"]
            item_id = self.tree.insert("", "end", values=(tname, f"{cnt} rows"))
            self.table_items[tname] = item_id

        if self.selected_table and self.selected_table in self.table_items:
            self.tree.selection_set(self.table_items[self.selected_table])

    def on_table_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        if vals:
            tname = vals[0]
            self.selected_table = tname
            self.app.open_tab("table", tname)

    def select_table_by_name(self, tname):
        self.selected_table = tname
        if tname in self.table_items:
            self.tree.selection_set(self.table_items[tname])
        else:
            self.tree.selection_remove(self.tree.selection())

    def open_new_table_dialog(self):
        if not self.app.db.con:
            messagebox.showinfo("New Table", "Please open or create a database first.", parent=self)
            return

        def create_cb(sql):
            res = self.app.db.run(sql)
            if res.error:
                messagebox.showerror("Error Creating Table", res.error, parent=self)
            else:
                self.app.refresh_tables()
                self.app.update_pending()

        NewTableDialog(self, create_cb)

    def toggle_collapse(self):
        self.app.toggle_sidebar()
