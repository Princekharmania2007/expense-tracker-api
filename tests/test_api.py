"""
Automated tests for Expense Tracker API using pytest and FastAPI TestClient.

Key Testing Principles Applied:
1. Isolation: Every test uses a temporary SQLite database (via pytest's tmp_path
   and monkeypatch), so tests never touch the production expenses.db file.
2. Mocking: The LLM API is mocked (both unit and integration levels) to guarantee
   tests never call external network services or incur costs/latencies.
3. Edge Cases: Covers CRUD happy path, Pydantic 422 validations, 404 errors,
   Pandas summary aggregations (empty and populated), and AI fallback degradation.
"""

from datetime import date
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.llm import categorize, parse_category
from app.main import app
from app.models import Category


@pytest.fixture(autouse=True)
def test_environment(tmp_path, monkeypatch):
    """
    Autouse fixture that runs before each test.
    Points DATABASE_PATH to an isolated temporary SQLite file in tmp_path,
    initializes the schema, and guarantees real expenses.db is untouched.
    """
    temp_db = tmp_path / "test_expenses.db"
    monkeypatch.setenv("DATABASE_PATH", str(temp_db))
    init_db(str(temp_db))
    yield str(temp_db)


@pytest.fixture
def client():
    """Create a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


# -----------------------------------------------------------------------------
# Health Check Tests
# -----------------------------------------------------------------------------

def test_health_check(client):
    """Ensure the health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# -----------------------------------------------------------------------------
# CRUD Happy Path Tests
# -----------------------------------------------------------------------------

