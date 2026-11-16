import tkinter as tk
from tkinter import ttk
from gui.theme import get_palette

class TabStrip:
    def __init__(self, parent, on_tab_close=None, on_tab_switch=None):
        self.parent = parent
        self.on_tab_close = on_tab_close
        self.on_tab_switch = on_tab_switch

        self.tabs = {}
        self.active_key = None

        p = get_palette()
        self.container = tk.Frame(parent, bg=p["bg"])

        # Tab strip header bar with subtle bottom border
        self.header_frame = tk.Frame(
            self.container, bg=p["panel"], height=36,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.header_frame.pack(fill="x", side="top", padx=2, pady=(2, 0))
        self.header_frame.pack_propagate(False)

        # Content area with soft border frame
        self.content_frame = tk.Frame(
            self.container, bg=p["surface"],
            highlightbackground=p["border"], highlightthickness=1
        )
        self.content_frame.pack(fill="both", expand=True, side="bottom", padx=2, pady=2)

        # Empty hint
        self.empty_label = tk.Label(
            self.content_frame,
            text="Open a table from the left to view data",
            font=("Segoe UI", 11, "bold"),
            fg=p["muted"],
            bg=p["surface"]
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def pack(self, **kwargs):
        self.container.pack(**kwargs)

    def select(self, key):
        if key not in self.tabs:
            return
        self.active_key = key
        p = get_palette()

        for k, info in self.tabs.items():
            btn_frame = info["header"]
            lbl = info["title_lbl"]
            cls = info["close_lbl"]
            if k == key:
                btn_frame.config(bg=p["surface"], highlightbackground=p["accent"], highlightthickness=1)
                lbl.config(bg=p["surface"], fg=p["accent"], font=("Segoe UI", 9, "bold"))
                cls.config(bg=p["surface"], fg=p["danger"])
                info["page"].tkraise()
            else:
                btn_frame.config(bg=p["panel"], highlightbackground=p["border"], highlightthickness=1)
                lbl.config(bg=p["panel"], fg=p["text"], font=("Segoe UI", 9))
                cls.config(bg=p["panel"], fg=p["muted"])

        self.empty_label.place_forget()
        if self.on_tab_switch:
            self.on_tab_switch(key, self.tabs[key]["kind"], self.tabs[key]["page"])

    def add_tab(self, key, kind, title, page):
        if key in self.tabs:
            self.select(key)
            return self.tabs[key]["page"]

        p = get_palette()
        tab_hdr = tk.Frame(
            self.header_frame, bg=p["panel"], padx=8, pady=3,
            highlightbackground=p["border"], highlightthickness=1, relief="solid", bd=1
        )
        tab_hdr.pack(side="left", padx=3, pady=(3, 2))

        lbl = tk.Label(tab_hdr, text=title, font=("Segoe UI", 9), bg=p["panel"], fg=p["text"], cursor="hand2")
        lbl.pack(side="left", padx=(2, 6))
        lbl.bind("<Button-1>", lambda e, k=key: self.select(k))
        tab_hdr.bind("<Button-1>", lambda e, k=key: self.select(k))

        cls = tk.Label(tab_hdr, text=" × ", font=("Segoe UI", 10, "bold"), bg=p["panel"], fg=p["muted"], cursor="hand2")
        cls.pack(side="right")
        cls.bind("<Button-1>", lambda e, k=key: self.close_tab(k))

        page.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        self.tabs[key] = {
            "kind": kind,
            "title": title,
            "page": page,
            "header": tab_hdr,
            "title_lbl": lbl,
            "close_lbl": cls
        }

        self.select(key)
        return page

    def close_tab(self, key):
        if key not in self.tabs:
            return
        info = self.tabs.pop(key)
        if hasattr(info["page"], "on_close"):
            info["page"].on_close()
        info["header"].destroy()
        info["page"].destroy()

        if self.on_tab_close:
            self.on_tab_close(key, info["kind"])

        if self.active_key == key:
            if self.tabs:
                next_key = list(self.tabs.keys())[-1]
                self.select(next_key)
            else:
                self.active_key = None
                p = get_palette()
                self.empty_label.config(bg=p["surface"], fg=p["muted"])
                self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
                if self.on_tab_switch:
                    self.on_tab_switch(None, None, None)

    def rename_tab(self, old_key, new_key, new_title):
        if old_key not in self.tabs:
            return
        info = self.tabs.pop(old_key)
        info["title"] = new_title
        info["title_lbl"].config(text=new_title)
        info["title_lbl"].unbind("<Button-1>")
        info["title_lbl"].bind("<Button-1>", lambda e, k=new_key: self.select(k))
        info["header"].unbind("<Button-1>")
        info["header"].bind("<Button-1>", lambda e, k=new_key: self.select(k))
        info["close_lbl"].unbind("<Button-1>")
        info["close_lbl"].bind("<Button-1>", lambda e, k=new_key: self.close_tab(k))
        self.tabs[new_key] = info
        if self.active_key == old_key:
            self.active_key = new_key

    def close_table_and_history(self, table_name):
        self.close_tab(f"history:{table_name}")
        self.close_tab(f"table:{table_name}")

    def rename_table_tabs(self, old_name, new_name):
        old_t, new_t = f"table:{old_name}", f"table:{new_name}"
        old_h, new_h = f"history:{old_name}", f"history:{new_name}"
        if old_t in self.tabs:
            self.rename_tab(old_t, new_t, new_name)
        if old_h in self.tabs:
            self.rename_tab(old_h, new_h, f"History: {new_name}")

    def apply_theme(self, p):
        self.container.config(bg=p["bg"])
        self.header_frame.config(bg=p["panel"], highlightbackground=p["border"])
        self.content_frame.config(bg=p["surface"], highlightbackground=p["border"])
        self.empty_label.config(bg=p["surface"], fg=p["muted"])
        for k, info in self.tabs.items():
            btn_frame, lbl, cls = info["header"], info["title_lbl"], info["close_lbl"]
            if k == self.active_key:
                btn_frame.config(bg=p["surface"], highlightbackground=p["accent"])
                lbl.config(bg=p["surface"], fg=p["accent"])
                cls.config(bg=p["surface"], fg=p["danger"])
            else:
                btn_frame.config(bg=p["panel"], highlightbackground=p["border"])
                lbl.config(bg=p["panel"], fg=p["text"])
                cls.config(bg=p["panel"], fg=p["muted"])
            if hasattr(info["page"], "apply_theme"):
                info["page"].apply_theme(p)
