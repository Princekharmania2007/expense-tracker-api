"""
Pydantic models and Category enum for Expense Tracker API.

These models define data validation rules for API requests and responses.
Pydantic v2 automatically validates types and constraints, returning
HTTP 422 Unprocessable Entity whenever inputs fail validation.
"""

from datetime import date as dt_date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    """
    Allowed expense categories.
    Inheriting from (str, Enum) makes each member serialize as a plain string in JSON,
    which simplifies comparisons and responses.
    """
    FOOD = "Food"
    TRANSPORT = "Transport"
    SHOPPING = "Shopping"
    BILLS = "Bills"
    ENTERTAINMENT = "Entertainment"
    HEALTH = "Health"
    EDUCATION = "Education"
    OTHER = "Other"


class ExpenseCreate(BaseModel):
    """
    Schema for creating a new expense (POST /expenses).
    - amount: Must be strictly positive (> 0).
    - description: Non-empty string.
    - category: Optional; if omitted, AI categorization will deduce it.
    - date: Optional; defaults to today's date if omitted.
    """
    amount: float = Field(..., gt=0, description="Expense amount, must be greater than 0")
    description: str = Field(..., min_length=1, description="Short description of the expense")
    category: Optional[Category] = Field(default=None, description="Expense category; deduced by AI if omitted")
    date: Optional[dt_date] = Field(default_factory=dt_date.today, description="Expense date (YYYY-MM-DD); defaults to today")

    @field_validator("description")
    @classmethod
    def validate_non_whitespace_description(cls, value: str) -> str:
        """Ensure description is not just whitespace."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Description cannot be empty or only whitespace")
        return stripped


class ExpenseUpdate(BaseModel):
    """
    Schema for updating an existing expense (PUT /expenses/{id}).
    All fields are optional to allow updating only what is provided.
    """
    amount: Optional[float] = Field(default=None, gt=0, description="New amount (> 0)")
    description: Optional[str] = Field(default=None, min_length=1, description="New description")
    category: Optional[Category] = Field(default=None, description="New category")
    date: Optional[dt_date] = Field(default=None, description="New date (YYYY-MM-DD)")

    @field_validator("description")
    @classmethod
    def validate_non_whitespace_description(cls, value: Optional[str]) -> Optional[str]:
        """Ensure description is not just whitespace when provided."""
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("Description cannot be empty or only whitespace")
            return stripped
        return value


class ExpenseResponse(BaseModel):
    """
    Schema for returning an expense object in API responses.
    """
    id: int
    amount: float
    description: str
    category: Category
    date: dt_date

    # from_attributes=True enables compatibility with dictionary or ORM-like objects
    model_config = ConfigDict(from_attributes=True)


class ExpenseSummaryResponse(BaseModel):
    """
    Schema for the analytics summary endpoint (GET /expenses/summary).
    Computed via Pandas.
    """
    total: float = Field(..., description="Grand total of all expenses")
    count: int = Field(..., description="Total number of expense entries")
    by_category: dict[str, float] = Field(..., description="Total spent per category")
    by_month: dict[str, float] = Field(..., description="Total spent per month (YYYY-MM)")
