import os
import tkinter as tk
import pytest
from gui.theme import apply
from gui.login import LoginWindow
from gui.main_window import MainWindow

def test_login_window_smoke():
    root = tk.Tk()
    root.withdraw()
    apply(root, "light")

    result = {}
    def on_success(uid, uname):
        result["user_id"] = uid
        result["username"] = uname

    win = LoginWindow(root, on_success)
    assert win.mode == "login"
    assert win.submit_btn.cget("text") == "Sign In"

    # Test empty submit
    win.do_submit()
    assert "enter both" in win.err_label.cget("text")

    # Test switch mode
    win.toggle_mode()
    assert win.mode == "register"
    assert win.submit_btn.cget("text") == "Create Account"

    win.set_mode("login")
    assert win.mode == "login"
    assert win.submit_btn.cget("text") == "Sign In"

    # Test dark mode apply
    apply(root, "dark")

    root.destroy()

def test_gui_full_smoke():
    root = tk.Tk()
    root.withdraw()  # do not show window during test
    apply(root, "light")

    app = MainWindow(root, user_id=1, username="musfiq")
    assert app.console.hdr_title.cget("text") == "SQL Console"
    assert "Ctrl+Enter" in app.console.hdr_hint.cget("text")
    sample_db = os.path.join(os.path.dirname(__file__), "..", "sample", "school.db")
    if os.path.exists(sample_db):
        assert app.db.open(sample_db) is True
        app.refresh_tables()
        assert len(app.sidebar.table_items) >= 3

        # Open table tab
        app.open_tab("table", "students")
        assert "table:students" in app.tabs.tabs
        t_page = app.tabs.tabs["table:students"]["page"]
        assert t_page.total_count > 0

        # Open history tab
        app.open_tab("history", "students")
        assert "history:students" in app.tabs.tabs

        # Open memory tab
        app.open_tab("memory", None)
        assert "memory" in app.tabs.tabs

        # Close tabs
        app.tabs.close_tab("history:students")
        assert "history:students" not in app.tabs.tabs

        # Test close_table_tabs
        assert "table:students" in app.tabs.tabs
        app.close_table_tabs()
        assert "table:students" not in app.tabs.tabs
        assert "memory" in app.tabs.tabs  # memory tab remains open

    app.db.close()
    app.history.close()
    app.memory.close()
    root.destroy()

