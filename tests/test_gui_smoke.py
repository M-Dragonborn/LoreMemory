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

        # Open admin tab (musfiq is super_admin)
        app.open_tab("admin", None)
        assert "admin" in app.tabs.tabs
        admin_page = app.tabs.tabs["admin"]["page"]
        assert len(admin_page.users_tree.get_children()) >= 1
        admin_page.switch_view("audit")
        assert admin_page.active_subview == "audit"
        admin_page.switch_view("users")
        assert admin_page.active_subview == "users"
        app.tabs.close_tab("admin")
        assert "admin" not in app.tabs.tabs

        # Close tabs
        app.tabs.close_tab("history:students")
        assert "history:students" not in app.tabs.tabs

        # Test close_table_tabs
        assert "table:students" in app.tabs.tabs
        app.close_table_tabs()
        assert "table:students" not in app.tabs.tabs
        assert "memory" in app.tabs.tabs  # memory tab remains open

        # Test autocomplete Tab completion
        app.console.set_editor_text("SELECT * FROM stu")
        app.console.editor.mark_set("insert", "end-1c")
        app.autocomplete.trigger_autocomplete(force=True)
        assert len(app.autocomplete.matches) > 0
        app.autocomplete.on_tab(None)
        assert app.console.editor.get("1.0", "end-1c") == "SELECT * FROM students"

        # Test keyword completion
        app.console.set_editor_text("sel")
        app.console.editor.mark_set("insert", "end-1c")
        app.autocomplete.trigger_autocomplete(force=True)
        app.autocomplete.on_tab(None)
        assert app.console.editor.get("1.0", "end-1c") == "SELECT"

    app.db.close()
    app.history.close()
    app.memory.close()
    root.destroy()

