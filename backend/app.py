import io
from typing import List

from fastapi.openapi.models import HTTPBearer
from fastapi.security import HTTPBearer as HTTPBearerScheme

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Depends, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from statement_parser import (
    extract_markdown_from_bytes,
    extract_account_number,
    extract_statement_balances,
    extract_statement_period,
)
from parser import extract_transactions
from trans_classifier import categorize_transactions
from analyzer import analyze, generate_pie_chart
from auth import fastapi_users, auth_backend, current_active_user
from schemas import UserRead, UserCreate, UserUpdate
from models import User
from database import get_async_session
from crud import (
    create_financial_account, get_financial_accounts, get_financial_account, delete_financial_account,
    create_statement, get_statements, get_statement, delete_statement,
    create_transactions, get_transactions, get_transactions_by_account,
)


app = FastAPI(
    title="FNB PDF Bank Statement Converter",
    description="Convert FNB bank statement PDFs to CSV or JSON formats.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------
# AUTH ROUTES
# -------------------------

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


# -------------------------
# REQUEST MODELS
# -------------------------

class Transaction(BaseModel):
    date: str
    description: str
    amount: float | None
    balance: float | None
    type: str

class CategorizeRequest(BaseModel):
    transactions: List[Transaction]

class AccountCreate(BaseModel):
    name: str


# -------------------------
# ROUTES
# -------------------------

@app.get("/")
def read_root():
    return {"message": "PDF extractor is running. Go to /docs to upload a statement."}


@app.get("/me")
async def get_me(user: User = Depends(current_active_user)):
    return {"id": user.id, "email": user.email, "name": user.name}


# -------------------------
# ACCOUNT ROUTES
# -------------------------

@app.post("/accounts", tags=["accounts"])
async def create_account_route(
    body: AccountCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await create_financial_account(session, user_id=user.id, name=body.name)
    return {"id": account.id, "name": account.name, "created_at": account.created_at}


@app.get("/accounts", tags=["accounts"])
async def list_accounts(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    accounts = await get_financial_accounts(session, user_id=user.id)
    return [{"id": a.id, "name": a.name, "created_at": a.created_at} for a in accounts]


@app.delete("/accounts/{account_id}", tags=["accounts"])
async def remove_account(
    account_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    deleted = await delete_financial_account(session, account_id=account_id, user_id=user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found.")
    return {"message": "Account deleted."}


# -------------------------
# STATEMENT ROUTES
# -------------------------

@app.get("/accounts/{account_id}/statements", tags=["statements"])
async def list_statements(
    account_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    account = await get_financial_account(session, account_id=account_id, user_id=user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    statements = await get_statements(session, account_id=account_id)
    return [
        {
            "id": s.id,
            "account_number": s.account_number,
            "start_date": s.start_date,
            "end_date": s.end_date,
            "opening_balance": s.opening_balance,
            "closing_balance": s.closing_balance,
            "uploaded_at": s.uploaded_at,
        }
        for s in statements
    ]


@app.get("/statements/{statement_id}/transactions", tags=["statements"])
async def list_transactions(
    statement_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    statement = await get_statement(session, statement_id=statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found.")
    # Verify the statement belongs to the user via account
    account = await get_financial_account(session, account_id=statement.account_id, user_id=user.id)
    if not account:
        raise HTTPException(status_code=403, detail="Not authorised.")
    transactions = await get_transactions(session, statement_id=statement_id)
    return [
        {
            "date": t.date,
            "description": t.description,
            "amount": t.amount,
            "balance": t.balance,
            "type": t.type,
            "category": t.category,
        }
        for t in transactions
    ]


@app.delete("/statements/{statement_id}", tags=["statements"])
async def remove_statement(
    statement_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    statement = await get_statement(session, statement_id=statement_id)
    if not statement:
        raise HTTPException(status_code=404, detail="Statement not found.")
    account = await get_financial_account(session, account_id=statement.account_id, user_id=user.id)
    if not account:
        raise HTTPException(status_code=403, detail="Not authorised.")
    await delete_statement(session, statement_id=statement_id)
    return {"message": "Statement deleted."}


# -------------------------
# EXTRACT ROUTES
# -------------------------

@app.post("/extract")
async def extract_statement(
    file: UploadFile = File(..., description="PDF bank statement"),
    format: str = Query("json", regex="^(json|csv)$", description="Return format: 'json' or 'csv'"),
    user: User = Depends(current_active_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")

    pdf_bytes = await file.read()

    try:
        markdown_text = extract_markdown_from_bytes(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {e}")

    try:
        statement_start, statement_end = extract_statement_period(markdown_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    account_number = extract_account_number(markdown_text)
    opening_balance, closing_balance = extract_statement_balances(markdown_text)
    transactions = extract_transactions(pdf_bytes, statement_start, statement_end)

    if not transactions:
        raise HTTPException(status_code=422, detail="Could not find transaction data in the provided PDF.")

    output = {
        "account_number": account_number,
        "statement_period": {
            "start_date": statement_start.strftime("%Y-%m-%d"),
            "end_date": statement_end.strftime("%Y-%m-%d"),
        },
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "transactions": transactions,
    }

    if format == "json":
        return output

    elif format == "csv":
        df = pd.DataFrame(transactions)
        meta_rows = pd.DataFrame([
            {"date": "", "description": f"Account: {account_number}", "amount": "", "balance": "", "type": ""},
            {"date": "", "description": f"Period: {statement_start.date()} to {statement_end.date()}", "amount": "", "balance": "", "type": ""},
            {"date": "", "description": f"Opening Balance: {opening_balance}", "amount": "", "balance": "", "type": ""},
            {"date": "", "description": f"Closing Balance: {closing_balance}", "amount": "", "balance": "", "type": ""},
        ])
        df = pd.concat([meta_rows, df], ignore_index=True)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={file.filename}.csv"},
        )


@app.post("/categorize")
async def categorize(
    request: CategorizeRequest,
    user: User = Depends(current_active_user),
):
    transactions = [txn.model_dump() for txn in request.transactions]
    try:
        categorized = categorize_transactions(transactions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {e}")
    return {"transactions": categorized}


@app.post("/accounts/{account_id}/upload", tags=["statements"])
async def extract_and_analyze(
    account_id: int,
    file: UploadFile = File(..., description="PDF bank statement"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Full pipeline: extract → categorize → analyze → save to database.
    Returns statement metadata + full analytics summary in one call.
    """
    account = await get_financial_account(session, account_id=account_id, user_id=user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.")

    pdf_bytes = await file.read()

    try:
        markdown_text = extract_markdown_from_bytes(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF: {e}")

    try:
        statement_start, statement_end = extract_statement_period(markdown_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    account_number = extract_account_number(markdown_text)
    opening_balance, closing_balance = extract_statement_balances(markdown_text)
    transactions = extract_transactions(markdown_text, statement_start, statement_end)

    if not transactions:
        raise HTTPException(status_code=422, detail="Could not find transaction data in the provided PDF.")

    try:
        categorized = categorize_transactions(transactions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {e}")

    # Save to database
    statement = await create_statement(
        session,
        account_id=account_id,
        account_number=account_number,
        start_date=statement_start.strftime("%Y-%m-%d"),
        end_date=statement_end.strftime("%Y-%m-%d"),
        opening_balance=opening_balance,
        closing_balance=closing_balance,
    )
    await create_transactions(session, statement_id=statement.id, transactions=categorized)

    summary = analyze(categorized)

    return {
        "statement_id": statement.id,
        "account_number": account_number,
        "statement_period": {
            "start_date": statement_start.strftime("%Y-%m-%d"),
            "end_date": statement_end.strftime("%Y-%m-%d"),
        },
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "analytics": summary,
        "transactions": categorized,
    }


@app.get("/accounts/{account_id}/trends", tags=["statements"])
async def get_trends(
    account_id: int,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Returns spending trends across all statements for an account.
    """
    account = await get_financial_account(session, account_id=account_id, user_id=user.id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    transactions = await get_transactions_by_account(session, account_id=account_id)
    if not transactions:
        raise HTTPException(status_code=404, detail="No transactions found for this account.")

    txn_dicts = [
        {
            "date": t.date,
            "description": t.description,
            "amount": t.amount,
            "balance": t.balance,
            "type": t.type,
            "category": t.category,
        }
        for t in transactions
    ]

    return analyze(txn_dicts)


@app.post("/analyze")
async def analyze_transactions(
    request: CategorizeRequest,
    user: User = Depends(current_active_user),
):
    transactions = [txn.model_dump() for txn in request.transactions]
    return analyze(transactions)


@app.post("/analyze/chart")
async def spending_chart(
    request: CategorizeRequest,
    user: User = Depends(current_active_user),
):
    transactions = [txn.model_dump() for txn in request.transactions]
    summary = analyze(transactions)
    try:
        png_bytes = generate_pie_chart(summary["category_breakdown"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(content=png_bytes, media_type="image/png")