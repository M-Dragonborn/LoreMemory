import os
import sys
if sys.platform == "win32":
    sys.coinit_flags = 2  # COINIT_APARTMENTTHREADED for Windows COM dialogs
    for p, sub in [("TCL_LIBRARY", ("Library", "lib", "tcl8.6")), ("TK_LIBRARY", ("Library", "lib", "tk8.6"))]:
        if p not in os.environ:
            d = os.path.join(sys.prefix, *sub)
            if os.path.exists(d): os.environ[p] = d

import tkinter as tk
from tkinter import messagebox
import traceback
import cli
from gui.theme import apply
from gui.login import LoginWindow
from gui.main_window import MainWindow

def hide_windows_console_if_double_clicked():
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.WinDLL("kernel32")
            user32 = ctypes.WinDLL("user32")
            proc_list = (ctypes.c_uint * 1)()
            count = kernel32.GetConsoleProcessList(proc_list, 1)
            if count == 1:
                hwnd = kernel32.GetConsoleWindow()
                if hwnd:
                    user32.ShowWindow(hwnd, 0)
        except Exception:
            pass

def start_gui(initial_db=None):
    hide_windows_console_if_double_clicked()

    root = tk.Tk()
    def on_tk_exception(exc_type, exc_val, exc_tb):
        err = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        try:
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(err + "\n")
        except Exception:
            pass
        if sys.stderr:
            try: print("Exception:", err, file=sys.stderr)
            except Exception: pass
        try:
            exc_desc = f"{exc_type.__name__}: {exc_val}" if exc_type else "An unexpected error occurred."
            messagebox.showerror("Application Error", f"{exc_desc}\n\nDetails have been logged to crash.log.", parent=root)
        except Exception:
            pass
    root.report_callback_exception = on_tk_exception
    sys.excepthook = on_tk_exception

    apply(root, "light")
    try:
        root.state("zoomed")
    except Exception:
        root.geometry("1200x800")

    def show_login():
        for w in root.winfo_children():
            w.destroy()
        LoginWindow(root, on_login_success)

    def on_login_success(user_id, username):
        for w in root.winfo_children():
            w.destroy()
        app = MainWindow(root, user_id, username, on_logout=show_login)
        if initial_db and os.path.exists(initial_db):
            def load_init():
                if app.db.open(initial_db):
                    app.sidebar.update_db_name(initial_db)
                    app.status_file.config(text=os.path.basename(initial_db))
                    app.refresh_tables(); app.update_pending()
            root.after(100, load_init)

    show_login()
    root.mainloop()

def main():
    if len(sys.argv) > 1:
        first = sys.argv[1]
        cli_cmds = ("remember", "recall", "recent", "pending", "episode", "consolidate", "importance", "stats", "-h", "--help")
        if first.lower() in cli_cmds:
            sys.exit(cli.run(sys.argv[1:]))
        elif first.endswith((".db", ".sqlite", ".sqlite3")) or os.path.exists(first) or first in ("--gui", "-g"):
            start_gui(initial_db=first if first not in ("--gui", "-g") else None)
        else:
            print(f"Unknown command or database: '{first}'. Run with --help for terminal commands.", file=sys.stderr)
            sys.exit(1)
    else:
        start_gui()

if __name__ == "__main__":
    main()
