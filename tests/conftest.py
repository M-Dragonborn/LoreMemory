import os
import sys

if sys.platform == "win32":
    for base in [r"C:\Users\M\miniconda3\Library\lib", os.path.join(sys.prefix, "Library", "lib")]:
        tcl_p = os.path.join(base, "tcl8.6")
        tk_p = os.path.join(base, "tk8.6")
        if os.path.isdir(tcl_p) and "TCL_LIBRARY" not in os.environ:
            os.environ["TCL_LIBRARY"] = tcl_p
        if os.path.isdir(tk_p) and "TK_LIBRARY" not in os.environ:
            os.environ["TK_LIBRARY"] = tk_p
