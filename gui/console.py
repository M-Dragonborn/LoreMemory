import re
import tkinter as tk
from tkinter import ttk, messagebox
from gui.theme import get_palette
from gui.dialogs import confirm_dangerous

SQL_KEYWORDS_SET = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET",
    "DELETE", "DROP", "CREATE", "ALTER", "TABLE", "JOIN", "ON", "ORDER",
    "BY", "GROUP", "LIMIT", "AND", "OR", "NOT", "NULL", "PRIMARY", "KEY"
}

class Console(tk.Frame):
    def __init__(self, parent, app):
        p = get_palette()
        super().__init__(parent, bg=p["bg"], highlightbackground=p["border_dark"], highlightthickness=1)
        self.app = app
        self.history_commands = []
        self.history_index = -1
        self.last_command = ""

        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        paned = ttk.Panedwindow(self, orient="vertical")
        paned.pack(fill="both", expand=True, padx=2, pady=2)

        top_pane = tk.Frame(paned, bg=p["bg"])
        paned.add(top_pane, weight=3)

        # Output Area with clear border
        out_frame = tk.Frame(
            top_pane, bg=p["surface"],
            highlightbackground=p["border_dark"], highlightthickness=1
        )
        out_frame.pack(fill="both", expand=True, side="top", pady=(0, 4))

        self.output = tk.Text(
            out_frame, wrap="word", font=("Consolas", 9),
            bg=p["surface"], fg=p["text"], padx=8, pady=8,
            borderwidth=0, highlightthickness=0, state="disabled"
        )
        out_scroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=out_scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        out_scroll.pack(side="right", fill="y")

        self.output.tag_configure("cmd", foreground=p["text"], font=("Consolas", 9, "bold"))
        self.output.tag_configure("outcome", foreground=p["muted"], font=("Consolas", 9, "italic"))
        self.output.tag_configure("error", foreground=p["danger"], font=("Consolas", 9, "bold"))

        # Editor Area with prominent border outline
        ed_frame = tk.Frame(
            top_pane, bg=p["surface"],
            highlightbackground=p["border_dark"], highlightthickness=2
        )
        ed_frame.pack(fill="both", expand=True, side="bottom")

        self.editor = tk.Text(
            ed_frame, wrap="word", font=("Consolas", 10),
            bg=p["surface"], fg=p["text"], padx=8, pady=8,
            borderwidth=0, highlightthickness=0, height=8, insertbackground=p["text"]
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.tag_configure("keyword", foreground=p["accent"], font=("Consolas", 10, "bold"))

        self.editor.bind("<KeyRelease>", self.on_editor_key_release)
        self.editor.bind("<Control-Return>", lambda e: self.on_run())
        self.editor.bind("<Control-Up>", lambda e: self.recall_prev())
        self.editor.bind("<Control-Down>", lambda e: self.recall_next())
        self.editor.bind("<Up>", self.on_arrow_up)
        self.editor.bind("<Down>", self.on_arrow_down)

        # Button & Status Area with panel border
        bot_pane = tk.Frame(
            paned, bg=p["panel"], padx=10, pady=8,
            highlightbackground=p["border_dark"], highlightthickness=1
        )
        paned.add(bot_pane, weight=1)

        self.pending_lbl = tk.Label(
            bot_pane, text="No pending changes", bg=p["panel"],
            fg=p["muted"], font=("Segoe UI", 9, "bold")
        )
        self.pending_lbl.pack(anchor="w", pady=(0, 6))

        btn_row1 = tk.Frame(bot_pane, bg=p["panel"])
        btn_row1.pack(fill="x", pady=(0, 4))

        self.run_btn = ttk.Button(btn_row1, text="Run", style="Run.TButton", command=self.on_run)
        self.run_btn.pack(side="left", padx=(0, 4))

        self.commit_btn = ttk.Button(btn_row1, text="Commit", command=self.on_commit)
        self.commit_btn.pack(side="left", padx=4)

        self.rollback_btn = ttk.Button(btn_row1, text="Rollback", command=self.on_rollback)
        self.rollback_btn.pack(side="left", padx=4)

        btn_row2 = tk.Frame(bot_pane, bg=p["panel"])
        btn_row2.pack(fill="x")

        ttk.Button(btn_row2, text="Table history", command=self.on_table_history).pack(side="left", padx=(0, 2))
        ttk.Button(btn_row2, text="Memory", command=self.on_memory).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Copy last", command=self.on_copy_last).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Clear", command=self.on_clear_output).pack(side="left", padx=2)

    def on_editor_key_release(self, event=None):
        content = self.editor.get("1.0", "end-1c")
        self.editor.tag_remove("keyword", "1.0", "end")
        for match in re.finditer(r"\b([A-Za-z_]+)\b", content):
            word = match.group(1).upper()
            if word in SQL_KEYWORDS_SET:
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.editor.tag_add("keyword", start, end)

    def on_arrow_up(self, event):
        cur_line = int(self.editor.index("insert").split(".")[0])
        if cur_line == 1:
            return self.recall_prev()

    def on_arrow_down(self, event):
        cur_line = int(self.editor.index("insert").split(".")[0])
        total_lines = int(self.editor.index("end-1c").split(".")[0])
        if cur_line == total_lines:
            return self.recall_next()

    def recall_prev(self):
        if not self.history_commands:
            return "break"
        if self.history_index == -1:
            self.history_index = len(self.history_commands) - 1
        elif self.history_index > 0:
            self.history_index -= 1
        self.set_editor_text(self.history_commands[self.history_index])
        return "break"

    def recall_next(self):
        if not self.history_commands or self.history_index == -1:
            return "break"
        if self.history_index < len(self.history_commands) - 1:
            self.history_index += 1
            self.set_editor_text(self.history_commands[self.history_index])
        else:
            self.history_index = -1
            self.set_editor_text("")
        return "break"

    def set_editor_text(self, text):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.on_editor_key_release()

    def print_output(self, text, tag="outcome"):
        self.output.config(state="normal")
        self.output.insert("end", text + "\n", tag)
        self.output.see("end")
        self.output.config(state="disabled")

    def on_run(self):
        try:
            sel_text = self.editor.get("sel.first", "sel.last").strip()
        except tk.TclError:
            sel_text = ""
        sql_to_run = sel_text if sel_text else self.editor.get("1.0", "end-1c").strip()
        if not sql_to_run:
            return

        self.last_command = sql_to_run
        self.history_commands.append(sql_to_run)
        self.history_index = -1

        danger = self.app.db.is_dangerous(sql_to_run)
        if danger:
            if not confirm_dangerous(self, danger):
                return

        self.print_output(f"> {sql_to_run}", tag="cmd")

        def work():
            return self.app.db.run_script(sql_to_run)

        def done(results, error):
            if error:
                self.print_output(f"Error: {error}", tag="error")
                return

            had_error = False
            last_select_result = None
            for res in results:
                if res.error:
                    self.print_output(f"Error: {res.error}", tag="error")
                    had_error = True
                    break
                elif res.columns:
                    last_select_result = res
                    trunc_note = " (cut at 1000 rows)" if res.truncated else ""
                    self.print_output(f"{len(res.rows)} rows{trunc_note}, {res.elapsed_ms:.1f} ms", tag="outcome")
                elif res.rowcount >= 0:
                    self.print_output(f"{res.rowcount} row(s) affected, {res.elapsed_ms:.1f} ms", tag="outcome")
                else:
                    self.print_output(f"OK, {res.elapsed_ms:.1f} ms", tag="outcome")

            if not had_error:
                if not sel_text:
                    self.set_editor_text("")
                if last_select_result:
                    self.app.show_select_result(last_select_result)
            self.app.refresh_tables()
            self.app.update_pending()

        self.app.run_in_background(work, done)

    def on_commit(self):
        self.app.db.commit()
        self.print_output("COMMIT executed", tag="outcome")
        self.app.update_pending()

    def on_rollback(self):
        self.app.db.rollback()
        self.print_output("ROLLBACK executed", tag="outcome")
        self.app.refresh_tables()
        self.app.update_pending()

    def on_table_history(self):
        active_tbl = self.app.active_table
        self.app.open_tab("history", active_tbl)

    def on_memory(self):
        self.app.open_tab("memory", None)

    def on_copy_last(self):
        if self.last_command:
            self.clipboard_clear()
            self.clipboard_append(self.last_command)

    def on_clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

    def update_pending_status(self, is_pending):
        p = get_palette()
        if is_pending:
            self.pending_lbl.config(text="● Uncommitted changes", fg=p["danger"])
        else:
            self.pending_lbl.config(text="No pending changes", fg=p["muted"])
