"""Shared data preparation for the predefined V4 Python operations."""
import json
import math

import numpy as np
import pandas as pd

from app.tools.sql_tool import execute_sql, validate_sql

MAX_PYTHON_ROWS = 50000
MAX_PYTHON_COLUMNS = 20


def load_frame(file_path: str, sql: str) -> pd.DataFrame:
    """Fetch one extra row to reject oversized inputs instead of silently sampling."""
    validate_sql(sql)
    query = sql.strip().removesuffix(";")
    frame = execute_sql(
        file_path,
        f"SELECT * FROM (\n{query}\n) AS analysis_input LIMIT {MAX_PYTHON_ROWS + 1}",
    )
    if len(frame) > MAX_PYTHON_ROWS:
        raise ValueError(
            f"Python input exceeds {MAX_PYTHON_ROWS} rows. Select a meaningful subset "
            "and disclose its scope; do not add an arbitrary LIMIT for statistical tests."
        )
    if len(frame.columns) > MAX_PYTHON_COLUMNS:
        raise ValueError("Select only the needed columns (maximum 20).")
    if frame.empty:
        raise ValueError("The query returned no rows; analysis cannot be computed.")
    return frame


def prepare_frame(frame, columns, numeric=()):
    """Complete-case filtering, with invalid numbers counted as excluded rows."""
    columns = list(dict.fromkeys(columns))
    if not columns or any(not column or column not in frame for column in columns):
        raise ValueError("Every selected column must exist in the SQL result.")
    clean = frame.loc[:, columns].copy()
    for column in numeric:
        clean[column] = pd.to_numeric(clean[column], errors="coerce")
        clean[column] = clean[column].replace([np.inf, -np.inf], np.nan)
    clean = clean.dropna()
    if clean.empty:
        raise ValueError("No usable rows remain after removing missing or invalid values.")
    return clean, len(frame) - len(clean)


def json_result(value):
    """Strict JSON: undefined numerical outputs are null, never NaN/Infinity."""
    def normalize(item):
        if isinstance(item, dict):
            return {str(key): normalize(val) for key, val in item.items()}
        if isinstance(item, (list, tuple, np.ndarray)):
            return [normalize(val) for val in item]
        if isinstance(item, np.generic):
            return normalize(item.item())
        if isinstance(item, float) and not math.isfinite(item):
            return None
        return item
    return json.dumps(normalize(value), ensure_ascii=False, allow_nan=False)
