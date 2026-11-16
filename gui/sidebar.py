import os
import tkinter as tk
from tkinter import ttk, messagebox
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
        self.item_to_table = {}

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        # Database Header & Menu
        self.top_frame = tk.Frame(self, bg=p["panel"], padx=8, pady=8, highlightbackground=p["border"], highlightthickness=1)
        self.top_frame.pack(fill="x", side="top", padx=3, pady=3)

        self.db_menu_btn = tk.Menubutton(
            self.top_frame, text="No Database ▾", font=("Segoe UI", 10, "bold"),
            bg=p["surface"], fg=p["text"], relief="solid", bd=1, padx=8, pady=3, cursor="hand2"
        )
        self.db_menu = tk.Menu(self.db_menu_btn, tearoff=0)
        self.db_menu.add_command(label="Open database...", command=self.app.on_open_database)
        self.db_menu.add_command(label="New database...", command=self.app.on_new_database)
        self.db_menu.add_command(label="Close database", command=self.app.on_close_database)
        self.db_menu_btn.config(menu=self.db_menu)
        self.db_menu_btn.pack(side="left")

        self.collapse_btn = ttk.Button(self.top_frame, text="‹", width=2, command=self.toggle_collapse)
        self.collapse_btn.pack(side="right")

        # Section Header (Registry Editor Style)
        self.tables_hdr = tk.Frame(self, bg=p["bg"], padx=8, pady=5)
        self.tables_hdr.pack(fill="x", side="top")
        self.tables_lbl = tk.Label(self.tables_hdr, text="OBJECT EXPLORER", bg=p["bg"], fg=p["muted"], font=("Segoe UI", 8, "bold"))
        self.tables_lbl.pack(side="left")

        self.new_tbl_btn = tk.Label(
            self.tables_hdr, text=" + New Table ", font=("Segoe UI", 9, "bold"),
            fg=p["accent_text"], bg=p["accent"], cursor="hand2", relief="flat", padx=4, pady=1
        )
        self.new_tbl_btn.pack(side="right")
        self.new_tbl_btn.bind("<Button-1>", lambda e: self.open_new_table_dialog())

        # Bottom Bar: User, Logout, Dark Mode toggle
        self.bottom_frame = tk.Frame(self, bg=p["panel"], padx=8, pady=6, highlightbackground=p["border"], highlightthickness=1)
        self.bottom_frame.pack(fill="x", side="bottom", padx=3, pady=3)

        role = getattr(self.app, "role", "user")
        if role in ("admin", "super_admin"):
            self.admin_frame = tk.Frame(self, bg=p["panel"], padx=4, pady=4, highlightbackground=p["border"], highlightthickness=1)
            self.admin_frame.pack(fill="x", side="bottom", padx=3, pady=(0, 2))
            self.admin_btn = tk.Button(
                self.admin_frame, text="⚙ Admin Panel", font=("Segoe UI", 9, "bold"),
                bg=p["surface"], fg=p["accent"], relief="flat", cursor="hand2", pady=2,
                command=self._on_admin_click
            )
            self.admin_btn.pack(fill="x")

        # Tables list area enclosed with 1px border
        self.list_frame = tk.Frame(self, bg=p["bg"], padx=3, pady=1)
        self.list_frame.pack(fill="both", expand=True)

        self.tree_border = tk.Frame(self.list_frame, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        self.tree_border.pack(fill="both", expand=True)

        self.tree_scroll = ttk.Scrollbar(self.tree_border, orient="vertical")
        self.tree = ttk.Treeview(self.tree_border, show="tree", selectmode="browse", yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.config(command=self.tree.yview)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)
        self.tree.bind("<Double-Button-1>", self.on_tree_activate)
        self.tree.bind("<Return>", self.on_tree_activate)
        self.tree.bind("<Button-3>", self.on_context_menu)

        u_txt = f"{self.app.username} ({role})" if role != "user" else self.app.username
        self.user_lbl = tk.Label(self.bottom_frame, text=u_txt, bg=p["panel"], fg=p["text"], font=("Segoe UI", 9, "bold"))
        self.user_lbl.pack(side="left")

        self.logout_lbl = tk.Label(self.bottom_frame, text="Log out", fg=p["accent"], bg=p["panel"], cursor="hand2", font=("Segoe UI", 9, "bold", "underline"))
        self.logout_lbl.pack(side="left", padx=(10, 0))
        self.logout_lbl.bind("<Button-1>", lambda e: self.app.on_logout())

        self.theme_btn = tk.Label(self.bottom_frame, text=" ☾ ", font=("Segoe UI", 10), fg=p["text"], bg=p["surface"], relief="solid", bd=1, cursor="hand2")
        self.theme_btn.pack(side="right")
        self.theme_btn.bind("<Button-1>", lambda e: self.app.toggle_theme())

        self._apply_tag_styles(p)
        self.refresh_tables([])

    def _apply_tag_styles(self, p):
        self.tree.tag_configure("db_root", font=("Segoe UI", 9, "bold"), foreground=p["text"])
        self.tree.tag_configure("folder", font=("Segoe UI", 9), foreground=p["text"])
        self.tree.tag_configure("table", font=("Segoe UI", 9), foreground=p["text"])
        self.tree.tag_configure("column", font=("Segoe UI", 9), foreground=p["text"])
        self.tree.tag_configure("action", font=("Segoe UI", 9), foreground=p["text"])

    def apply_theme(self, p):
        self.config(bg=p["bg"], highlightbackground=p["border"])
        self.top_frame.config(bg=p["panel"], highlightbackground=p["border"])
        self.db_menu_btn.config(bg=p["surface"], fg=p["text"])
        self.tables_hdr.config(bg=p["bg"])
        self.tables_lbl.config(bg=p["bg"], fg=p["muted"])
        self.new_tbl_btn.config(bg=p["accent"], fg=p["accent_text"])
        self.list_frame.config(bg=p["bg"])
        self.tree_border.config(bg=p["surface"], highlightbackground=p["border"])
        self.bottom_frame.config(bg=p["panel"], highlightbackground=p["border"])
        self.user_lbl.config(bg=p["panel"], fg=p["text"])
        self.logout_lbl.config(bg=p["panel"], fg=p["accent"])
        self.theme_btn.config(bg=p["surface"], fg=p["text"])
        if hasattr(self, "admin_frame"):
            self.admin_frame.config(bg=p["panel"], highlightbackground=p["border"])
            self.admin_btn.config(bg=p["surface"], fg=p["accent"])
        self._apply_tag_styles(p)

    def update_db_name(self, path):
        if path:
            self.db_menu_btn.config(text=f"{os.path.basename(path)} ▾")
        else:
            self.db_menu_btn.config(text="No Database ▾")

    def refresh_tables(self, tables_info=None):
        if tables_info is None:
            tables_info = self.app.db.get_table_info() if (self.app.db and self.app.db.con) else []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.table_items = {}
        self.item_to_table = {}

        if not self.app.db or not self.app.db.con:
            root_id = self.tree.insert("", "end", text="  (No Database Loaded)", open=True, tags=("db_root",))
            self.tree.insert(root_id, "end", text="📂  Open SQLite Database...", tags=("action", "action_open"))
            self.tree.insert(root_id, "end", text="➕  Create New Database...", tags=("action", "action_new"))
            return

        db_name = os.path.basename(self.app.db.path) if self.app.db.path else "Database"
        root_id = self.tree.insert("", "end", text=f"🗄️  {db_name}", open=True, tags=("db_root",))

        tbl_folder = self.tree.insert(root_id, "end", text=f"📁  Tables ({len(tables_info)})", open=True, tags=("folder",))

        for t in tables_info:
            tname = t["name"]
            cnt = t.get("row_count", 0)
            cols = t.get("columns", [])
            node_text = f"📄  {tname}  [{cnt}]"
            tbl_id = self.tree.insert(tbl_folder, "end", text=node_text, open=False, tags=("table",))
            self.table_items[tname] = tbl_id
            self.item_to_table[tbl_id] = tname

            for c in cols:
                prefix = "🔑 " if c.get("pk") else ("🔗 " if c.get("fk") else "▫ ")
                tag_desc = f"{c['name']} : {c['type']}"
                if c.get("fk"): tag_desc += f" → {c['fk']}"
                self.tree.insert(tbl_id, "end", text=f"   {prefix}{tag_desc}", tags=("column",))

        self.tree.insert(tbl_folder, "end", text="➕  New Table...", tags=("action", "action_new_tbl"))

        if self.selected_table and self.selected_table in self.table_items:
            self.select_table_by_name(self.selected_table)

    def on_tree_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        tags = self.tree.item(item_id, "tags")
        if "action_open" in tags:
            self.app.on_open_database()
        elif "action_new" in tags:
            self.app.on_new_database()
        elif "action_new_tbl" in tags:
            self.open_new_table_dialog()
        elif "table" in tags:
            tname = self.item_to_table.get(item_id)
            if tname:
                self.selected_table = tname
                self.app.open_tab("table", tname)
        elif "column" in tags:
            parent_id = self.tree.parent(item_id)
            tname = self.item_to_table.get(parent_id)
            if tname:
                self.selected_table = tname
                self.app.open_tab("table", tname)

    def on_tree_activate(self, event):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        tags = self.tree.item(item_id, "tags")
        if "table" in tags:
            tname = self.item_to_table.get(item_id)
            if tname:
                self.selected_table = tname
                self.app.open_tab("table", tname)
        elif "column" in tags:
            tname = self.item_to_table.get(self.tree.parent(item_id))
            if tname:
                self.selected_table = tname
                self.app.open_tab("table", tname)
        elif "action_open" in tags: self.app.on_open_database()
        elif "action_new" in tags: self.app.on_new_database()
        elif "action_new_tbl" in tags: self.open_new_table_dialog()

    def on_context_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        tname = None
        if item_id:
            self.tree.selection_set(item_id)
            tags = self.tree.item(item_id, "tags")
            if "table" in tags: tname = self.item_to_table.get(item_id)
            elif "column" in tags: tname = self.item_to_table.get(self.tree.parent(item_id))

        m = tk.Menu(self, tearoff=0)
        if tname:
            m.add_command(label=f"Open '{tname}'", command=lambda t=tname: self.app.open_tab("table", t))
            m.add_command(label=f"Table History", command=lambda t=tname: self.app.open_tab("history", t))
            m.add_separator()
            m.add_command(label="Copy Table Name", command=lambda t=tname: self._copy_to_clipboard(t))
            m.add_separator()
        m.add_command(label="New Table...", command=self.open_new_table_dialog)
        m.add_command(label="Refresh", command=self.app.refresh_tables)
        m.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text):
        try:
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception: pass

    def select_table_by_name(self, tname):
        self.selected_table = tname
        if tname in self.table_items:
            item_id = self.table_items[tname]
            p_id = self.tree.parent(item_id)
            while p_id:
                self.tree.item(p_id, open=True)
                p_id = self.tree.parent(p_id)
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
        else:
            sel = self.tree.selection()
            if sel: self.tree.selection_remove(sel)

    def open_new_table_dialog(self):
        if not self.app.db.con:
            messagebox.showinfo("New Table", "Please open or create a database first.", parent=self.app.root)
            return

        def create_cb(sql):
            res = self.app.db.run(sql)
            if res.error:
                messagebox.showerror("Error Creating Table", res.error, parent=self.app.root)
            else:
                self.app.refresh_tables()
                self.app.update_pending()

        NewTableDialog(self.app.root, create_cb)

    def toggle_collapse(self):
        self.app.toggle_sidebar()

    def _on_admin_click(self):
        try:
            self.app.open_tab("admin", None)
        except Exception as e:
            try:
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"admin_btn error: {e}\n")
            except Exception: pass
            messagebox.showerror("Admin Error", str(e), parent=self.app.root)
