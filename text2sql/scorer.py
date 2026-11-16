import sqlite3
from dataclasses import dataclass
from itertools import permutations

import sqlglot

from text2sql.executor import QueryTimeout, execute
from text2sql.guard import UnsafeSQLError, guard

MAX_ROWS = 1000


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

# 정답 SQL은 guard 없이 원문 실행. 1,000행 초과면 예측 쪽 LIMIT과 어긋나므로 중단
def run_gold(gold_sql: str) -> list[tuple]:
    rows = execute(gold_sql)
    if len(rows) > MAX_ROWS:
        raise ValueError(f"gold result {len(rows)} rows > {MAX_ROWS}: 골든셋 원칙 위반")
    return rows


def is_ordered(sql: str) -> bool:
    return sqlglot.parse_one(sql, read="sqlite").args.get("order") is not None


def score(gold_sql: str, pred_sql: str) -> Verdict:
    expected = run_gold(gold_sql)
    try:
        got = execute(guard(pred_sql, MAX_ROWS))
    except (UnsafeSQLError, QueryTimeout, sqlite3.Error) as e:
        return Verdict("error", f"{type(e).__name__}: {e}")
    ordered = is_ordered(gold_sql)
    if normalize(got, ordered) == normalize(expected, ordered):
        return Verdict("correct")
    return Verdict("silent_wrong", f"expected {expected[:3]}, got {got[:3]}")


# 너그러운 채점: 컬럼 수만 다르고 겹치는 컬럼 값은 같으면 True (예: 순위는 맞는데 개수 컬럼 누락)
def same_on_shared_columns(expected: list[tuple], got: list[tuple], ordered: bool) -> bool:
    if not expected or not got or len(expected) != len(got):
        return False
    small, big = sorted([got, expected], key=lambda rows: len(rows[0]))
    k, n = len(small[0]), len(big[0])
    if k == n:
        return False
    target = normalize(small, ordered)
    return any(
        normalize([tuple(row[i] for i in cols) for row in big], ordered) == target
        for cols in permutations(range(n), k)
    )


def is_lenient_correct(gold_sql: str, pred_sql: str) -> bool:
    expected = run_gold(gold_sql)
    try:
        got = execute(guard(pred_sql, MAX_ROWS))
    except (UnsafeSQLError, QueryTimeout, sqlite3.Error):
        return False
    return same_on_shared_columns(expected, got, is_ordered(gold_sql))
