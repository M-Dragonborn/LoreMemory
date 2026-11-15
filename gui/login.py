import tkinter as tk
from tkinter import ttk
import auth
from gui.theme import get_palette

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("LoreMemory - Login")
        self.root.geometry("360x340")
        self.root.resizable(False, False)

        p = get_palette()
        self.root.configure(bg=p["bg"])

        # Center window
        self.root.eval('tk::PlaceWindow . center')

        frame = ttk.Frame(self.root, padding=30)
        frame.pack(fill="both", expand=True)

        # Wordmark
        title_label = tk.Label(
            frame,
            text="LoreMemory",
            font=("Segoe UI", 20, "bold"),
            fg=p["accent"],
            bg=p["bg"]
        )
        title_label.pack(pady=(0, 20))

        # Username
        ttk.Label(frame, text="Username").pack(anchor="w")
        self.user_entry = ttk.Entry(frame, width=30)
        self.user_entry.pack(fill="x", pady=(2, 10))
        self.user_entry.focus()

        # Password
        ttk.Label(frame, text="Password").pack(anchor="w")
        self.pass_entry = ttk.Entry(frame, show="*", width=30)
        self.pass_entry.pack(fill="x", pady=(2, 10))

        # Error / Status line
        self.err_label = tk.Label(frame, text="", fg=p["danger"], bg=p["bg"], font=("Segoe UI", 9))
        self.err_label.pack(pady=(0, 10))

        # Login button
        self.login_btn = ttk.Button(frame, text="Login", style="Run.TButton", command=self.do_login)
        self.login_btn.pack(fill="x", pady=(0, 10))

        # Create account link
        self.create_link = tk.Label(
            frame,
            text="Create account",
            fg=p["accent"],
            bg=p["bg"],
            cursor="hand2",
            font=("Segoe UI", 9, "underline")
        )
        self.create_link.pack()
        self.create_link.bind("<Button-1>", lambda e: self.do_register())

        # Enter key triggers login
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
