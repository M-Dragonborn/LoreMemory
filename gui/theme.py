import tkinter as tk
from tkinter import ttk

LIGHT_PALETTE = {
    "bg": "#f1f5f9",            # Soft modern slate background
    "surface": "#ffffff",       # Clean white surface
    "panel": "#f8fafc",         # Very soft panel background
    "text": "#0f172a",          # Clear, sharp slate text
    "muted": "#475569",         # Subtle secondary text
    "accent": "#0284c7",        # Vibrant blue
    "accent_hover": "#0369a1",
    "accent_text": "#ffffff",
    "border": "#cbd5e1",        # Soft, low-transparency 1px outline
    "border_dark": "#94a3b8",   # Refined border
    "border_subtle": "#e2e8f0",
    "danger": "#dc2626",
    "success": "#16a34a",
    "select_bg": "#e0f2fe",
    "select_fg": "#0369a1"
}

DARK_PALETTE = {
    "bg": "#0b0f19",            # Deep slate dark background
    "surface": "#151c2c",       # Slate surface
    "panel": "#111827",         # Secondary dark panel
    "text": "#f8fafc",          # High-contrast white text
    "muted": "#94a3b8",         # Refined muted text
    "accent": "#38bdf8",        # Bright sky blue
    "accent_hover": "#0284c7",
    "accent_text": "#0b0f19",
    "border": "#283548",        # Subtle dark border
    "border_dark": "#475569",   # Clear dark outline
    "border_subtle": "#1e293b",
    "danger": "#ef4444",
    "success": "#22c55e",
    "select_bg": "#0284c7",
    "select_fg": "#ffffff"
}

CURRENT_THEME = "light"

def get_palette():
    return DARK_PALETTE if CURRENT_THEME == "dark" else LIGHT_PALETTE

def apply(root, mode="light"):
    global CURRENT_THEME
    CURRENT_THEME = mode
    p = get_palette()

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    root.configure(bg=p["bg"])

    normal_font = ("Segoe UI", 10)
    bold_font = ("Segoe UI", 10, "bold")

    style.configure(".", font=normal_font, background=p["bg"], foreground=p["text"])
    style.configure("TFrame", background=p["bg"])
    style.configure("Surface.TFrame", background=p["surface"])
    style.configure("Panel.TFrame", background=p["panel"])

    style.configure("TLabel", background=p["bg"], foreground=p["text"], font=normal_font)
    style.configure("Muted.TLabel", foreground=p["muted"], font=normal_font)
    style.configure("Bold.TLabel", font=bold_font, foreground=p["text"])
    style.configure("Error.TLabel", foreground=p["danger"], font=bold_font)

    # Flat, clean buttons with soft 1px border
    style.configure(
        "TButton",
        background=p["surface"],
        foreground=p["text"],
        borderwidth=1,
        bordercolor=p["border"],
        darkcolor=p["border_subtle"],
        lightcolor=p["border_subtle"],
        relief="solid",
        padding=(8, 4),
        font=normal_font
    )
    style.map(
        "TButton",
        background=[("active", p["select_bg"]), ("pressed", p["border"])],
        foreground=[("active", p["select_fg"])],
        bordercolor=[("active", p["accent"])]
    )

    style.configure(
        "Run.TButton",
        background=p["accent"],
        foreground=p["accent_text"],
        borderwidth=1,
        bordercolor=p["accent_hover"],
        darkcolor=p["accent_hover"],
        lightcolor=p["accent_hover"],
        relief="solid",
        padding=(10, 5),
        font=bold_font
    )
    style.map(
        "Run.TButton",
        background=[("active", p["accent_hover"])],
        bordercolor=[("active", p["border_dark"])]
    )

    # Treeview with smooth rows and subtle outlines
    style.configure(
        "Treeview",
        background=p["surface"],
        foreground=p["text"],
        fieldbackground=p["surface"],
        bordercolor=p["border"],
        darkcolor=p["border_subtle"],
        lightcolor=p["border_subtle"],
        borderwidth=1,
        relief="solid",
        rowheight=26
    )
    style.map(
        "Treeview",
        background=[("selected", p["select_bg"])],
        foreground=[("selected", p["select_fg"])]
    )
    style.configure(
        "Treeview.Heading",
        font=bold_font,
        background=p["panel"],
        foreground=p["text"],
        bordercolor=p["border"],
        relief="solid",
        borderwidth=1
    )

    # Entry with soft 1px border
    style.configure(
        "TEntry",
        fieldbackground=p["surface"],
        foreground=p["text"],
        bordercolor=p["border"],
        darkcolor=p["border_subtle"],
        lightcolor=p["border_subtle"],
        borderwidth=1,
        padding=4
    )

    style.configure("TPanedwindow", background=p["border"])
    return p
