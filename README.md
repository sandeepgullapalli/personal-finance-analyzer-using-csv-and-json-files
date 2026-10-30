# SpendPulse — Personal Finance & Statement Analyzer 📊

A local-first, privacy-focused financial analytics web application designed to ingest **any** CSV or JSON financial statement, automatically normalize schemas, clean merchant names, auto-categorize transactions, and compute comprehensive cash flow analytics.

---

## ✨ Features

- **Universal Statement Ingestion:**
  - Ingests **any** bank statement, credit card export, PayPal/Stripe dump, or custom accounting export.
  - Supports CSV (any delimiter: comma, semicolon, tab) and JSON (arrays or nested objects).
  - Smart heuristic auto-detection for `Date`, `Amount`, `Debit`, `Credit`, and `Description`.
  - Built-in **Column Mapper Modal** to customize or override column mappings for non-standard formats.
- **Categorization & Merchant Cleaning:**
  - Auto-normalizes messy merchant descriptors (e.g. `AMZN Mktp US*1234` $\rightarrow$ `Amazon`).
  - Hierarchical regex rules for 11 core financial categories (Housing, Groceries, Dining, Utilities, Subscriptions, Fuel, Healthcare, Shopping, etc.).
  - Real-time inline category reassignment in the transactions ledger.
- **Deep Financial Analytics & Insights:**
  - **KPI Metrics:** Total Income, Total Expenses, Net Cash Flow, Savings Rate.
  - **Cash Flow Trend:** Month-over-month income vs. expense comparison.
  - **Category Doughnut:** Proportional allocation of expenditures.
  - **Recurring Subscriptions Detector:** Automatically identifies repeated monthly charges (Netflix, Spotify, Internet, Gym, Rent) and projects annual costs.
  - **Category Budget Health Tracker:** Visual progress bars tracking pacing against category budget caps (Safe / Pacing High / Exceeded).
- **100% Local & Private:**
  - Zero cloud syncing; statements remain strictly on your machine.
- **Standardized Export:**
  - Export cleansed, categorized, and deduplicated data as a standard CSV with a single click.

---

## 🚀 Quick Start (Local Run)

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Run Directly
```bash
cd personal-finance-analyzer
python -m pip install -r requirements.txt
python app.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🧪 Testing with Sample Datasets
The application comes pre-packaged with 3 realistic sample datasets you can trigger instantly with one click in the top navigation bar:

1. **Bank CSV:** Standard checking statement with salary deposits, rent, groceries, and utilities.
2. **Card JSON:** Credit card statement format with timestamp, merchant, and positive expense amounts.
3. **Custom Semicolon CSV:** Non-standard freelance accounting statement with separate `Paid_Out` and `Paid_In` columns and semicolon delimiters.

---

## 🛠️ Deploying to the Cloud

### Option 1: Docker / Docker Compose (Any Server or VPS)
Build and run using Docker Compose:
```bash
docker compose up -d --build
```
The app will be live at `http://localhost:8000`.

To run with plain Docker:
```bash
docker build -t spendpulse .
docker run -p 8000:8000 spendpulse
```

---

### Option 2: 1-Click Free Deployment on Render (render.com)
1. Push this repository to your GitHub/GitLab account.
2. Log into [Render.com](https://render.com) and click **New + > Web Service**.
3. Connect your repository.
4. Render will automatically detect `render.yaml` or use these settings:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Click **Create Web Service**. Your website is live with a free SSL URL!

---

### Option 3: Deploy on Railway (railway.app)
1. Install the Railway CLI or connect via GitHub:
   ```bash
   railway login
   railway init
   railway up
   ```
2. The included `Procfile` will automatically configure and run the Uvicorn web server.

---

### Option 4: Deploy on Fly.io
1. Install `flyctl` and run:
   ```bash
   fly launch
   fly deploy
   ```
2. The included `fly.toml` is configured to run on shared CPU with auto-sleep when inactive.

---

## 📂 Project Architecture

```
personal-finance-analyzer/
├── app.py                      # FastAPI server & REST API
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Compose service configuration
├── render.yaml                 # 1-click Render blueprint
├── Procfile                    # Railway / Heroku process definition
├── fly.toml                    # Fly.io deployment config
├── analyzer/
│   ├── ingestion.py            # CSV/JSON parsers, auto-detection, deduplication
│   ├── categorizer.py          # Rule engine & merchant name cleaner
│   ├── analytics.py            # KPI, cash flow, recurring sub detector, budget tracker
│   └── sample_data.py          # Sample datasets generator
└── static/
    ├── index.html              # Modern responsive Tailwind dashboard
    ├── app.js                  # Frontend logic & Chart.js visualizations
    └── style.css               # Accents and scrollbar styling
```
