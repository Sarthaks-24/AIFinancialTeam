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


def _load_data():
    """Load both CSVs and return as DataFrames."""
    settlements = pd.read_csv(SETTLEMENTS_FILE)
    ledger = pd.read_csv(LEDGER_FILE)
    return settlements, ledger


def _deterministic_match(settlements: pd.DataFrame, ledger: pd.DataFrame):
    """
    First pass: exact match on txn_id == reference AND amount equality.
    Returns (matched_pairs, unmatched_settlements, unmatched_ledger).
    """
    matched = []
    unmatched_settlements = []
    unmatched_ledger_refs = set(ledger["reference"].tolist())

    ledger_by_ref = ledger.set_index("reference").to_dict("index")

    for _, s_row in settlements.iterrows():
        txn_id = s_row["txn_id"]
        if txn_id in ledger_by_ref:
            l_row = ledger_by_ref[txn_id]
            unmatched_ledger_refs.discard(txn_id)

            s_amount = float(s_row["amount"])
            l_amount = float(l_row["amount"])

            if abs(s_amount - l_amount) < 0.01:
                # Perfect match
                matched.append({
                    "txn_id": txn_id,
                    "settlement_amount": s_amount,
                    "ledger_amount": l_amount,
                })
            else:
                # Amount mismatch — send to AI
                unmatched_settlements.append({
                    "txn_id": txn_id,
                    "settlement_amount": s_amount,
                    "ledger_amount": l_amount,
                    "settlement_date": s_row["settled_at"],
                    "ledger_date": l_row["date"],
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
    unmatched_ledger = []
    for ref in unmatched_ledger_refs:
        l_row = ledger_by_ref[ref]
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
            "ai_reasoning": ai.get("reasoning", f"Classified as {row['hint']} by deterministic check."),
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


def run_reconciliation() -> dict:
    """
    Full reconciliation pipeline.
    Returns structured result dict ready for the API response.
    """
    start = time.time()

    settlements, ledger = _load_data()
    matched, unmatched_settlements, unmatched_ledger = _deterministic_match(settlements, ledger)

    all_unresolved = unmatched_settlements + unmatched_ledger
    exceptions = _ai_classify_exceptions(all_unresolved)

    total_unique = len(settlements) + len(unmatched_ledger)  # all settlement rows + ledger-only rows
    matched_count = len(matched)
    match_rate = round((matched_count / total_unique) * 100, 1) if total_unique else 0

    elapsed_ms = round((time.time() - start) * 1000)

    summary = _ai_summary(exceptions, match_rate, total_unique)

    return {
        "total_settlement_records": len(settlements),
        "total_ledger_records": len(ledger),
        "total_processed": total_unique,
        "matched": matched_count,
        "exceptions_count": len(exceptions),
        "match_rate_pct": match_rate,
        "processing_time_ms": elapsed_ms,
        "exceptions": exceptions,
        "ai_summary": summary,
    }
