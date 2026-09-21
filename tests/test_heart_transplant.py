import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import cli
from cardiac_transplant_rejection import (
    ACRGrade,
    ImmunosuppressantDrug,
    OverallRejectionTier,
    TransplantCaseInput,
    calculate_metrics,
    evaluate_transplant_rejection,
    normalize_acr,
    normalize_pamr,
    process_batch,
    pAMRGrade,
)


class TestCardiacTransplantRejectionAgent(unittest.TestCase):
    def test_quiescent_baseline(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(
                acr_grade=ACRGrade.GRADE_0R,
                pamr_grade=pAMRGrade.pAMR_0,
                dsa_positive=False,
                dd_cfdna_pct=0.06,
                allomap_score=24.0,
                lvef_pct=64.0,
                baseline_lvef_pct=65.0,
            )
        )
        self.assertEqual(report.overall_rejection_tier, OverallRejectionTier.QUIESCENT.value)
        self.assertLess(report.rejection_risk_score, 20)
        self.assertTrue(report.limitations)

    def test_acr_2r_prompts_review_without_drug_prescription(self):
        report = evaluate_transplant_rejection(TransplantCaseInput(acr_grade="2R"))
        self.assertEqual(report.overall_rejection_tier, OverallRejectionTier.MODERATE_REJECTION.value)
        joined = " ".join(report.treatment_protocol).lower()
        self.assertIn("transplant-team", joined)
        self.assertNotIn("methylprednisolone", joined)
        self.assertNotIn("rituximab", joined)

    def test_acr_3r_is_very_high_concern(self):
        report = evaluate_transplant_rejection(TransplantCaseInput(acr_grade="3R"))
        self.assertEqual(report.overall_rejection_tier, OverallRejectionTier.SEVERE_CRITICAL.value)
        self.assertTrue(any("URGENT" in item for item in report.critical_alerts))

    def test_pamr_2_is_high_concern(self):
        report = evaluate_transplant_rejection(TransplantCaseInput(pamr_grade="pAMR 2"))
        self.assertEqual(report.overall_rejection_tier, OverallRejectionTier.MODERATE_REJECTION.value)
        self.assertIn("pAMR 2", report.pamr_status)

    def test_dd_cfdna_is_described_as_injury_not_diagnostic(self):
        report = evaluate_transplant_rejection(TransplantCaseInput(dd_cfdna_pct=0.45))
        self.assertTrue(any("not rejection-specific" in item for item in report.critical_alerts))

    def test_gep_before_two_months_is_not_scored(self):
        early = evaluate_transplant_rejection(
            TransplantCaseInput(days_post_transplant=45, allomap_score=40.0, dd_cfdna_pct=0.0)
        )
        later = evaluate_transplant_rejection(
            TransplantCaseInput(days_post_transplant=60, allomap_score=40.0, dd_cfdna_pct=0.0)
        )
        self.assertEqual(early.rejection_risk_score, 0.0)
        self.assertGreater(later.rejection_risk_score, early.rejection_risk_score)

    def test_mfi_value_alone_does_not_force_dsa_positive(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(dsa_positive=False, dsa_class_ii_mfi=12000, dd_cfdna_pct=0.0)
        )
        self.assertIn("not flagged positive", report.dsa_status)
        self.assertEqual(report.rejection_risk_score, 0.0)

    def test_de_novo_dsa_adds_concern(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(dsa_positive=True, de_novo_dsa=True, dsa_class_i_mfi=2500, dd_cfdna_pct=0.0)
        )
        self.assertGreaterEqual(report.rejection_risk_score, 20.0)
        self.assertTrue(any("De novo DSA" in item for item in report.critical_alerts))

    def test_supplied_trough_target_is_used(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(
                trough_level_ng_ml=4.0,
                trough_target_low_ng_ml=6.0,
                trough_target_high_ng_ml=10.0,
                dd_cfdna_pct=0.0,
            )
        )
        self.assertIn("below supplied target", report.tdm_status)
        self.assertEqual(report.rejection_risk_score, 10.0)

    def test_sirolimus_does_not_fall_through_to_cyclosporine_targets(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(
                primary_immunosuppressant=ImmunosuppressantDrug.SIROLIMUS,
                trough_level_ng_ml=6.0,
                dd_cfdna_pct=0.0,
            )
        )
        self.assertIn("no patient/center-specific target", report.tdm_status)
        self.assertEqual(report.rejection_risk_score, 0.0)

    def test_hemodynamic_compromise_is_very_high_concern(self):
        report = evaluate_transplant_rejection(
            TransplantCaseInput(hemodynamic_compromise=True, lvef_pct=35.0, dd_cfdna_pct=0.0)
        )
        self.assertEqual(report.overall_rejection_tier, OverallRejectionTier.SEVERE_CRITICAL.value)

    def test_lvef_physiological_bounds(self):
        evaluate_transplant_rejection(
            TransplantCaseInput(lvef_pct=5.0, baseline_lvef_pct=5.0, dd_cfdna_pct=0.0)
        )
        with self.assertRaises(ValueError):
            evaluate_transplant_rejection(TransplantCaseInput(lvef_pct=-1))
        with self.assertRaises(ValueError):
            evaluate_transplant_rejection(TransplantCaseInput(lvef_pct=101))

    def test_unknown_grades_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_acr("banana")
        with self.assertRaises(ValueError):
            normalize_pamr("negative-ish")

    def test_legacy_1990_acr_mapping_is_explicit_and_correct(self):
        self.assertEqual(normalize_acr("1990 2"), "1R")
        self.assertEqual(normalize_acr("1990 3A"), "2R")
        self.assertEqual(normalize_acr("1990 3B"), "3R")
        self.assertEqual(normalize_acr("2"), "2R")

    def test_normalize_pamr_aliases(self):
        self.assertEqual(normalize_pamr("pAMR 1-I"), "pAMR 1(I+)")
        self.assertEqual(normalize_pamr("pAMR 2"), "pAMR 2")

    def test_calculate_metrics_invalid_numeric_raises(self):
        with self.assertRaises(ValueError):
            calculate_metrics(days="not-a-number")

    def test_calculate_metrics_invalid_boolean_raises(self):
        with self.assertRaises(ValueError):
            calculate_metrics(dsa_positive="sometimes")

    def test_calculate_metrics_aliases(self):
        result = calculate_metrics(
            case_id="A", acr="2R", pamr="pAMR 0", trough=9, lvef=60, dd_cfdna_pct=0
        )
        self.assertEqual(result["tool"], "cardiac-transplant-rejection-agent")
        self.assertEqual(result["classification"], OverallRejectionTier.MODERATE_REJECTION.value)

    def test_json_serialization(self):
        data = evaluate_transplant_rejection(
            TransplantCaseInput(case_id="JSON", dd_cfdna_pct=0)
        ).to_dict()
        self.assertEqual(json.loads(json.dumps(data))["case_id"], "JSON")

    def test_batch_preserves_invalid_rows_with_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = os.path.join(tmpdir, "input.csv")
            output = os.path.join(tmpdir, "output.csv")
            with open(source, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["case_id", "acr_grade", "days_post_transplant"])
                writer.writeheader()
                writer.writerow({"case_id": "valid", "acr_grade": "0R", "days_post_transplant": "180"})
                writer.writerow({"case_id": "invalid", "acr_grade": "X", "days_post_transplant": "180"})
            self.assertEqual(process_batch(source, output), 2)
            with open(output, encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["processing_error"], "")
            self.assertIn("Unsupported ACR grade", rows[1]["processing_error"])

    def test_cli_audit_json(self):
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(
                cli.main(["audit", "--case-id", "CLI", "--json", "--dd-cfdna", "0"]),
                0,
            )
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["case_id"], "CLI")

    def test_cli_invalid_grade_returns_2(self):
        with patch("sys.stderr", new_callable=io.StringIO) as err:
            self.assertEqual(cli.main(["audit", "--acr", "X"]), 2)
            self.assertIn("Unsupported ACR grade", err.getvalue())

    def test_cli_guidelines(self):
        with patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(cli.main(["guidelines"]), 0)
            self.assertIn("unvalidated research heuristic", out.getvalue())

    def test_interactive_wizard(self):
        inputs = [
            "TX-WIZ", "", "120", "2", "1", "n", "0.08", "28", "8", "", "", "60", "65", "n"
        ]
        with patch("builtins.input", side_effect=inputs):
            case = cli.interactive_wizard()
        self.assertEqual(case.case_id, "TX-WIZ")
        self.assertEqual(case.acr_grade, "1R")


if __name__ == "__main__":
    unittest.main()
