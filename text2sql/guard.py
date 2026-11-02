import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ALLOWED_TABLES = {
    "orders", "order_items", "order_payments", "order_reviews",
    "customers", "products", "sellers", "product_category_name_translation",
}

class UnsafeSQLError(ValueError):
    pass

def guard(sql: str, max_rows: int = 1000) -> str:
    try:
        trees = [t for t in sqlglot.parse(sql, read="sqlite") if t is not None]
    except ParseError as e:
        raise UnsafeSQLError(f"parse error: {e}") from e
    if len(trees) != 1:
        raise UnsafeSQLError(f"expected 1 statement, got {len(trees)}")
    tree = trees[0]
    if not isinstance(tree, exp.Query):
        raise UnsafeSQLError(f"only queries allowed, got {tree.key.upper()}")
    ctes = {cte.alias.lower() for cte in tree.find_all(exp.CTE)}
    tables = {t.name.lower() for t in tree.find_all(exp.Table)} - ctes
    if not tables <= ALLOWED_TABLES:
        raise UnsafeSQLError(f"unknown tables: {sorted(tables - ALLOWED_TABLES)}")
    limit = tree.args.get("limit")
    n = limit.expression if limit else None
    if not (isinstance(n, exp.Literal) and n.is_int and int(n.this) <= max_rows):
        tree = tree.limit(max_rows)
    return tree.sql(dialect="sqlite")
