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

        self.db_menu_btn = tk.Menubutton(self.top_frame, text="No Database ▾", font=("Segoe UI", 10, "bold"), bg=p["surface"], fg=p["text"], relief="solid", bd=1, padx=8, pady=3, cursor="hand2")
        self.db_menu = tk.Menu(self.db_menu_btn, tearoff=0)
        for lbl, fn in [("Open database...", self.app.on_open_database), ("New database...", self.app.on_new_database), ("Close database", self.app.on_close_database)]:
            self.db_menu.add_command(label=lbl, command=fn)
        self.db_menu_btn.config(menu=self.db_menu); self.db_menu_btn.pack(side="left")

        self.collapse_btn = ttk.Button(self.top_frame, text="‹", width=2, command=self.toggle_collapse)
        self.collapse_btn.pack(side="right")

        # Section Header (Registry Editor Style)
        self.tables_hdr = tk.Frame(self, bg=p["bg"], padx=8, pady=5)
        self.tables_hdr.pack(fill="x", side="top")
        self.tables_lbl = tk.Label(self.tables_hdr, text="OBJECT EXPLORER", bg=p["bg"], fg=p["muted"], font=("Segoe UI", 8, "bold"))
        self.tables_lbl.pack(side="left")
        self.refresh_btn = ttk.Button(self.tables_hdr, text="⟳", width=2, command=self.app.refresh_database)
        self.refresh_btn.pack(side="left", padx=(6, 0))

        self.new_tbl_btn = tk.Label(self.tables_hdr, text=" + New Table ", font=("Segoe UI", 9, "bold"), fg=p["accent_text"], bg=p["accent"], cursor="hand2", relief="flat", padx=4, pady=1)
        self.new_tbl_btn.pack(side="right")
        self.new_tbl_btn.bind("<Button-1>", lambda e: self.after(10, self.open_new_table_dialog))

        # Bottom Bar: Symmetrical user profile & balanced action toolbar
        self.bottom_frame = tk.Frame(self, bg=p["panel"], padx=6, pady=6, highlightbackground=p["border"], highlightthickness=1)
        self.bottom_frame.pack(fill="x", side="bottom", padx=3, pady=3)

        role = getattr(self.app, "role", "user")
        user_row = tk.Frame(self.bottom_frame, bg=p["panel"])
        user_row.pack(fill="x", pady=(0, 4))
        self.user_lbl = tk.Label(user_row, text=f"👤 {self.app.username}", bg=p["panel"], fg=p["text"], font=("Segoe UI", 9, "bold"))
        self.user_lbl.pack(side="left")
        self.role_badge = tk.Label(user_row, text=f" {role.upper()} ", bg=p["surface"], fg=p["accent"], font=("Segoe UI", 7, "bold"), relief="solid", bd=1)
        self.role_badge.pack(side="right")

        self.btn_row = tk.Frame(self.bottom_frame, bg=p["panel"])
        self.btn_row.pack(fill="x")

        is_admin = role in ("admin", "super_admin")
        col_idx = 0
        if is_admin:
            self.admin_btn = tk.Button(self.btn_row, text="⚙ Admin", font=("Segoe UI", 8, "bold"),
                                       bg=p["surface"], fg=p["accent"], relief="solid", bd=1, cursor="hand2", pady=3,
                                       command=self._on_admin_click)
            self.admin_btn.grid(row=0, column=col_idx, sticky="ew", padx=(0, 2))
            self.btn_row.columnconfigure(col_idx, weight=3)
            col_idx += 1

        self.logout_btn = tk.Button(self.btn_row, text="⎋ Logout", font=("Segoe UI", 8, "bold"),
                                    bg=p["surface"], fg=p["text"], relief="solid", bd=1, cursor="hand2", pady=3,
                                    command=lambda: self.app.on_logout())
        self.logout_btn.grid(row=0, column=col_idx, sticky="ew", padx=2 if is_admin else (0, 2))
        self.btn_row.columnconfigure(col_idx, weight=3)
        col_idx += 1

        self.theme_btn = tk.Button(self.btn_row, text="☾", font=("Segoe UI", 9, "bold"),
                                   bg=p["surface"], fg=p["text"], relief="solid", bd=1, cursor="hand2", pady=3,
                                   command=lambda: self.app.toggle_theme())
        self.theme_btn.grid(row=0, column=col_idx, sticky="ew", padx=(2, 0))
        self.btn_row.columnconfigure(col_idx, weight=1 if is_admin else 2)

        # Tables list area enclosed with 1px border
        self.list_frame = tk.Frame(self, bg=p["bg"], padx=3, pady=1)
        self.list_frame.pack(fill="both", expand=True)

        self.tree_border = tk.Frame(self.list_frame, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        self.tree_border.pack(fill="both", expand=True)

        self.tree_scroll = ttk.Scrollbar(self.tree_border, orient="vertical")
        self.tree = ttk.Treeview(self.tree_border, show="tree", selectmode="browse", yscrollcommand=self.tree_scroll.set, style="Sidebar.Treeview")
        self.tree_scroll.config(command=self.tree.yview)
        self.tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        for ev, fn in [("<ButtonRelease-1>", self.on_tree_click), ("<Double-Button-1>", self.on_tree_activate),
                       ("<Return>", self.on_tree_activate), ("<Button-3>", self.on_context_menu)]:
            self.tree.bind(ev, fn)

        self._apply_tag_styles(p)
        self.refresh_tables([])

    def _apply_tag_styles(self, p):
        self.tree.tag_configure("db_root", font=("Segoe UI", 9, "bold"), foreground=p["text"])
        for tag in ("folder", "table", "column", "action"):
            self.tree.tag_configure(tag, font=("Segoe UI", 9), foreground=p["text"])

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
        self.role_badge.config(bg=p["surface"], fg=p["accent"])
        self.btn_row.config(bg=p["panel"])
        self.logout_btn.config(bg=p["surface"], fg=p["text"])
        self.theme_btn.config(bg=p["surface"], fg=p["text"])
        if hasattr(self, "admin_btn"):
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
        ch = self.tree.get_children()
        if ch: self.tree.delete(*ch)
        self.table_items, self.item_to_table = {}, {}

        if not self.app.db or not self.app.db.con:
            root_id = self.tree.insert("", "end", text="  (No Database Loaded)", open=True, tags=("db_root",))
            self.tree.insert(root_id, "end", text="📂  Open SQLite Database...", tags=("action", "action_open"))
            self.tree.insert(root_id, "end", text="➕  Create New Database...", tags=("action", "action_new"))
            return

        db_name = os.path.basename(self.app.db.path) if self.app.db.path else "Database"
        root_id = self.tree.insert("", "end", text=f"🗄️  {db_name}", open=True, tags=("db_root",))

        tbl_folder = self.tree.insert(root_id, "end", text=f"📁  Tables ({len(tables_info)})", open=True, tags=("folder",))

        for t in tables_info:
            tname, cnt, cols = t["name"], t.get("row_count", 0), t.get("columns", [])
            tbl_id = self.tree.insert(tbl_folder, "end", text=f"📄  {tname}  [{cnt}]", open=False, tags=("table",))
            self.table_items[tname], self.item_to_table[tbl_id] = tbl_id, tname

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
        if item_id: self._handle_item(item_id)

    def on_tree_activate(self, event):
        sel = self.tree.selection()
        if sel: self._handle_item(sel[0])

    def _handle_item(self, item_id):
        tags = self.tree.item(item_id, "tags")
        if "action_open" in tags: self.app.on_open_database()
        elif "action_new" in tags: self.app.on_new_database()
        elif "action_new_tbl" in tags: self.open_new_table_dialog()
        elif "table" in tags or "column" in tags:
            tname = self.item_to_table.get(item_id if "table" in tags else self.tree.parent(item_id))
            if tname and (self.selected_table != tname or self.app.tabs.active_key != f"table:{tname}"):
                self.selected_table = tname
                self.app.open_tab("table", tname)

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
        if not self.app.db or not self.app.db.con:
            messagebox.showinfo("New Table", "Please open or create a database first.", parent=self.app.root); return
        def create_cb(sql, tname=None):
            res = self.app.db.run(sql)
            if res.error: messagebox.showerror("Error Creating Table", res.error, parent=self.app.root); return False
            self.app.refresh_tables(); self.app.update_pending()
            if tname: self.select_table_by_name(tname); self.app.open_tab("table", tname)
            return True
        try: NewTableDialog(self.app.root, create_cb)
        except Exception as e: messagebox.showerror("New Table Error", str(e), parent=self.app.root)

    def toggle_collapse(self): self.app.toggle_sidebar()

    def _on_admin_click(self):
        try: self.app.open_tab("admin", None)
        except Exception as e:
            try:
                with open("crash.log", "a", encoding="utf-8") as f: f.write(f"admin_btn error: {e}\n")
            except Exception: pass
            messagebox.showerror("Admin Error", str(e), parent=self.app.root)
