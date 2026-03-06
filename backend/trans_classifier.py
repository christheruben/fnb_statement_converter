import os
import json
from groq import Groq
from dotenv import load_dotenv

"""
This module contains the core logic for categorizing transactions. It includes:
- A set of hardcoded rules for categorization based on keywords in the description
- A function to call Groq with uncategorized descriptions using tool calling
- A main function that applies rules first, then falls back to Groq for anything unmatched
"""

load_dotenv()  

# -------------------------
# RULES
# -------------------------

RULES = {
    # Bank charges & fees
    "byc debit": "Bank Charge",
    "credit int paid": "Interest",
    "credit interest": "Interest",
    "service fee": "Bank Charge",
    "monthly fee": "Bank Charge",

    # Income
    "payshap credit": "Income",
    "agtape credit": "Income",
    "salary": "Income",

    # Transport
    "irish rail": "Transport",
    "uber": "Transport",
    "bolt": "Transport",

    # Groceries
    "checkers": "Groceries",
    "woolworths": "Groceries",
    "pnp": "Groceries",
    "pick n pay": "Groceries",
    "shoprite": "Groceries",
    "spar": "Groceries",
    "pingo doce": "Groceries",

    # Fuel
    "engen": "Fuel",
    "shell": "Fuel",
    "bp ": "Fuel",
    "sasol": "Fuel",
    "caltex": "Fuel",

    # Education
    "scrimba": "Education",
    "udemy": "Education",
    "coursera": "Education",

    # Subscriptions / Software
    "paddle.net": "Subscriptions",
    "netflix": "Subscriptions",
    "spotify": "Subscriptions",
    "apple.com": "Subscriptions",
    "google": "Subscriptions",
    "microsoft": "Subscriptions",
}

CATEGORIES = [
    "Groceries", "Dining", "Transport", "Fuel", "Education",
    "Subscriptions", "Entertainment", "Income", "Bank Charge",
    "Interest", "Shopping", "Health", "Insurance", "Utilities",
    "Transfer", "Other"
]


def apply_rules(description: str) -> str | None:
    """Returns a category if a rule matches, otherwise None."""
    desc_lower = description.lower()
    for keyword, category in RULES.items():
        if keyword in desc_lower:
            return category
    return None


# -------------------------
# GROQ TOOL CALL
# -------------------------

# Tool schema - forces the model to return structured data matching this shape
CATEGORIZE_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_categories",
        "description": "Submit the category for each transaction description.",
        "parameters": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "The original transaction description."
                            },
                            "category": {
                                "type": "string",
                                "enum": CATEGORIES,
                                "description": "The category for this transaction."
                            }
                        },
                        "required": ["description", "category"]
                    }
                }
            },
            "required": ["results"]
        }
    }
}


def categorize_with_groq(descriptions: list[str]) -> dict[str, str]:
    """
    Sends a batch of uncategorized descriptions to Groq using tool calling.
    Returns a dict mapping description -> category.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a bank transaction categorizer. Categorize each transaction description by calling the submit_categories tool."
            },
            {
                "role": "user",
                "content": f"Categorize these transactions:\n{json.dumps(descriptions, indent=2)}"
            }
        ],
        tools=[CATEGORIZE_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_categories"}},
        temperature=0,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    results = json.loads(tool_call.function.arguments)["results"]

    return {item["description"]: item["category"] for item in results}


# -------------------------
# MAIN CATEGORIZATION
# -------------------------

def categorize_transactions(transactions: list[dict]) -> list[dict]:
    """
    Applies rules first, then sends unmatched descriptions to Groq.
    Returns transactions with a 'category' field added.
    """
    uncategorized = []

    # First pass: apply rules
    for txn in transactions:
        desc = txn.get("description", "")
        category = apply_rules(desc)
        if category:
            txn["category"] = category
        elif not desc.strip():
            txn["category"] = "Bank Charge"  # Empty descriptions are usually fees
        else:
            txn["category"] = None
            uncategorized.append(desc)

    # Second pass: batch send unmatched to Groq in a single tool call
    if uncategorized:
        unique_descs = list(set(uncategorized))
        groq_results = categorize_with_groq(unique_descs)

        for txn in transactions:
            if txn["category"] is None:
                desc = txn.get("description", "")
                txn["category"] = groq_results.get(desc, "Other")

    return transactions