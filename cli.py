#!/usr/bin/env python3
"""
Cardiac Transplant Rejection & Allograft Surveillance CLI
==========================================================
Command line interface for assessing ISHLT cellular (0R-3R) and antibody-mediated
(pAMR 0-3) rejection, DSA titers, dd-cfDNA %, and immunosuppressive TDM.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from cardiac_transplant_rejection import (
    ACRGrade,
    ImmunosuppressantDrug,
    TransplantCaseInput,
    calculate_metrics,
    evaluate_transplant_rejection,
    pAMRGrade,
    process_batch,
)


def format_report_table(report: dict) -> str:
    """Format allograft surveillance dossier into an ASCII table."""
    lines = []
    lines.append("=" * 76)
    lines.append(f"  HEART ALLOGRAFT SURVEILLANCE & REJECTION DOSSIER (ISHLT)")
    lines.append("=" * 76)
    lines.append(f"  Case ID               : {report['case_id']}")
    lines.append(f"  Patient ID            : {report.get('patient_id') or 'N/A'}")
    lines.append(f"  Post-Transplant Time  : Day {report['days_post_transplant']}")
    lines.append(f"  Rejection Risk Score  : {report['rejection_risk_score']:.1f} / 100")
    lines.append(f"  Overall Status        : {report['overall_rejection_tier']}")
    lines.append("-" * 76)
    lines.append("  PATHOLOGY & HISTOPATHOLOGY (ISHLT BIOPSY):")
    lines.append(f"    * Acute Cellular Rejection (ACR): {report['acr_status']}")
    lines.append(f"    * Antibody-Mediated (pAMR)      : {report['pamr_status']}")
    lines.append("-" * 76)
    lines.append("  SEROLOGY, BIOMARKERS & PHARMACOKINETICS:")
    lines.append(f"    * Donor-Specific Antibodies (DSA): {report['dsa_status']}")
    lines.append(f"    * Non-Invasive Biomarkers        : {report['biomarker_status']}")
    lines.append(f"    * Immunosuppressant Trough (TDM) : {report['tdm_status']}")
    lines.append(f"    * Allograft Hemodynamics / LVEF  : {report['graft_function_status']}")
    lines.append("-" * 76)
    lines.append("  RECOMMENDED CLINICAL ACTION PROTOCOL:")
    for step in report.get("treatment_protocol", []):
        lines.append(f"    -> {step}")
    lines.append("-" * 76)
    lines.append("  SURVEILLANCE & MONITORING DIRECTIVES:")
    for m in report.get("monitoring_recommendations", []):
        lines.append(f"    * {m}")
    if report.get("critical_alerts"):
        lines.append("-" * 76)
        lines.append("  CRITICAL SAFETY ALERTS:")
        for a in report["critical_alerts"]:
            lines.append(f"    [!] {a}")
    lines.append("=" * 76)
    return "\n".join(lines)


def interactive_wizard() -> TransplantCaseInput:
    """Run interactive question prompt to gather transplant surveillance data."""
    print("\n--- Cardiac Transplant Rejection Surveillance Wizard ---")
    case_id = input("Case ID [TX-SURV-01]: ").strip() or "TX-SURV-01"
    patient_id = input("Patient ID / MRN: ").strip() or None

    def ask_int(prompt: str, default: int) -> int:
        resp = input(f"{prompt} [{default}]: ").strip()
        if not resp:
            return default
        try:
            return int(resp)
        except ValueError:
            return default

    def ask_float(prompt: str, default: float) -> float:
        resp = input(f"{prompt} [{default}]: ").strip()
        if not resp:
            return default
        try:
            return float(resp)
        except ValueError:
            return default

    def ask_bool(prompt: str) -> bool:
        resp = input(f"{prompt} (y/n): ").strip().lower()
        return resp in ("y", "yes", "true", "1")

    days = ask_int("Days post-transplant", 180)
    
    print("\nISHLT Acute Cellular Rejection (ACR) Grade:")
    print("  [1] 0R (None)")
    print("  [2] 1R (Mild)")
    print("  [3] 2R (Moderate)")
    print("  [4] 3R (Severe)")
    acr_choice = input("Select ACR (1-4) [1]: ").strip()
    acr_map = {"1": "0R", "2": "1R", "3": "2R", "4": "3R"}
    acr_grade = acr_map.get(acr_choice, "0R")

    print("\nISHLT Pathologic Antibody-Mediated Rejection (pAMR) Grade:")
    print("  [1] pAMR 0 (Negative)")
    print("  [2] pAMR 1(H+) (Histologic alone)")
    print("  [3] pAMR 1(I+) (C4d/C3d positive alone)")
    print("  [4] pAMR 2 (Active AMR)")
    print("  [5] pAMR 3 (Severe AMR)")
    pamr_choice = input("Select pAMR (1-5) [1]: ").strip()
    pamr_map = {"1": "pAMR 0", "2": "pAMR 1(H+)", "3": "pAMR 1(I+)", "4": "pAMR 2", "5": "pAMR 3"}
    pamr_grade = pamr_map.get(pamr_choice, "pAMR 0")

    dsa_pos = ask_bool("Donor-Specific Anti-HLA Antibodies (DSA) positive?")
    dsa_i = 0.0
    dsa_ii = 0.0
    if dsa_pos:
        dsa_i = ask_float("Max Class I HLA MFI", 0.0)
        dsa_ii = ask_float("Max Class II HLA MFI (e.g. DQ)", 3500.0)

    cfdna = ask_float("Donor-derived cell-free DNA dd-cfDNA (%) [threshold 0.12%]", 0.08)
    trough = ask_float("Tacrolimus trough level (ng/mL)", 8.5)
    lvef = ask_float("Current LVEF (%)", 62.0)
    compromise = ask_bool("Hemodynamic compromise or inotrope requirement?")

    return TransplantCaseInput(
        case_id=case_id,
        patient_id=patient_id,
        days_post_transplant=days,
        acr_grade=acr_grade,
        pamr_grade=pamr_grade,
        dsa_positive=dsa_pos,
        dsa_class_i_mfi=dsa_i,
        dsa_class_ii_mfi=dsa_ii,
        dd_cfdna_pct=cfdna,
        trough_level_ng_ml=trough,
        lvef_pct=lvef,
        hemodynamic_compromise=compromise,
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="cardiac-transplant-rejection",
        description="Cardiac Transplant Rejection & Allograft Surveillance Engine (ISHLT / DSA / Biomarkers)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Audit / Evaluate command
    audit_parser = subparsers.add_parser("audit", help="Audit single allograft surveillance case")
    audit_parser.add_argument("--case-id", default="TX-AUDIT-01", help="Case identifier")
    audit_parser.add_argument("--patient-id", default=None, help="Patient MRN / ID")
    audit_parser.add_argument("--days", type=int, default=180, help="Days post-transplant")
    audit_parser.add_argument("--acr", choices=["0R", "1R", "2R", "3R"], default="0R", help="ISHLT ACR Grade")
    audit_parser.add_argument("--pamr", choices=["pAMR 0", "pAMR 1(H+)", "pAMR 1(I+)", "pAMR 1", "pAMR 2", "pAMR 3"], default="pAMR 0", help="ISHLT pAMR Grade")
    audit_parser.add_argument("--dsa-positive", action="store_true", help="DSA positive flag")
    audit_parser.add_argument("--dsa-mfi", type=float, default=0.0, help="Peak DSA Luminex MFI")
    audit_parser.add_argument("--de-novo-dsa", action="store_true", help="De novo DSA emergence")
    audit_parser.add_argument("--dd-cfdna", type=float, default=0.08, help="Donor-derived cell-free DNA (%%)")
    audit_parser.add_argument("--allomap", type=float, default=28.0, help="AlloMap GEP score (0-40)")
    audit_parser.add_argument("--drug", choices=["Tacrolimus", "Cyclosporine"], default="Tacrolimus", help="Primary calcineurin inhibitor")
    audit_parser.add_argument("--trough", type=float, default=8.5, help="Drug trough level (ng/mL)")
    audit_parser.add_argument("--lvef", type=float, default=62.0, help="Current LVEF (%%)")
    audit_parser.add_argument("--baseline-lvef", type=float, default=65.0, help="Baseline LVEF (%%)")
    audit_parser.add_argument("--compromise", action="store_true", help="Hemodynamic compromise present")
    audit_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Interactive surveillance audit wizard")
    interactive_parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch audit cases from CSV")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch_parser.add_argument("-o", "--output", default="tx_rejection_results.csv", help="Output CSV path")

    # Guidelines reference command
    guide_parser = subparsers.add_parser("guidelines", help="Display ISHLT biopsy grading & biomarker thresholds")

    args = parser.parse_args(argv)

    if args.command == "audit":
        inp = TransplantCaseInput(
            case_id=args.case_id,
            patient_id=args.patient_id,
            days_post_transplant=args.days,
            acr_grade=args.acr,
            pamr_grade=args.pamr,
            dsa_positive=args.dsa_positive or (args.dsa_mfi > 1000.0),
            dsa_class_ii_mfi=args.dsa_mfi,
            de_novo_dsa=args.de_novo_dsa,
            dd_cfdna_pct=args.dd_cfdna,
            allomap_score=args.allomap,
            primary_immunosuppressant=args.drug,
            trough_level_ng_ml=args.trough,
            lvef_pct=args.lvef,
            baseline_lvef_pct=args.baseline_lvef,
            hemodynamic_compromise=args.compromise,
        )
        report = evaluate_transplant_rejection(inp)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_table(report.to_dict()))
        return 0

    elif args.command == "interactive":
        inp = interactive_wizard()
        report = evaluate_transplant_rejection(inp)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print(format_report_table(report.to_dict()))
        return 0

    elif args.command == "batch":
        count = process_batch(args.input, args.output)
        print(f"Processed {count} cardiac transplant records into '{args.output}'.")
        return 0

    elif args.command == "guidelines":
        print("=" * 76)
        print("  ISHLT 2004 & 2013 HEART ALLOGRAFT REJECTION CLASSIFICATION MATRIX")
        print("=" * 76)
        print("  Acute Cellular Rejection (ACR):")
        print("    - Grade 0R : No rejection")
        print("    - Grade 1R : Mild (interstitial infiltrate, <= 1 focus myocyte damage)")
        print("    - Grade 2R : Moderate (>= 2 foci myocyte damage) -> Pulse Steroids")
        print("    - Grade 3R : Severe (diffuse infiltrate, necrosis, edema) -> Pulse + rATG")
        print("  Pathologic Antibody-Mediated Rejection (pAMR):")
        print("    - pAMR 0   : Negative")
        print("    - pAMR 1   : Suspicious (Histologic H+ or Immunopathologic I+ C4d)")
        print("    - pAMR 2   : Active AMR (Concurrent H+ and I+) -> Plasmapheresis + IVIG")
        print("    - pAMR 3   : Severe AMR (Capillary destruction, microthrombi) -> PLEX + IVIG + Rituximab")
        print("  Non-Invasive Surveillance Biomarkers:")
        print("    - dd-cfDNA : < 0.12% normal, >= 0.20% high allograft injury probability")
        print("    - AlloMap  : < 34 low risk of moderate/severe ACR (>= 55 days post-tx)")
        print("=" * 76)
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
