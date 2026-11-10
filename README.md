# 💰 Expense Tracker API with AI Categorization

[![CI Pipeline](https://github.com/Princekharmania2007/expense-tracker-api/actions/workflows/ci.yml/badge.svg)](https://github.com/Princekharmania2007/expense-tracker-api/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-Built--in-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.2+-150458.svg?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Tests](https://img.shields.io/badge/Tests-19%20Passed-success.svg?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, interview-ready RESTful API built with **FastAPI**, **SQLite**, and **Pandas**. Features automated **AI-driven expense categorization** (compatible with Google Gemini, Groq, or OpenAI) with zero-downtime graceful fallback, strict data validation, and aggregated time-series financial analytics.

---

## 🏛️ System Architecture & Workflow

```mermaid
flowchart TD
    Client(["🌐 Client (cURL / Swagger / Frontend)"])

    subgraph FastAPI_Application ["⚡ FastAPI Application Layer"]
        Router["HTTP Router & Middleware<br/>(app/main.py)"]
        Validation{"Pydantic v2 Validation<br/>(app/models.py)"}
        
        subgraph AI_Engine ["🤖 AI Categorization Engine (app/llm.py)"]
            CheckCategory{"Category<br/>Provided?"}
            LLMCall["Call OpenAI-compatible LLM<br/>(Gemini / Groq / OpenAI)"]
            LenientParse["Lenient String Parser<br/>(temperature=0)"]
            Fallback["Fallback to 'Other'<br/>(Timeout / Error / Invalid)"]
        end
        
        subgraph Analytics_Engine ["📊 Analytics Engine (app/summary.py)"]
            PandasLoad["Load Records into Pandas DataFrame"]
            Agg["Group by Category & Monthly Time-Series"]
        end
        
        subgraph Database_Layer ["🗄️ Database Access (app/db.py)"]
            SQLQueries[("SQLite Storage<br/>(expenses.db)<br/>Parameterized Queries")]
        end
    end

    Client -->|HTTP Request| Router
    Router --> Validation
    Validation -->|Valid Payload| CheckCategory
    Validation -.->|Invalid (HTTP 422)| Client

    CheckCategory -->|Yes| SQLQueries
    CheckCategory -->|No| LLMCall
    LLMCall -->|200 OK| LenientParse
    LLMCall -->|Timeout / Exception| Fallback
    LenientParse --> SQLQueries
    Fallback --> SQLQueries

    Router -->|GET /expenses/summary| PandasLoad
    PandasLoad --> Agg
    Agg --> Router

    SQLQueries --> Router
    Router -->|JSON Response| Client
```

---

## ✨ Key Features

- **Full RESTful CRUD Suite**: Endpoints for creating, listing, filtering, updating, and deleting expenses with standard HTTP status codes (`200`, `201`, `204`, `404`, `422`).
- **Resilient AI Categorization**: Automatically categorizes expenses if the category is omitted. Integrates with any OpenAI-compatible provider (free Google Gemini, Groq, or OpenAI) at `temperature=0`.
- **Fault-Tolerant Fallback**: If the external AI service times out (10s), has rate limits, or is unreachable, the system gracefully assigns `"Other"` without blocking or failing the transaction.
- **In-Memory Analytics with Pandas**: Aggregates total expenditure, item counts, category-wise breakdowns, and monthly trends (`YYYY-MM`) with zero ORM overhead.
- **Strict Data Integrity**: Pydantic v2 schemas validate positive monetary values (`amount > 0`), non-empty strings, ISO dates, and valid category enums.
- **Zero Heavyweight ORM**: Direct `sqlite3` execution using parameterized SQL (`?`) ensures full protection against SQL injection while keeping the code clean and transparent.
- **Comprehensive Test Suite & CI/CD**: 19 automated tests with `pytest` using isolated temporary databases and mocked external calls, backed by automated GitHub Actions CI.

---

## 📁 Repository Structure

```text
expense-tracker-api/
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI pipeline (Python 3.11, 3.12, 3.13)
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI routing and application lifecycle
│   ├── models.py           # Pydantic v2 schemas and Category enum
│   ├── db.py               # Raw SQLite connection pool and CRUD helpers
│   ├── llm.py              # AI categorization with resilient fallback
│   └── summary.py          # Pandas analytics and aggregation engine
├── tests/
│   ├── __init__.py
│   └── test_api.py         # 19 automated unit & integration tests
├── .env.example            # Environment configuration template
├── .gitignore              # Ignores .venv, .env, *.db, STUDY_NOTES.md
├── LICENSE                 # MIT Open Source License
├── requirements.txt        # Pinned project dependencies
└── README.md               # Project documentation
```

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Princekharmania2007/expense-tracker-api.git
cd expense-tracker-api
```

### 2. Set Up Virtual Environment
```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
# python3 -m venv .venv
# source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```

Configure your LLM provider in `.env` (optional; defaults gracefully to `"Other"` without an API key):
```env
# Free Google Gemini Configuration
LLM_API_KEY=your_gemini_api_key_here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-1.5-flash
```

### 5. Launch the API Server
```bash
uvicorn app.main:app --reload --port 8000
```
- **Interactive OpenAPI Documentation (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative API Reference (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📡 API Reference

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service health status | `200 OK` |
| `POST` | `/expenses` | Create an expense (AI categorizes if category omitted) | `201 Created` |
| `GET` | `/expenses` | List all expenses (optional query filter: `?category=`) | `200 OK` |
| `GET` | `/expenses/summary` | Financial analytics summary (grand total, category & monthly breakdown) | `200 OK` |
| `GET` | `/expenses/{id}` | Retrieve a specific expense by ID | `200 OK` / `404 Not Found` |
| `PUT` | `/expenses/{id}` | Update an existing expense by ID | `200 OK` / `404 Not Found` |
| `DELETE` | `/expenses/{id}` | Remove an expense record by ID | `204 No Content` / `404 Not Found` |

---

## 🧪 Automated Testing

The project includes **19 automated unit and integration tests** guaranteeing full coverage across database transactions, validation errors, Pandas metrics, and AI fallback edge cases.

- **Isolated Storage**: Tests utilize `pytest`'s `tmp_path` fixture; the production SQLite database is never touched.
- **Zero Cost & Offline Testing**: External network calls to LLMs are completely mocked.

Run tests:
```bash
pytest -v
```

---

## 💡 Engineering & Design Highlights

1. **Synchronous `def` vs `async def` Route Handlers**:
   SQLite and Pandas perform synchronous, blocking I/O operations. In FastAPI, defining endpoints with standard `def` automatically delegates execution to an internal external threadpool, preventing event-loop starvation and ensuring maximum server responsiveness.
2. **Raw Parameterized SQLite over Heavy ORM**:
   Avoided heavy ORM abstractions (SQLAlchemy/Tortoise) to minimize startup latency and memory overhead. All database operations strictly employ parameterized queries (`?`) to prevent SQL injection risks.
3. **Route Declaration Order (`/summary` vs `/{id}`)**:
   FastAPI resolves URL routes sequentially. Declaring `/expenses/summary` ahead of `/expenses/{id}` prevents the routing engine from mistakenly treating `"summary"` as an integer path parameter (avoiding HTTP 422 errors).
4. **Deterministic Classification (`temperature=0`)**:
   Expense categorization is a classification task. A zero temperature parameter eliminates generative hallucinations and yields consistent classification results.
5. **Decoupled Architecture**:
   Database access, AI categorization, statistical analysis, and routing are decoupled across modular files (`db.py`, `llm.py`, `summary.py`, `main.py`), ensuring clean separation of concerns.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
