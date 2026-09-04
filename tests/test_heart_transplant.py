#!/usr/bin/env python3
"""
Unit Test Suite for Cardiac Transplant Rejection Surveillance Agent
===================================================================
Tests cover:
  - ISHLT 2004 ACR grading (0R, 1R, 2R, 3R)
  - ISHLT 2013 pAMR grading (pAMR 0, 1, 2, 3)
  - Donor-Specific Antibody (DSA) MFI tiers and de novo emergence
  - Non-invasive biomarkers (dd-cfDNA % and AlloMap score)
  - Therapeutic Drug Monitoring (Tacrolimus/Cyclosporine trough windows)
  - Hemodynamic dysfunction and acute LVEF deterioration
  - Treatment protocol generation (Solu-Medrol, rATG, Plasmapheresis, IVIG)
  - Input validation exceptions
  - Batch CSV processing & JSON serialization
  - CLI subcommand execution
"""

import csv
import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from cardiac_transplant_rejection import (
    ACRGrade,
    ImmunosuppressantDrug,
    OverallRejectionTier,
    TransplantCaseInput,
    TransplantRejectionReport,
    calculate_metrics,
    evaluate_transplant_rejection,
    normalize_acr,
    normalize_pamr,
    pAMRGrade,
    process_batch,
)
import cli


