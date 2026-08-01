"""
Shared pytest fixtures for testing app.py's endpoints.

ASSUMPTIONS TO VERIFY AGAINST YOUR ACTUAL CODE:
- database.py exposes `Base` (SQLAlchemy declarative base) and `get_async_session`
- models.py exposes `User` with at least: id, email, hashed_password, is_active,
  is_superuser, is_verified, name
- auth.py exposes `current_active_user` (the dependency app.py uses)
If any of these names differ, adjust the imports below to match.

Install what's needed for this test suite:
    pip install pytest pytest-asyncio httpx aiosqlite --break-system-packages
"""

import os

# app.py -> auth.py -> database.py creates a real SQLAlchemy engine at IMPORT
# TIME, reading DATABASE_URL straight from the environment. In Docker, .env is
# loaded before this ever runs; under pytest, nothing has loaded it yet. We
# never actually connect with this engine (get_async_session is overridden
# below), so a dummy value is enough to prevent the import-time crash.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-used-for-real-auth")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-used-for-real-calls")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app import app
from database import get_async_session
from auth import current_active_user
from models import Base, User

# In-memory SQLite for tests — fast, isolated, no real Postgres needed.
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Fresh schema for every test function — full isolation, no cross-test bleed."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def fake_user():
    """A fixed, always-authenticated user — bypasses real JWT/login flow entirely."""
    return User(
        id=1,
        email="test@example.com",
        hashed_password="not-a-real-hash",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        name="Test User",
    )


@pytest_asyncio.fixture
async def client(db_session, fake_user):
    """
    An HTTP test client with:
      - the real DB dependency swapped for our in-memory test session
      - the real auth dependency swapped for a fixed, always-authenticated user
    This lets us test business logic without needing real JWTs, cookies, or Postgres.
    """

    async def override_get_async_session():
        yield db_session

    async def override_current_active_user():
        return fake_user

    app.dependency_overrides[get_async_session] = override_get_async_session
    app.dependency_overrides[current_active_user] = override_current_active_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sample_transactions():
    """A small, known set of transactions — used to mock parser.extract_transactions
    and trans_classifier.categorize_transactions so tests don't need a real PDF or
    a real Groq API key."""
    return [
        {"date": "2026-06-20", "description": "POS Purchase Test Store", "amount": -50.0, "balance": 950.0, "type": "debit"},
        {"date": "2026-06-21", "description": "Salary Deposit", "amount": 5000.0, "balance": 5950.0, "type": "credit"},
    ]


@pytest.fixture
def sample_transactions_categorized(sample_transactions):
    """Same as sample_transactions, but with a category attached, mimicking what
    trans_classifier.categorize_transactions would normally add."""
    return [
        {**t, "category": "Shopping" if t["type"] == "debit" else "Income"}
        for t in sample_transactions
    ]