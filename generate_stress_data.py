"""Generate larger, noisier reconciliation datasets for evaluation."""

import argparse
import csv
import json
import os
import random
from datetime import datetime, timedelta

BASE_DATE = datetime(2026, 1, 1)
CATEGORIES = [
    "Product Sale", "Service Fee", "Subscription", "Refund Reversal",
    "License Fee", "Consulting", "Maintenance", "Support Contract",
]


def _txn_id(index):
    return f"stress_txn_{index:05d}"


def generate_dataset(record_count, discrepancy_density, seed, output_dir):
    random.seed(seed)
    records = []
    for index in range(1, record_count + 1):
        date = BASE_DATE + timedelta(days=random.randint(0, 364))
        amount = round(random.uniform(500, 75000), 2)
        records.append({
            "index": index,
            "txn_id": _txn_id(index),
            "order_id": f"stress_order_{index:05d}",
            "amount": amount,
            "date": date,
            "category": random.choice(CATEGORIES),
        })

    discrepancy_count = max(1, round(record_count * discrepancy_density))
    targets = random.sample(records, discrepancy_count)
    discrepancy_map = {}
    for offset, record in enumerate(targets):
        mode = offset % 5
        if mode == 0:
            record["ledger_amount"] = round(record["amount"] + random.choice([-1, 1]) * random.uniform(25, 900), 2)
            discrepancy_map[record["txn_id"]] = "amount_mismatch"
        elif mode == 1:
            record["skip_ledger"] = True
            discrepancy_map[record["txn_id"]] = "missing_in_ledger"
        elif mode == 2:
            record["skip_settlement"] = True
            discrepancy_map[record["txn_id"]] = "missing_in_settlement"
        elif mode == 3:
            record["ledger_date"] = record["date"] + timedelta(days=random.randint(4, 30))
            discrepancy_map[record["txn_id"]] = "date_mismatch"
        else:
            # Deliberately ambiguous: the manifest calls this a date issue,
            # while the amount and date both differ in the source files.
            record["ledger_amount"] = round(record["amount"] + random.choice([-1, 1]) * random.uniform(25, 900), 2)
            record["ledger_date"] = record["date"] + timedelta(days=random.randint(4, 30))
            discrepancy_map[record["txn_id"]] = "date_mismatch"

    os.makedirs(output_dir, exist_ok=True)
    settlements_path = os.path.join(output_dir, "razorpay_settlements.csv")
    ledger_path = os.path.join(output_dir, "internal_ledger.csv")
    with open(settlements_path, "w", newline="", encoding="utf-8") as settlements_file:
        writer = csv.DictWriter(settlements_file, fieldnames=["txn_id", "order_id", "amount", "fee", "tax", "net_amount", "settled_at", "merchant_ref"])
        writer.writeheader()
        for record in records:
            if record.get("skip_settlement"):
                continue
            fee = round(record["amount"] * 0.02, 2)
            tax = round(fee * 0.18, 2)
            writer.writerow({
                "txn_id": record["txn_id"],
                "order_id": record["order_id"],
                "amount": f"{record['amount']:.2f}",
                "fee": f"{fee:.2f}",
                "tax": f"{tax:.2f}",
                "net_amount": f"{record['amount'] - fee - tax:.2f}",
                "settled_at": record["date"].strftime("%Y-%m-%d"),
                "merchant_ref": f"MR-{record['order_id'].upper()}",
            })

    with open(ledger_path, "w", newline="", encoding="utf-8") as ledger_file:
        writer = csv.DictWriter(ledger_file, fieldnames=["entry_id", "reference", "amount", "date", "category", "notes"])
        writer.writeheader()
        for record in records:
            if record.get("skip_ledger"):
                continue
            writer.writerow({
                "entry_id": f"STRESS_LED_{record['index']:05d}",
                "reference": record["txn_id"],
                "amount": f"{record.get('ledger_amount', record['amount']):.2f}",
                "date": record.get("ledger_date", record["date"]).strftime("%Y-%m-%d"),
                "category": record["category"],
                "notes": f"Stress payment for {record['order_id']}",
            })

    with open(os.path.join(output_dir, "ground_truth.json"), "w", encoding="utf-8") as truth_file:
        json.dump({
            "total_records": record_count,
            "discrepancies": {
                record["txn_id"]: discrepancy_map.get(record["txn_id"], "matched")
                for record in records
            },
        }, truth_file, indent=2)

    return discrepancy_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, required=True)
    parser.add_argument("--density", type=float, default=0.25)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    count = generate_dataset(args.records, args.density, args.seed, args.output_dir)
    print(f"Generated {args.records} records with {count} discrepancies in {args.output_dir}")


if __name__ == "__main__":
    main()
