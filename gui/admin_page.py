import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import auth
from config import USERS_DB
from gui.theme import get_palette

class AdminPage(tk.Frame):
    def __init__(self, parent, app):
        p = get_palette()
        super().__init__(parent, bg=p["surface"])
        self.app = app
        self.active_subview = "users"
        self.setup_ui()
        self.load_users()
        self.load_audit_log()

    def setup_ui(self):
        p = get_palette()
        # Top Header Bar
        self.hdr = tk.Frame(self, bg=p["panel"], padx=10, pady=8, highlightbackground=p["border"], highlightthickness=1)
        self.hdr.pack(fill="x", side="top", padx=3, pady=3)

        tk.Label(self.hdr, text="👥 User & Role Administration", bg=p["panel"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(side="left")
        role_badge = f"{self.app.username} ({self.app.role})"
        self.role_badge_lbl = tk.Label(self.hdr, text=role_badge, bg=p["select_bg"], fg=p["accent"], font=("Segoe UI", 9, "bold"), padx=8, pady=2)
        self.role_badge_lbl.pack(side="right")

        # View Switcher Segments
        self.switch_frame = tk.Frame(self, bg=p["bg"], padx=6, pady=4)
        self.switch_frame.pack(fill="x", side="top")
        self.btn_users_view = tk.Button(self.switch_frame, text="User Accounts", font=("Segoe UI", 9, "bold"),
                                        relief="flat", bg=p["surface"], fg=p["accent"], cursor="hand2", padx=10, pady=4,
                                        command=lambda: self.switch_view("users"))
        self.btn_users_view.pack(side="left", padx=(0, 4))
        self.btn_audit_view = tk.Button(self.switch_frame, text="Role Audit Log", font=("Segoe UI", 9),
                                        relief="flat", bg=p["bg"], fg=p["muted"], cursor="hand2", padx=10, pady=4,
                                        command=lambda: self.switch_view("audit"))
        self.btn_audit_view.pack(side="left")

        # Container for sub-views
        self.container = tk.Frame(self, bg=p["surface"])
        self.container.pack(fill="both", expand=True, padx=3, pady=3)

        # 1. Users Frame
        self.users_frame = tk.Frame(self.container, bg=p["surface"])
        self.u_toolbar = tk.Frame(self.users_frame, bg=p["panel"], padx=6, pady=6, highlightbackground=p["border"], highlightthickness=1)
        self.u_toolbar.pack(fill="x", side="top", pady=(0, 4))

        tk.Button(self.u_toolbar, text="+ New User", bg=p["accent"], fg=p["accent_text"], font=("Segoe UI", 9, "bold"),
                  relief="flat", cursor="hand2", padx=8, pady=3, command=self.on_create_user).pack(side="left", padx=2)
        tk.Button(self.u_toolbar, text="Change Role", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9),
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=3, command=self.on_change_role).pack(side="left", padx=2)
        tk.Button(self.u_toolbar, text="Toggle Active", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9),
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=3, command=self.on_toggle_active).pack(side="left", padx=2)
        tk.Button(self.u_toolbar, text="Reset Password", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9),
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=3, command=self.on_reset_password).pack(side="left", padx=2)
        tk.Button(self.u_toolbar, text="⟳ Refresh", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9),
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=3, command=self.load_users).pack(side="right", padx=2)

        self.users_tree = ttk.Treeview(self.users_frame, columns=("id", "username", "role", "status", "last_login", "created_at"),
                                       show="headings", selectmode="browse")
        for col, (name, w) in [("id", ("ID", 45)), ("username", ("Username", 130)), ("role", ("Role", 110)),
                               ("status", ("Status", 90)), ("last_login", ("Last Login", 150)), ("created_at", ("Created", 150))]:
            self.users_tree.heading(col, text=name); self.users_tree.column(col, width=w, anchor="center" if col in ("id", "role", "status") else "w")
        u_scroll = ttk.Scrollbar(self.users_frame, orient="vertical", command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=u_scroll.set)
        self.users_tree.pack(side="left", fill="both", expand=True)
        u_scroll.pack(side="right", fill="y")
        self.users_frame.pack(fill="both", expand=True)

        # 2. Audit Frame
        self.audit_frame = tk.Frame(self.container, bg=p["surface"])
        self.a_toolbar = tk.Frame(self.audit_frame, bg=p["panel"], padx=6, pady=6, highlightbackground=p["border"], highlightthickness=1)
        self.a_toolbar.pack(fill="x", side="top", pady=(0, 4))
        tk.Button(self.a_toolbar, text="⟳ Refresh Audit Log", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9),
                  relief="solid", bd=1, cursor="hand2", padx=8, pady=3, command=self.load_audit_log).pack(side="right", padx=2)

        self.audit_tree = ttk.Treeview(self.audit_frame, columns=("id", "target", "changed_by", "change", "changed_at", "reason"),
                                       show="headings", selectmode="browse")
        for col, (name, w) in [("id", ("Audit ID", 65)), ("target", ("Target User", 120)), ("changed_by", ("Changed By", 120)),
                               ("change", ("Role Transition", 160)), ("changed_at", ("Timestamp", 150)), ("reason", ("Reason / Notes", 220))]:
            self.audit_tree.heading(col, text=name); self.audit_tree.column(col, width=w, anchor="center" if col in ("id", "change") else "w")
        a_scroll = ttk.Scrollbar(self.audit_frame, orient="vertical", command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=a_scroll.set)
        self.audit_tree.pack(side="left", fill="both", expand=True)
        a_scroll.pack(side="right", fill="y")

    def switch_view(self, view):
        p = get_palette()
        self.active_subview = view
        if view == "users":
            self.audit_frame.pack_forget(); self.users_frame.pack(fill="both", expand=True)
            self.btn_users_view.config(bg=p["surface"], fg=p["accent"], font=("Segoe UI", 9, "bold"))
            self.btn_audit_view.config(bg=p["bg"], fg=p["muted"], font=("Segoe UI", 9))
            self.load_users()
        else:
            self.users_frame.pack_forget(); self.audit_frame.pack(fill="both", expand=True)
            self.btn_audit_view.config(bg=p["surface"], fg=p["accent"], font=("Segoe UI", 9, "bold"))
            self.btn_users_view.config(bg=p["bg"], fg=p["muted"], font=("Segoe UI", 9))
            self.load_audit_log()

    def load_users(self):
        for item in self.users_tree.get_children(): self.users_tree.delete(item)
        try:
            con = auth.get_connection(USERS_DB)
            users = auth.list_users(con); con.close()
            for u in users:
                status = "Active" if u["is_active"] else "Deactivated"
                self.users_tree.insert("", "end", values=(u["user_id"], u["username"], u["role"], status, u["last_login"] or "Never", u["created_at"]))
        except Exception as e: messagebox.showerror("Database Error", f"Failed to load users:\n{e}", parent=self)

    def load_audit_log(self):
        for item in self.audit_tree.get_children(): self.audit_tree.delete(item)
        try:
            con = auth.get_connection(USERS_DB)
            logs = auth.list_role_audit(con); con.close()
            for l in logs:
                transition = f"{l['old_role']} → {l['new_role']}"
                self.audit_tree.insert("", "end", values=(l["audit_id"], l["target_user"], l["changed_by_user"], transition, l["changed_at"], l["reason"]))
        except Exception as e: messagebox.showerror("Database Error", f"Failed to load audit log:\n{e}", parent=self)

    def _get_selected_user(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showinfo("Selection Required", "Please select a user from the table first.", parent=self)
            return None
        vals = self.users_tree.item(sel[0], "values")
        return {"user_id": int(vals[0]), "username": vals[1], "role": vals[2], "is_active": vals[3] == "Active"}

    def on_create_user(self):
        p = get_palette()
        dlg = tk.Toplevel(self); dlg.title("Create New User"); dlg.transient(self); dlg.grab_set(); dlg.configure(bg=p["bg"])
        card = tk.Frame(dlg, bg=p["surface"], padx=16, pady=16, highlightbackground=p["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(card, text="Username:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        u_ent = ttk.Entry(card, width=24); u_ent.grid(row=0, column=1, pady=4); u_ent.focus_set()

        tk.Label(card, text="Password:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        p_ent = ttk.Entry(card, width=24, show="•"); p_ent.grid(row=1, column=1, pady=4)

        tk.Label(card, text="Role:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=4)
        roles = ["user", "admin"] if self.app.role == "super_admin" else ["user"]
        if self.app.role == "super_admin": roles.append("super_admin")
        r_combo = ttk.Combobox(card, values=roles, state="readonly", width=22); r_combo.set("user"); r_combo.grid(row=2, column=1, pady=4)

        def save():
            uname, pwd, role = u_ent.get().strip(), p_ent.get(), r_combo.get()
            if not uname or not pwd: messagebox.showwarning("Incomplete", "Username and password cannot be empty.", parent=dlg); return
            con = auth.get_connection(USERS_DB)
            ok = auth.register(con, uname, pwd, role=role, created_by=self.app.user_id)
            con.close()
            if ok:
                dlg.destroy(); self.load_users(); messagebox.showinfo("Success", f"User '{uname}' ({role}) created successfully.", parent=self)
            else: messagebox.showerror("Error", f"Failed to create user '{uname}'. Username may already exist.", parent=dlg)

        btn_box = tk.Frame(card, bg=p["surface"])
        btn_box.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky="e")
        tk.Button(btn_box, text="Cancel", relief="solid", bd=1, bg=p["surface"], fg=p["text"], command=dlg.destroy, padx=8, pady=3).pack(side="right", padx=(4, 0))
        tk.Button(btn_box, text="Create", relief="flat", bg=p["accent"], fg=p["accent_text"], font=("Segoe UI", 9, "bold"), command=save, padx=12, pady=3).pack(side="right")

    def on_change_role(self):
        u = self._get_selected_user()
        if not u: return
        if self.app.role != "super_admin" and u["role"] in ("admin", "super_admin"):
            messagebox.showwarning("Permission Denied", "Only Super Admins can modify Admin or Super Admin roles.", parent=self); return
        p = get_palette()
        dlg = tk.Toplevel(self); dlg.title(f"Change Role: {u['username']}"); dlg.transient(self); dlg.grab_set(); dlg.configure(bg=p["bg"])
        card = tk.Frame(dlg, bg=p["surface"], padx=16, pady=16, highlightbackground=p["border"], highlightthickness=1)
        card.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(card, text=f"Target: {u['username']} (current: {u['role']})", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(card, text="New Role:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=4)
        roles = ["user", "admin", "super_admin"] if self.app.role == "super_admin" else ["user"]
        r_combo = ttk.Combobox(card, values=roles, state="readonly", width=22); r_combo.set(u["role"]); r_combo.grid(row=1, column=1, pady=4)

        tk.Label(card, text="Reason:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=4)
        reason_ent = ttk.Entry(card, width=24); reason_ent.grid(row=2, column=1, pady=4); reason_ent.focus_set()

        def apply_role():
            new_r, reason = r_combo.get(), reason_ent.get().strip()
            if new_r == u["role"]: messagebox.showinfo("No Change", "Selected role is identical to current role.", parent=dlg); return
            con = auth.get_connection(USERS_DB)
            ok = auth.change_role(con, u["user_id"], new_r, self.app.user_id, reason=reason)
            con.close()
            if ok:
                dlg.destroy(); self.load_users(); self.load_audit_log()
                messagebox.showinfo("Success", f"Updated {u['username']} to '{new_r}'.", parent=self)
            else: messagebox.showerror("Error", "Failed to update role.", parent=dlg)

        btn_box = tk.Frame(card, bg=p["surface"])
        btn_box.grid(row=3, column=0, columnspan=2, pady=(12, 0), sticky="e")
        tk.Button(btn_box, text="Cancel", relief="solid", bd=1, bg=p["surface"], fg=p["text"], command=dlg.destroy, padx=8, pady=3).pack(side="right", padx=(4, 0))
        tk.Button(btn_box, text="Save Change", relief="flat", bg=p["accent"], fg=p["accent_text"], font=("Segoe UI", 9, "bold"), command=apply_role, padx=10, pady=3).pack(side="right")

    def on_toggle_active(self):
        u = self._get_selected_user()
        if not u: return
        if u["user_id"] == self.app.user_id:
            messagebox.showwarning("Invalid Action", "You cannot deactivate your own account.", parent=self); return
        if self.app.role != "super_admin" and u["role"] in ("admin", "super_admin"):
            messagebox.showwarning("Permission Denied", "Only Super Admins can alter Admin status.", parent=self); return
        new_status = not u["is_active"]
        action = "activate" if new_status else "deactivate"
        if not messagebox.askyesno("Confirm Status Change", f"Are you sure you want to {action} account '{u['username']}'?", parent=self): return
        con = auth.get_connection(USERS_DB)
        auth.set_active(con, u["user_id"], new_status)
        con.close()
        self.load_users()

    def on_reset_password(self):
        u = self._get_selected_user()
        if not u: return
        new_pwd = simpledialog.askstring("Reset Password", f"Enter new password for '{u['username']}':", show="•", parent=self)
        if not new_pwd: return
        con = auth.get_connection(USERS_DB)
        ok = auth.change_password(con, u["username"], new_pwd)
        con.close()
        if ok: messagebox.showinfo("Success", f"Password for '{u['username']}' updated.", parent=self)
        else: messagebox.showerror("Error", "Failed to reset password.", parent=self)

    def apply_theme(self, p):
        self.config(bg=p["surface"])
        self.hdr.config(bg=p["panel"], highlightbackground=p["border"])
        for child in self.hdr.winfo_children():
            if isinstance(child, tk.Label): child.config(bg=p["panel"], fg=p["text"])
        self.role_badge_lbl.config(bg=p["select_bg"], fg=p["accent"])
        self.switch_frame.config(bg=p["bg"])
        self.container.config(bg=p["surface"])
        self.users_frame.config(bg=p["surface"])
        self.audit_frame.config(bg=p["surface"])
        self.u_toolbar.config(bg=p["panel"], highlightbackground=p["border"])
        self.a_toolbar.config(bg=p["panel"], highlightbackground=p["border"])
        self.switch_view(self.active_subview)
