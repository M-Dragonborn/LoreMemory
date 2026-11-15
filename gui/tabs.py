import tkinter as tk
from tkinter import ttk
from gui.theme import get_palette

class TabStrip:
    def __init__(self, parent, on_tab_close=None, on_tab_switch=None):
        self.parent = parent
        self.on_tab_close = on_tab_close
        self.on_tab_switch = on_tab_switch

        self.tabs = {}  # key -> dict(kind, title, page, frame, tab_widget)
        self.active_key = None

        p = get_palette()
        self.container = ttk.Frame(parent)

        # Tab strip header
        self.header_frame = tk.Frame(self.container, bg=p["bg"], height=32)
        self.header_frame.pack(fill="x", side="top")
        self.header_frame.pack_propagate(False)

        # Content area
        self.content_frame = ttk.Frame(self.container)
        self.content_frame.pack(fill="both", expand=True, side="bottom")

        # Empty hint
        self.empty_label = tk.Label(
            self.content_frame,
            text="Open a table from the left",
            font=("Segoe UI", 12),
            fg=p["muted"],
            bg=p["bg"]
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

    def pack(self, **kwargs):
        self.container.pack(**kwargs)

    def select(self, key):
        if key not in self.tabs:
            return
        self.active_key = key
        p = get_palette()

        # Update tab headers
        for k, info in self.tabs.items():
            btn_frame = info["header"]
            lbl = info["title_lbl"]
            cls = info["close_lbl"]
            if k == key:
                btn_frame.config(bg=p["surface"], highlightbackground=p["accent"], highlightthickness=1)
                lbl.config(bg=p["surface"], fg=p["accent"])
                cls.config(bg=p["surface"], fg=p["muted"])
                info["page"].tkraise()
                if hasattr(info["page"], "reload"):
                    info["page"].reload()
            else:
                btn_frame.config(bg=p["bg"], highlightthickness=0)
                lbl.config(bg=p["bg"], fg=p["text"])
                cls.config(bg=p["bg"], fg=p["muted"])

        self.empty_label.place_forget()
        if self.on_tab_switch:
            self.on_tab_switch(key, self.tabs[key]["kind"], self.tabs[key]["page"])

    def add_tab(self, key, kind, title, page):
        if key in self.tabs:
            self.select(key)
            return self.tabs[key]["page"]

        p = get_palette()
        tab_hdr = tk.Frame(self.header_frame, bg=p["bg"], padx=6, pady=2)
        tab_hdr.pack(side="left", padx=2, pady=(4, 0))

        lbl = tk.Label(tab_hdr, text=title, font=("Segoe UI", 9), bg=p["bg"], fg=p["text"], cursor="hand2")
        lbl.pack(side="left", padx=(2, 4))
        lbl.bind("<Button-1>", lambda e, k=key: self.select(k))
        tab_hdr.bind("<Button-1>", lambda e, k=key: self.select(k))

        cls = tk.Label(tab_hdr, text="×", font=("Segoe UI", 10, "bold"), bg=p["bg"], fg=p["muted"], cursor="hand2")
        cls.pack(side="right", padx=(2, 2))
        cls.bind("<Button-1>", lambda e, k=key: self.close_tab(k))

        # Position page in content frame
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
                self.empty_label.config(bg=p["bg"], fg=p["muted"])
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
        t_key = f"table:{table_name}"
        h_key = f"history:{table_name}"
        self.close_tab(h_key)
        self.close_tab(t_key)

    def rename_table_tabs(self, old_name, new_name):
        old_t, new_t = f"table:{old_name}", f"table:{new_name}"
        old_h, new_h = f"history:{old_name}", f"history:{new_name}"
        if old_t in self.tabs:
            self.rename_tab(old_t, new_t, new_name)
        if old_h in self.tabs:
            self.rename_tab(old_h, new_h, f"History: {new_name}")
