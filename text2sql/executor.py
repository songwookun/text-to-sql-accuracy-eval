import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "olist.db"


class QueryTimeout(Exception):
    pass

def execute(sql: str, timeout: float = 10.0) -> list[tuple]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    deadline = time.monotonic() + timeout
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)
    try:
        return conn.execute(sql).fetchall()
    except sqlite3.OperationalError as e:
        if time.monotonic() > deadline:
            raise QueryTimeout(f"exceeded {timeout}s") from e
        raise
    finally:
        conn.close()