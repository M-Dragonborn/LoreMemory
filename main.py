import sys
if sys.platform == "win32":
    sys.coinit_flags = 2  # COINIT_APARTMENTTHREADED for Windows COM dialogs

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
        print("Exception:", err, file=sys.stderr)
        try:
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(err + "\n")
        except Exception: pass
        try:
            messagebox.showerror("Unexpected Error", f"An error occurred:\n\n{err}", parent=root)
        except Exception:
            pass
    root.report_callback_exception = on_tk_exception

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
        first = sys.argv[1].lower()
        if first in ("remember", "recall", "recent", "pending", "episode", "consolidate", "importance", "stats", "-h", "--help"):
            sys.exit(cli.run(sys.argv[1:]))
        else:
            start_gui(initial_db=sys.argv[1])
    else:
        start_gui()

if __name__ == "__main__":
    main()
