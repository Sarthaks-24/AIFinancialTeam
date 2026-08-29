"""
Reconciliation Service
======================
Deterministic pre-match on txn_id/reference + amount, then sends
unresolved rows to Gemini for AI classification and reasoning.
"""

import logging
import os
import time
import json
import re

import pandas as pd
from django.conf import settings

from .ai_service import ask_specialist

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.BASE_DIR, "reconciliation_data")
SETTLEMENTS_FILE = os.path.join(DATA_DIR, "razorpay_settlements.csv")
LEDGER_FILE = os.path.join(DATA_DIR, "internal_ledger.csv")
REQUIRED_SETTLEMENT_COLUMNS = {
    "txn_id", "amount", "settled_at",
}
REQUIRED_LEDGER_COLUMNS = {
    "reference", "amount", "date",
}


def _load_data(data_dir=DATA_DIR):
    """Load both CSVs and return as DataFrames."""
    settlements = pd.read_csv(os.path.join(data_dir, "razorpay_settlements.csv"))
    ledger = pd.read_csv(os.path.join(data_dir, "internal_ledger.csv"))
    missing_settlement = REQUIRED_SETTLEMENT_COLUMNS - set(settlements.columns)
    missing_ledger = REQUIRED_LEDGER_COLUMNS - set(ledger.columns)
    if missing_settlement or missing_ledger:
        missing = []
        if missing_settlement:
            missing.append(f"settlements missing: {', '.join(sorted(missing_settlement))}")
        if missing_ledger:
            missing.append(f"ledger missing: {', '.join(sorted(missing_ledger))}")
        raise ValueError("Invalid reconciliation input: " + "; ".join(missing))
    return settlements, ledger