def test_crud_happy_path(client):
    """
    Test full CRUD lifecycle:
    1. Create an expense (POST /expenses)
    2. Read expense by ID (GET /expenses/{id})
    3. List expenses (GET /expenses)
    4. Update expense (PUT /expenses/{id})
    5. Delete expense (DELETE /expenses/{id})
    6. Verify expense is deleted (GET /expenses/{id} -> 404)
    """
    # 1. Create
    payload = {
        "amount": 45.50,
        "description": "Weekly grocery run",
        "category": "Food",
        "date": "2026-11-01",
    }
    create_res = client.post("/expenses", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["id"] is not None
    assert created["amount"] == 45.50
    assert created["description"] == "Weekly grocery run"
    assert created["category"] == "Food"
    assert created["date"] == "2026-11-01"
    expense_id = created["id"]

    # 2. Read by ID
    get_res = client.get(f"/expenses/{expense_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == expense_id

    # 3. List
    list_res = client.get("/expenses")
    assert list_res.status_code == 200
    expenses = list_res.json()
    assert len(expenses) == 1
    assert expenses[0]["id"] == expense_id

    # 4. Update
    update_payload = {
        "amount": 55.00,
        "description": "Weekly grocery run with snacks",
    }
    put_res = client.put(f"/expenses/{expense_id}", json=update_payload)
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["amount"] == 55.00
    assert updated["description"] == "Weekly grocery run with snacks"
    assert updated["category"] == "Food"  # Unchanged

    # 5. Delete
    del_res = client.delete(f"/expenses/{expense_id}")
    assert del_res.status_code == 204

    # 6. Verify deletion
    verify_res = client.get(f"/expenses/{expense_id}")
    assert verify_res.status_code == 404


def test_list_expenses_category_filter(client):
    """Ensure GET /expenses?category= correctly filters results."""
    client.post("/expenses", json={"amount": 10.0, "description": "Bus ticket", "category": "Transport"})
    client.post("/expenses", json={"amount": 25.0, "description": "T-shirt", "category": "Shopping"})

    # Filter Transport
    res_transport = client.get("/expenses?category=Transport")
    assert res_transport.status_code == 200
    items = res_transport.json()
    assert len(items) == 1
    assert items[0]["category"] == "Transport"

    # Filter Bills (none exist)
    res_bills = client.get("/expenses?category=Bills")
    assert res_bills.status_code == 200
    assert res_bills.json() == []


def test_create_expense_default_date(client):
    """Ensure date defaults to today when omitted."""
    payload = {
        "amount": 12.00,
        "description": "Coffee",
        "category": "Food",
    }
    response = client.post("/expenses", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["date"] == date.today().isoformat()


# -----------------------------------------------------------------------------
# Pydantic 422 Validation Error Tests
# -----------------------------------------------------------------------------

def test_validation_negative_amount(client):
    """Ensure amount <= 0 triggers HTTP 422 Unprocessable Entity."""
    res_negative = client.post("/expenses", json={"amount": -5.0, "description": "Invalid"})
    assert res_negative.status_code == 422

    res_zero = client.post("/expenses", json={"amount": 0.0, "description": "Zero"})
    assert res_zero.status_code == 422


def test_validation_empty_description(client):
    """Ensure empty or whitespace-only description triggers 422."""
    res_empty = client.post("/expenses", json={"amount": 10.0, "description": ""})
    assert res_empty.status_code == 422

    res_whitespace = client.post("/expenses", json={"amount": 10.0, "description": "   "})
    assert res_whitespace.status_code == 422


def test_validation_invalid_category_enum(client):
    """Ensure invalid category triggers 422."""
    res = client.post("/expenses", json={"amount": 10.0, "description": "Valid", "category": "Crypto"})
    assert res.status_code == 422


def test_validation_update_invalid_amount(client):
    """Ensure PUT with negative amount triggers 422."""
    create_res = client.post("/expenses", json={"amount": 10.0, "description": "Valid", "category": "Food"})
    exp_id = create_res.json()["id"]

    res = client.put(f"/expenses/{exp_id}", json={"amount": -20.0})
    assert res.status_code == 422


# -----------------------------------------------------------------------------
# HTTP 404 Not Found Tests
# -----------------------------------------------------------------------------

def test_404_get_nonexistent(client):
    """Ensure GET on missing ID returns 404 with clear message."""
    res = client.get("/expenses/99999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Expense with ID 99999 not found"


def test_404_update_nonexistent(client):
    """Ensure PUT on missing ID returns 404 with clear message."""
    res = client.put("/expenses/99999", json={"amount": 20.0})
    assert res.status_code == 404
    assert res.json()["detail"] == "Expense with ID 99999 not found"


def test_404_delete_nonexistent(client):
    """Ensure DELETE on missing ID returns 404 with clear message."""
    res = client.delete("/expenses/99999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Expense with ID 99999 not found"


# -----------------------------------------------------------------------------
# Summary (Pandas) Tests
# -----------------------------------------------------------------------------

def test_summary_empty_database(client):
    """Ensure GET /expenses/summary returns zeroes and empty dictionaries on empty DB."""
    res = client.get("/expenses/summary")
    assert res.status_code == 200
    assert res.json() == {
        "total": 0.0,
        "count": 0,
        "by_category": {},
        "by_month": {},
    }


def test_summary_with_data(client):
    """Ensure summary computes correct totals, category groupings, and monthly aggregations."""
    client.post("/expenses", json={"amount": 50.0, "description": "Groceries", "category": "Food", "date": "2026-01-15"})
    client.post("/expenses", json={"amount": 30.0, "description": "Dinner", "category": "Food", "date": "2026-01-20"})
    client.post("/expenses", json={"amount": 20.0, "description": "Metro", "category": "Transport", "date": "2026-02-05"})

    res = client.get("/expenses/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 100.0
    assert data["count"] == 3
    assert data["by_category"]["Food"] == 80.0
    assert data["by_category"]["Transport"] == 20.0
    assert data["by_month"]["2026-01"] == 80.0
    assert data["by_month"]["2026-02"] == 20.0


# -----------------------------------------------------------------------------
# AI Categorization & Fallback Tests
# -----------------------------------------------------------------------------

def test_ai_categorization_in_post_expense(client):
    """
    Ensure omitting category in POST /expenses triggers AI categorization.
    Mocks app.main.categorize so external API is not called.
    """
    with patch("app.main.categorize", return_value=Category.TRANSPORT) as mock_cat:
        response = client.post("/expenses", json={"amount": 18.0, "description": "Uber ride home"})
        assert response.status_code == 201
        data = response.json()
        assert data["category"] == "Transport"
        mock_cat.assert_called_once_with("Uber ride home")


def test_llm_categorize_mocked_success(monkeypatch):
    """
    Test llm.categorize() happy path by mocking httpx.Client.post.
    """
    monkeypatch.setenv("LLM_API_KEY", "test-mock-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Health"}}]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = categorize("Pharmacy prescription")
        assert result == Category.HEALTH


def test_llm_fallback_on_network_timeout(monkeypatch):
    """
    Ensure llm.categorize() falls back to Category.OTHER on httpx.TimeoutException without crashing.
    """
    monkeypatch.setenv("LLM_API_KEY", "test-mock-key")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        result = categorize("Expensive gadget")
        assert result == Category.OTHER


def test_llm_fallback_on_missing_api_key(monkeypatch):
    """
    Ensure llm.categorize() gracefully defaults to Category.OTHER when LLM_API_KEY is not set.
    """
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = categorize("Dinner at restaurant")
    assert result == Category.OTHER


def test_llm_fallback_on_invalid_category_output(monkeypatch):
    """
    Ensure llm.categorize() defaults to Category.OTHER when LLM returns an unrecognized word.
    """
    monkeypatch.setenv("LLM_API_KEY", "test-mock-key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "SpaceshipRocket"}}]
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = categorize("Alien artifact")
        assert result == Category.OTHER


def test_parse_category_lenient():
    """Test lenient parsing logic in parse_category helper."""
    assert parse_category("Food") == Category.FOOD
    assert parse_category(" food\n") == Category.FOOD
    assert parse_category("'Shopping'") == Category.SHOPPING
    assert parse_category("Category: Entertainment.") == Category.ENTERTAINMENT
    assert parse_category("Unknown nonsense") is None
    assert parse_category("") is None

