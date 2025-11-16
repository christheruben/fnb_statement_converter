import sys
import csv
import re
import pandas as pd
from pdfminer.high_level import extract_text, extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine, LTChar, LAParams
import io


# Date pattern: "20 Sep", "10 Oct", etc. at start of text
date_pattern = re.compile(r'^(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\s+(.*)')




#Process amounts
def process_amount(amount_str):
    if not amount_str or amount_str.strip() == '':
        return 0.0

    # Remove commas and spaces
    amt = amount_str.replace(',', '').replace(' ', '')

    # Check for credit
    if 'Cr' in amt:
        amt = amt.replace('Cr', '')
        sign = 1
    else:
        sign = -1

    try:
        return float(amt) * sign
    except ValueError:
        return 0.0


# Extract text and return a DataFrame
def extract_statement_from_pdf(pdf_bytes: bytes, tolerance: int =3):
    """Extract bank statement data from PDF bytes into a DataFrame.
        Raises ValueError if no header line found.
    """
    pdf_stream = io.BytesIO(pdf_bytes)

    lines = []


    for page_layout in extract_pages(pdf_stream):
        # collect all text pieces
        items = []
        for el in page_layout:
            if isinstance(el, LTTextContainer):
                items.append({
                    "text": el.get_text().strip(),
                    "y": el.y0,
                    "x": el.x0,
                })
        
        # group by y
        items.sort(key=lambda i: (-i["y"], i["x"]))  # top to bottom, left to right
        current_line_y = None
        current_line = []

        for it in items:
            if current_line_y is None or abs(it["y"] - current_line_y) <= tolerance:
                current_line.append(it)
                current_line_y = it["y"] if current_line_y is None else current_line_y
            else:
                # commit previous line
                lines.append(sorted(current_line, key=lambda i: i["x"]))
                # start new line
                current_line = [it]
                current_line_y = it["y"]

        if current_line:
            lines.append(sorted(current_line, key=lambda i: i["x"]))

    # Find all header lines
    header_indices = []
    for idx, line in enumerate(lines):
        line_text = " ".join(i["text"] for i in line)
        if "Date" in line_text and "Description" in line_text and "Amount" in line_text and "Balance" in line_text:
            header_indices.append(idx)
            

    if not header_indices:
            # Raise Value Error
            raise ValueError("No header line found in PDF")
    
    header_line = lines[header_indices[0]]
    
    # Sort header items by x position to get correct column order
    header_items = sorted(header_line, key=lambda i: i["x"])
        
    # Create columns dict - merge multi-line text into single column name
    columns = {}
    for item in header_items:
        col_name = item["text"].replace("\n", " ").strip()
        if col_name and col_name not in ["Accrued", "Bank", "Charges"]:  # Skip the split parts
            columns[col_name] = item["x"]
    
    # Manually add Accrued Bank Charges column with x position after Balance
    if 'Balance' in columns:
        balance_x = columns.get("Balance", 0)
        columns["Accrued Bank Charges"] = balance_x + 100  # Arbitrary x position to the right
     
    # Process rows - collect from all sections between headers
    rows = []
    for header_idx in header_indices:
        # Find where this section ends (next header or end of lines)
        next_header = next((h for h in header_indices if h > header_idx), len(lines))
        
        # Process lines between this header and the next
        for line in lines[header_idx + 1:next_header]:
            line_text = " ".join(i["text"] for i in line)
            
            # Skip lines that are clearly not transactions
            if "Closing Balance" in line_text or "Turnover" in line_text or "Page" in line_text:
                break
            
            # Skip empty or header-like lines
            if not line or len(line_text.strip()) < 3:
                continue
                
            row = {col: "" for col in columns.keys()}
            
            for item in line:
                text = item["text"]
                
                # Check if this text starts with a date
                date_match = date_pattern.match(text)
                if date_match:
                    date_str = date_match.group(1)
                    remaining_text = date_match.group(2).strip()
                    
                    # Put date in Date column
                    date_col = next((col for col in columns.keys() if "Date" in col), None)
                    if date_col:
                        row[date_col] = date_str
                    
                    # Put remaining text in Description column (it's usually next to date)
                    if remaining_text:
                        desc_col = next((col for col in columns.keys() if "Description" in col), None)
                        if desc_col and row[desc_col]:
                            row[desc_col] += " " + remaining_text
                        elif desc_col:
                            row[desc_col] = remaining_text
                else:
                    # No date found, process normally by x position
                    closest_col = min(columns.keys(), key=lambda col: abs(item["x"] - columns[col]))
                    if row[closest_col]:
                        row[closest_col] += " " + text
                    else:
                        row[closest_col] = text
            
            # Only add rows that have at least a date or amount
            if row.get(next((c for c in columns if "Date" in c), "")) or any(row.values()):
                rows.append(row)
                print(row)
    
    # Convert to DataFrame and process amounts
    if not rows:
        # no transactions
        return pd.DataFrame([]), []
    
    df = pd.DataFrame(rows)
        
        # Process Amount column: Cr = positive, no Cr = negative
    if 'Amount' in df.columns:
        df["Amount"] = df["Amount"].apply(process_amount)

    return df, rows 
