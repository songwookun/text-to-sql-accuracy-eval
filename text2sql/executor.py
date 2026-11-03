import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "olist.db"


class QueryTimeout(Exception):
    pass

def query(sql: str, timeout: float = 10.0) -> tuple[list[str], list[tuple]]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    deadline = time.monotonic() + timeout
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)
    try:
        cur = conn.execute(sql)
        return [d[0] for d in cur.description or []], cur.fetchall()
    except sqlite3.OperationalError as e:
        if time.monotonic() > deadline:
            raise QueryTimeout(f"exceeded {timeout}s") from e
        raise
    finally:
        conn.close()


def execute(sql: str, timeout: float = 10.0) -> list[tuple]:
    return query(sql, timeout)[1]
