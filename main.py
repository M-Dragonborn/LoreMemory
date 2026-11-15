import sys
import tkinter as tk
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

def start_gui():
    hide_windows_console_if_double_clicked()

    root = tk.Tk()
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
        MainWindow(root, user_id, username, on_logout=show_login)

    show_login()
    root.mainloop()

def main():
    if len(sys.argv) > 1:
        sys.exit(cli.run(sys.argv[1:]))
    else:
        start_gui()

if __name__ == "__main__":
    main()
