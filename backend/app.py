from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
import io

from parser import extract_statement_from_pdf
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware



# Define FastAPI app

app = FastAPI(
    title="FNB PDF Bank Statement Converter",
    description="Convert FNB bank statement PDFs to CSV or JSON formats.",
    version="1.0.0",
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

@app.get("/")
def read_root():
    return {"message": "PDF extractor is running. Go to /docs to upload a statement."}

# Endpoint to extract
@app.post("/extract")
# Async function to handle file upload and format query parameter
async def extract_statement(
    file: UploadFile = File(..., description="PDF bank statement"),
    #define query parameter called format
    format: str = Query("json", regex="^(json|csv)$", description="Return format: 'json' or 'csv'")
):
    #ensure file is PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF file.   ")
    # Read file bytes
    pdf_bytes = await file.read()
    # Attempt to run the parser
    try:
        df, rows = extract_statement_from_pdf(pdf_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Hanlde a 'no data' pdf
    if df.empty:
        return {"message": "No transaction data found in the provided PDF.", "rows":[]}
    
    # Return data in JSON format will give a dictionary with key 'rows' containing list of records
    if format == "json":
        data = df.to_dict(orient="records")
        return {"rows": data}
    
    # Return data in CSV format
    elif format == "csv":
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={file.filename}.csv"},
        )
