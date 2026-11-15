import os
import sys
from pathlib import Path

# Paths
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

USERS_DB = DATA_DIR / "users.db"
HISTORY_DB = DATA_DIR / "history.db"
MEMORY_DB = DATA_DIR / "memory.db"

# Limits
ROW_LIMIT = 1000
PAGE_SIZE = 100
HISTORY_BATCH = 500
MIN_WINDOW = "1100x700"

# AI Memory weights and settings
VEC_W = 0.5
KW_W = 0.3
IMP_W = 0.2
RECENCY_W = 0.1
HALF_LIFE_HOURS = 168
CONSOLIDATE_HOURS = 24
MIN_SIM = 0.25

