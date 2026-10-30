"""
Analytics and Insights Module
Calculates cash flow KPIs, category distributions, monthly breakdowns,
recurring subscription detection, budget health, and anomaly detection.
"""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Tuple
import math

DEFAULT_BUDGETS = {
    "Housing & Rent": 20000.0,
    "Groceries": 8000.0,
    "Dining & Cafes": 5000.0,
    "Utilities & Bills": 3500.0,
    "Transportation": 3000.0,
    "Entertainment & Subscriptions": 2500.0,
    "Shopping & Retail": 6000.0,
    "Healthcare & Fitness": 3000.0,
    "Bank Fees & Charges": 500.0,
    "Uncategorized": 2000.0
}


def calculate_analytics(
    transactions: List[Dict[str, Any]],
    custom_budgets: Dict[str, float] = None
) -> Dict[str, Any]:
    """Computes all analytical metrics for the provided transactions."""
    if not transactions:
        return {
            "summary": {
                "total_income": 0.0,
                "total_expense": 0.0,
                "net_cash_flow": 0.0,
                "savings_rate": 0.0,
                "transaction_count": 0,
                "date_range": {"start": None, "end": None}
            },
            "monthly_trends": [],
            "category_breakdown": [],
            "recurring_subscriptions": [],
            "top_merchants": [],
            "daily_trend": [],
            "budgets": [],
            "anomalies": []
        }

    total_income = 0.0
    total_expense = 0.0
    category_totals = defaultdict(float)
    category_counts = defaultdict(int)
    merchant_expenses = defaultdict(float)
    monthly_data = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    daily_expenses = defaultdict(float)
    dates = []

    # Category transaction amounts for anomaly calculation
    cat_amounts = defaultdict(list)

    for tx in transactions:
        amt = tx["amount"]
        cat = tx.get("category", "Uncategorized")
        merch = tx.get("merchant", tx.get("description", "Unknown"))
        d_str = tx["date"]
        dates.append(d_str)

        # Monthly key YYYY-MM
        m_key = d_str[:7]

        if amt > 0:
            total_income += amt
            monthly_data[m_key]["income"] += amt
        else:
            exp_abs = abs(amt)
            total_expense += exp_abs
            category_totals[cat] += exp_abs
            category_counts[cat] += 1
            merchant_expenses[merch] += exp_abs
            monthly_data[m_key]["expense"] += exp_abs
            daily_expenses[d_str] += exp_abs
            cat_amounts[cat].append((exp_abs, tx))

        monthly_data[m_key]["count"] += 1

    # Date range
    dates.sort()
    start_date = dates[0] if dates else None
    end_date = dates[-1] if dates else None

    # Net and Savings Rate
    net_cash_flow = total_income - total_expense
    savings_rate = (net_cash_flow / total_income * 100) if total_income > 0 else 0.0

    # Monthly Trends (sorted by month)
    monthly_trends = []
    for m in sorted(monthly_data.keys()):
        inc = round(monthly_data[m]["income"], 2)
        exp = round(monthly_data[m]["expense"], 2)
        monthly_trends.append({
            "month": m,
            "income": inc,
            "expense": exp,
            "net": round(inc - exp, 2),
            "count": monthly_data[m]["count"]
        })

    # Category Breakdown
    category_breakdown = []
    for cat, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
        pct = (total / total_expense * 100) if total_expense > 0 else 0.0
        category_breakdown.append({
            "category": cat,
            "total": round(total, 2),
            "percentage": round(pct, 1),
            "count": category_counts[cat]
        })

    # Top 10 Merchants
    top_merchants = []
    for merch, exp in sorted(merchant_expenses.items(), key=lambda x: x[1], reverse=True)[:10]:
        top_merchants.append({
            "merchant": merch,
            "total": round(exp, 2)
        })

    # Daily Trend (Cumulative or daily expense)
    daily_trend = []
    for d in sorted(daily_expenses.keys()):
        daily_trend.append({
            "date": d,
            "expense": round(daily_expenses[d], 2)
        })

    # Recurring Subscriptions Detection
    recurring_subscriptions = detect_recurring_charges(transactions)

    # Budget Health Check
    budgets_list = []
    active_budgets = {**DEFAULT_BUDGETS, **(custom_budgets or {})}
    for cat, budget_limit in active_budgets.items():
        spent = category_totals.get(cat, 0.0)
        pct = (spent / budget_limit * 100) if budget_limit > 0 else 0.0
        status = "safe"
        if pct >= 100:
            status = "exceeded"
        elif pct >= 80:
            status = "warning"
        
        budgets_list.append({
            "category": cat,
            "budget": budget_limit,
            "spent": round(spent, 2),
            "remaining": round(max(0, budget_limit - spent), 2),
            "percentage": round(pct, 1),
            "status": status
        })
    budgets_list.sort(key=lambda x: x["percentage"], reverse=True)

    # Anomalies Detection (Transactions > mean + 2*std in category)
    anomalies = []
    for cat, items in cat_amounts.items():
        if len(items) >= 4:
            amounts = [it[0] for it in items]
            mean_val = sum(amounts) / len(amounts)
            variance = sum((x - mean_val) ** 2 for x in amounts) / len(amounts)
            std_dev = math.sqrt(variance)
            threshold = mean_val + (2.0 * std_dev)

            for exp_abs, tx in items:
                if exp_abs > threshold and exp_abs > 100.0:  # Ignore trivial amounts
                    anomalies.append({
                        "id": tx["id"],
                        "date": tx["date"],
                        "description": tx["description"],
                        "merchant": tx.get("merchant", tx["description"]),
                        "amount": round(exp_abs, 2),
                        "category": cat,
                        "expected_avg": round(mean_val, 2),
                        "threshold": round(threshold, 2)
                    })

    return {
        "summary": {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_cash_flow": round(net_cash_flow, 2),
            "savings_rate": round(savings_rate, 1),
            "transaction_count": len(transactions),
            "date_range": {"start": start_date, "end": end_date}
        },
        "monthly_trends": monthly_trends,
        "category_breakdown": category_breakdown,
        "recurring_subscriptions": recurring_subscriptions,
        "top_merchants": top_merchants,
        "daily_trend": daily_trend,
        "budgets": budgets_list,
        "anomalies": anomalies[:10]  # Return top 10 anomalies
    }


