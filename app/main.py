"""
FastAPI Application and Route Handlers for Expense Tracker API.

Design Note:
Route functions use synchronous 'def' instead of 'async def'.
Because sqlite3 and Pandas perform synchronous, blocking I/O operations,
declaring route handlers as 'def' instructs FastAPI to automatically execute them
in an external threadpool. This prevents blocking the asyncio event loop.
"""

from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, status

from app.db import (
    delete_expense as db_delete_expense,
    get_all_expenses as db_get_all_expenses,
    get_expense_by_id as db_get_expense_by_id,
    init_db,
    insert_expense as db_insert_expense,
    update_expense as db_update_expense,
)
from app.models import (
    Category,
    ExpenseCreate,
    ExpenseResponse,
    ExpenseSummaryResponse,
    ExpenseUpdate,
)
from app.llm import categorize
from app.summary import calculate_summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Code before 'yield' runs on application startup.
    Code after 'yield' runs on application shutdown.
    """
    init_db()  # Ensure SQLite database table exists on launch
    yield


app = FastAPI(
    title="Expense Tracker API",
    description="A lightweight FastAPI expense tracking service with SQLite and AI categorization.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
def health_check():
    """Simple health check endpoint returning API operational status."""
    return {"status": "ok"}


@app.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Expenses"],
)
def create_expense(expense: ExpenseCreate):
    """
    Create a new expense entry.
    If category is omitted, uses AI categorization via app.llm.categorize().
    """
    # Use user-supplied category, or let AI categorize based on description
    if expense.category:
        category_value = expense.category.value
    else:
        category_value = categorize(expense.description).value

    date_str = expense.date.isoformat() if expense.date else None

    created = db_insert_expense(
        amount=expense.amount,
        description=expense.description,
        category=category_value,
        date_str=date_str,
    )
    return created


@app.get(
    "/expenses",
    response_model=List[ExpenseResponse],
    tags=["Expenses"],
)
def list_expenses(category: Optional[Category] = Query(default=None, description="Filter by category")):
    """
    Retrieve all expenses, with optional filtering by Category.
    """
    category_filter = category.value if category else None
    return db_get_all_expenses(category=category_filter)


# IMPORTANT: /expenses/summary must be defined BEFORE /expenses/{id}
# Otherwise, FastAPI route matching would match 'summary' as an integer {id} and return 422.
@app.get(
    "/expenses/summary",
    response_model=ExpenseSummaryResponse,
    tags=["Analytics"],
)
def get_expenses_summary():
    """
    Get aggregated summary statistics for all expenses.
    Computed via Pandas in app.summary.calculate_summary().
    """
    return calculate_summary()


@app.get(
    "/expenses/{id}",
    response_model=ExpenseResponse,
    tags=["Expenses"],
)
def get_expense(id: int):
    """
    Fetch a single expense by its ID.
    Returns 404 if not found.
    """
    expense = db_get_expense_by_id(id)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {id} not found",
        )
    return expense


@app.put(
    "/expenses/{id}",
    response_model=ExpenseResponse,
    tags=["Expenses"],
)
def update_expense(id: int, expense_data: ExpenseUpdate):
    """
    Update an existing expense by ID.
    Returns 404 if the expense does not exist.
    """
    update_dict = {}
    if expense_data.amount is not None:
        update_dict["amount"] = expense_data.amount
    if expense_data.description is not None:
        update_dict["description"] = expense_data.description
    if expense_data.category is not None:
        update_dict["category"] = expense_data.category.value
    if expense_data.date is not None:
        update_dict["date"] = expense_data.date.isoformat()

    updated = db_update_expense(id, update_dict)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {id} not found",
        )
    return updated


@app.delete(
    "/expenses/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Expenses"],
)
def delete_expense(id: int):
    """
    Delete an expense by ID.
    Returns 204 No Content on success, 404 if not found.
    """
    deleted = db_delete_expense(id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense with ID {id} not found",
        )
    return None
