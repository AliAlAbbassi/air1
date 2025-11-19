import os
import re
from typing import Dict


def with_params(sql: str, *params) -> tuple[str, tuple]:
    """Convert :param style to $1, $2 format for Prisma and return params tuple"""
    param_pattern = r":(\w+)"
    matches = re.findall(param_pattern, sql)

    converted_sql = sql
    for i, param_name in enumerate(matches, 1):
        converted_sql = converted_sql.replace(f":{param_name}", f"${i}")

    return converted_sql, params


def load_sql_queries(file_path: str) -> Dict[str, str]:
    """Load SQL queries from a file, parsing -- name: comments"""
    queries = {}

    if not os.path.exists(file_path):
        return queries

    with open(file_path, "r") as f:
        content = f.read()

    # Split by -- name: comments
    parts = re.split(r"-- name: (\w+)", content)

    # parts[0] is empty, then alternates between name and query
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            query_name = parts[i].strip()
            query_sql = parts[i + 1].strip()

            # Remove the ^ marker if present
            if query_name.endswith("^"):
                query_name = query_name[:-1]

            # Clean up the SQL - remove extra whitespace but preserve structure
            query_sql = re.sub(r"\n\s*\n", "\n", query_sql)  # Remove empty lines
            query_sql = query_sql.strip()

            queries[query_name] = query_sql

    return queries


# Load queries on module import
query_dir = os.path.join(os.path.dirname(__file__), "query")
linkedin_queries = load_sql_queries(os.path.join(query_dir, "linkedin.sql"))
linkedin_company_queries = load_sql_queries(os.path.join(query_dir, "linkedin_company_members.sql"))
