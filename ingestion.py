"""
Data Ingestion & Normalization Module
Supports arbitrary CSV and JSON financial datasets with automatic column detection,
fuzzy mapping, data sanitization, and deduplication.
"""

import csv
import json
import io
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import dateutil.parser

# Common aliases for column auto-detection
DATE_ALIASES = [
    'date', 'transaction_date', 'trans_date', 'posting_date', 'post_date',
    'txn_date', 'timestamp', 'time', 'effective_date', 'trans date', 'post date',
    'value date', 'value_date', 'value dt', 'val dt', 'txn date', 'txndate'
]

DESC_ALIASES = [
    'description', 'desc', 'merchant', 'payee', 'details', 'memo',
    'narration', 'name', 'vendor', 'transaction_details', 'title', 'particulars',
    'remarks', 'transaction narration'
]

AMOUNT_ALIASES = [
    'amount', 'amt', 'transaction_amount', 'net_amount', 'total', 'sum', 'cost', 'charge'
]

DEBIT_ALIASES = [
    'debit', 'withdrawal', 'withdraw', 'withdrawal amt', 'withdrawal amount',
    'paid_out', 'expense', 'dr', 'money_out', 'debit amt', 'debit amount'
]

CREDIT_ALIASES = [
    'credit', 'deposit', 'deposit amt', 'deposit amount', 'paid_in',
    'income', 'cr', 'money_in', 'credit amt', 'credit amount'
]

CATEGORY_ALIASES = [
    'category', 'cat', 'tag', 'transaction_type', 'type', 'group'
]


def clean_number(val: Any) -> Optional[float]:
    """Parse messy currency strings, accounting brackets, negative signs."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    
    s = str(val).strip()
    if not s or s.lower() in ('nan', 'none', 'null', '-'):
        return None

    # Check for trailing DR/CR
    is_dr = bool(re.search(r'\bDR\b', s, re.IGNORECASE))
    is_cr = bool(re.search(r'\bCR\b', s, re.IGNORECASE))

    # Accounting parentheses e.g. ($50.00) or (50.00)
    is_paren_negative = False
    if s.startswith('(') and s.endswith(')'):
        is_paren_negative = True
        s = s[1:-1].strip()

    # Strip symbols
    s = re.sub(r'[^\d\.\-\+]', '', s)
    if not s:
        return None

    try:
        num = float(s)
        if is_paren_negative:
            num = -abs(num)
        elif is_dr and num > 0:
            num = -num
        elif is_cr and num < 0:
            num = abs(num)
        return num
    except ValueError:
        return None


def parse_date_safely(date_val: Any) -> Optional[str]:
    """Parse varied date formats and return standard YYYY-MM-DD."""
    if not date_val:
        return None
    s = str(date_val).strip()
    if not s or len(s) < 5:
        return None
    
    # Avoid parsing floating point monetary numbers as dates
    if re.match(r'^-?[\$€£₹]?\s*\d+[\.,]\d{1,4}$', s):
        return None

    # Check if unix epoch timestamp in seconds or ms (between 2010 and 2035)
    if s.isdigit():
        try:
            ts = int(s)
            if ts > 1e11:  # milliseconds
                ts = ts / 1000.0
            if 1.2e9 < ts < 2.1e9:
                return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        except Exception:
            pass
        return None

    # Must contain date separators or month letters
    if not re.search(r'[-/,\.]|[a-zA-Z]{3,}', s):
        return None

    try:
        dt = dateutil.parser.parse(s, fuzzy=False, dayfirst=True)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass

    try:
        dt = dateutil.parser.parse(s, fuzzy=True, dayfirst=True)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        # Fallback to direct regex match for YYYY-MM-DD or DD/MM/YYYY
        m = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
        if m:
            return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        m2 = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
        if m2:
            return f"{m2.group(1)}-{int(m2.group(2)):02d}-{int(m2.group(3)):02d}"
        return None


def tokenize_column_name(col: str) -> List[str]:
    """Tokenize column name by underscore, hyphen, space, and camelCase."""
    # Split camelCase e.g. StoreVendor -> Store Vendor
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', col)
    # Replace non-alphanumeric with space
    s = re.sub(r'[^a-zA-Z0-9]', ' ', s).lower()
    return [t for t in s.split() if t]


def detect_columns(columns: List[str]) -> Dict[str, Optional[str]]:
    """Heuristically detect which column matches standard roles using exact, token, and substring matching."""
    detected = {
        "date_col": None,
        "desc_col": None,
        "amount_col": None,
        "debit_col": None,
        "credit_col": None,
        "category_col": None
    }

    col_tokens = {c: (c.strip().lower(), tokenize_column_name(c)) for c in columns}

    def find_match(aliases: List[str], exclude: List[Optional[str]] = None) -> Optional[str]:
        exclude_set = {x for x in (exclude or []) if x}
        # 1. Exact match
        for alias in aliases:
            for orig, (c_lower, tokens) in col_tokens.items():
                if orig in exclude_set:
                    continue
                if alias == c_lower or alias in tokens:
                    return orig
        # 2. Substring match
        for alias in aliases:
            if len(alias) < 3:
                continue
            for orig, (c_lower, tokens) in col_tokens.items():
                if orig in exclude_set:
                    continue
                if alias in c_lower:
                    return orig
        return None

    # Date
    detected["date_col"] = find_match(DATE_ALIASES)

    # Debit / Credit first (to avoid misclassifying debit/credit as general amount)
    detected["debit_col"] = find_match(DEBIT_ALIASES, [detected["date_col"]])
    detected["credit_col"] = find_match(CREDIT_ALIASES, [detected["date_col"], detected["debit_col"]])

    # Amount (only if debit/credit not both found, or find direct amount)
    if not (detected["debit_col"] and detected["credit_col"]):
        detected["amount_col"] = find_match(AMOUNT_ALIASES, [detected["date_col"], detected["debit_col"], detected["credit_col"]])
    else:
        detected["amount_col"] = None

    # Description / Payee
    detected["desc_col"] = find_match(
        DESC_ALIASES, 
        [detected["date_col"], detected["amount_col"], detected["debit_col"], detected["credit_col"]]
    )

    # Category
    detected["category_col"] = find_match(
        CATEGORY_ALIASES,
        [detected["date_col"], detected["desc_col"], detected["amount_col"], detected["debit_col"], detected["credit_col"]]
    )

    return detected


def extract_raw_records_from_json(json_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extract list of dicts from varying JSON structures."""
    data = json.loads(json_content)
    records = []

    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        # Look for candidate list keys
        candidate_keys = ['transactions', 'data', 'items', 'records', 'statement', 'results', 'rows']
        for k in candidate_keys:
            if k in data and isinstance(data[k], list) and len(data[k]) > 0 and isinstance(data[k][0], dict):
                records = data[k]
                break
        if not records:
            # Check any value that is a list of dicts
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    records = v
                    break

    columns = list({k for r in records for k in r.keys()}) if records else []
    return records, columns


