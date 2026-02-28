import re
import json
from datetime import datetime
from chunknorris.parsers import PdfParser
from chunknorris.chunkers import MarkdownChunker
from chunknorris.pipelines import BasePipeline


# -------------------------
# CONFIG
# -------------------------

PDF_PATH = "./EASY_ACCOUNT_61.pdf"
# OUTPUT_JSON = "transactions.json"  # Option 2: Uncomment to enable file output


# -------------------------
# PIPELINE SETUP
# -------------------------

def extract_markdown_from_pdf(pdf_path: str) -> str:
    """Used when running statement_parser.py standalone for testing."""
    pipeline = BasePipeline(
        parser=PdfParser(use_ocr="never"),
        chunker=MarkdownChunker()
    )
    chunks = pipeline.chunk_file(filepath=pdf_path)

    # 🔥 COMMENTED OUT FOR NOW (debug only)
    # pipeline.save_chunks(chunks, output_filename="chunks.md")

    return "\n".join(chunk.get_text() for chunk in chunks)


def extract_markdown_from_bytes(pdf_bytes: bytes) -> str:
    """Used by the API - accepts raw bytes, no temp file needed."""
    pipeline = BasePipeline(
        parser=PdfParser(use_ocr="never"),
        chunker=MarkdownChunker()
    )
    chunks = pipeline.chunk_string(pdf_bytes)
    return "\n".join(chunk.get_text() for chunk in chunks)


# -------------------------
# METADATA EXTRACTION
# -------------------------

ACCOUNT_PATTERN = re.compile(
    r"Easy\s+Account\s*:\s*(\d+)",
    re.IGNORECASE
)

BALANCE_PATTERN = re.compile(
    r"Opening\s+Balance\s+([\d,]+\.\d+)\s*(Cr|Dr).*?"
    r"Closing\s+Balance\s+([\d,]+\.\d+)\s*(Cr|Dr)",
    re.IGNORECASE
)

def extract_account_number(markdown_text: str):
    match = ACCOUNT_PATTERN.search(markdown_text)
    if not match:
        return None
    return match.group(1)


def extract_statement_balances(markdown_text: str):
    match = BALANCE_PATTERN.search(markdown_text)
    if not match:
        return None, None

    opening_raw, opening_type, closing_raw, closing_type = match.groups()

    def convert(value, balance_type):
        value = float(value.replace(",", ""))
        if balance_type.lower() == "dr":
            return -value
        return value

    opening_balance = convert(opening_raw, opening_type)
    closing_balance = convert(closing_raw, closing_type)

    return opening_balance, closing_balance


# -------------------------
# STATEMENT PERIOD EXTRACTION
# -------------------------

STATEMENT_PERIOD_PATTERN = re.compile(
    r"Statement\s+Period\s*:\s*"
    r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})"
    r"\s+to\s+"
    r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.IGNORECASE
)

def extract_statement_period(markdown_text: str):
    match = STATEMENT_PERIOD_PATTERN.search(markdown_text)

    if not match:
        raise ValueError("Statement Period not found in document.")

    start_str, end_str = match.groups()

    start_date = datetime.strptime(start_str, "%d %B %Y")
    end_date = datetime.strptime(end_str, "%d %B %Y")

    return start_date, end_date


# -------------------------
# TRANSACTION PARSER
# -------------------------

DATE_PATTERN = re.compile(r"(\d{2}\s+[A-Za-z]{3})")


def parse_amount(value: str):
    """
    Convert amount string into (signed_float, type)
    """
    if not value:
        return None, None

    value_clean = value.strip().replace(",", "")

    if "Cr" in value_clean:
        txn_type = "credit"
    else:
        txn_type = "debit"

    number = re.search(r"[\d.]+", value_clean)
    if not number:
        return None, txn_type

    amount = float(number.group())

    if txn_type == "debit":
        amount *= -1

    return amount, txn_type


def normalize_date(date_str, statement_start, statement_end):
    """
    Determine correct year dynamically using statement period.
    If month >= start month and statement crosses year boundary,
    assign appropriate year.
    """
    day_month = datetime.strptime(date_str, "%d %b")
    month = day_month.month

    if statement_start.year != statement_end.year:
        if month >= statement_start.month:
            year = statement_start.year
        else:
            year = statement_end.year
    else:
        year = statement_start.year

    final_date = datetime.strptime(f"{date_str} {year}", "%d %b %Y")
    return final_date.strftime("%Y-%m-%d")


def split_multi_date_rows(date_col, description):
    """
    Split rows containing multiple dates in the date column.
    """
    dates = DATE_PATTERN.findall(date_col)

    if len(dates) <= 1:
        return [(dates[0] if dates else None, description)]

    parts = DATE_PATTERN.split(date_col)
    rows = []

    for i in range(1, len(parts), 2):
        date_part = parts[i]
        text_part = parts[i + 1] if i + 1 < len(parts) else ""
        combined_desc = (text_part + " " + description).strip()
        rows.append((date_part, combined_desc))

    return rows


def extract_transactions(markdown_text: str, statement_start, statement_end):
    lines = markdown_text.splitlines()

    transactions = []
    in_table = False

    for line in lines:

        if "|  Date  |  Description  |  Amount  |  Balance  |" in line:
            in_table = True
            continue

        if not in_table:
            continue

        if line.strip().startswith("|:"):
            continue

        if not line.strip().startswith("|"):
            break

        cols = [c.strip() for c in line.strip().strip("|").split("|")]

        if len(cols) < 4:
            continue

        date_col = cols[0]
        description = cols[1]
        amount_raw = cols[2]
        balance_raw = cols[3]

        split_rows = split_multi_date_rows(date_col, description)

        for date_str, desc in split_rows:
            if not date_str:
                continue

            normalized_date = normalize_date(date_str, statement_start, statement_end)
            amount, txn_type = parse_amount(amount_raw)
            balance, _ = parse_amount(balance_raw)

            transactions.append({
                "date": normalized_date,
                "description": desc.strip(),
                "amount": amount,
                "balance": balance,
                "type": txn_type
            })

    return transactions


# -------------------------
# MAIN
# -------------------------

def main():
    print("Extracting markdown from PDF...")
    markdown_text = extract_markdown_from_pdf(PDF_PATH)

    print("Extracting statement period...")
    statement_start, statement_end = extract_statement_period(markdown_text)

    print("Extracting account details...")
    account_number = extract_account_number(markdown_text)
    opening_balance, closing_balance = extract_statement_balances(markdown_text)

    print("Parsing transactions...")
    transactions = extract_transactions(markdown_text, statement_start, statement_end)
    print(f"Found {len(transactions)} transactions.")

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

    # Option 2: Uncomment to save output to a JSON file for auditing/logging
    # with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    #     json.dump(output, f, indent=2)
    # print(f"Statement data saved to {OUTPUT_JSON}")

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()