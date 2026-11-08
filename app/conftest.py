import os
import sqlite3
import tempfile

# Set DB_PATH before main.py is imported so the module-level constant picks it up.
_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DB_PATH"] = _db_path
