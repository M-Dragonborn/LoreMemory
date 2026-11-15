import tkinter as tk
from tkinter import ttk
import auth
from gui.theme import get_palette

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("LoreMemory - Login")
        self.root.geometry("380x360")
        self.root.resizable(False, False)

        p = get_palette()
        self.root.configure(bg=p["bg"])
        self.root.eval('tk::PlaceWindow . center')

        # Outer card with solid outline
        card = tk.Frame(
            self.root, bg=p["surface"],
            highlightbackground=p["border_dark"],
            highlightthickness=2, padx=25, pady=25
        )
        card.pack(fill="both", expand=True, padx=15, pady=15)

        # Wordmark
        title_label = tk.Label(
            card, text="LoreMemory",
            font=("Segoe UI", 20, "bold"),
            fg=p["accent"], bg=p["surface"]
        )
        title_label.pack(pady=(0, 15))

        # Username
        tk.Label(card, text="Username", bg=p["surface"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.user_entry = ttk.Entry(card, width=30)
        self.user_entry.pack(fill="x", pady=(2, 10))
        self.user_entry.focus()

        # Password
        tk.Label(card, text="Password", bg=p["surface"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.pass_entry = ttk.Entry(card, show="*", width=30)
        self.pass_entry.pack(fill="x", pady=(2, 10))

        # Error / Status line
        self.err_label = tk.Label(card, text="", fg=p["danger"], bg=p["surface"], font=("Segoe UI", 9, "bold"))
        self.err_label.pack(pady=(0, 10))

        # Login button
        self.login_btn = ttk.Button(card, text="Login", style="Run.TButton", command=self.do_login)
        self.login_btn.pack(fill="x", pady=(0, 10))

        # Create account link
        self.create_link = tk.Label(
            card, text="Create account",
            fg=p["accent"], bg=p["surface"],
            cursor="hand2", font=("Segoe UI", 9, "bold", "underline")
        )
        self.create_link.pack()
        self.create_link.bind("<Button-1>", lambda e: self.do_register())

        self.root.bind("<Return>", lambda e: self.do_login())

    def do_login(self):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get()
        if not u or not p:
            self.err_label.config(text="Enter a username and a password", fg=get_palette()["danger"])
            return

        uid = auth.login_user(u, p)
        if uid is None:
            self.err_label.config(text="Wrong username or password", fg=get_palette()["danger"])
        else:
            self.root.unbind("<Return>")
            self.on_success(uid, u)

    def do_register(self):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get()
        if not u or not p:
            self.err_label.config(text="Enter a username and a password", fg=get_palette()["danger"])
            return

        ok = auth.register_user(u, p)
        if ok:
            self.err_label.config(text="Account created. You can now log in.", fg=get_palette()["success"])
        else:
            self.err_label.config(text="That username already exists", fg=get_palette()["danger"])
