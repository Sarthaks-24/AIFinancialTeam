import os
import tempfile
from unittest.mock import patch

import pandas as pd
from django.test import TestCase

from agents.models import ReconciliationException, ReconciliationRun
from agents.services.reconciliation_service import (
    _ai_classify_exceptions,
    _deterministic_match,
    run_reconciliation,
)


class ReconciliationFailureModeTests(TestCase):
    def test_gemini_timeout_keeps_exception_visible(self):
        unresolved = [{
            "txn_id": "timeout_txn",
            "settlement_amount": 100,
            "ledger_amount": 90,
            "settlement_date": "2026-01-01",
            "ledger_date": "2026-01-01",
            "delta": 10,
            "hint": "amount_mismatch",
        }]
        with patch(
            "agents.services.reconciliation_service.ask_specialist",
            side_effect=TimeoutError("Gemini timed out"),
        ):
            result = _ai_classify_exceptions(unresolved)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["txn_id"], "timeout_txn")
        self.assertEqual(result[0]["type"], "amount_mismatch")

    def test_malformed_gemini_json_keeps_exception_visible(self):
        unresolved = [{
            "txn_id": "malformed_txn",
            "settlement_amount": 100,
            "ledger_amount": 90,
            "settlement_date": "2026-01-01",
            "ledger_date": "2026-01-01",
            "delta": 10,
            "hint": "amount_mismatch",
        }]
        with patch(
            "agents.services.reconciliation_service.ask_specialist",
            return_value='{"not": "an array"}',
        ):
            result = _ai_classify_exceptions(unresolved)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["txn_id"], "malformed_txn")
        self.assertEqual(result[0]["type"], "amount_mismatch")

    def test_duplicate_references_are_unresolvable_instead_of_crashing(self):
        settlements = pd.DataFrame([
            {"txn_id": "duplicate_txn", "amount": 100, "settled_at": "2026-01-01"},
        ])
        ledger = pd.DataFrame([
            {"reference": "duplicate_txn", "amount": 100, "date": "2026-01-01"},
            {"reference": "duplicate_txn", "amount": 100, "date": "2026-01-01"},
        ])

        matched, unresolved, ledger_only = _deterministic_match(settlements, ledger)

        self.assertEqual(matched, [])
        self.assertEqual(unresolved[0]["hint"], "unresolvable")
        self.assertIn("Duplicate", unresolved[0]["validation_reason"])
        self.assertEqual(ledger_only, [])

    def test_row_with_missing_required_values_is_unresolvable(self):
        settlements = pd.DataFrame([
            {"txn_id": "incomplete_txn", "amount": None, "settled_at": None},
        ])
        ledger = pd.DataFrame([
            {"reference": "incomplete_txn", "amount": 100, "date": "2026-01-01"},
        ])

        matched, unresolved, ledger_only = _deterministic_match(settlements, ledger)

        self.assertEqual(matched, [])
        self.assertEqual(unresolved[0]["hint"], "unresolvable")
        self.assertEqual(ledger_only, [])

    def test_missing_required_columns_persist_validation_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            pd.DataFrame([{"txn_id": "txn_without_amount"}]).to_csv(
                os.path.join(directory, "razorpay_settlements.csv"), index=False
            )
            pd.DataFrame([{"reference": "txn_without_amount", "amount": 100, "date": "2026-01-01"}]).to_csv(
                os.path.join(directory, "internal_ledger.csv"), index=False
            )

            result = run_reconciliation(data_dir=directory, dataset_name="invalid_input")

        self.assertEqual(result["exceptions"][0]["type"], "unresolvable")
        self.assertIn("settlements missing: amount", result["error"])
        run = ReconciliationRun.objects.get(dataset_name="invalid_input")
        exception = ReconciliationException.objects.get(run=run)
        self.assertEqual(exception.exception_type, "unresolvable")
        self.assertEqual(exception.txn_id, "input_validation")
