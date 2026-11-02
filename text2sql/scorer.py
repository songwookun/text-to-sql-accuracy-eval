import sqlite3
from dataclasses import dataclass

import sqlglot

from text2sql.executor import QueryTimeout, execute
from text2sql.guard import UnsafeSQLError, guard


@dataclass
class Verdict:
    label: str
    detail: str = ""


def normalize(rows: list[tuple], ordered: bool) -> list[tuple]:
    out = [
        tuple(round(float(v), 2) if isinstance(v, (int, float)) else v for v in row)
        for row in rows
    ]
    return out if ordered else sorted(out, key=repr)

def is_ordered(sql: str) -> bool:
    return sqlglot.parse_one(sql, read="sqlite").args.get("order") is not None


def score(gold_sql: str, pred_sql: str) -> Verdict:
    expected = execute(guard(gold_sql))
    try:
        got = execute(guard(pred_sql))
    except (UnsafeSQLError, QueryTimeout, sqlite3.Error) as e:
        return Verdict("error", f"{type(e).__name__}: {e}")
    ordered = is_ordered(gold_sql)
    if normalize(got, ordered) == normalize(expected, ordered):
        return Verdict("correct")
    return Verdict("silent_wrong", f"expected {expected[:3]}, got {got[:3]}")