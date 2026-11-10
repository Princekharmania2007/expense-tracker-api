"""
Pandas analytics helper module for Expense Tracker API.

Why Pandas?
Pandas provides high-performance data manipulation and aggregation tools.
While simple sums can be done in raw SQL, loading data into a DataFrame is
the foundational pattern in data science / AI applications, allowing easy
aggregation by category and time-series grouping by month.
"""

import sqlite3
from typing import Any, Dict, Optional
import pandas as pd

from app.db import get_db_path, init_db


def calculate_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load expenses from SQLite into a Pandas DataFrame and compute aggregations:
    - Grand total of all expenses
    - Total count of expense records
    - Grouped totals per category
    - Grouped totals per month in YYYY-MM format

    Handles empty datasets gracefully without errors.
    """
    path = get_db_path(db_path)
    init_db(path)  # Ensure table exists even if database was just created

    conn = sqlite3.connect(path)
    try:
        df = pd.read_sql_query(
            "SELECT id, amount, description, category, date FROM expenses",
            conn,
        )
    finally:
        conn.close()

    # Handle empty dataset cleanly
    if df.empty:
        return {
            "total": 0.0,
            "count": 0,
            "by_category": {},
            "by_month": {},
        }

    # Ensure amount column is numeric
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # Overall totals
    total_amount = float(df["amount"].sum())
    total_count = int(len(df))

    # Category aggregation
    by_category_series = df.groupby("category")["amount"].sum()
    by_category = {
        str(cat): round(float(val), 2)
        for cat, val in by_category_series.items()
    }

    # Monthly aggregation (YYYY-MM)
    df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m")
    df["month"] = df["month"].fillna("Unknown")

    by_month_series = df.groupby("month")["amount"].sum()
    by_month = {
        str(month): round(float(val), 2)
        for month, val in by_month_series.items()
    }

    return {
        "total": round(total_amount, 2),
        "count": total_count,
        "by_category": by_category,
        "by_month": by_month,
    }
