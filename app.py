"""
Personal Finance Analyzer - FastAPI Web Application
Provides API endpoints for file ingestion, arbitrary data inspection,
categorization, analytics calculation, sample datasets, and serves the frontend dashboard.
"""

import os
import json
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from analyzer.ingestion import (
    extract_raw_records_from_csv,
    extract_raw_records_from_json,
    detect_columns,
    normalize_transactions
)
from analyzer.categorizer import apply_categories
from analyzer.analytics import calculate_analytics
from analyzer.sample_data import (
    SAMPLE_CHECKING_CSV,
    SAMPLE_CREDIT_CARD_JSON,
    SAMPLE_ARBITRARY_CSV,
    write_sample_files_to_disk
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Ensure sample files exist on disk
write_sample_files_to_disk(BASE_DIR)

app = FastAPI(
    title="SpendPulse - Personal Finance Analyzer",
    description="Local-first intelligent personal finance data processor and analytics dashboard",
    version="1.0.0"
)


class AnalyzeRequest(BaseModel):
    records: List[Dict[str, Any]]
    column_mapping: Optional[Dict[str, Any]] = None
    account_name: Optional[str] = "Imported Account"
    custom_budgets: Optional[Dict[str, float]] = None


class CategoryUpdateRequest(BaseModel):
    transactions: List[Dict[str, Any]]
    transaction_id: str
    new_category: str
    custom_budgets: Optional[Dict[str, float]] = None


@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "SpendPulse Personal Finance Analyzer API is running."}


@app.post("/api/inspect")
async def inspect_file(file: UploadFile = File(...)):
    """
    Inspects any CSV or JSON file and returns detected columns,
    suggested field mappings, and sample preview rows.
    """
    content_bytes = await file.read()
    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("latin-1")

    filename = file.filename.lower()
    is_json = filename.endswith(".json")

    try:
        if is_json:
            records, columns = extract_raw_records_from_json(content_str)
        else:
            records, columns = extract_raw_records_from_csv(content_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    if not records:
        raise HTTPException(status_code=400, detail="No readable records found in the uploaded file.")

    detected_mapping = detect_columns(columns)
    preview_rows = records[:5]

    return {
        "filename": file.filename,
        "is_json": is_json,
        "total_rows": len(records),
        "columns": columns,
        "suggested_mapping": detected_mapping,
        "preview_rows": preview_rows
    }


@app.post("/api/upload")
async def upload_and_analyze(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None),
    account_name: Optional[str] = Form("Uploaded Statement")
):
    """
    Ingests any CSV or JSON dataset, normalizes columns,
    auto-categorizes transactions, and computes full analytics.
    """
    content_bytes = await file.read()
    try:
        content_str = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_str = content_bytes.decode("latin-1")

    filename = file.filename.lower()
    is_json = filename.endswith(".json")

    try:
        if is_json:
            records, columns = extract_raw_records_from_json(content_str)
        else:
            records, columns = extract_raw_records_from_csv(content_str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    if not records:
        raise HTTPException(status_code=400, detail="No valid data rows found in this file.")

    parsed_mapping = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except Exception:
            parsed_mapping = None

    # Normalize transactions
    normalized, summary = normalize_transactions(records, parsed_mapping, account_name)
    if not normalized:
        raise HTTPException(status_code=400, detail="Could not extract valid transactions. Please check column mappings.")

    # Apply categorization & merchant cleaning
    categorized = apply_categories(normalized)

    # Compute financial analytics
    analytics = calculate_analytics(categorized)

    return {
        "success": True,
        "filename": file.filename,
        "summary": summary,
        "columns": columns,
        "transactions": categorized,
        "analytics": analytics
    }


@app.get("/api/sample/{sample_type}")
def get_sample_dataset(sample_type: str):
    """
    Returns immediate analysis for pre-packaged sample datasets.
    sample_type can be: 'checking_csv', 'credit_card_json', or 'arbitrary_csv'.
    """
    if sample_type == "checking_csv":
        records, cols = extract_raw_records_from_csv(SAMPLE_CHECKING_CSV)
        mapping = None
        account = "Chase Checking"
        filename = "sample_checking_statement.csv"
    elif sample_type == "credit_card_json":
        records, cols = extract_raw_records_from_json(json.dumps(SAMPLE_CREDIT_CARD_JSON))
        mapping = {
            "date_col": "timestamp",
            "desc_col": "merchant_name",
            "amount_col": "charged_amount",
            "invert_amount": True  # Positive charges on card are expenses
        }
        account = "Sapphire Reserve Card"
        filename = "sample_credit_card_statement.json"
    elif sample_type == "arbitrary_csv":
        records, cols = extract_raw_records_from_csv(SAMPLE_ARBITRARY_CSV)
        mapping = {
            "date_col": "Txn_Date",
            "desc_col": "Payee_Vendor",
            "debit_col": "Paid_Out",
            "credit_col": "Paid_In"
        }
        account = "Freelance Consulting Account"
        filename = "sample_arbitrary_format.csv"
    else:
        raise HTTPException(status_code=404, detail="Sample dataset not found.")

    normalized, summary = normalize_transactions(records, mapping, account)
    categorized = apply_categories(normalized)
    analytics = calculate_analytics(categorized)

    return {
        "success": True,
        "filename": filename,
        "sample_type": sample_type,
        "summary": summary,
        "columns": cols,
        "transactions": categorized,
        "analytics": analytics
    }


@app.get("/api/download-sample/{file_type}")
def download_sample_file(file_type: str):
    """Allows downloading sample statement files directly from the browser."""
    samples_dir = os.path.join(BASE_DIR, "sample_datasets")
    if file_type == "csv":
        path = os.path.join(samples_dir, "sample_checking_statement.csv")
        filename = "sample_bank_statement.csv"
        media_type = "text/csv"
    elif file_type == "json":
        path = os.path.join(samples_dir, "sample_credit_card_statement.json")
        filename = "sample_credit_card_statement.json"
        media_type = "application/json"
    elif file_type == "arbitrary":
        path = os.path.join(samples_dir, "sample_arbitrary_format.csv")
        filename = "sample_freelance_statement.csv"
        media_type = "text/csv"
    else:
        raise HTTPException(status_code=404, detail="Sample not found")

    return FileResponse(
        path=path,
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.post("/api/update-transaction-category")
def update_category(req: CategoryUpdateRequest):
    """Update a transaction's category and recompute analytics."""
    updated_txs = []
    for tx in req.transactions:
        t = dict(tx)
        if t["id"] == req.transaction_id:
            t["category"] = req.new_category
        updated_txs.append(t)

    analytics = calculate_analytics(updated_txs, req.custom_budgets)
    return {
        "success": True,
        "transactions": updated_txs,
        "analytics": analytics
    }


@app.post("/api/export/csv")
def export_transactions_csv(payload: Dict[str, Any]):
    """Exports processed transactions as clean standardized CSV."""
    transactions = payload.get("transactions", [])
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions to export.")

    header = "ID,Date,Merchant,Description,Category,Amount,Type,Account\n"
    lines = [header]
    for tx in transactions:
        line = f'"{tx.get("id","")}","{tx.get("date","")}","{tx.get("merchant","")}","{tx.get("description","")}","{tx.get("category","")}","{tx.get("amount",0.0)}","{tx.get("type","")}","{tx.get("account","")}"\n'
        lines.append(line)

    csv_data = "".join(lines)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendpulse_cleaned_transactions.csv"}
    )


# Mount static assets directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting SpendPulse Financial Analyzer on http://localhost:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
