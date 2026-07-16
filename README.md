# FNB Statement Converter

A full-stack tool for extracting, categorizing, and tracking transactions from FNB (First National Bank) PDF statements across multiple accounts and months.

## Stack
React 18 (Vite) · FastAPI · PostgreSQL · SQLAlchemy (async) · Docker · JWT-based auth (fastapi-users)

## What it does
- Parses FNB PDF statements into structured transaction data
- Categorizes transactions using a hybrid regex + LLM (Groq) pipeline
- Stores accounts, statements, and transactions in Postgres, supporting multiple accounts and multiple statements per account
- Provides spending analytics and category breakdowns per account
- Fully Dockerized: `docker compose up --build` runs Postgres, backend, and frontend together

## Current limitations
- Parsing is built specifically for FNB's "Easy Account" statement layout. Other FNB account types (e.g. Gold, Cheque, Premier) use different table formats and are not currently supported.
- Auth is currently email/password via JWT (Google OAuth2 in progress)

## Setup

1. Copy `.env.example` to `.env` and fill in the required values (`JWT_SECRET`, `GROQ_API_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`)
2. Run the full stack:
```bash
   docker compose up --build
```
3. Apply database migrations:
```bash
   docker compose exec backend alembic upgrade head
```
4. Open the app:
   - Frontend: http://localhost:5173
   - Backend API docs: http://localhost:5000/docs

## Project structure

**Backend** (`backend/`)
- `app.py` — API endpoints
- `models.py` — SQLAlchemy models (users, accounts, statements, transactions)
- `auth.py` — Authentication setup (fastapi-users, JWT)
- `statement_parser.py` — FNB Easy Account PDF parsing logic
- `trans_classifier.py` — Regex + LLM transaction categorization
- `alembic/` — Database migrations

**Frontend** (`frontend/src/`)
- `pages/` — Route-level pages (login, register, accounts, statements)
- `components/` — Reusable UI components
- `api.ts` — Backend API client

## License
MIT