def detect_recurring_charges(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Identifies recurring subscription and bill patterns by merchant and interval."""
    # Group expense transactions by cleaned merchant
    merchant_groups = defaultdict(list)
    for tx in transactions:
        if tx["amount"] < 0:
            merch = tx.get("merchant", tx["description"])
            merchant_groups[merch].append({
                "date": tx["date"],
                "amount": abs(tx["amount"]),
                "description": tx["description"],
                "category": tx.get("category", "Uncategorized")
            })

    recurring = []
    for merch, items in merchant_groups.items():
        if len(items) < 2:
            continue

        # Sort by date
        items.sort(key=lambda x: x["date"])
        amounts = [it["amount"] for it in items]
        
        # Check amount variance (subscriptions usually have consistent pricing, <= 10% diff)
        avg_amt = sum(amounts) / len(amounts)
        max_diff = max(abs(a - avg_amt) for a in amounts)

        # Check date intervals in days
        date_objs = [datetime.strptime(it["date"], "%Y-%m-%d") for it in items]
        intervals = [(date_objs[i] - date_objs[i-1]).days for i in range(1, len(date_objs))]

        # If variance is low (< $5.00 or < 5% variance) and at least 2 charges
        is_consistent_price = max_diff < 5.0 or (avg_amt > 0 and (max_diff / avg_amt) < 0.08)

        # Check if approx monthly (interval between 20 and 40 days) or known subscription keyword
        is_monthly = any(20 <= gap <= 40 for gap in intervals) or len(items) >= 3
        is_known_sub = any(k in merch.lower() for k in [
            'netflix', 'spotify', 'prime', 'hulu', 'gym', 'internet',
            'utility', 'fitness', 'disney', 'cloud', 'apple', 'patreon', 'youtube'
        ])

        if (is_consistent_price and (is_monthly or len(items) >= 2)) or is_known_sub:
            estimated_annual = avg_amt * 12.0
            recurring.append({
                "merchant": merch,
                "category": items[0]["category"],
                "average_amount": round(avg_amt, 2),
                "frequency": "Monthly" if is_monthly else f"{round(sum(intervals)/len(intervals))} days approx",
                "occurrences": len(items),
                "last_charged": items[-1]["date"],
                "estimated_annual_cost": round(estimated_annual, 2)
            })

    recurring.sort(key=lambda x: x["estimated_annual_cost"], reverse=True)
    return recurring
