#!/usr/bin/env python3
"""
FNB PDF → Excel Converter using Camelot

Usage:
    python fnb_pdf_to_excel.py FNB_Statement.pdf -o FNB_Statement.xlsx
    python fnb_pdf_to_excel.py FNB_Statement.pdf --pages 1-3
    python fnb_pdf_to_excel.py FNB_Statement.pdf --password XXXX

Requirements (pip):
    camelot-py[cv]
    opencv-python
    ghostscript
    pandas
    openpyxl

Notes:
    - Works best on digital (not scanned) PDFs.
    - FNB format often has ONE 'Amount' column with 'Cr' to indicate credit.
      This script handles that: '1,234.00 Cr' → +1234.00, '125.00' → -125.00
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import camelot


import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Helpers for PDF reading
# ─────────────────────────────────────────────────────────────────────────────

tables = camelot.read_pdf('./EASY_ACCOUNT_58.pdf', pages='1,2', process_background=True)


df = tables[0].df.copy()

# Drop any empty rows and clean newlines
df = df.replace(r'\n', ' ', regex=True)
df = df.dropna(how='all')
df.columns = ["Date", "Description", "Amount", "Balance", "AccruedBankCharges"]


def parse_fnb_amt(val):
    # Convert 1 000Cr -> Credit = 1000, Debit = 0

    txt = str(val)
    is_credit = txt.lower().endswith("cr")
    txt = txt.replace('Cr', '').replace('cr','')
    txt = txt.replace(',','')

    try:
        num = float(txt)
    except ValueError:
        return pd.Series({"Credit":pd.NA, "Debit":pd.NA})
    
    if is_credit:
        return pd.Series({"Credit":num, "Debit": 0.0})
    else:
        return pd.Series({"Credit":0.0, "Debit": num})
    
#apply updates to database
df[["Credit", "Debit"]] = df["Amount"].apply(parse_fnb_amt)
# Find where 'Amount' sits
pos = df.columns.get_loc("Amount")

# Extract and drop Amount
df = df.drop(columns=["Amount"])

# Insert the two new columns at that same position
df.insert(pos, "Credit", df.pop("Credit"))
df.insert(pos + 1, "Debit", df.pop("Debit"))

df.to_excel('output.xlsx')