def _deterministic_match(settlements: pd.DataFrame, ledger: pd.DataFrame):
    """
    First pass: exact match on txn_id == reference, amount, and date.
    Returns (matched_pairs, unmatched_settlements, unmatched_ledger).
    """
    matched = []
    unmatched_settlements = []
    unmatched_ledger_refs = set()
    ledger_by_ref = {}
    duplicate_ledger_refs = set(
        ledger.loc[ledger["reference"].duplicated(keep=False), "reference"].tolist()
    )

    unmatched_ledger = []
    for ledger_index, l_row in ledger.iterrows():
        reference = l_row["reference"]
        if pd.isna(reference) or pd.isna(l_row["amount"]) or pd.isna(l_row["date"]):
            unmatched_ledger.append({
                "txn_id": f"invalid_ledger_row_{ledger_index + 1}",
                "settlement_amount": None,
                "ledger_amount": l_row["amount"] if not pd.isna(l_row["amount"]) else None,
                "settlement_date": None,
                "ledger_date": l_row["date"] if not pd.isna(l_row["date"]) else None,
                "delta": None,
                "hint": "unresolvable",
                "validation_reason": "Ledger row is missing a required value.",
            })
            continue
        unmatched_ledger_refs.add(reference)
        ledger_by_ref.setdefault(reference, []).append(l_row.to_dict())

    for _, s_row in settlements.iterrows():
        txn_id = s_row["txn_id"]
        if pd.isna(txn_id) or pd.isna(s_row["amount"]) or pd.isna(s_row["settled_at"]):
            if not pd.isna(txn_id):
                unmatched_ledger_refs.discard(txn_id)
            unmatched_settlements.append({
                "txn_id": f"invalid_settlement_row_{s_row.name + 1}",
                "settlement_amount": s_row["amount"] if not pd.isna(s_row["amount"]) else None,
                "ledger_amount": None,
                "settlement_date": s_row["settled_at"] if not pd.isna(s_row["settled_at"]) else None,
                "ledger_date": None,
                "delta": None,
                "hint": "unresolvable",
                "validation_reason": "Settlement row is missing a required value.",
            })
            continue

        duplicate_settlement = settlements["txn_id"].eq(txn_id).sum() > 1
        if duplicate_settlement or txn_id in duplicate_ledger_refs:
            l_row = ledger_by_ref.get(txn_id, [{}])[0]
            unmatched_ledger_refs.discard(txn_id)
            unmatched_settlements.append({
                "txn_id": txn_id,
                "settlement_amount": float(s_row["amount"]),
                "ledger_amount": l_row.get("amount"),
                "settlement_date": str(s_row["settled_at"]),
                "ledger_date": str(l_row["date"]) if l_row.get("date") is not None else None,
                "delta": None,
                "hint": "unresolvable",
                "validation_reason": "Duplicate transaction reference makes this record ambiguous.",
            })
            continue

        if txn_id in ledger_by_ref:
            l_row = ledger_by_ref[txn_id][0]
            unmatched_ledger_refs.discard(txn_id)

            s_amount = float(s_row["amount"])
            l_amount = float(l_row["amount"])

            settlement_date = str(s_row["settled_at"])
            ledger_date = str(l_row["date"])

            if abs(s_amount - l_amount) < 0.01 and settlement_date == ledger_date:
                # Perfect match
                matched.append({
                    "txn_id": txn_id,
                    "settlement_amount": s_amount,
                    "ledger_amount": l_amount,
                })
            elif abs(s_amount - l_amount) < 0.01:
                # Date mismatch — send to AI
                unmatched_settlements.append({
                    "txn_id": txn_id,
                    "settlement_amount": s_amount,
                    "ledger_amount": l_amount,
                    "settlement_date": settlement_date,
                    "ledger_date": ledger_date,
                    "delta": 0,
                    "hint": "date_mismatch",
                })
            else:
                # Amount mismatch — send to AI
                unmatched_settlements.append({
                    "txn_id": txn_id,
                    "settlement_amount": s_amount,
                    "ledger_amount": l_amount,
                    "settlement_date": settlement_date,
                    "ledger_date": ledger_date,
                    "delta": round(s_amount - l_amount, 2),
                    "hint": "amount_mismatch",
                })
        else:
            # In settlement but not in ledger
            unmatched_settlements.append({
                "txn_id": txn_id,
                "settlement_amount": float(s_row["amount"]),
                "ledger_amount": None,
                "settlement_date": s_row["settled_at"],
                "ledger_date": None,
                "delta": None,
                "hint": "missing_in_ledger",
            })

    # Ledger entries with no matching settlement
    for ref in unmatched_ledger_refs:
        l_row = ledger_by_ref[ref][0]
        if ref in duplicate_ledger_refs:
            unmatched_ledger.append({
                "txn_id": ref,
                "settlement_amount": None,
                "ledger_amount": float(l_row["amount"]),
                "settlement_date": None,
                "ledger_date": l_row["date"],
                "delta": None,
                "hint": "unresolvable",
                "validation_reason": "Duplicate transaction reference makes this record ambiguous.",
            })
        else:
            unmatched_ledger.append({
                "txn_id": ref,
                "settlement_amount": None,
                "ledger_amount": float(l_row["amount"]),
                "settlement_date": None,
                "ledger_date": l_row["date"],
                "delta": None,
                "hint": "missing_in_settlement",
            })

    return matched, unmatched_settlements, unmatched_ledger


