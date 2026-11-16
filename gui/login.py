import tkinter as tk
from tkinter import ttk
import auth
from gui.theme import get_palette

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("LoreMemory - Authentication")
        self.mode = "login"

        p = get_palette()
        self.root.configure(bg=p["bg"])

        # Main background container filling full window
        self.bg_frame = tk.Frame(self.root, bg=p["bg"])
        self.bg_frame.pack(fill="both", expand=True)

        # Responsive centered card with clean 1px border
        card = tk.Frame(
            self.bg_frame, bg=p["surface"],
            highlightbackground=p["border"],
            highlightthickness=1, padx=36, pady=32
        )
        card.place(relx=0.5, rely=0.5, anchor="center", width=380)

        # Minimal brand header
        brand_row = tk.Frame(card, bg=p["surface"])
        brand_row.pack(pady=(0, 4))
        tk.Label(
            brand_row, text="◈", font=("Segoe UI", 18, "bold"),
            fg=p["accent"], bg=p["surface"]
        ).pack(side="left", padx=(0, 8))
        tk.Label(
            brand_row, text="LoreMemory", font=("Segoe UI", 18, "bold"),
            fg=p["text"], bg=p["surface"]
        ).pack(side="left")

        self.sub_label = tk.Label(
            card, text="Sign in to your local workspace",
            font=("Segoe UI", 9), fg=p["muted"], bg=p["surface"]
        )
        self.sub_label.pack(pady=(0, 18))

        # Stylized segmented mode selector
        toggle_bar = tk.Frame(
            card, bg=p["panel"],
            highlightbackground=p["border_subtle"],
            highlightthickness=1, padx=2, pady=2
        )
        toggle_bar.pack(fill="x", pady=(0, 18))

        self.tab_login = tk.Label(
            toggle_bar, text="Sign In", font=("Segoe UI", 9, "bold"),
            bg=p["surface"], fg=p["text"], cursor="hand2", padx=12, pady=6,
            highlightbackground=p["border_subtle"], highlightthickness=1
        )
        self.tab_login.pack(side="left", fill="x", expand=True)
        self.tab_login.bind("<Button-1>", lambda e: self.set_mode("login"))

        self.tab_reg = tk.Label(
            toggle_bar, text="Create Account", font=("Segoe UI", 9),
            bg=p["panel"], fg=p["muted"], cursor="hand2", padx=12, pady=6
        )
        self.tab_reg.pack(side="right", fill="x", expand=True)
        self.tab_reg.bind("<Button-1>", lambda e: self.set_mode("register"))

        # Username
        tk.Label(
            card, text="Username", bg=p["surface"], fg=p["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        self.user_entry = ttk.Entry(card, width=32)
        self.user_entry.pack(fill="x", pady=(3, 14))
        self.user_entry.focus()

        # Password
        tk.Label(
            card, text="Password", bg=p["surface"], fg=p["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")
        self.pass_entry = ttk.Entry(card, show="*", width=32)
        self.pass_entry.pack(fill="x", pady=(3, 10))

        # Status / Feedback label
        self.err_label = tk.Label(
            card, text="", fg=p["danger"], bg=p["surface"],
            font=("Segoe UI", 9), wraplength=300
        )
        self.err_label.pack(fill="x", pady=(0, 10))

        # Submit button
        self.submit_btn = ttk.Button(
            card, text="Sign In", style="Primary.TButton",
            cursor="hand2", command=self.do_submit
        )
        self.submit_btn.pack(fill="x", pady=(0, 14))

        # Switch prompt
        self.switch_label = tk.Label(
            card, text="Don't have an account? Create one",
            fg=p["muted"], bg=p["surface"], font=("Segoe UI", 9),
            cursor="hand2"
        )
        self.switch_label.pack()
        self.switch_label.bind("<Button-1>", lambda e: self.toggle_mode())
        self.switch_label.bind("<Enter>", lambda e: self.switch_label.config(fg=get_palette()["accent"]))
        self.switch_label.bind("<Leave>", lambda e: self.switch_label.config(fg=get_palette()["muted"]))

        # Bind Enter
        self.root.bind("<Return>", lambda e: self.do_submit())

        # Minimal footnote
        tk.Label(
            card, text="SQLite Studio & Mnemosyne Graph",
            font=("Segoe UI", 8), fg=p["muted"], bg=p["surface"]
        ).pack(pady=(18, 0))

    def set_mode(self, mode):
        self.mode = mode
        p = get_palette()
        self.err_label.config(text="")
        if self.mode == "login":
            self.sub_label.config(text="Sign in to your local workspace")
            self.submit_btn.config(text="Sign In")
            self.tab_login.config(bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold"), highlightthickness=1)
            self.tab_reg.config(bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9), highlightthickness=0)
            self.switch_label.config(text="Don't have an account? Create one")
        else:
            self.sub_label.config(text="Register a new local account")
            self.submit_btn.config(text="Create Account")
            self.tab_login.config(bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9), highlightthickness=0)
            self.tab_reg.config(bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold"), highlightthickness=1)
            self.switch_label.config(text="Already have an account? Sign in")

    def toggle_mode(self):
        self.set_mode("register" if self.mode == "login" else "login")

    def do_submit(self):
        if self.mode == "login":
            self.do_login()
        else:
            self.do_register()

    def do_login(self):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get()
        if not u or not p:
            self.err_label.config(text="● Please enter both username and password", fg=get_palette()["danger"])
            return

        uid = auth.login_user(u, p)
        if uid is None:
            self.err_label.config(text="● Invalid username or password", fg=get_palette()["danger"])
        else:
            self.root.unbind("<Return>")
            self.on_success(uid, u)

    def do_register(self):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get()
        if not u or not p:
            self.err_label.config(text="● Please enter both username and password", fg=get_palette()["danger"])
            return

        ok = auth.register_user(u, p)
        if ok:
            self.set_mode("login")
            self.err_label.config(text="✓ Account created! You can now sign in.", fg=get_palette()["success"])
            self.pass_entry.delete(0, tk.END)
            self.pass_entry.focus()
        else:
            self.err_label.config(text="● Username already exists", fg=get_palette()["danger"])
