import re

class UnsafeSQLError(ValueError):
    pass

def guard(sql: str, default_limit: int = 1000) -> str:
    sql = sql.strip().rstrip(";").strip()
    if ";" in sql:
        raise UnsafeSQLError("multiple statements")
    if not re.match(r"(?i)^\s*(SELECT|WITH)\b", sql):
        raise UnsafeSQLError("only SELECT statements are allowed")
    if not re.search(r"(?i)\blimit\s+\d+(\s*(,|offset)\s*\d+)?\s*$", sql):
        sql = f"{sql}\nLIMIT {default_limit}"
    return sql