def extract_raw_records_from_csv(csv_content: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Parse CSV text with smart header discovery to skip bank preamble/metadata lines."""
    if not csv_content:
        return [], []

    # Strip UTF-8 BOM
    if csv_content.startswith('\ufeff'):
        csv_content = csv_content[1:]

    lines = csv_content.splitlines()
    if not lines:
        return [], []

    # Candidate financial header tokens
    header_tokens = {
        'date', 'txn', 'transaction', 'narration', 'description', 'particulars',
        'details', 'amount', 'debit', 'withdrawal', 'credit', 'deposit', 'balance',
        'dr', 'cr', 'chq', 'ref', 'value', 'type', 'category'
    }

    best_line_idx = 0
    best_score = -1
    best_delimiter = ','

    # Check first 30 lines for the real table header row
    for idx, line in enumerate(lines[:30]):
        line_clean = line.strip()
        if not line_clean:
            continue
        for d in [',', '\t', ';', '|']:
            parts = [p.strip().strip('"').lower() for p in line_clean.split(d)]
            if len(parts) >= 2:
                score = sum(1 for p in parts if any(tok in p for tok in header_tokens))
                if score > best_score:
                    best_score = score
                    best_line_idx = idx
                    best_delimiter = d

    # If no header tokens matched, try standard csv sniffer fallback
    if best_score < 1:
        sample = csv_content[:4096]
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            best_delimiter = dialect.delimiter
        except Exception:
            if '\t' in sample:
                best_delimiter = '\t'
            elif ';' in sample:
                best_delimiter = ';'

    content_to_parse = '\n'.join(lines[best_line_idx:])
    reader = csv.DictReader(io.StringIO(content_to_parse), delimiter=best_delimiter)
    headers = [h.strip() for h in (reader.fieldnames or []) if h]

    records = []
    for row in reader:
        cleaned_row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
        # Ignore empty rows or total summary lines
        if any(cleaned_row.values()):
            records.append(cleaned_row)

    return records, headers


def normalize_transactions(
    records: List[Dict[str, Any]],
    mapping: Optional[Dict[str, Any]] = None,
    default_account: str = "Primary Account"
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Normalizes records into canonical transaction objects.
    Returns: (normalized_transactions, metadata_summary)
    """
    if not records:
        return [], {"total_raw": 0, "valid": 0, "skipped": 0, "duplicates": 0}

    # If mapping is not provided or incomplete, detect automatically
    available_cols = list(records[0].keys()) if records else []
    detected = detect_columns(available_cols)

    mapping = mapping or {}
    date_col = mapping.get('date_col') or detected.get('date_col')
    desc_col = mapping.get('desc_col') or detected.get('desc_col')
    amount_col = mapping.get('amount_col') or detected.get('amount_col')
    debit_col = mapping.get('debit_col') or detected.get('debit_col')
    credit_col = mapping.get('credit_col') or detected.get('credit_col')
    category_col = mapping.get('category_col') or detected.get('category_col')
    invert_amount = mapping.get('invert_amount', False)

    # Dynamic value-based fallback if headers could not be matched by name
    if not date_col:
        for c in available_cols:
            sample_vals = [r.get(c) for r in records[:5] if r.get(c)]
            if sample_vals and any(parse_date_safely(v) for v in sample_vals):
                date_col = c
                break

    if not amount_col and not (debit_col or credit_col):
        for c in available_cols:
            if c in (date_col, desc_col, category_col):
                continue
            sample_vals = [r.get(c) for r in records[:5] if r.get(c) is not None and str(r.get(c)).strip()]
            if sample_vals and any(clean_number(v) is not None for v in sample_vals):
                amount_col = c
                break

    if not desc_col:
        for c in available_cols:
            if c not in (date_col, amount_col, debit_col, credit_col, category_col):
                desc_col = c
                break

    normalized: List[Dict[str, Any]] = []
    seen_hashes = set()
    skipped_count = 0
    duplicate_count = 0

    for idx, row in enumerate(records):
        # 1. Date
        raw_date = row.get(date_col) if date_col else None
        parsed_date = parse_date_safely(raw_date)
        if not parsed_date:
            skipped_count += 1
            continue

        # 2. Description
        desc = str(row.get(desc_col, '')).strip() if desc_col else ''
        if not desc:
            desc = "Unspecified Transaction"

        # 3. Amount computation
        amt: Optional[float] = None
        if debit_col or credit_col:
            # Check separate debit/credit columns first
            debit_val = clean_number(row.get(debit_col)) if debit_col else None
            credit_val = clean_number(row.get(credit_col)) if credit_col else None

            if debit_val is not None and debit_val > 0:
                amt = -abs(debit_val)
            elif credit_val is not None and credit_val > 0:
                amt = abs(credit_val)
            elif debit_val is not None and debit_val != 0:
                amt = debit_val
            elif credit_val is not None and credit_val != 0:
                amt = credit_val

        if amt is None and amount_col and row.get(amount_col) not in (None, ''):
            val = clean_number(row.get(amount_col))
            if val is not None:
                amt = -val if invert_amount else val

        if amt is None:
            skipped_count += 1
            continue

        # 4. Category if pre-supplied
        cat = str(row.get(category_col, '')).strip() if category_col else ''

        # 5. Deduplication Hash
        sig = f"{parsed_date}_{amt:.2f}_{desc}_{default_account}"
        tx_hash = hashlib.sha256(sig.encode('utf-8')).hexdigest()[:16]

        if tx_hash in seen_hashes:
            duplicate_count += 1
            continue

        seen_hashes.add(tx_hash)

        normalized.append({
            "id": f"tx_{idx+1}_{tx_hash}",
            "date": parsed_date,
            "description": desc,
            "amount": round(amt, 2),
            "type": "income" if amt > 0 else "expense",
            "category": cat if cat else None,
            "account": default_account
        })

    # Sort chronologically
    normalized.sort(key=lambda x: x["date"], reverse=True)

    summary = {
        "total_raw": len(records),
        "valid": len(normalized),
        "skipped": skipped_count,
        "duplicates": duplicate_count,
        "detected_mapping": {
            "date_col": date_col,
            "desc_col": desc_col,
            "amount_col": amount_col,
            "debit_col": debit_col,
            "credit_col": credit_col,
            "category_col": category_col
        }
    }

    return normalized, summary
