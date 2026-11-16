import tkinter as tk
from tkinter import ttk

LIGHT_PALETTE = {
    "bg": "#e2e8f0",            # 15-20% higher contrast grey canvas (slate 200)
    "surface": "#ffffff",       # Pure white content areas that pop against canvas
    "panel": "#edf2f7",         # Lightly tinted panel containers
    "text": "#090d16",          # Deep crisp text for readability
    "muted": "#334155",         # Clear slate secondary text
    "accent": "#0284c7",        # Vibrant royal/sky blue
    "accent_hover": "#0369a1",
    "accent_text": "#ffffff",
    "border": "#94a3b8",        # Clean, distinct 1px outline (about 20% darker than before)
    "border_dark": "#64748b",   # Focused border
    "border_subtle": "#cbd5e1",
    "danger": "#dc2626",
    "success": "#16a34a",
    "select_bg": "#bae6fd",     # Vivid light blue selection
    "select_fg": "#0369a1",
    "grid_alt": "#f1f5f9",      # Crisp subtle light tint for alternating rows (slate-100)
    "grid_line": "#cbd5e1"      # Distinct 1px clean grid line (slate-300)
}

DARK_PALETTE = {
    "bg": "#090d16",            # Deep slate dark background
    "surface": "#161f30",       # Slate surface with distinct boundary
    "panel": "#101726",         # Secondary dark panel
    "text": "#f8fafc",          # High-contrast white text
    "muted": "#94a3b8",         # Clean light slate text
    "accent": "#38bdf8",        # Bright sky blue
    "accent_hover": "#7dd3fc",
    "accent_text": "#090d16",
    "border": "#3b4b63",        # 15-20% brighter 1px outline in dark mode
    "border_dark": "#64748b",
    "border_subtle": "#283548",
    "danger": "#ef4444",
    "success": "#22c55e",
    "select_bg": "#0284c7",
    "select_fg": "#ffffff",
    "grid_alt": "#1e293b",      # Subtle flipped dark contrast tint for alternating rows (slate-800)
    "grid_line": "#334155"      # Clean flipped subtle 1px grid divider (slate-700)
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

    # Flat, clean buttons with distinct 1px border
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
        background=[("pressed", p["accent_hover"]), ("active", p["accent_hover"])],
        foreground=[("pressed", p["accent_text"]), ("active", p["accent_text"])],
        bordercolor=[("pressed", p["border_dark"]), ("active", p["border_dark"])]
    )

    # Primary action button with comfortable padding and high hover contrast
    style.configure(
        "Primary.TButton",
        background=p["accent"],
        foreground=p["accent_text"],
        borderwidth=1,
        bordercolor=p["accent_hover"],
        darkcolor=p["accent_hover"],
        lightcolor=p["accent_hover"],
        relief="solid",
        padding=(14, 8),
        font=bold_font
    )
    style.map(
        "Primary.TButton",
        background=[("pressed", p["accent_hover"]), ("active", p["accent_hover"])],
        foreground=[("pressed", p["accent_text"]), ("active", p["accent_text"])],
        bordercolor=[("pressed", p["accent_hover"]), ("active", p["accent_hover"])]
    )

    # Treeview with smooth rows and clear 1px outlines
    style.configure(
        "Treeview",
        background=p["surface"],
        foreground=p["text"],
        fieldbackground=p["surface"],
        bordercolor=p["grid_line"],
        darkcolor=p["grid_line"],
        lightcolor=p["grid_line"],
        borderwidth=1,
        relief="solid",
        rowheight=26
    )
    style.map(
        "Treeview",
        background=[("selected", p["select_bg"])],
        foreground=[("selected", p["select_fg"])]
    )
    style.layout("Treeview.Row", [("border", {"sticky": "nswe", "children": [("Treeitem.row", {"sticky": "nswe"})]})])
    style.configure("Treeview.Row", borderwidth=1, relief="solid",
                    bordercolor=p["grid_line"], darkcolor=p["grid_line"], lightcolor=p["grid_line"])
    style.configure(
        "Treeview.Heading",
        font=bold_font,
        background=p["panel"],
        foreground=p["text"],
        bordercolor=p["grid_line"],
        relief="solid",
        borderwidth=1
    )

    # Clean sidebar treeview without row borders (Regedit style)
    style.layout("Sidebar.Treeview", style.layout("Treeview"))
    style.layout("Sidebar.Treeview.Row", [("Treeitem.row", {"sticky": "nswe"})])
    style.configure("Sidebar.Treeview", background=p["surface"], foreground=p["text"],
                    fieldbackground=p["surface"], rowheight=24, borderwidth=0)
    style.map("Sidebar.Treeview", background=[("selected", p["select_bg"])], foreground=[("selected", p["select_fg"])])

    # Entry with distinct 1px border and focus border
    style.configure(
        "TEntry",
        fieldbackground=p["surface"],
        foreground=p["text"],
        bordercolor=p["border"],
        darkcolor=p["border_subtle"],
        lightcolor=p["border_subtle"],
        borderwidth=1,
        padding=5
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", p["accent"])],
        darkcolor=[("focus", p["accent"])],
        lightcolor=[("focus", p["accent"])]
    )

    style.configure("TPanedwindow", background=p["border"])
    return p
