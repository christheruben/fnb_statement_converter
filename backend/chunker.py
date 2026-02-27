from chunknorris.parsers import PdfParser
from chunknorris.chunkers import MarkdownChunker
from chunknorris.pipelines import BasePipeline

# Instanciate components
pipeline = BasePipeline(
    parser=PdfParser( use_ocr="never"),
    chunker=MarkdownChunker()
    )

# Get some chunks !
chunks = pipeline.chunk_file(filepath="./EASY_ACCOUNT_61.pdf")

# Save chunks
pipeline.save_chunks(
    chunks,
    output_filename='chunks.md',
    )

# Print chunks:
for chunk in chunks:
    print(chunk.get_text())

"""
-------------------- 
    CHUNK PARSER 
-------------------- 
"""

import re
import json
from datetime import datetime

DATE_PATTERN = re.compile(r"^\s*(\d{2}\s+[A-Za-z]{3})")

def parse_amount(value: str):
    """
    Convert '920.00 Cr' or '81.10 Dr' into signed float.
    """
    if not value:
        return None

    value = value.strip()
    value = value.replace(",", "")

    sign = 1
    if "Dr" in value:
        sign = -1

    number = re.search(r"[\d.]+", value)
    if not number:
        return None

    return sign * float(number.group())


def normalize_date(date_str, year_hint=2026):
    """
    Convert '24 Dec' → '2026-12-24'
    Assumes statement year (pass dynamically if needed).
    """
    try:
        dt = datetime.strptime(f"{date_str} {year_hint}", "%d %b %Y")
        return dt.strftime("%Y-%m-%d")
    except:
        return None


def extract_transactions(markdown_text: str):
    lines = markdown_text.splitlines()

    transactions = []
    in_table = False

    for line in lines:

        # Detect start of transaction table
        if "|  Date  |  Description  |  Amount  |  Balance  |" in line:
            in_table = True
            continue

        if not in_table:
            continue

        # Skip separator row
        if line.strip().startswith("|:"):
            continue

        # Stop if table ends
        if not line.strip().startswith("|"):
            break

        # Split markdown row
        cols = [c.strip() for c in line.strip().strip("|").split("|")]

        if len(cols) < 4:
            continue

        date_col = cols[0]

        # Only process rows starting with a date
        if not DATE_PATTERN.match(date_col):
            continue

        description = cols[1]
        amount_raw = cols[2]
        balance_raw = cols[3]

        transaction = {
            "date": normalize_date(date_col),
            "description": description,
            "amount": parse_amount(amount_raw),
            "balance": parse_amount(balance_raw)
        }

        transactions.append(transaction)

    return transactions


if __name__ == "__main__":
    with open("statement.md", "r", encoding="utf-8") as f:
        markdown_text = f.read()

    txns = extract_transactions(markdown_text)

    print(json.dumps(txns, indent=2))