import queue
import threading
import tkinter as tk

def run_in_background(root, work, done):
    q = queue.Queue()

    def worker():
        try:
            val = work()
            q.put((val, None))
        except Exception as e:
            q.put((None, str(e)))

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    def check_queue():
        try:
            val, err = q.get_nowait()
            done(val, err)
        except queue.Empty:
            root.after(50, check_queue)

    root.after(50, check_queue)
    return t

class TreeGrid:
    """Manages uniform 1px 2D grid lines (vertical and horizontal) for ttk.Treeview widgets."""
    def __init__(self, tree, h_scroll=None, get_color=None):
        self.tree, self.h_scroll, self.get_color = tree, h_scroll, get_color
        self.v_divs, self.h_divs, self._after_id = [], [], None
        if h_scroll:
            tree.configure(xscrollcommand=self._on_xscroll)
        orig_y = tree.cget("yscrollcommand")
        def _on_yscroll(first, last):
            if orig_y:
                try: tree.tk.call(orig_y, first, last)
                except Exception: pass
            self.schedule_update()
        tree.configure(yscrollcommand=_on_yscroll)
        tree.bind("<Configure>", self._on_configure, add="+")
        tree.bind("<ButtonRelease-1>", lambda e: self.schedule_update(20), add="+")
        tree.bind("<B1-Motion>", lambda e: self.schedule_update(15), add="+")
        tree.bind("<MouseWheel>", lambda e: self.schedule_update(10), add="+")

    @property
    def dividers(self):
        return self.v_divs

    def _pass_click(self, e):
        self.tree.event_generate(
            "<Button-1>", x=e.x_root - self.tree.winfo_rootx(), y=e.y_root - self.tree.winfo_rooty()
        )

    def _on_configure(self, e):
        if e.widget == self.tree:
            self.schedule_update()

    def _on_xscroll(self, first, last):
        if self.h_scroll:
            self.h_scroll.set(first, last)
        self.schedule_update()

    def schedule_update(self, delay=0):
        if self._after_id is not None:
            return
        if delay > 0:
            self._after_id = self.tree.after(delay, self._run_update)
        else:
            self._after_id = self.tree.after_idle(self._run_update)

    def _run_update(self):
        self._after_id = None
        self.update()

    def update(self):
        try:
            cols = self.tree["columns"]
        except Exception:
            return
        color = self.get_color() if self.get_color else "#000000"
        tree_w = self.tree.winfo_width()
        tree_h = self.tree.winfo_height()
        tot_w = sum(self.tree.column(c, "width") for c in cols) if cols else 0
        x_off = int(round(self.tree.xview()[0] * tot_w)) if tot_w else 0
        line_w = max(0, min(tree_w, tot_w - x_off))
        children = self.tree.get_children()
        head_h = next((y for y in range(15, 45) if self.tree.identify_region(20, y) != "heading"), 25)

        # 1. Determine horizontal divider lines and content bottom boundary
        y_positions = [head_h - 1]
        max_y = head_h
        item = self.tree.identify_row(head_h + 2)
        if not item and children:
            for c in children:
                if self.tree.bbox(c):
                    item = c
                    break
        while item:
            bb = self.tree.bbox(item)
            if not bb: break
            y_bot = bb[1] + bb[3] - 1
            if y_bot < tree_h:
                y_positions.append(y_bot)
            max_y = max(max_y, bb[1] + bb[3])
            item = self.tree.next(item)

        # 2. Vertical column dividers (bounded by visible data rows)
        v_h = min(tree_h, max_y)
        needed_v = max(0, len(cols) - 1) if cols else 0
        while len(self.v_divs) < needed_v:
            d = tk.Frame(self.tree, bg=color, width=1)
            d.bind("<Button-1>", self._pass_click)
            self.v_divs.append(d)
        while len(self.v_divs) > needed_v:
            self.v_divs.pop().destroy()

        if needed_v:
            cur_x = 1 - x_off
            for idx in range(needed_v):
                cur_x += self.tree.column(cols[idx], "width")
                tx = cur_x - 1
                div = self.v_divs[idx]
                if 0 <= tx <= tree_w and v_h > 0:
                    if div.winfo_x() != tx or div.winfo_height() != v_h or not div.winfo_ismapped():
                        div.place(x=tx, y=0, height=v_h, width=1, relheight="")
                else:
                    if div.winfo_ismapped(): div.place_forget()

        # 3. Horizontal row dividers (header divider + visible row dividers)
        needed_h = len(y_positions) if line_w > 0 else 0
        while len(self.h_divs) < needed_h:
            d = tk.Frame(self.tree, bg=color, height=1)
            d.bind("<Button-1>", self._pass_click)
            self.h_divs.append(d)
        while len(self.h_divs) > needed_h:
            self.h_divs.pop().destroy()

        for idx in range(needed_h):
            ty = y_positions[idx]
            div = self.h_divs[idx]
            if div.winfo_y() != ty or div.winfo_width() != line_w or not div.winfo_ismapped():
                div.place(x=0, y=ty, width=line_w, height=1, relwidth="")

    def apply_theme(self, p):
        color = p.get("grid_line", "#000000")
        for d in self.v_divs + self.h_divs:
            d.config(bg=color)
        self.schedule_update()


