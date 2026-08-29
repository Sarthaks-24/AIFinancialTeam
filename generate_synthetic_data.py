"""
Synthetic Data Generator for Reconciliation Engine
Usage:
    python generate_synthetic_data.py --batch canonical_60
    python generate_synthetic_data.py --batch stress_220
    python generate_synthetic_data.py --batch stress_280
    python generate_synthetic_data.py --batch all
"""
import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reconciliation_data")
BASE_DATE = datetime(2026, 7, 1)
CATEGORIES = [
    "Product Sale", "Service Fee", "Subscription", "Refund Reversal",
    "License Fee", "Consulting", "Maintenance", "Support Contract",
]

def _txn_id(i: int) -> str: return f"rzp_txn_{i:04d}"
def _order_id(i: int) -> str: return f"order_{i:04d}"
def _entry_id(i: int) -> str: return f"LED_{i:04d}"
def _random_date(base: datetime, spread_days: int = 60) -> datetime:
    return base + timedelta(days=random.randint(0, spread_days))
def _random_amount() -> float: return round(random.uniform(500, 75000), 2)

def generate_base_records(n: int):
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

def inject_discrepancies(records: list, num_discrepancies: int):
    indices = list(range(len(records)))
    random.shuffle(indices)
    targets = indices[:num_discrepancies]
    discrepancy_map = {}
    
    parts = 6
    chunk = num_discrepancies // parts
    
    # 1. Amount mismatches
    for idx in targets[:chunk]:
        drift = round(random.uniform(5, 500), 2) * random.choice([1, -1])
        records[idx]["ledger_amount_override"] = round(records[idx]["amount"] + drift, 2)
        discrepancy_map[records[idx]["index"]] = "amount_mismatch"
        
    # 2. Missing in ledger
    for idx in targets[chunk:2*chunk]:
        records[idx]["skip_ledger"] = True
        discrepancy_map[records[idx]["index"]] = "missing_in_ledger"
        
    # 3. Missing in settlement
    for idx in targets[2*chunk:3*chunk]:
        records[idx]["skip_settlement"] = True
        discrepancy_map[records[idx]["index"]] = "missing_in_settlement"
        
    # 4. Date mismatches
    for idx in targets[3*chunk:4*chunk]:
        records[idx]["ledger_date_override"] = records[idx]["date"] + timedelta(days=random.randint(4, 12))
        discrepancy_map[records[idx]["index"]] = "date_mismatch"

    # 5. Duplicate references (Ledger has duplicate)
    for idx in targets[4*chunk:5*chunk]:
        records[idx]["duplicate_ledger"] = True
        discrepancy_map[records[idx]["index"]] = "unresolvable"
        
    # 6. Invalid inputs (missing amount in settlement)
    for idx in targets[5*chunk:]:
        records[idx]["invalid_settlement"] = True
        discrepancy_map[records[idx]["index"]] = "unresolvable"

    # Any remaining will be amount mismatches (remainder handling)
    for idx in targets[6*chunk:]:
        drift = round(random.uniform(5, 500), 2) * random.choice([1, -1])
        records[idx]["ledger_amount_override"] = round(records[idx]["amount"] + drift, 2)
        discrepancy_map[records[idx]["index"]] = "amount_mismatch"

    return discrepancy_map

def write_settlements_csv(records: list, path: str):
    fieldnames = ["txn_id", "order_id", "amount", "fee", "tax", "net_amount", "settled_at", "merchant_ref"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            if rec.get("skip_settlement"):
                continue
            row = {
                "txn_id": rec["txn_id"],
                "order_id": rec["order_id"],
                "amount": f'{rec["amount"]:.2f}',
                "fee": f'{rec["fee"]:.2f}',
                "tax": f'{rec["tax"]:.2f}',
                "net_amount": f'{rec["net_amount"]:.2f}',
                "settled_at": rec["date"].strftime("%Y-%m-%d"),
                "merchant_ref": f'MR-{rec["order_id"].upper()}',
            }
            if rec.get("invalid_settlement"):
                row["amount"] = ""
            writer.writerow(row)

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

            row = {
                "entry_id": _entry_id(rec["index"]),
                "reference": rec["txn_id"],
                "amount": f"{amount:.2f}",
                "date": date.strftime("%Y-%m-%d"),
                "category": rec["category"],
                "notes": f"Payment received for {rec['order_id']}",
            }
            writer.writerow(row)
            if rec.get("duplicate_ledger"):
                row["entry_id"] = _entry_id(rec["index"]) + "_DUP"
                writer.writerow(row)

def build_dataset(name: str, num_records: int, num_discrepancies: int):
    output_dir = os.path.join(DATA_DIR, name)
    os.makedirs(output_dir, exist_ok=True)

    records = generate_base_records(num_records)
    discrepancy_map = inject_discrepancies(records, num_discrepancies)

    settlements_path = os.path.join(output_dir, "razorpay_settlements.csv")
    ledger_path = os.path.join(output_dir, "internal_ledger.csv")

    write_settlements_csv(records, settlements_path)
    write_ledger_csv(records, ledger_path)

    ground_truth = {
        "dataset": name,
        "total_records": num_records,
        "discrepancies": {}
    }
    for rec in records:
        idx = rec["index"]
        txn_id = rec["txn_id"]
        dtype = discrepancy_map.get(idx, "matched")
        ground_truth["discrepancies"][txn_id] = dtype
        
    gt_path = os.path.join(output_dir, "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
        
    print(f"Generated dataset '{name}': {num_records} records, {len(discrepancy_map)} discrepancies")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", default="canonical_60", help="Dataset name or 'all'")
    args = parser.parse_args()
    random.seed(42)

    configs = {
        "canonical_60": (60, 10),
        "stress_220": (220, 30),
        "stress_280": (280, 45),
    }

    if args.batch == "all":
        for name, params in configs.items():
            build_dataset(name, params[0], params[1])
    else:
        params = configs.get(args.batch, (60, 10))
        build_dataset(args.batch, params[0], params[1])

if __name__ == "__main__":
    main()
