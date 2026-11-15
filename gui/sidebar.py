import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from gui.dialogs import NewTableDialog
from gui.theme import get_palette

class Sidebar(tk.Frame):
    def __init__(self, parent, app):
        p = get_palette()
        super().__init__(parent, bg=p["bg"], highlightbackground=p["border"], highlightthickness=1)
        self.app = app
        self.collapsed = False
        self.selected_table = None
        self.table_items = {}

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        # Database Header & Menu
        top_frame = tk.Frame(self, bg=p["panel"], padx=8, pady=8, highlightbackground=p["border"], highlightthickness=1)
        top_frame.pack(fill="x", side="top", padx=3, pady=3)

        self.db_menu_btn = tk.Menubutton(
            top_frame,
            text="No Database ▾",
            font=("Segoe UI", 10, "bold"),
            bg=p["surface"],
            fg=p["text"],
            relief="solid",
            bd=1,
            padx=8,
            pady=3,
            cursor="hand2"
        )
        self.db_menu = tk.Menu(self.db_menu_btn, tearoff=0)
        self.db_menu.add_command(label="Open database...", command=self.app.on_open_database)
        self.db_menu.add_command(label="New database...", command=self.app.on_new_database)
        self.db_menu.add_command(label="Close database", command=self.app.on_close_database)
        self.db_menu_btn.config(menu=self.db_menu)
        self.db_menu_btn.pack(side="left")

        self.collapse_btn = ttk.Button(top_frame, text="‹", width=2, command=self.toggle_collapse)
        self.collapse_btn.pack(side="right")

        # Tables Section Header
        tables_hdr = tk.Frame(self, bg=p["bg"], padx=8, pady=6)
        tables_hdr.pack(fill="x", side="top")

        tk.Label(
            tables_hdr, text="TABLES", bg=p["bg"], fg=p["muted"],
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        self.new_tbl_btn = tk.Label(
            tables_hdr, text=" + ", font=("Segoe UI", 11, "bold"),
            fg=p["accent_text"], bg=p["accent"], cursor="hand2", relief="flat"
        )
        self.new_tbl_btn.pack(side="right")
        self.new_tbl_btn.bind("<Button-1>", lambda e: self.open_new_table_dialog())

        # Tables list area enclosed with soft 1px border
        list_frame = tk.Frame(self, bg=p["bg"], padx=3, pady=1)
        list_frame.pack(fill="both", expand=True)

        tree_border = tk.Frame(list_frame, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        tree_border.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(tree_border, columns=("name", "count"), show="", selectmode="browse")
        self.tree.column("name", width=140, anchor="w")
        self.tree.column("count", width=60, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_table_selected)

        # Bottom Bar: User, Logout, Dark Mode toggle
        bottom_frame = tk.Frame(
            self, bg=p["panel"], padx=8, pady=6,
            highlightbackground=p["border"], highlightthickness=1
        )
        bottom_frame.pack(fill="x", side="bottom", padx=3, pady=3)

        self.user_lbl = tk.Label(bottom_frame, text=self.app.username, bg=p["panel"], fg=p["text"], font=("Segoe UI", 9, "bold"))
        self.user_lbl.pack(side="left")

        self.logout_lbl = tk.Label(
            bottom_frame, text="Log out", fg=p["accent"],
            bg=p["panel"], cursor="hand2", font=("Segoe UI", 9, "bold", "underline")
        )
        self.logout_lbl.pack(side="left", padx=(10, 0))
        self.logout_lbl.bind("<Button-1>", lambda e: self.app.on_logout())

        self.theme_btn = tk.Label(
            bottom_frame, text=" ☾ ", font=("Segoe UI", 10),
            fg=p["text"], bg=p["surface"], relief="solid", bd=1, cursor="hand2"
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
