import tkinter as tk
from tkinter import ttk

LIGHT_PALETTE = {
    "bg": "#e2e8f0",            # High-contrast slate grey background
    "surface": "#ffffff",       # Crisp white surfaces
    "panel": "#f1f5f9",         # Subtle secondary panel
    "text": "#090d16",          # Deep black text for maximum readability
    "muted": "#334155",         # Dark slate muted text
    "accent": "#0d57d5",        # Bold royal blue
    "accent_hover": "#0945ab",
    "accent_text": "#ffffff",
    "border": "#94a3b8",        # Distinct medium slate outline
    "border_dark": "#334155",   # High-contrast dark outline
    "danger": "#b91c1c",        # High-contrast red
    "success": "#15803d",       # High-contrast green
    "select_bg": "#bae6fd",     # Vibrant selection background
    "select_fg": "#0c4a6e"      # High-contrast selection text
}

DARK_PALETTE = {
    "bg": "#090d16",            # Deep dark background
    "surface": "#161e2e",       # Dark slate surface
    "panel": "#111827",         # Secondary dark panel
    "text": "#f8fafc",          # Crisp white text
    "muted": "#94a3b8",         # Light slate muted text
    "accent": "#38bdf8",        # Vivid cyan/sky blue
    "accent_hover": "#0284c7",
    "accent_text": "#090d16",
    "border": "#475569",        # Distinct dark border
    "border_dark": "#94a3b8",   # High-contrast bright outline
    "danger": "#f87171",
    "success": "#4ade80",
    "select_bg": "#0369a1",
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

    # Buttons with clear outlines
    style.configure(
        "TButton",
        background=p["surface"],
        foreground=p["text"],
        borderwidth=1,
        bordercolor=p["border_dark"],
        darkcolor=p["border"],
        lightcolor=p["border"],
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
        borderwidth=2,
        bordercolor=p["border_dark"],
        darkcolor=p["accent_hover"],
        lightcolor=p["accent_hover"],
        relief="solid",
        padding=(10, 5),
        font=bold_font
    )
    style.map(
        "Run.TButton",
        background=[("active", p["accent_hover"])],
        bordercolor=[("active", p["text"])]
    )

    # Treeview with solid border and highlighted headers
    style.configure(
        "Treeview",
        background=p["surface"],
        foreground=p["text"],
        fieldbackground=p["surface"],
        bordercolor=p["border_dark"],
        darkcolor=p["border"],
        lightcolor=p["border"],
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
        background=p["bg"],
        foreground=p["text"],
        bordercolor=p["border_dark"],
        relief="solid",
        borderwidth=1
    )

    # Entry with solid border
    style.configure(
        "TEntry",
        fieldbackground=p["surface"],
        foreground=p["text"],
        bordercolor=p["border_dark"],
        darkcolor=p["border"],
        lightcolor=p["border"],
        borderwidth=1,
        padding=4
    )

    # PanedWindow dividers
    style.configure("TPanedwindow", background=p["border_dark"])

    return p