class TestCardiacTransplantRejectionAgent(unittest.TestCase):

    def test_quiescent_allograft_baseline(self):
        """Quiescent baseline: 0R, pAMR 0, DSA negative, normal dd-cfDNA, therapeutic trough."""
        inp = TransplantCaseInput(
            case_id="TX-TEST-NORM",
            days_post_transplant=180,
            acr_grade=ACRGrade.GRADE_0R,
            pamr_grade=pAMRGrade.pAMR_0,
            dsa_positive=False,
            dd_cfdna_pct=0.06,
            allomap_score=24.0,
            trough_level_ng_ml=8.0,
            lvef_pct=64.0,
        )
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.QUIESCENT.value)
        self.assertLess(rep.rejection_risk_score, 20.0)
        self.assertEqual(len(rep.critical_alerts), 0)

    def test_mild_cellular_rejection_1r(self):
        """Grade 1R ACR classified as mild suspicion watch."""
        inp = TransplantCaseInput(acr_grade=ACRGrade.GRADE_1R)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.MILD_SUSPICION.value)
        self.assertIn("1R", rep.acr_status)

    def test_moderate_cellular_rejection_2r(self):
        """Grade 2R ACR triggers pulse corticosteroid protocol."""
        inp = TransplantCaseInput(acr_grade=ACRGrade.GRADE_2R)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.MODERATE_REJECTION.value)
        self.assertTrue(any("Methylprednisolone" in step for step in rep.treatment_protocol))

    def test_severe_cellular_rejection_3r(self):
        """Grade 3R ACR triggers severe critical tier and Thymoglobulin (rATG)."""
        inp = TransplantCaseInput(acr_grade=ACRGrade.GRADE_3R)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.SEVERE_CRITICAL.value)
        self.assertTrue(any("antithymocyte globulin" in step.lower() or "atg" in step.lower() for step in rep.treatment_protocol))

    def test_pamr_1_suspicious_amr(self):
        """pAMR 1 classified under mild/moderate surveillance suspicion."""
        inp = TransplantCaseInput(pamr_grade=pAMRGrade.pAMR_1_I)
        rep = evaluate_transplant_rejection(inp)
        self.assertIn("pAMR 1(I+)", rep.pamr_status)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.MILD_SUSPICION.value)

    def test_pamr_2_active_amr(self):
        """pAMR 2 triggers plasmapheresis + IVIG protocol."""
        inp = TransplantCaseInput(pamr_grade=pAMRGrade.pAMR_2)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.MODERATE_REJECTION.value)
        self.assertTrue(any("Plasmapheresis" in step for step in rep.treatment_protocol))
        self.assertTrue(any("IVIG" in step for step in rep.treatment_protocol))

    def test_pamr_3_severe_amr(self):
        """pAMR 3 severe AMR triggers ICU admission, PLEX, IVIG, and biologicals."""
        inp = TransplantCaseInput(pamr_grade=pAMRGrade.pAMR_3)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.SEVERE_CRITICAL.value)
        self.assertTrue(any("Rituximab" in step for step in rep.treatment_protocol))

    def test_ultra_high_dsa_mfi_alert(self):
        """DSA MFI >= 10000 triggers critical alert."""
        inp = TransplantCaseInput(dsa_positive=True, dsa_class_ii_mfi=12500.0)
        rep = evaluate_transplant_rejection(inp)
        self.assertTrue(any("Ultra-high" in a or "12500" in a for a in rep.critical_alerts))

    def test_de_novo_dsa_alert(self):
        """De novo DSA development adds risk penalty and alert."""
        inp = TransplantCaseInput(dsa_positive=True, dsa_class_i_mfi=4500.0, de_novo_dsa=True)
        rep = evaluate_transplant_rejection(inp)
        self.assertTrue(any("De novo DSA" in a for a in rep.critical_alerts))

    def test_markedly_elevated_dd_cfdna(self):
        """dd-cfDNA >= 0.20% indicates active allograft injury."""
        inp = TransplantCaseInput(dd_cfdna_pct=0.45)
        rep = evaluate_transplant_rejection(inp)
        self.assertTrue(any("cell-free DNA" in a for a in rep.critical_alerts))
        self.assertIn("dd-cfDNA markedly elevated", rep.biomarker_status)

    def test_elevated_allomap_gep(self):
        """AlloMap score >= 34 triggers warning."""
        inp = TransplantCaseInput(days_post_transplant=120, allomap_score=36.5)
        rep = evaluate_transplant_rejection(inp)
        self.assertTrue(any("AlloMap score" in a for a in rep.critical_alerts))

    def test_subtherapeutic_tacrolimus_trough(self):
        """Tacrolimus trough < 6.0 at day 180 flags subtherapeutic."""
        inp = TransplantCaseInput(days_post_transplant=180, trough_level_ng_ml=4.2)
        rep = evaluate_transplant_rejection(inp)
        self.assertIn("Subtherapeutic", rep.tdm_status)
        self.assertTrue(any("Subtherapeutic" in a for a in rep.critical_alerts))

    def test_supratherapeutic_tacrolimus_trough(self):
        """Tacrolimus trough > 14.0 ng/mL triggers nephrotoxicity advisory."""
        inp = TransplantCaseInput(days_post_transplant=180, trough_level_ng_ml=15.5)
        rep = evaluate_transplant_rejection(inp)
        self.assertIn("Supratherapeutic", rep.tdm_status)

    def test_hemodynamic_compromise_trigger(self):
        """Hemodynamic compromise elevates status to severe critical."""
        inp = TransplantCaseInput(hemodynamic_compromise=True, lvef_pct=35.0)
        rep = evaluate_transplant_rejection(inp)
        self.assertEqual(rep.overall_rejection_tier, OverallRejectionTier.SEVERE_CRITICAL.value)
        self.assertTrue(any("Hemodynamic compromise" in a for a in rep.critical_alerts))

    def test_acute_lvef_drop_warning(self):
        """Drop in LVEF from 65% to 48% (17% drop) triggers severe graft dysfunction."""
        inp = TransplantCaseInput(baseline_lvef_pct=65.0, lvef_pct=48.0)
        rep = evaluate_transplant_rejection(inp)
        self.assertIn("Severe Hemodynamic Dysfunction", rep.graft_function_status)

    def test_invalid_days_post_transplant(self):
        """Negative days post-transplant raises ValueError."""
        inp = TransplantCaseInput(days_post_transplant=-5)
        with self.assertRaises(ValueError):
            evaluate_transplant_rejection(inp)

    def test_invalid_lvef_bounds(self):
        """Unphysiological LVEF raises ValueError."""
        inp = TransplantCaseInput(lvef_pct=5.0)
        with self.assertRaises(ValueError):
            evaluate_transplant_rejection(inp)

    def test_invalid_trough_bounds(self):
        """Negative trough raises ValueError."""
        inp = TransplantCaseInput(trough_level_ng_ml=-2.0)
        with self.assertRaises(ValueError):
            evaluate_transplant_rejection(inp)

    def test_normalization_helpers(self):
        """Test robust grading string normalizers."""
        self.assertEqual(normalize_acr("2R_MODERATE"), "2R")
        self.assertEqual(normalize_acr("GRADE_3R"), "3R")
        self.assertEqual(normalize_pamr("pAMR 2"), "pAMR 2")
        self.assertEqual(normalize_pamr("pAMR 1-I"), "pAMR 1(I+)")

    def test_calculate_metrics_wrapper_aliases(self):
        """Test calculate_metrics with dictionary parameters."""
        res = calculate_metrics(
            case_id="TX-WRAP-01",
            acr_grade="2R",
            pamr_grade="pAMR 0",
            trough=9.0,
            lvef=60.0,
        )
        self.assertEqual(res["tool"], "cardiac-transplant-rejection-agent")
        self.assertEqual(res["classification"], OverallRejectionTier.MODERATE_REJECTION.value)
        self.assertIn("score", res)

    def test_to_dict_and_json_serialization(self):
        """Ensure report serializes to valid JSON."""
        inp = TransplantCaseInput(case_id="TX-JSON-01")
        rep = evaluate_transplant_rejection(inp)
        d = rep.to_dict()
        s = json.dumps(d)
        deserialized = json.loads(s)
        self.assertEqual(deserialized["case_id"], "TX-JSON-01")
        self.assertIn("rejection_risk_score", deserialized)

    def test_batch_processing(self):
        """Test batch CSV processing for transplant registry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            in_csv = os.path.join(tmpdir, "tx_in.csv")
            out_csv = os.path.join(tmpdir, "tx_out.csv")

            with open(in_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["case_id", "days_post_transplant", "acr_grade", "pamr_grade", "trough_level_ng_ml", "lvef_pct"])
                writer.writeheader()
                writer.writerow({"case_id": "C1", "days_post_transplant": "180", "acr_grade": "0R", "pamr_grade": "pAMR 0", "trough_level_ng_ml": "8.5", "lvef_pct": "64"})
                writer.writerow({"case_id": "C2", "days_post_transplant": "90", "acr_grade": "2R", "pamr_grade": "pAMR 2", "trough_level_ng_ml": "5.0", "lvef_pct": "45"})

            count = process_batch(in_csv, out_csv)
            self.assertEqual(count, 2)
            self.assertTrue(os.path.exists(out_csv))

            with open(out_csv, "r", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[0]["case_id"], "C1")
                self.assertEqual(rows[1]["case_id"], "C2")

    def test_cli_audit_command(self):
        """Test CLI audit subcommand."""
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["audit", "--case-id", "CLI-TX-01", "--acr", "2R", "--trough", "8.5"])
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            self.assertIn("HEART ALLOGRAFT SURVEILLANCE", output)
            self.assertIn("CLI-TX-01", output)

    def test_cli_audit_json_flag(self):
        """Test CLI JSON output mode."""
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["audit", "--case-id", "CLI-JSON", "--json"])
            self.assertEqual(exit_code, 0)
            data = json.loads(mock_out.getvalue())
            self.assertEqual(data["case_id"], "CLI-JSON")
            self.assertIn("overall_rejection_tier", data)

    def test_cli_guidelines_command(self):
        """Test CLI guidelines reference table."""
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            exit_code = cli.main(["guidelines"])
            self.assertEqual(exit_code, 0)
            output = mock_out.getvalue()
            self.assertIn("Acute Cellular Rejection", output)
            self.assertIn("Antibody-Mediated Rejection", output)

    def test_interactive_wizard_mock(self):
        """Test interactive wizard prompt."""
        user_inputs = ["TX-WIZ", "PAT-99", "120", "2", "1", "n", "0.08", "8.0", "60", "n"]
        with patch("builtins.input", side_effect=user_inputs):
            inp = cli.interactive_wizard()
            self.assertEqual(inp.case_id, "TX-WIZ")
            self.assertEqual(inp.acr_grade, "1R")

    def test_calculate_metrics_default_invocation(self):
        """Test default invocation returns complete dict."""
        res = calculate_metrics()
        self.assertEqual(res["tool"], "cardiac-transplant-rejection-agent")
        self.assertIn("rejection_risk_score", res)


if __name__ == "__main__":
    unittest.main()
