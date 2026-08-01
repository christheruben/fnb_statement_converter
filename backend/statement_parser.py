import re
import json
from datetime import datetime
from chunknorris.parsers import PdfParser
from chunknorris.chunkers import MarkdownChunker
from chunknorris.pipelines import BasePipeline


"""
This module contains old parsing logic.
Now adapted for metadata extaction in the statements.
"""

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