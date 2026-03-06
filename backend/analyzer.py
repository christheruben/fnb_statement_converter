"""
analyzer.py

Takes a list of categorized transactions and returns:
  - Total income
  - Total spend
  - Net savings
  - Spending breakdown by category (amounts + percentages)
  - A matplotlib pie chart saved to bytes (for API streaming or file export)
"""

import io
from typing import Any
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — safe for servers
import matplotlib.pyplot as plt


# -------------------------
# CORE ANALYTICS
# -------------------------

def compute_summary(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute income, spend, savings, and per-category spend breakdown.

    Expects each transaction to have:
        - amount: float  (negative = debit/spend, positive = credit/income)
        - category: str
    """
    total_income = 0.0
    total_spend = 0.0
    category_spend : dict[str, float] = {}

    for txn in transactions:
        amount = txn.get("amount")
        category = txn.get("category", "Uncategorized") or "Uncategorized"

        if amount is None:
            continue

        if amount > 0:
            total_income += amount
        else:
            abs_amount = abs(amount)
            total_spend += abs_amount
            category_spend[category] = category_spend.get(category, 0.0) + abs_amount

    savings = total_income - total_spend

    # Build category breakdown with percentages
    category_breakdown = []
    for cat, spent in sorted(category_spend.items(), key=lambda x: x[1], reverse=True):
        pct = (spent / total_spend * 100) if total_spend > 0 else 0.0
        category_breakdown.append({
            "category": cat,
            "amount": round(spent, 2),
            "percentage": round(pct, 1),
        })

    return {
        "total_income": round(total_income, 2),
        "total_spend": round(total_spend, 2),
        "net_savings": round(savings, 2),
        "savings_rate": round((savings / total_income * 100) if total_income > 0 else 0.0, 1),
        "category_breakdown": category_breakdown,
    }


# -------------------------
# PIE CHART GENERATION
# -------------------------

def generate_pie_chart(category_breakdown: list[dict[str, Any]]) -> bytes:
    """
    Generate a spending pie chart from category_breakdown.
    Returns raw PNG bytes.
    """
    if not category_breakdown:
        raise ValueError("No category data to chart.")

    labels = [item["category"] for item in category_breakdown]
    sizes = [item["amount"] for item in category_breakdown]

    # Collapse small slices (<2%) into "Other" to keep the chart readable
    threshold = 0.02 * sum(sizes)
    main_labels, main_sizes, other_total = [], [], 0.0
    for label, size in zip(labels, sizes):
        if size >= threshold:
            main_labels.append(label)
            main_sizes.append(size)
        else:
            other_total += size

    if other_total > 0:
        main_labels.append("Other")
        main_sizes.append(other_total)

    # Color palette
    colors = plt.cm.Set3.colors[:len(main_labels)]  # type: ignore

    fig, ax = plt.subplots(figsize=(8, 6))
    wedges, texts, autotexts = ax.pie(
        main_sizes,
        labels=main_labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.82,
        wedgeprops={"linewidth": 1.5, "edgecolor": "white"},
    )

    # Style tweaks
    for text in texts:
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight("bold")

    ax.set_title("Spending by Category", fontsize=14, fontweight="bold", pad=20)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# -------------------------
# COMBINED ENTRY POINT
# -------------------------

def analyze(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Returns the full analytics summary.
    Chart is NOT included here — call generate_pie_chart() separately
    if you need to stream it as an image endpoint.
    """
    return compute_summary(transactions)
