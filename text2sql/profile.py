import re
import sqlite3
from functools import cache

from text2sql.executor import DB_PATH

DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def date_kind(values: list[str]) -> str | None:
    dates = [v for v in values if isinstance(v, str) and DATETIME.match(v)]
    if not values or len(dates) < len(values):
        return None
    midnight = sum(v.endswith("00:00:00") for v in dates)
    return "date only (time always 00:00:00)" if midnight / len(dates) >= 0.99 else "datetime"


def describe(col: str, typ: str, values: list, total: int) -> str:
    parts = [typ or "TEXT", f"nulls {1 - len(values) / total:.1%}"]
    kind = date_kind(values)
    distinct = set(values)
    if kind:
        parts.append(kind)
    elif not col.endswith("_id") and len(distinct) <= 10:
        parts.append("values: " + ", ".join(sorted(map(str, distinct))))
        return ", ".join(parts)
    if values and not col.endswith("_id"):
        parts.append(f"e.g. {str(values[0])[:40]}")
    return ", ".join(parts)


@cache
def profile_columns() -> str:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        lines = ["## Column profile (computed from the data)"]
        tables = [t for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        for t in tables:
            total = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for _, col, typ, *_ in conn.execute(f"PRAGMA table_info({t})").fetchall():
                values = [v for (v,) in conn.execute(f"SELECT {col} FROM {t} WHERE {col} IS NOT NULL")]
                lines.append(f"- {t}.{col}: {describe(col, typ, values, total)}")
    finally:
        conn.close()
    return "\n".join(lines)
