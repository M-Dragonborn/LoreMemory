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
    """Manages vertical grid lines and dynamic scroll sync for ttk.Treeview widgets."""
    def __init__(self, tree, h_scroll=None, get_color=None):
        self.tree, self.h_scroll, self.get_color = tree, h_scroll, get_color
        self.dividers = []
        if h_scroll:
            tree.configure(xscrollcommand=self._on_xscroll)
        tree.bind("<Configure>", lambda e: self.update(), add="+")
        tree.bind("<ButtonRelease-1>", lambda e: tree.after(15, self.update), add="+")

    def _on_xscroll(self, first, last):
        if self.h_scroll:
            self.h_scroll.set(first, last)
        self.update()

    def update(self):
        try:
            cols = self.tree["columns"]
        except Exception:
            return
        if not cols:
            for d in self.dividers: d.place_forget()
            return
        needed = max(0, len(cols) - 1)
        color = self.get_color() if self.get_color else "#cbd5e1"
        while len(self.dividers) < needed:
            d = tk.Frame(self.tree, bg=color, width=1)
            d.bind("<Button-1>", lambda e: self.tree.event_generate(
                "<Button-1>", x=e.x_root - self.tree.winfo_rootx(), y=e.y_root - self.tree.winfo_rooty()
            ))
            self.dividers.append(d)
        while len(self.dividers) > needed:
            self.dividers.pop().destroy()

        children = self.tree.get_children()
        if children:
            for idx in range(needed):
                bbox = self.tree.bbox(children[0], cols[idx])
                if bbox and bbox[2] > 0:
                    self.dividers[idx].place(x=bbox[0] + bbox[2] - 1, y=0, relheight=1.0, width=1)
                else:
                    self.dividers[idx].place_forget()
        else:
            cur_x = 0
            for idx in range(needed):
                cur_x += self.tree.column(cols[idx], "width")
                self.dividers[idx].place(x=cur_x - 1, y=0, relheight=1.0, width=1)

    def apply_theme(self, p):
        color = p.get("grid_line", "#cbd5e1")
        for d in self.dividers:
            d.config(bg=color)
        self.update()


