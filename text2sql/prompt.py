import sqlite3

from text2sql.executor import DB_PATH

REFERENCE_DATE = "2018-08-31"


def load_schema() -> str:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
    finally:
        conn.close()
    return "\n\n".join(sql for (sql,) in rows)

def build_prompt(question: str) -> str:
    parts = [
        "You are a SQLite expert. Write one SQLite query that answers the question.",
        f"Today is {REFERENCE_DATE}. Resolve relative dates like 'last month' from this date.",
        "Output only the SQL. No explanation.",
        "## Schema\n" + load_schema(),
        f"## Question\n{question}",
    ]
    return "\n\n".join(parts)
