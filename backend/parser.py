"""
This module contains the core logic for parsing bank statements from PDF files. It includes functions for:
- Extracting markdown text from PDFs
- Extracting account numbers and balances
- Parsing transaction tables, including handling multi-date rows and normalizing dates
"""

import re
import io
from datetime import datetime

import pandas as pd
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer


# Date pattern: "20 Sep", "10 Oct", etc. at start of text
DATE_PATTERN = re.compile(
    r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\s+(.*)'
)


def process_amount(amount_str: str):
    """Convert a raw amount string into a signed float. 'Cr' = positive, otherwise negative."""
    if not amount_str or amount_str.strip() == '':
        return 0.0

    amt = amount_str.replace(',', '').replace(' ', '')

    if 'Cr' in amt:
        amt = amt.replace('Cr', '')
        sign = 1
    else:
        sign = -1

    try:
        return float(amt) * sign
    except ValueError:
        return 0.0


def extract_statement_from_pdf(pdf_bytes: bytes, tolerance: int = 3):
    """
    Extract bank statement transaction data from PDF bytes into a DataFrame.
    Raises ValueError if no header line found.
    """
    pdf_stream = io.BytesIO(pdf_bytes)

    lines = []

    for page_layout in extract_pages(pdf_stream):
        items = []
        for el in page_layout:
            if isinstance(el, LTTextContainer):
                items.append({
                    "text": el.get_text().strip(),
                    "y": el.y0,
                    "x": el.x0,
                })

        items.sort(key=lambda i: (-i["y"], i["x"]))
        current_line_y = None
        current_line = []

        for it in items:
            if current_line_y is None or abs(it["y"] - current_line_y) <= tolerance:
                current_line.append(it)
                current_line_y = it["y"] if current_line_y is None else current_line_y
            else:
                lines.append(sorted(current_line, key=lambda i: i["x"]))
                current_line = [it]
                current_line_y = it["y"]

        if current_line:
            lines.append(sorted(current_line, key=lambda i: i["x"]))

    header_indices = []
    for idx, line in enumerate(lines):
        line_text = " ".join(i["text"] for i in line)
        if "Date" in line_text and "Description" in line_text and "Amount" in line_text and "Balance" in line_text:
            header_indices.append(idx)

    if not header_indices:
        raise ValueError("No header line found in PDF")

    header_line = lines[header_indices[0]]
    header_items = sorted(header_line, key=lambda i: i["x"])

    columns = {}
    for item in header_items:
        col_name = item["text"].replace("\n", " ").strip()
        if col_name and col_name not in ["Accrued", "Bank", "Charges"]:
            columns[col_name] = item["x"]

    if 'Balance' in columns:
        balance_x = columns.get("Balance", 0)
        columns["Accrued Bank Charges"] = balance_x + 100

    rows = []
    for header_idx in header_indices:
        next_header = next((h for h in header_indices if h > header_idx), len(lines))

        for line in lines[header_idx + 1:next_header]:
            line_text = " ".join(i["text"] for i in line)

            if "Closing Balance" in line_text or "Turnover" in line_text or "Page" in line_text:
                break

            if not line or len(line_text.strip()) < 3:
                continue

            row = {col: "" for col in columns.keys()}

            for item in line:
                text = item["text"]

                date_match = DATE_PATTERN.match(text)
                if date_match:
                    date_str = date_match.group(1)
                    remaining_text = date_match.group(2).strip()

                    date_col = next((col for col in columns.keys() if "Date" in col), None)
                    if date_col:
                        row[date_col] = date_str

                    if remaining_text:
                        desc_col = next((col for col in columns.keys() if "Description" in col), None)
                        if desc_col and row[desc_col]:
                            row[desc_col] += " " + remaining_text
                        elif desc_col:
                            row[desc_col] = remaining_text
                else:
                    closest_col = min(columns.keys(), key=lambda col: abs(item["x"] - columns[col]))
                    if row[closest_col]:
                        row[closest_col] += " " + text
                    else:
                        row[closest_col] = text

            # Safety net: sometimes pdfminer merges a date AND the start of the
            # description into a single text fragment that fails the per-item
            # DATE_PATTERN check (e.g. due to layout quirks), leaving the whole
            # string dumped into the Date column. Re-check the assembled Date
            # column value and re-split it here if needed, so we don't silently
            # drop these transactions later when normalizing the date.
            date_col_name = next((c for c in columns if "Date" in c), None)
            desc_col_name = next((c for c in columns if "Description" in c), None)
            if date_col_name:
                date_field = row.get(date_col_name, "")
                re_match = DATE_PATTERN.match(date_field)
                if re_match and re_match.group(2).strip():
                    row[date_col_name] = re_match.group(1)
                    overflow = re_match.group(2).strip()
                    if desc_col_name:
                        existing_desc = row.get(desc_col_name, "")
                        row[desc_col_name] = (overflow + " " + existing_desc).strip() if existing_desc else overflow

            # Skip junk rows: header/footer fragments with no real date and no amount.
            # (e.g. wrapped column headers, reference-number artifacts between pages)
            amount_col_name = next((c for c in columns if "Amount" in c), None)
            has_date = bool(row.get(date_col_name, "").strip())
            has_amount = bool(row.get(amount_col_name, "").strip())
            if not has_date and not has_amount:
                continue

            rows.append(row)

    if not rows:
        return pd.DataFrame([]), []

    df = pd.DataFrame(rows)
    if 'Amount' in df.columns:
        df["Amount"] = df["Amount"].apply(process_amount)

    return df, rows


