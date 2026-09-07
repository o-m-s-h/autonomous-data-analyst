import re

import duckdb
from langchain_core.tools import tool


def get_schema(file_path: str) -> str:
    """
    Get the schema of the CSV using DuckDB.
    """

    con = duckdb.connect()

    try:

        query = f"""
            DESCRIBE
            SELECT *
            FROM read_csv_auto('{file_path}')
        """

        result = con.execute(query).fetchdf()

        return result.to_string(index=False)

    finally:

        con.close()


def validate_sql(sql: str):
    """
    Allow only SELECT/WITH queries.
    """

    sql_clean = sql.strip().lower()

    if not (
        sql_clean.startswith("select")
        or sql_clean.startswith("with")
    ):
        raise ValueError(
            "Only SELECT or WITH queries are allowed."
        )

    forbidden = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "create",
        "replace",
        "truncate",
        "copy",
        "attach",
        "install",
        "load"
    ]

    for keyword in forbidden:

        pattern = rf"\b{keyword}\b"

        if re.search(pattern, sql_clean):

            raise ValueError(
                f"Forbidden SQL operation: {keyword}"
            )


def execute_sql(
    file_path: str,
    sql: str
):
    """
    Execute SQL against the uploaded CSV.
    """

    validate_sql(sql)

    con = duckdb.connect()

    try:

        con.execute(
            f"""
            CREATE OR REPLACE VIEW dataset AS
            SELECT *
            FROM read_csv_auto('{file_path}')
            """
        )

        result = con.execute(sql).fetchdf()

        return result

    finally:

        con.close()


@tool
def inspect_schema(file_path: str) -> str:
    """
    Inspect the uploaded CSV dataset.

    Returns the column names and DuckDB data types.
    Use this before writing SQL when the dataset structure
    is unknown.
    """

    return get_schema(file_path)


@tool
def run_sql(file_path: str, sql: str) -> str:
    """
    Execute a read-only DuckDB SQL query against the uploaded
    CSV dataset.

    The CSV is available as a table called `dataset`.

    Only SELECT and WITH queries are allowed.

    Returns the query result as a text table.
    """

    result = execute_sql(
        file_path,
        sql
    )

    if result.empty:
        return "Query executed successfully but returned no rows."

    return result.to_string(index=False)