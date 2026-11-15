import os
import tkinter as tk
import pytest
from gui.theme import apply
from gui.main_window import MainWindow

def test_gui_full_smoke():
    root = tk.Tk()
    root.withdraw()  # do not show window during test
    apply(root, "light")

    app = MainWindow(root, user_id=1, username="alice")
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

    app.db.close()
    app.history.close()
    app.memory.close()
    root.destroy()
