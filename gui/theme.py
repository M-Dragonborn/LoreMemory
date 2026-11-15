import tkinter as tk
from tkinter import ttk

LIGHT_PALETTE = {
    "bg": "#f8f9fa",
    "surface": "#ffffff",
    "text": "#202124",
    "muted": "#5f6368",
    "accent": "#1a73e8",
    "accent_hover": "#1765cc",
    "accent_text": "#ffffff",
    "border": "#dadce0",
    "danger": "#d93025",
    "success": "#188038",
    "select_bg": "#e8f0fe",
    "select_fg": "#1a73e8"
}

DARK_PALETTE = {
    "bg": "#1e1e1e",
    "surface": "#252526",
    "text": "#d4d4d4",
    "muted": "#858585",
    "accent": "#0e639c",
    "accent_hover": "#1177bb",
    "accent_text": "#ffffff",
    "border": "#3c3c3c",
    "danger": "#f14c4c",
    "success": "#73c991",
    "select_bg": "#264f78",
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

    # Base Fonts
    normal_font = ("Segoe UI", 10)
    bold_font = ("Segoe UI", 10, "bold")

    style.configure(".", font=normal_font, background=p["bg"], foreground=p["text"])
    style.configure("TFrame", background=p["bg"])
    style.configure("Surface.TFrame", background=p["surface"])

    style.configure("TLabel", background=p["bg"], foreground=p["text"], font=normal_font)
    style.configure("Muted.TLabel", foreground=p["muted"], font=normal_font)
    style.configure("Bold.TLabel", font=bold_font, foreground=p["text"])
    style.configure("Error.TLabel", foreground=p["danger"], font=normal_font)

    # Buttons: Flat and Run
    style.configure(
        "TButton",
        background=p["surface"],
        foreground=p["text"],
        borderwidth=1,
        bordercolor=p["border"],
        relief="flat",
        padding=(8, 4)
    )
    style.map("TButton", background=[("active", p["border"])])

    style.configure(
        "Run.TButton",
        background=p["accent"],
        foreground=p["accent_text"],
        borderwidth=0,
        relief="flat",
        padding=(10, 5),
        font=bold_font
    )
    style.map("Run.TButton", background=[("active", p["accent_hover"])])

    # Treeview
    style.configure(
        "Treeview",
        background=p["surface"],
        foreground=p["text"],
        fieldbackground=p["surface"],
        bordercolor=p["border"],
        borderwidth=1,
        rowheight=24
    )
    style.map("Treeview", background=[("selected", p["select_bg"])], foreground=[("selected", p["select_fg"])])
    style.configure("Treeview.Heading", font=bold_font, background=p["bg"], foreground=p["text"])

    # Entry
    style.configure("TEntry", fieldbackground=p["surface"], foreground=p["text"], bordercolor=p["border"])
    style.configure("TPanedwindow", background=p["border"])

    return p