# -------------------------
# SHAPE CONVERSION — matches app.py's expected Transaction shape
# -------------------------

def _normalize_date(date_str: str, statement_start: datetime, statement_end: datetime) -> str:
    """
    Convert a 'DD Mon' string into a full 'YYYY-MM-DD' date, picking the
    correct year based on the statement period (handles year boundaries).
    """
    day_month = datetime.strptime(date_str.strip(), "%d %b")
    month = day_month.month

    if statement_start.year != statement_end.year:
        year = statement_start.year if month >= statement_start.month else statement_end.year
    else:
        year = statement_start.year

    final_date = datetime.strptime(f"{date_str.strip()} {year}", "%d %b %Y")
    return final_date.strftime("%Y-%m-%d")


def extract_transactions(pdf_bytes: bytes, statement_start: datetime, statement_end: datetime):
    """
    Extract transactions from PDF bytes, returning a list of dicts in the
    shape app.py and the frontend expect:
        {"date": "YYYY-MM-DD", "description": str, "amount": float, "balance": float|None, "type": "credit"|"debit"}
    """
    _, rows = extract_statement_from_pdf(pdf_bytes)

    date_col = None
    desc_col = None
    amount_col = None
    balance_col = None

    if rows:
        for col in rows[0].keys():
            if "Date" in col and date_col is None:
                date_col = col
            elif "Description" in col and desc_col is None:
                desc_col = col
            elif col == "Amount" and amount_col is None:
                amount_col = col
            elif col == "Balance" and balance_col is None:
                balance_col = col

    transactions = []

    for row in rows:
        raw_date = row.get(date_col, "").strip() if date_col else ""
        if not raw_date:
            continue

        try:
            normalized_date = _normalize_date(raw_date, statement_start, statement_end)
        except ValueError:
            # Skip rows whose date doesn't match the expected 'DD Mon' format
            continue

        raw_amount = row.get(amount_col, "") if amount_col else ""
        raw_balance = row.get(balance_col, "") if balance_col else ""

        amount = process_amount(raw_amount)
        balance = process_amount(raw_balance) if raw_balance else None
        # Determine type from the presence of the 'Cr' marker in the raw string,
        # not from the sign of the resulting float — a zero-value debit (no 'Cr'
        # marker) produces -0.0, and -0.0 >= 0 is True in Python, which would
        # otherwise misclassify it as a credit.
        txn_type = "credit" if "Cr" in raw_amount else "debit"

        description = row.get(desc_col, "").strip() if desc_col else ""

        transactions.append({
            "date": normalized_date,
            "description": description,
            "amount": round(amount, 2),
            "balance": round(balance, 2) if balance is not None else None,
            "type": txn_type,
        })

    return transactions