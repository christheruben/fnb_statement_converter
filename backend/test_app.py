"""
Endpoint tests for app.py.

Run with:
    pytest test_app.py -v

These tests mock:
  - parser.extract_transactions   (no real PDF needed)
  - trans_classifier.categorize_transactions  (no real Groq API key needed)
  - statement_parser's metadata extractors (account number, balances, period)

This keeps tests fast, deterministic, and independent of external services —
the goal is to test YOUR business logic (routing, auth, DB writes, response
shape), not pdfminer or Groq's correctness (those are covered separately by
scratch_test.py against real statements).
"""

import io
from unittest.mock import patch

import pytest


# -------------------------
# Health check / root
# -------------------------

@pytest.mark.asyncio
async def test_read_root(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "message" in resp.json()


# -------------------------
# /me
# -------------------------

@pytest.mark.asyncio
async def test_get_me_returns_authenticated_user(client, fake_user):
    resp = await client.get("/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == fake_user.email
    assert body["id"] == fake_user.id


# -------------------------
# Account CRUD
# -------------------------

@pytest.mark.asyncio
async def test_create_and_list_account(client):
    create_resp = await client.post("/accounts", json={"name": "Cheque Account"})
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["name"] == "Cheque Account"
    assert "id" in created

    list_resp = await client.get("/accounts")
    assert list_resp.status_code == 200
    accounts = list_resp.json()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Cheque Account"


@pytest.mark.asyncio
async def test_delete_account(client):
    create_resp = await client.post("/accounts", json={"name": "Temp Account"})
    account_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/accounts/{account_id}")
    assert delete_resp.status_code == 200

    list_resp = await client.get("/accounts")
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_account_returns_404(client):
    resp = await client.delete("/accounts/99999")
    assert resp.status_code == 404


# -------------------------
# Upload / extraction pipeline
# -------------------------

@pytest.mark.asyncio
async def test_upload_rejects_non_pdf(client):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    files = {"file": ("statement.txt", io.BytesIO(b"not a pdf"), "text/plain")}
    resp = await client.post(f"/accounts/{account_id}/upload", files=files)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_returns_404_for_nonexistent_account(client):
    files = {"file": ("statement.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
    resp = await client.post("/accounts/99999/upload", files=files)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_returns_422_when_no_transactions_found(client):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    with patch("app.extract_markdown_from_bytes", return_value="fake markdown"), \
         patch("app.extract_statement_period", return_value=(__import__("datetime").datetime(2026, 6, 20), __import__("datetime").datetime(2026, 7, 20))), \
         patch("app.extract_account_number", return_value="12345678"), \
         patch("app.extract_statement_balances", return_value=(1000.0, 950.0)), \
         patch("app.extract_transactions", return_value=[]):

        files = {"file": ("statement.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        resp = await client.post(f"/accounts/{account_id}/upload", files=files)

    assert resp.status_code == 422
    assert "transaction data" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_success_returns_full_summary(client, sample_transactions, sample_transactions_categorized):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    with patch("app.extract_markdown_from_bytes", return_value="fake markdown"), \
         patch("app.extract_statement_period", return_value=(__import__("datetime").datetime(2026, 6, 20), __import__("datetime").datetime(2026, 7, 20))), \
         patch("app.extract_account_number", return_value="12345678"), \
         patch("app.extract_statement_balances", return_value=(1000.0, 5950.0)), \
         patch("app.extract_transactions", return_value=sample_transactions), \
         patch("app.categorize_transactions", return_value=sample_transactions_categorized):

        files = {"file": ("statement.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        resp = await client.post(f"/accounts/{account_id}/upload", files=files)

    assert resp.status_code == 200
    body = resp.json()

    # Shape check — matches what the frontend's UploadResponse type expects
    assert "statement_id" in body
    assert body["account_number"] == "12345678"
    assert body["statement_period"]["start_date"] == "2026-06-20"
    assert body["statement_period"]["end_date"] == "2026-07-20"
    assert body["opening_balance"] == 1000.0
    assert body["closing_balance"] == 5950.0
    assert "analytics" in body
    assert len(body["transactions"]) == len(sample_transactions)


@pytest.mark.asyncio
async def test_upload_returns_400_when_statement_period_missing(client):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    with patch("app.extract_markdown_from_bytes", return_value="fake markdown"), \
         patch("app.extract_statement_period", side_effect=ValueError("Statement Period not found in document.")):

        files = {"file": ("statement.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")}
        resp = await client.post(f"/accounts/{account_id}/upload", files=files)

    assert resp.status_code == 400


# -------------------------
# Statements
# -------------------------

@pytest.mark.asyncio
async def test_list_statements_for_account(client):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    resp = await client.get(f"/accounts/{account_id}/statements")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_statements_for_nonexistent_account_returns_404(client):
    resp = await client.get("/accounts/99999/statements")
    assert resp.status_code == 404


# -------------------------
# Trends
# -------------------------

@pytest.mark.asyncio
async def test_trends_with_no_transactions_returns_404(client):
    create_resp = await client.post("/accounts", json={"name": "Test Account"})
    account_id = create_resp.json()["id"]

    resp = await client.get(f"/accounts/{account_id}/trends")
    assert resp.status_code == 404
    assert "No transactions" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_trends_for_nonexistent_account_returns_404(client):
    resp = await client.get("/accounts/99999/trends")
    assert resp.status_code == 404


# -------------------------
# /categorize
# -------------------------

@pytest.mark.asyncio
async def test_categorize_endpoint(client, sample_transactions, sample_transactions_categorized):
    with patch("app.categorize_transactions", return_value=sample_transactions_categorized):
        resp = await client.post("/categorize", json={"transactions": sample_transactions})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["transactions"]) == len(sample_transactions)
    assert "category" in body["transactions"][0]


@pytest.mark.asyncio
async def test_categorize_handles_classifier_failure(client, sample_transactions):
    with patch("app.categorize_transactions", side_effect=Exception("Groq API down")):
        resp = await client.post("/categorize", json={"transactions": sample_transactions})

    assert resp.status_code == 500


# -------------------------
# /analyze
# -------------------------

@pytest.mark.asyncio
async def test_analyze_endpoint(client, sample_transactions_categorized):
    resp = await client.post("/analyze", json={"transactions": sample_transactions_categorized})
    assert resp.status_code == 200
    body = resp.json()
    assert "total_income" in body or "category_breakdown" in body