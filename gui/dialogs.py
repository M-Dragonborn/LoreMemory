import tkinter as tk
from tkinter import ttk, messagebox
from gui.theme import get_palette

class RowDialog(tk.Toplevel):
    def __init__(self, parent, title, columns, initial_values=None):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.columns = columns
        self.initial_values = initial_values or {}
        self.entries = {}

        p = get_palette()
        self.configure(bg=p["bg"])
        self.transient(parent)
        try: self.grab_set()
        except Exception: pass

        card = tk.Frame(
            self, bg=p["surface"], padx=16, pady=16,
            highlightbackground=p["border"], highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=8, pady=8)

        row_idx = 0
        for col in self.columns:
            cname = col["name"]
            ctype = col["type"].upper()
            if "BLOB" in ctype:
                continue

            lbl_txt = f"{cname} ({ctype})"
            if col["pk"]:
                lbl_txt += " [PK]"
            if col["notnull"]:
                lbl_txt += " *"

            tk.Label(
                card, text=lbl_txt, bg=p["surface"], fg=p["text"],
                font=("Segoe UI", 9, "bold")
            ).grid(row=row_idx, column=0, sticky="w", pady=4, padx=(0, 8))

            ent = ttk.Entry(card, width=32)
            ent.grid(row=row_idx, column=1, sticky="ew", pady=4)

            val = self.initial_values.get(cname, "")
            if val is not None and str(val) != "":
                ent.insert(0, str(val))
            self.entries[cname] = (ent, col)
            row_idx += 1

        btn_frame = tk.Frame(card, bg=p["surface"], pady=12)
        btn_frame.grid(row=row_idx, column=0, columnspan=2, sticky="e")

        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Save", style="Run.TButton", command=self.on_save).pack(side="right")

        self.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

    def on_save(self):
        data = {}
        for cname, (ent, col) in self.entries.items():
            val = ent.get().strip()
            if val == "":
                if self.initial_values:
                    if col["notnull"] and col["default"] is None and not col["pk"]:
                        messagebox.showerror("Validation Error", f"Field '{cname}' cannot be empty (NOT NULL).", parent=self)
                        return
                    data[cname] = None
                else:
                    pass
            else:
                ctype = col["type"].upper()
                try:
                    if "INT" in ctype:
                        data[cname] = int(val)
                    elif any(t in ctype for t in ("REAL", "FLOAT", "DOUB", "NUM")):
                        data[cname] = float(val)
                    else:
                        data[cname] = val
                except ValueError:
                    messagebox.showerror("Validation Error", f"Invalid format for '{cname}' ({ctype}).", parent=self)
                    return

        self.result = data
        self.destroy()

class NewTableDialog(tk.Toplevel):
    def __init__(self, parent, on_create):
        super().__init__(parent)
        self.title("New Table")
        self.on_create = on_create
        p = get_palette()
        self.configure(bg=p["bg"])
        self.transient(parent)
        try: self.grab_set()
        except Exception: pass

        card = tk.Frame(
            self, bg=p["surface"], padx=16, pady=16,
            highlightbackground=p["border"], highlightthickness=1
        )
        card.pack(fill="both", expand=True, padx=8, pady=8)

        tk.Label(card, text="Table Name:", bg=p["surface"], fg=p["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        self.name_entry = ttk.Entry(card, width=30)
        self.name_entry.grid(row=0, column=1, sticky="w", pady=4)
        self.name_entry.focus()

        tk.Label(
            card, text="Columns (name type [PK] [NOT NULL]):",
            bg=p["surface"], fg=p["text"], font=("Segoe UI", 9, "bold")
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 4))

        self.col_text = tk.Text(
            card, width=45, height=8, font=("Consolas", 10),
            bg=p["surface"], fg=p["text"], relief="solid", borderwidth=1,
            highlightbackground=p["border"], highlightthickness=1
        )
        self.col_text.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=4)
        self.col_text.insert("1.0", "id INTEGER PRIMARY KEY AUTOINCREMENT\nname TEXT NOT NULL\ncreated_at TEXT DEFAULT CURRENT_TIMESTAMP")

        btn_frame = tk.Frame(card, bg=p["surface"], pady=10)
        btn_frame.grid(row=3, column=0, columnspan=2, sticky="e")
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Create Table", style="Run.TButton", command=self.do_create).pack(side="right")

        self.update_idletasks()
        try:
            w, h = 420, 320
            x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
            y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
            self.geometry(f"+{x}+{y}")
        except Exception: pass

    def do_create(self):
        tname = self.name_entry.get().strip()
        if not tname:
            messagebox.showerror("Error", "Please enter a table name.", parent=self)
            return
        lines = [line.strip() for line in self.col_text.get("1.0", "end").splitlines() if line.strip()]
        if not lines:
            messagebox.showerror("Error", "Please enter at least one column definition.", parent=self)
            return
        cols_sql = ",\n    ".join(lines)
        sql = f"CREATE TABLE \"{tname}\" (\n    {cols_sql}\n);"
        try:
            res = self.on_create(sql, tname)
        except TypeError:
            res = self.on_create(sql)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        if res is not False:
            self.destroy()

def confirm_dangerous(parent, warning_text):
    msg = f"{warning_text}\n\nDo you want to proceed?"
    return messagebox.askyesno("Dangerous Query Warning", msg, parent=parent)
