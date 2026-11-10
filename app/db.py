"""
Database helper functions using Python's built-in sqlite3 library.

Why no ORM?
Using raw sqlite3 keeps the application lightweight, free of complex abstractions,
and easy to explain in technical interviews. Parameterized queries ('?') are used
throughout to protect against SQL injection vulnerabilities.
"""

from contextlib import contextmanager
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional


def get_db_path(custom_path: Optional[str] = None) -> str:
    """
    Get the SQLite database file path.
    Allows overriding via function argument or DATABASE_PATH environment variable
    so test suites can use isolated temporary test databases.
    """
    if custom_path:
        return custom_path
    return os.getenv("DATABASE_PATH", "expenses.db")


@contextmanager
def get_db_connection(db_path: Optional[str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager that yields an open SQLite connection and guarantees
    it is closed upon exiting.
    """
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # Enables column-name dictionary access
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """
    Create the 'expenses' table if it does not already exist.
    Called automatically on application startup.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL
            );
        """)
        conn.commit()


def insert_expense(
    amount: float,
    description: str,
    category: str,
    date_str: str,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Insert a new expense record into the SQLite database.
    Returns the newly created expense as a dictionary.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO expenses (amount, description, category, date)
            VALUES (?, ?, ?, ?)
            """,
            (amount, description, category, date_str),
        )
        conn.commit()
        expense_id = cursor.lastrowid
        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE id = ?",
            (expense_id,),
        )
        row = cursor.fetchone()
        return dict(row)


def get_all_expenses(
    category: Optional[str] = None,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all expenses, optionally filtered by category.
    Ordered by newest ID first.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        if category:
            cursor.execute(
                """
                SELECT id, amount, description, category, date
                FROM expenses
                WHERE category = ?
                ORDER BY id DESC
                """,
                (category,),
            )
        else:
            cursor.execute(
                """
                SELECT id, amount, description, category, date
                FROM expenses
                ORDER BY id DESC
                """
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_expense_by_id(
    expense_id: int,
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single expense by its primary key ID.
    Returns None if no matching expense is found.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE id = ?",
            (expense_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def update_expense(
    expense_id: int,
    update_data: Dict[str, Any],
    db_path: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update provided fields of an existing expense by ID.
    Returns the updated expense dict, or None if the record does not exist.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()

        # First check if the record exists
        cursor.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
        if not cursor.fetchone():
            return None

        # Build dynamic UPDATE query only for fields that were supplied
        fields = []
        values = []
        for col in ["amount", "description", "category", "date"]:
            if col in update_data and update_data[col] is not None:
                fields.append(f"{col} = ?")
                values.append(update_data[col])

        if fields:
            values.append(expense_id)
            query = f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, tuple(values))
            conn.commit()

        cursor.execute(
            "SELECT id, amount, description, category, date FROM expenses WHERE id = ?",
            (expense_id,),
        )
        row = cursor.fetchone()
        return dict(row)


def delete_expense(
    expense_id: int,
    db_path: Optional[str] = None,
) -> bool:
    """
    Delete an expense by ID.
    Returns True if a record was deleted, False if no matching record was found.
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
        return cursor.rowcount > 0
