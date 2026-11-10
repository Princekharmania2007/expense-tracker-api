# Expense Tracker API with AI Categorization

A clean, lightweight, and interview-ready RESTful API built with **Python 3.13**, **FastAPI**, **SQLite**, and **Pandas**. The API tracks daily expenses and features automated **AI categorization** using any OpenAI-compatible LLM provider.

---

## Architecture & Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (high performance, automatic OpenAPI documentation, clean dependency handling)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/) (strict typing, field constraints, auto 422 errors)
- **Database**: Python built-in `sqlite3` (no ORM; direct SQL queries with parameterization)
- **Analytics Engine**: [Pandas](https://pandas.pydata.org/) (aggregation by category and monthly time-series)
- **HTTP Client**: [HTTPX](https://www.python-httpx.org/) (synchronous client for OpenAI-compatible chat completion endpoints)
- **Configuration**: [python-dotenv](https://github.com/theskumar/python-dotenv)
- **Testing**: [pytest](https://docs.pytest.org/) with FastAPI `TestClient` (isolated temporary database and mocked external services)

---

## Project Structure

```text
expense-tracker-api/
├── app/
│   ├── __init__.py
│   ├── main.py         # FastAPI application and route endpoints
│   ├── models.py       # Pydantic schemas and Category enum
│   ├── db.py           # Raw SQLite connection and CRUD helpers
│   ├── llm.py          # AI categorization module via HTTPX
│   └── summary.py      # Pandas aggregations (totals, category, monthly)
├── tests/
│   ├── __init__.py
│   └── test_api.py     # 19 automated unit & integration tests
├── .env.example        # Environment variable template
├── .gitignore          # Ignores .venv, .env, *.db, STUDY_NOTES.md
├── requirements.txt    # Frozen dependency specifications
└── README.md           # Public documentation
```

---

## Features

1. **Full CRUD Operations**:
   - `POST /expenses`: Create an expense (amount > 0, non-empty description, optional category, date defaults to today).
   - `GET /expenses`: List all expenses with optional filtering by `?category=`.
   - `GET /expenses/{id}`: Retrieve a specific expense by ID.
   - `PUT /expenses/{id}`: Update an existing expense.
   - `DELETE /expenses/{id}`: Remove an expense (HTTP 204 No Content).
2. **Category Enum**:
   - `Food`, `Transport`, `Shopping`, `Bills`, `Entertainment`, `Health`, `Education`, `Other`.
3. **AI Categorization & Resilience**:
   - If an expense is created without a category, the system calls an OpenAI-compatible `/chat/completions` endpoint.
   - System prompt instructs the model to reply with only the category name at `temperature=0`.
   - Robust fallback: If the API key is missing, network times out (10s), HTTP error occurs, or the output is unrecognizable, the category smoothly falls back to `"Other"` without crashing or blocking expense creation.
4. **Data Analytics via Pandas**:
   - `GET /expenses/summary` loads expense records into a DataFrame to compute grand total, entry count, totals by category, and totals by month (`YYYY-MM`). Empty databases return clean zero structures.
5. **Strict Data Validation & Error Handling**:
   - Pydantic v2 enforces positive amounts (`gt=0`), non-empty descriptions, valid enum choices, and date formatting (HTTP 422).
   - Missing IDs return structured HTTP 404 errors.

---

## Setup & Installation (Windows)

### 1. Clone or Open the Repository
Open PowerShell or Command Prompt in the project root directory:
```powershell
cd "c:\Users\nikky\OneDrive\Desktop\Expense Tracker API"
```

### 2. Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
*(If PowerShell restricts script execution, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```powershell
Copy-Item .env.example .env
```
Edit `.env` if you have an API key from an OpenAI-compatible provider (e.g., Groq, Together AI, OpenRouter, or OpenAI):
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```
*Note: If no API key is provided, the API still runs perfectly and categorizes omitted entries as `"Other"`.*

### 5. Run the Server
```powershell
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Alternative ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health status | `200 OK` |
| `POST` | `/expenses` | Create an expense (AI categorizes if omitted) | `201 Created` |
| `GET` | `/expenses` | List expenses (optional `?category=` query parameter) | `200 OK` |
| `GET` | `/expenses/summary` | Analytics summary (total, category & monthly breakdown) | `200 OK` |
| `GET` | `/expenses/{id}` | Get a single expense by ID | `200 OK` / `404` |
| `PUT` | `/expenses/{id}` | Update an existing expense by ID | `200 OK` / `404` |
| `DELETE` | `/expenses/{id}` | Delete an expense by ID | `204 No Content` / `404` |

---

## Example `curl` Commands

### 1. Health Check
```powershell
curl.exe -s http://127.0.0.1:8000/health
```

### 2. Create an Expense with Category
```powershell
curl.exe -s -X POST http://127.0.0.1:8000/expenses `
  -H "Content-Type: application/json" `
  -d '{"amount": 25.50, "description": "Chipotle burrito bowl", "category": "Food"}'
```

### 3. Create an Expense without Category (Auto-categorized by AI)
```powershell
curl.exe -s -X POST http://127.0.0.1:8000/expenses `
  -H "Content-Type: application/json" `
  -d '{"amount": 14.00, "description": "Metro subway card recharge"}'
```

### 4. List All Expenses
```powershell
curl.exe -s http://127.0.0.1:8000/expenses
```

### 5. Filter Expenses by Category
```powershell
curl.exe -s "http://127.0.0.1:8000/expenses?category=Food"
```

### 6. Get Analytics Summary
```powershell
curl.exe -s http://127.0.0.1:8000/expenses/summary
```
*Example response:*
```json
{
  "total": 39.50,
  "count": 2,
  "by_category": {
    "Food": 25.50,
    "Transport": 14.00
  },
  "by_month": {
    "2026-11": 39.50
  }
}
```

### 7. Get Expense by ID
```powershell
curl.exe -s http://127.0.0.1:8000/expenses/1
```

### 8. Update an Expense
```powershell
curl.exe -s -X PUT http://127.0.0.1:8000/expenses/1 `
  -H "Content-Type: application/json" `
  -d '{"amount": 28.00, "description": "Chipotle bowl with guacamole"}'
```

### 9. Delete an Expense
```powershell
curl.exe -s -i -X DELETE http://127.0.0.1:8000/expenses/1
```

### 10. Validation Error Example (Amount <= 0)
```powershell
curl.exe -s -X POST http://127.0.0.1:8000/expenses `
  -H "Content-Type: application/json" `
  -d '{"amount": -5.00, "description": "Negative amount test"}'
```
*Returns HTTP 422 Unprocessable Entity.*

---

## Running Automated Tests

The project includes 19 automated tests using `pytest` and FastAPI's `TestClient`.

Tests enforce strict isolation:
- Every test runs against a temporary database via `tmp_path` fixture; the production `expenses.db` is never modified.
- External LLM calls are mocked; no real API tokens are consumed during tests.

Run tests:
```powershell
pytest -v
```

---

## Design Decisions

1. **Synchronous `def` Route Handlers**:
   Because `sqlite3` and `pandas` execute synchronous blocking I/O, route handlers are defined with standard `def` rather than `async def`. FastAPI automatically dispatches `def` endpoints to a separate threadpool, preventing event loop starvation.
2. **Built-in `sqlite3` instead of an ORM**:
   Avoids heavyweight ORM abstractions like SQLAlchemy or Tortoise. Keeps the codebase transparent, lightweight, and easy to explain line-by-line during interviews. All database queries use parameterized SQL (`?`) to prevent SQL injection.
3. **Route Declaration Order (`/expenses/summary` before `/expenses/{id}`)**:
   FastAPI resolves routes sequentially in registration order. If `/{id}` were declared first, requests to `/summary` would match the `{id}` parameter, attempting to parse `"summary"` as an integer and returning an HTTP 422 error.
4. **Resilient LLM Degradation**:
   External AI services can experience network lag, outages, or rate limits. The `categorize()` function wraps external HTTP calls in comprehensive exception blocks with a 10-second timeout, falling back to `Category.OTHER` rather than failing the transaction.
5. **Deterministic Categorization (`temperature=0`)**:
   Expense categorization is a classification task. Setting `temperature=0` removes sampling randomness and forces the model to choose the most statistically probable category consistently.
6. **Inheriting from `(str, Enum)`**:
   The `Category` enum inherits from both `str` and `Enum`. This enables direct JSON serialization without custom encoder functions and simplifies value comparisons.

---

## Limitations & Next Steps

- **Authentication & User Isolation**: The current implementation is single-tenant. Adding JWT authentication (OAuth2 Password Bearer) would allow multiple users to manage private expense records.
- **Async Database Driver**: For high-concurrency production deployments, migrating to PostgreSQL with an asynchronous driver (such as `asyncpg`) would allow native `async def` routes.
- **Asynchronous Task Queue**: Moving external LLM categorization calls to a background task queue (e.g., Celery or ARQ with Redis) would eliminate network latency from the user request cycle.
- **Receipt OCR**: Integrating a multimodal model or Tesseract OCR to automatically parse receipts from uploaded images.
