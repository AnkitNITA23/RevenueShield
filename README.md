# Revenue Recovery AI

An industry-grade AI Revenue Recovery platform designed to detect, diagnose, predict, and recover lost revenue across transaction failures, churn risks, and billing anomalies.

---

## High-Level Target Architecture

The eventual system operates on an autonomous closed loop:

```
[Detect] ──> [Diagnose] ──> [Predict] ──> [Decide] ──> [Apply Policy] ──> [Execute] ──> [Observe Outcome] ──> [Learn]
```

### Technology Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS *(Planned)*
- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic
- **Database**: PostgreSQL 16
- **Async & Infrastructure**: Redis, Celery, Docker *(Future Phase)*
- **AI & Analytics**: scikit-learn, LightGBM/XGBoost, LLM Integration *(Future Phase)*

---

## Current Project Status: Step 10 Complete

> **Step 10: WhatsApp Recovery Agent**
>
> Provider-agnostic WhatsApp communication layer (`WhatsAppProvider`, `DevelopmentWhatsAppProvider`, `TwilioWhatsAppProvider`), deterministic English and Hinglish template engine (`PAYMENT_RECOVERY_EN_V1`, `PAYMENT_RECOVERY_HI_V1`), safety policy scheduling (quiet hours 20:00–08:00 in customer timezone, 24h cooldown, max 3 attempts, Promise-to-Pay pausing), communication state machine (`Communication`), unique idempotency keys, delivery webhook callbacks, and payment success stopping rules.

---

## Project Structure

```text
revenue-recovery/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 0001_initial_core_schema.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── customer.py
│   │   │   ├── payment.py
│   │   │   ├── subscription.py
│   │   │   ├── invoice.py
│   │   │   ├── event.py
│   │   │   ├── recovery_case.py
│   │   │   ├── diagnosis.py
│   │   │   ├── recovery_action.py
│   │   │   ├── action_outcome.py
│   │   │   ├── promise_to_pay.py
│   │   │   ├── communication_log.py
│   │   │   ├── audit_log.py
│   │   │   └── model_version.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   └── seed_demo_data.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_health.py
│   │   └── test_db.py
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── README.md
├── docs/
│   ├── database.md
│   └── README.md
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

## Quickstart & Local Development

### 1. Start PostgreSQL with Docker

From the root project directory (`revenue-recovery/`):

```bash
docker compose up -d postgres
```

This starts PostgreSQL 16 on port `5432` with a persistent named volume `postgres_data`.

### 2. Configure Environment

Navigate to `backend/` and copy the environment template:

```bash
cd backend
cp .env.example .env
```

### 3. Virtual Environment & Dependencies

```bash
# Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Database Migrations

Apply all schema migrations to PostgreSQL:

```bash
alembic upgrade head
```

### 5. Seed Demo Data (Optional for Local Dev)

Populate demo customers, payments, invoices, and recovery cases:

```bash
python scripts/seed_demo_data.py
```

### 6. Start the Backend API

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Health & Verification Endpoints

- **Service Health**: `GET http://127.0.0.1:8000/health`
  ```json
  { "status": "ok" }
  ```
- **Database Connection Health**: `GET http://127.0.0.1:8000/health/db`
  ```json
  { "status": "ok", "database": "connected" }
  ```
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Running Automated Tests

Run the test suite from `backend/`:

```bash
pytest -v
```

The tests execute against an isolated in-memory test database, verifying all 12 entities, foreign key constraints, JSONB payloads, and relationship navigation without affecting your local development database.

---

## Documentation

- Detailed relational architecture & lifecycle documentation is available in [`docs/database.md`](docs/database.md).
