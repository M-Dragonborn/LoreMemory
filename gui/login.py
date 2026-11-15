import tkinter as tk
from tkinter import ttk
import auth
from gui.theme import get_palette

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("LoreMemory")

        p = get_palette()
        self.root.configure(bg=p["bg"])

        # Main background container filling full window
        self.bg_frame = tk.Frame(self.root, bg=p["bg"])
        self.bg_frame.pack(fill="both", expand=True)

        # Responsive centered card (soft 1px border)
        card = tk.Frame(
            self.bg_frame, bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1, padx=36, pady=36
        )
        card.place(relx=0.5, rely=0.5, anchor="center", width=420)

        # Wordmark
        title_label = tk.Label(
            card, text="LoreMemory",
            font=("Segoe UI", 24, "bold"),
            fg=p["accent"], bg=p["surface"]
        )
        title_label.pack(pady=(0, 6))

        subtitle = tk.Label(
            card, text="Desktop SQLite DBMS & AI Memory",
            font=("Segoe UI", 10),
            fg=p["muted"], bg=p["surface"]
        )
        subtitle.pack(pady=(0, 24))

        # Username
        tk.Label(card, text="Username", bg=p["surface"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.user_entry = ttk.Entry(card, width=32)
        self.user_entry.pack(fill="x", pady=(4, 14))
        self.user_entry.focus()

        # Password
        tk.Label(card, text="Password", bg=p["surface"], fg=p["text"], font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.pass_entry = ttk.Entry(card, show="*", width=32)
        self.pass_entry.pack(fill="x", pady=(4, 14))

        # Error / Status line
        self.err_label = tk.Label(card, text="", fg=p["danger"], bg=p["surface"], font=("Segoe UI", 9, "bold"))
        self.err_label.pack(pady=(0, 12))

        # Login button
        self.login_btn = ttk.Button(card, text="Sign In", style="Run.TButton", command=self.do_login)
        self.login_btn.pack(fill="x", pady=(0, 14))

        # Create account link
        self.create_link = tk.Label(
            card, text="Create an account",
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
            self.err_label.config(text="Account created. You can now sign in.", fg=get_palette()["success"])
        else:
            self.err_label.config(text="That username already exists", fg=get_palette()["danger"])
