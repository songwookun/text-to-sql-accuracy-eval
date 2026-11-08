import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from functools import cache

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope

from text2sql.catalog import METRICS, ONE_TO_MANY
from text2sql.executor import DB_PATH


@dataclass
class Issue:
    code: str
    message: str


@cache
def db_schema() -> dict:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        names = [n for (n,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        return {t: {r[1]: r[2] or "TEXT" for r in conn.execute(f"PRAGMA table_info({t})")} for t in names}
    finally:
        conn.close()


def resolve(col: exp.Column, scope) -> tuple[str, str] | None:
    src = scope.sources.get(col.table)
    return (src.name, col.name) if isinstance(src, exp.Table) else None


def lint(sql: str, question: str = "") -> list[Issue]:
    try:
        tree = qualify(sqlglot.parse_one(sql, read="sqlite"), schema=db_schema(), dialect="sqlite")
    except SqlglotError:
        return []  # 파싱·컬럼 해석 실패는 guard·실행 단계에서 걸림

    issues = []
    for scope in traverse_scope(tree):
        tables = {s.name for s in scope.sources.values() if isinstance(s, exp.Table)}

        # fan_out: 같은 부모의 1:N 자식 테이블 2개 이상을 한 SELECT에서 조인
        children = defaultdict(set)
        for parent, _, child, _ in ONE_TO_MANY:
            if child in tables:
                children[parent].add(child)
        for parent, kids in children.items():
            if len(kids) >= 2:
                issues.append(Issue("fan_out", f"{parent}의 1:N 자식 {sorted(kids)}를 함께 조인하면 행이 불어나요"))

        # count_dup: 1:N 자식을 조인한 상태에서 부모 키를 DISTINCT 없이 COUNT
        for count in scope.expression.find_all(exp.Count):
            arg = count.this
            if isinstance(arg, exp.Distinct) or not isinstance(arg, exp.Column):
                continue
            ref = resolve(arg, scope)
            for parent, key, child, _ in ONE_TO_MANY:
                if ref == (parent, key) and child in tables:
                    issues.append(Issue("count_dup", f"{child}를 조인한 뒤 {parent}.{key}를 DISTINCT 없이 세면 중복돼요"))

    # 지표: 질문에 키워드가 있으면 정의된 식·필터를 따라야 함
    q = question.lower()
    scopes = traverse_scope(tree)
    for name, m in METRICS.items():
        if not any(k in q for k in m["keywords"]):
            continue
        agg_cols = set()
        for scope in scopes:
            for agg in scope.expression.find_all(exp.AggFunc):
                if agg.key.upper() == m["agg"]:
                    agg_cols |= {resolve(c, scope) for c in agg.find_all(exp.Column)}
        if m["column"] not in agg_cols:
            t, c = m["column"]
            issues.append(Issue("metric_expr", f"{name}은 {m['agg']}({t}.{c})로 계산해야 해요"))

        ft, fc, fv = m["filter"]
        has_filter = any(
            resolve(eq.this, scope) == (ft, fc) and eq.expression.name == fv
            for scope in scopes
            for eq in scope.expression.find_all(exp.EQ)
            if isinstance(eq.this, exp.Column)
        )
        if not has_filter:
            issues.append(Issue("metric_filter", f"{name}은 {ft}.{fc} = '{fv}' 조건이 필요해요"))

    return issues