def _ai_classify_exceptions(unresolved: list[dict]) -> list[dict]:
    """
    Send unresolved rows to Gemini for classification and reasoning.
    Returns enriched exception dicts with ai_reasoning.
    """
    if not unresolved:
        return []

    rows_text = "\n".join(
        f"- txn_id={r['txn_id']}, settlement_amt={r['settlement_amount']}, "
        f"ledger_amt={r['ledger_amount']}, settlement_date={r['settlement_date']}, "
        f"ledger_date={r['ledger_date']}, delta={r['delta']}, hint={r['hint']}"
        for r in unresolved
    )

    data_context = (
        "Below are unresolved transaction records from a reconciliation between "
        "Razorpay settlement exports and an internal company ledger.\n\n"
        f"{rows_text}"
    )

    question = (
        "Classify each unresolved record into one of these categories: "
        "amount_mismatch, date_mismatch, missing_in_ledger, missing_in_settlement, unresolvable. "
        "Compare settlement_date with ledger_date explicitly: when the transaction ID and amount "
        "match but the dates differ, classify it as date_mismatch. "
        "For each, provide a short reasoning explaining the discrepancy.\n\n"
        "Return your response as a JSON array with objects having keys: "
        "txn_id, type, reasoning.\n"
        "Example: [{\"txn_id\": \"rzp_txn_0001\", \"type\": \"amount_mismatch\", "
        "\"reasoning\": \"Settlement shows ₹15,000 but ledger records ₹14,500 — ₹500 delta likely fee adjustment.\"}]\n\n"
        "Return ONLY the JSON array, no markdown fences, no extra text."
    )

    try:
        raw = ask_specialist(
            data_context=data_context,
            question=question,
            specialist_name="Nova",
            persona_prompt=(
                "You are Nova, a precise financial reconciliation specialist. "
                "You match Razorpay payment settlements against internal accounting records. "
                "Be exact with numbers. Classify discrepancies honestly."
            ),
            max_output_tokens=2000,
        )

        # Strip markdown fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        ai_results = json.loads(cleaned)
        if not isinstance(ai_results, list):
            raise ValueError("AI classification response was not a JSON array")
        ai_results = [result for result in ai_results if isinstance(result, dict) and result.get("txn_id")]
    except Exception as exc:
        logger.exception("AI classification failed: %s", exc)
        ai_results = []

    # Merge AI results back into unresolved records
    ai_lookup = {r["txn_id"]: r for r in ai_results}
    enriched = []
    for row in unresolved:
        ai = ai_lookup.get(row["txn_id"], {})
        enriched.append({
            "txn_id": row["txn_id"],
            "type": ai.get("type", row["hint"]),
            "settlement_amount": row["settlement_amount"],
            "ledger_amount": row["ledger_amount"],
            "delta": row["delta"],
            "ai_reasoning": ai.get(
                "reasoning",
                row.get("validation_reason") or f"Classified as {row['hint']} by deterministic check.",
            ),
        })

    return enriched


def _ai_summary(exceptions: list[dict], match_rate: float, total: int) -> str:
    """Ask Gemini for a one-paragraph executive summary of the reconciliation."""
    exception_text = "\n".join(
        f"- {e['txn_id']}: {e['type']} (delta: {e['delta']})"
        for e in exceptions
    )

    data_context = (
        f"Reconciliation complete.\n"
        f"Total records processed: {total}\n"
        f"Match rate: {match_rate:.1f}%\n"
        f"Exceptions found:\n{exception_text}"
    )

    try:
        return ask_specialist(
            data_context=data_context,
            question="Write a one-paragraph executive summary of this reconciliation run. Highlight the key risks and recommend next steps.",
            specialist_name="Atlas",
            persona_prompt="You are Atlas, the AI Chief of Staff synthesizing reconciliation findings into an executive briefing.",
            max_output_tokens=300,
        )
    except Exception as exc:
        logger.exception("AI summary failed: %s", exc)
        return "Summary generation unavailable."


