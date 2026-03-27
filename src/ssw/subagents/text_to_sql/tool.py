from __future__ import annotations

import re

from langchain_core.tools import tool


FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b("
    r"insert|update|delete|drop|alter|create|truncate|replace|merge|call|"
    r"grant|revoke|commit|rollback|lock|unlock|load|outfile|dumpfile"
    r")\b",
    re.IGNORECASE,
)


@tool
def validate_select_sql(sql: str) -> dict[str, object]:
    """校验 SQL 是否为单条只读 MySQL 查询。返回 valid 和 issues。"""

    normalized = sql.strip()
    issues: list[str] = []

    if not normalized:
        issues.append("SQL 为空。")

    sql_without_tail_semicolon = normalized[:-1].strip() if normalized.endswith(";") else normalized
    if ";" in sql_without_tail_semicolon:
        issues.append("只允许单条 SQL，不能包含多个语句。")

    lowered = sql_without_tail_semicolon.lower()
    if not (lowered.startswith("select ") or lowered.startswith("with ")):
        issues.append("只允许 SELECT 或 WITH 开头的查询 SQL。")

    if "--" in normalized or "/*" in normalized or "*/" in normalized:
        issues.append("不允许包含 SQL 注释。")

    forbidden = sorted({match.group(1).upper() for match in FORBIDDEN_SQL_KEYWORDS.finditer(normalized)})
    if forbidden:
        issues.append(f"包含非只读关键字：{', '.join(forbidden)}。")

    return {
        "valid": not issues,
        "issues": issues,
        "sql": normalized,
    }
