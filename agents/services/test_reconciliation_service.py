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

class ReconciliationIntegrationTests(TestCase):
    def test_end_to_end_reconciliation_pipeline(self):
        """
        Integration test verifying canonical_60 can be processed completely:
        loads data -> runs deterministic match -> simulates AI response 
        -> evaluates metrics -> persists to DB properly
        """
        from generate_synthetic_data import build_dataset
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch DATA_DIR in generator and run it
            with patch("generate_synthetic_data.DATA_DIR", temp_dir):
                build_dataset("test_canonical", 60, 10)
                
            # Run the reconciliation pipeline with mocked AI
            with patch(
                "agents.services.reconciliation_service.ask_specialist",
                return_value='{"invalid": "json"}',  # triggers total fallback to deterministic hints
            ):
                result = run_reconciliation(
                    data_dir=os.path.join(temp_dir, "test_canonical"), 
                    dataset_name="test_canonical"
                )

            self.assertEqual(result["total_processed"], 60)
            self.assertEqual(result["matched"], 50)
            self.assertEqual(result["exceptions_count"], 10)
            self.assertEqual(len(result["exceptions"]), 10)
            
            # Check evaluation was performed
            self.assertIn("overall", result["accuracy"])
            self.assertIn("precision", result["accuracy"]["overall"])
            self.assertIn("recall", result["accuracy"]["overall"])
            self.assertIn("f1", result["accuracy"]["overall"])
            
            # Check that the 10 exceptions got persisted
            run = ReconciliationRun.objects.get(dataset_name="test_canonical")
            exceptions = ReconciliationException.objects.filter(run=run)
            self.assertEqual(exceptions.count(), 10)
