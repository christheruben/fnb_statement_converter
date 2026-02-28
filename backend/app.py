import io
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd

from statement_parser import (
    extract_markdown_from_bytes,
    extract_account_number,
    extract_statement_balances,
    extract_statement_period,
    extract_transactions,
)
from trans_classifier import categorize_transactions

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


# -------------------------
# ROUTES
# -------------------------

@app.get("/")
def read_root():
    return {"message": "PDF extractor is running. Go to /docs to upload a statement."}


@app.post("/extract")
async def extract_statement(
    file: UploadFile = File(..., description="PDF bank statement"),
    format: str = Query("json", regex="^(json|csv)$", description="Return format: 'json' or 'csv'"),
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
    transactions = extract_transactions(markdown_text, statement_start, statement_end)

    if not transactions:
        return {"message": "No transaction data found in the provided PDF.", "rows": []}

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
async def categorize(request: CategorizeRequest):
    """
    Accepts a list of transactions and returns them with a 'category' field added.
    Uses rules first, then falls back to Groq for anything unmatched.
    """
    transactions = [txn.model_dump() for txn in request.transactions]

    try:
        categorized = categorize_transactions(transactions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Categorization failed: {e}")

    return {"transactions": categorized}