def _evaluate_accuracy(exceptions: list[dict], data_dir=DATA_DIR) -> dict:
    """Compare predicted exception types with the generated ground truth."""
    gt_path = os.path.join(data_dir, "ground_truth.json")
    if not os.path.exists(gt_path):
        return {}

    with open(gt_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f).get("discrepancies", {})

    predictions = {exception["txn_id"]: exception.get("type", "unresolvable") for exception in exceptions}
    labels = set(ground_truth.values()) | set(predictions.values())
    by_category = {}

    for label in sorted(labels):
        true_positive = false_positive = false_negative = 0
        for txn_id, actual in ground_truth.items():
            predicted = predictions.get(txn_id, "matched")
            true_positive += predicted == label and actual == label
            false_positive += predicted == label and actual != label
            false_negative += predicted != label and actual == label

        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
        by_category[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    total_correct = sum(
        predictions.get(txn_id, "matched") == actual
        for txn_id, actual in ground_truth.items()
    )
    overall = total_correct / len(ground_truth) if ground_truth else 0
    return {
        "overall": {
            "precision": round(overall, 4),
            "recall": round(overall, 4),
            "f1": round(overall, 4),
        },
        "by_category": by_category,
    }


def run_reconciliation(organization=None, data_dir=DATA_DIR, dataset_name="canonical_60") -> dict:
    """
    Full reconciliation pipeline.
    Returns structured result dict ready for the API response.
    """
    start = time.time()

    try:
        settlements, ledger = _load_data(data_dir)
    except ValueError as exc:
        from agents.models import ReconciliationRun, ReconciliationException

        elapsed_ms = round((time.time() - start) * 1000)
        message = str(exc)
        run_obj = ReconciliationRun.objects.create(
            organization=organization,
            dataset_name=dataset_name,
            total_processed=0,
            matched=0,
            exceptions_count=1,
            match_rate_pct=0,
            processing_time_ms=elapsed_ms,
            ai_summary=message,
        )
        ReconciliationException.objects.create(
            run=run_obj,
            txn_id="input_validation",
            exception_type="unresolvable",
            ai_reasoning=message,
        )
        return {
            "dataset_name": dataset_name,
            "total_settlement_records": 0,
            "total_ledger_records": 0,
            "total_processed": 0,
            "matched": 0,
            "exceptions_count": 1,
            "match_rate_pct": 0,
            "processing_time_ms": elapsed_ms,
            "exceptions": [{
                "txn_id": "input_validation",
                "type": "unresolvable",
                "ai_reasoning": message,
            }],
            "ai_summary": message,
            "accuracy": {},
            "throughput_records_per_sec": 0,
            "error": message,
        }
    matched, unmatched_settlements, unmatched_ledger = _deterministic_match(settlements, ledger)

    all_unresolved = unmatched_settlements + unmatched_ledger
    exceptions = _ai_classify_exceptions(all_unresolved)

    total_unique = len(settlements) + len(unmatched_ledger)  # all settlement rows + ledger-only rows
    matched_count = len(matched)
    match_rate = round((matched_count / total_unique) * 100, 1) if total_unique else 0

    elapsed_ms = round((time.time() - start) * 1000)

    summary = _ai_summary(exceptions, match_rate, total_unique)
    accuracy = _evaluate_accuracy(exceptions, data_dir)

    from agents.models import ReconciliationRun, ReconciliationException

    # Persist the run
    run_obj = ReconciliationRun.objects.create(
        organization=organization,
        dataset_name=dataset_name,
        total_processed=total_unique,
        matched=matched_count,
        exceptions_count=len(exceptions),
        match_rate_pct=match_rate,
        accuracy_overall_f1=accuracy.get("overall", {}).get("f1") if "overall" in accuracy else None,
        processing_time_ms=elapsed_ms,
        ai_summary=summary,
    )

    # Persist the exceptions
    exc_objects = []
    
    gt_path = os.path.join(data_dir, "ground_truth.json")
    ground_truth = {}
    if os.path.exists(gt_path):
        with open(gt_path, "r", encoding="utf-8") as f:
            ground_truth = json.load(f).get("discrepancies", {})

    for e in exceptions:
        tid = e["txn_id"]
        ptype = e["type"]
        gtype = ground_truth.get(tid, "matched")
        
        exc_objects.append(ReconciliationException(
            run=run_obj,
            txn_id=tid,
            exception_type=ptype,
            confidence=e.get("confidence"),
            settlement_amount=e.get("settlement_amount"),
            ledger_amount=e.get("ledger_amount"),
            delta=e.get("delta"),
            ai_reasoning=e.get("ai_reasoning", ""),
            ground_truth_type=gtype,
            is_correct=(ptype == gtype)
        ))
    
    ReconciliationException.objects.bulk_create(exc_objects)

    return {
        "dataset_name": dataset_name,
        "total_settlement_records": len(settlements),
        "total_ledger_records": len(ledger),
        "total_processed": total_unique,
        "matched": matched_count,
        "exceptions_count": len(exceptions),
        "match_rate_pct": match_rate,
        "processing_time_ms": elapsed_ms,
        "exceptions": exceptions,
        "ai_summary": summary,
        "accuracy": accuracy,
        "throughput_records_per_sec": round(total_unique / (elapsed_ms / 1000), 2) if elapsed_ms else 0,
    }
