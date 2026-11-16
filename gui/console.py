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
        super().__init__(parent, bg=p["bg"], highlightbackground=p["border"], highlightthickness=1)
        self.app = app
        self.history_commands, self.history_index = [], -1
        self.last_command, self.highlight_after_id = "", None
        self.setup_ui()

    def setup_ui(self):
        p = get_palette()

        # Bottom Button & Status Area docked to bottom
        self.bot_pane = tk.Frame(self, bg=p["panel"], padx=8, pady=6, highlightbackground=p["border"], highlightthickness=1)
        self.bot_pane.pack(fill="x", side="bottom", padx=2, pady=(0, 2))

        self.pending_lbl = tk.Label(self.bot_pane, text="No pending changes", bg=p["panel"], fg=p["muted"], font=("Segoe UI", 9, "bold"))
        self.pending_lbl.pack(anchor="w", pady=(0, 4))

        btn_row1 = tk.Frame(self.bot_pane, bg=p["panel"])
        btn_row1.pack(fill="x", pady=(0, 4))
        self.run_btn = ttk.Button(btn_row1, text="Run", style="Run.TButton", command=self.on_run)
        self.run_btn.pack(side="left", padx=(0, 4))
        self.commit_btn = ttk.Button(btn_row1, text="Commit", command=self.on_commit)
        self.commit_btn.pack(side="left", padx=3)
        self.rollback_btn = ttk.Button(btn_row1, text="Rollback", command=self.on_rollback)
        self.rollback_btn.pack(side="left", padx=3)

        btn_row2 = tk.Frame(self.bot_pane, bg=p["panel"])
        btn_row2.pack(fill="x")
        ttk.Button(btn_row2, text="Table history", command=self.on_table_history).pack(side="left", padx=(0, 2))
        ttk.Button(btn_row2, text="Memory", command=self.on_memory).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Copy last", command=self.on_copy_last).pack(side="left", padx=2)
        ttk.Button(btn_row2, text="Clear", command=self.on_clear_output).pack(side="left", padx=2)

        # Paned Window between Console Output (Box 1) and SQL Console Editor (Box 2)
        paned = ttk.Panedwindow(self, orient="vertical")
        paned.pack(fill="both", expand=True, padx=2, pady=2)

        # Box 1: Output Area with soft border & title bar
        out_frame = tk.Frame(paned, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        paned.add(out_frame, weight=1)

        self.out_hdr = tk.Frame(out_frame, bg=p["panel"], padx=8, pady=5, highlightbackground=p["border"], highlightthickness=1)
        self.out_hdr.pack(fill="x", side="top")
        self.out_title = tk.Label(self.out_hdr, text="Console Output", font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"])
        self.out_title.pack(side="left")
        self.out_hint = tk.Label(self.out_hdr, text="Execution Log", font=("Segoe UI", 8), fg=p["muted"], bg=p["panel"])
        self.out_hint.pack(side="right")

        self.output = tk.Text(
            out_frame, wrap="word", font=("Consolas", 9),
            bg=p["surface"], fg=p["text"], padx=8, pady=8,
            borderwidth=0, highlightthickness=0
        )
        out_scroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=out_scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        out_scroll.pack(side="right", fill="y")

        self.output.tag_configure("cmd", foreground=p["text"], font=("Consolas", 9, "bold"))
        self.output.tag_configure("outcome", foreground=p["muted"], font=("Consolas", 9))
        self.output.tag_configure("error", foreground=p["danger"], font=("Consolas", 9, "bold"))
        self.output.insert("end", "-- Query execution output and errors will appear here --\n", "outcome")
        self.output.config(state="disabled")

        # Box 2: SQL Console Editor with title bar
        ed_frame = tk.Frame(paned, bg=p["surface"], highlightbackground=p["border"], highlightthickness=1)
        paned.add(ed_frame, weight=1)

        self.header = tk.Frame(ed_frame, bg=p["panel"], padx=8, pady=5, highlightbackground=p["border"], highlightthickness=1)
        self.header.pack(fill="x", side="top")
        title_box = tk.Frame(self.header, bg=p["panel"])
        title_box.pack(side="left")

        self.hdr_prompt = tk.Label(title_box, text=">_", font=("Consolas", 10, "bold"), fg=p["accent"], bg=p["panel"])
        self.hdr_prompt.pack(side="left", padx=(0, 6))

        self.hdr_title = tk.Label(title_box, text="SQL Console", font=("Segoe UI", 9, "bold"), fg=p["text"], bg=p["panel"])
        self.hdr_title.pack(side="left")

        self.hdr_hint = tk.Label(self.header, text="Ctrl+Enter to Run", font=("Segoe UI", 8), fg=p["muted"], bg=p["panel"])
        self.hdr_hint.pack(side="right")

        self.editor = tk.Text(
            ed_frame, wrap="word", font=("Consolas", 10),
            bg=p["surface"], fg=p["text"], padx=8, pady=8,
            borderwidth=0, highlightthickness=0, height=8, insertbackground=p["text"]
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.tag_configure("keyword", foreground=p["accent"], font=("Consolas", 10, "bold"))

        for k, fn in [("<KeyRelease>", self.on_editor_key_release), ("<Control-Return>", lambda e: self.on_run()),
                      ("<Control-Up>", lambda e: self.recall_prev()), ("<Control-Down>", lambda e: self.recall_next()),
                      ("<Up>", self.on_arrow_up), ("<Down>", self.on_arrow_down)]:
            self.editor.bind(k, fn)

    def apply_theme(self, p):
        self.config(bg=p["bg"], highlightbackground=p["border"])
        self.out_hdr.config(bg=p["panel"], highlightbackground=p["border"])
        self.out_title.config(bg=p["panel"], fg=p["text"])
        self.out_hint.config(bg=p["panel"], fg=p["muted"])
        self.header.config(bg=p["panel"], highlightbackground=p["border"])
        self.hdr_prompt.config(bg=p["panel"], fg=p["accent"])
        self.hdr_title.config(bg=p["panel"], fg=p["text"])
        self.hdr_hint.config(bg=p["panel"], fg=p["muted"])
        self.bot_pane.config(bg=p["panel"], highlightbackground=p["border"])
        self.output.config(bg=p["surface"], fg=p["text"])
        self.editor.config(bg=p["surface"], fg=p["text"], insertbackground=p["text"])
        self.update_pending_status(self.app.db.has_pending)

    def on_editor_key_release(self, event=None):
        if self.highlight_after_id: self.after_cancel(self.highlight_after_id)
        self.highlight_after_id = self.after(100, self.apply_syntax_highlighting)

    def apply_syntax_highlighting(self):
        self.highlight_after_id = None
        content = self.editor.get("1.0", "end-1c")
        self.editor.tag_remove("keyword", "1.0", "end")
        for match in re.finditer(r"\b([A-Za-z_]+)\b", content):
            word = match.group(1).upper()
            if word in SQL_KEYWORDS_SET:
                self.editor.tag_add("keyword", f"1.0 + {match.start()} chars", f"1.0 + {match.end()} chars")

    def on_arrow_up(self, event):
        if int(self.editor.index("insert").split(".")[0]) == 1:
            return self.recall_prev()

    def on_arrow_down(self, event):
        cur_l = int(self.editor.index("insert").split(".")[0])
        if cur_l == int(self.editor.index("end-1c").split(".")[0]):
            return self.recall_next()

    def recall_prev(self):
        if not self.history_commands: return "break"
        self.history_index = len(self.history_commands) - 1 if self.history_index == -1 else max(0, self.history_index - 1)
        self.set_editor_text(self.history_commands[self.history_index])
        return "break"

    def recall_next(self):
        if not self.history_commands or self.history_index == -1: return "break"
        if self.history_index < len(self.history_commands) - 1:
            self.history_index += 1
            self.set_editor_text(self.history_commands[self.history_index])
        else:
            self.history_index = -1; self.set_editor_text("")
        return "break"

    def set_editor_text(self, text):
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.apply_syntax_highlighting()

    def print_output(self, text, tag="outcome"):
        self.output.config(state="normal")
        self.output.insert("end", text + "\n", tag)
        self.output.see("end")
        self.output.config(state="disabled")

    def on_run(self):
        try: sel_text = self.editor.get("sel.first", "sel.last").strip()
        except tk.TclError: sel_text = ""
        sql_to_run = sel_text if sel_text else self.editor.get("1.0", "end-1c").strip()
        if not sql_to_run: return

        self.last_command, self.history_index = sql_to_run, -1
        self.history_commands.append(sql_to_run)

        danger = self.app.db.is_dangerous(sql_to_run)
        if danger and not confirm_dangerous(self, danger): return

        self.print_output(f"> {sql_to_run}", tag="cmd")

        def work(): return self.app.db.run_script(sql_to_run)

        def done(results, error):
            if error:
                self.print_output(f"Error: {error}", tag="error")
                return
            had_error = False
            last_select_result = None
            for res in results:
                if res.error:
                    self.print_output(f"Error: {res.error}", tag="error")
                    had_error = True; break
                elif res.columns:
                    last_select_result = res
                    trunc = " (cut at 1000 rows)" if res.truncated else ""
                    self.print_output(f"{len(res.rows)} rows{trunc}, {res.elapsed_ms:.1f} ms", tag="outcome")
                elif res.rowcount >= 0:
                    self.print_output(f"{res.rowcount} row(s) affected, {res.elapsed_ms:.1f} ms", tag="outcome")
                else:
                    self.print_output(f"OK, {res.elapsed_ms:.1f} ms", tag="outcome")

            if not had_error:
                if not sel_text: self.set_editor_text("")
                if last_select_result: self.app.show_select_result(last_select_result)
            self.app.refresh_tables(); self.update_pending()

        self.app.run_in_background(work, done)

    def on_commit(self):
        self.app.db.commit()
        self.print_output("COMMIT executed", tag="outcome")
        self.app.update_pending()

    def on_rollback(self):
        self.app.db.rollback()
        self.print_output("ROLLBACK executed", tag="outcome")
        self.app.refresh_tables(); self.update_pending()

    def on_table_history(self):
        self.app.open_tab("history", self.app.active_table)

    def on_memory(self):
        self.app.open_tab("memory", None)

    def on_copy_last(self):
        if self.last_command:
            self.clipboard_clear(); self.clipboard_append(self.last_command)

    def on_clear_output(self):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.config(state="disabled")

    def update_pending_status(self, is_pending):
        p = get_palette()
        txt, col = ("● Uncommitted changes", p["danger"]) if is_pending else ("No pending changes", p["muted"])
        self.pending_lbl.config(text=txt, fg=col)
