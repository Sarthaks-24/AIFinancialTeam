"""
Synthetic Data Generator for Reconciliation Engine
===================================================
Creates two CSV files simulating:
  1. Razorpay settlement export  (razorpay_settlements.csv)
  2. Internal company ledger     (internal_ledger.csv)

Intentionally injects 8-12 discrepancies for the AI reconciliation
engine to detect: amount mismatches, missing records, date offsets.

Usage:
    python generate_synthetic_data.py
"""

import csv
import os
import random
from datetime import datetime, timedelta

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reconciliation_data")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NUM_RECORDS = 60
BASE_DATE = datetime(2026, 7, 1)
CATEGORIES = [
    "Product Sale", "Service Fee", "Subscription", "Refund Reversal",
    "License Fee", "Consulting", "Maintenance", "Support Contract",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _txn_id(i: int) -> str:
    return f"rzp_txn_{i:04d}"


def _order_id(i: int) -> str:
    return f"order_{i:04d}"


def _entry_id(i: int) -> str:
    return f"LED_{i:04d}"


def _random_date(base: datetime, spread_days: int = 60) -> datetime:
    return base + timedelta(days=random.randint(0, spread_days))


def _random_amount() -> float:
    return round(random.uniform(500, 75000), 2)


# ---------------------------------------------------------------------------
# Generate matched base records
# ---------------------------------------------------------------------------

def generate_base_records(n: int):
    """Return a list of dicts representing 'ground truth' transactions."""
    records = []
    for i in range(1, n + 1):
        date = _random_date(BASE_DATE)
        amount = _random_amount()
        fee = round(amount * random.uniform(0.018, 0.025), 2)
        tax = round(fee * 0.18, 2)
        net = round(amount - fee - tax, 2)
        records.append({
            "index": i,
            "txn_id": _txn_id(i),
            "order_id": _order_id(i),
            "amount": amount,
            "fee": fee,
            "tax": tax,
            "net_amount": net,
            "date": date,
            "category": random.choice(CATEGORIES),
        })
    return records


# ---------------------------------------------------------------------------
# Inject discrepancies
# ---------------------------------------------------------------------------

def inject_discrepancies(records: list):
    """
    Mutate a subset of records to create reconciliation exceptions.
    Returns a mapping of index -> discrepancy type for verification.
    """
    indices = list(range(len(records)))
    random.shuffle(indices)

    # Pick 10 records for discrepancies
    targets = indices[:10]
    discrepancy_map = {}

    # 3 amount mismatches
    for idx in targets[:3]:
        drift = round(random.uniform(5, 500), 2) * random.choice([1, -1])
        records[idx]["ledger_amount_override"] = round(records[idx]["amount"] + drift, 2)
        discrepancy_map[records[idx]["index"]] = "amount_mismatch"

    # 3 missing from ledger (settlement exists, ledger doesn't)
    for idx in targets[3:6]:
        records[idx]["skip_ledger"] = True
        discrepancy_map[records[idx]["index"]] = "missing_in_ledger"

    # 2 missing from settlement (ledger exists, settlement doesn't)
    for idx in targets[6:8]:
        records[idx]["skip_settlement"] = True
        discrepancy_map[records[idx]["index"]] = "missing_in_settlement"

    # 2 date mismatches (>3 day offset)
    for idx in targets[8:10]:
        records[idx]["ledger_date_override"] = records[idx]["date"] + timedelta(days=random.randint(4, 12))
        discrepancy_map[records[idx]["index"]] = "date_mismatch"

    return discrepancy_map


# ---------------------------------------------------------------------------
# Write CSVs
# ---------------------------------------------------------------------------

def write_settlements_csv(records: list, path: str):
    fieldnames = ["txn_id", "order_id", "amount", "fee", "tax", "net_amount", "settled_at", "merchant_ref"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            if rec.get("skip_settlement"):
                continue
            writer.writerow({
                "txn_id": rec["txn_id"],
                "order_id": rec["order_id"],
                "amount": f'{rec["amount"]:.2f}',
                "fee": f'{rec["fee"]:.2f}',
                "tax": f'{rec["tax"]:.2f}',
                "net_amount": f'{rec["net_amount"]:.2f}',
                "settled_at": rec["date"].strftime("%Y-%m-%d"),
                "merchant_ref": f'MR-{rec["order_id"].upper()}',
            })


def write_ledger_csv(records: list, path: str):
    fieldnames = ["entry_id", "reference", "amount", "date", "category", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            if rec.get("skip_ledger"):
                continue

            amount = rec.get("ledger_amount_override", rec["amount"])
            date = rec.get("ledger_date_override", rec["date"])

            writer.writerow({
                "entry_id": _entry_id(rec["index"]),
                "reference": rec["txn_id"],
                "amount": f"{amount:.2f}",
                "date": date.strftime("%Y-%m-%d"),
                "category": rec["category"],
                "notes": f"Payment received for {rec['order_id']}",
            })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    random.seed(42)  # Reproducible output
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    records = generate_base_records(NUM_RECORDS)
    discrepancy_map = inject_discrepancies(records)

    settlements_path = os.path.join(OUTPUT_DIR, "razorpay_settlements.csv")
    ledger_path = os.path.join(OUTPUT_DIR, "internal_ledger.csv")

    write_settlements_csv(records, settlements_path)
    write_ledger_csv(records, ledger_path)

    # Count actual rows written
    settlement_count = sum(1 for r in records if not r.get("skip_settlement"))
    ledger_count = sum(1 for r in records if not r.get("skip_ledger"))

    print("=" * 60)
    print("  Synthetic Reconciliation Data Generated")
    print("=" * 60)
    print(f"  Settlements CSV : {settlements_path}")
    print(f"    → {settlement_count} records")
    print(f"  Ledger CSV      : {ledger_path}")
    print(f"    → {ledger_count} records")
    print(f"  Discrepancies   : {len(discrepancy_map)} injected")
    for idx, dtype in sorted(discrepancy_map.items()):
        print(f"    record {idx:3d} → {dtype}")
    print("=" * 60)


if __name__ == "__main__":
    main()
