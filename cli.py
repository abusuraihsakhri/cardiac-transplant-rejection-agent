#!/usr/bin/env python3
"""Command-line interface for the cardiac transplant surveillance heuristic."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from cardiac_transplant_rejection import TransplantCaseInput, evaluate_transplant_rejection, process_batch


def format_report_table(report: dict) -> str:
    """Format a surveillance report for terminal display."""
    lines = [
        "=" * 76,
        "  HEART ALLOGRAFT SURVEILLANCE — RESEARCH / EDUCATIONAL HEURISTIC",
        "=" * 76,
        f"  Case ID               : {report['case_id']}",
        f"  Patient ID            : {report.get('patient_id') or 'N/A'}",
        f"  Post-transplant time  : Day {report['days_post_transplant']}",
        f"  Heuristic score       : {report['rejection_risk_score']:.1f} / 100",
        f"  Review tier           : {report['overall_rejection_tier']}",
        "-" * 76,
        f"  ACR                    : {report['acr_status']}",
        f"  pAMR                   : {report['pamr_status']}",
        f"  DSA                    : {report['dsa_status']}",
        f"  Biomarkers             : {report['biomarker_status']}",
        f"  Immunosuppression      : {report['tdm_status']}",
        f"  Graft function         : {report['graft_function_status']}",
        "-" * 76,
        "  REVIEW ACTIONS:",
    ]
    for step in report.get("treatment_protocol", []):
        lines.append(f"    - {step}")
    if report.get("monitoring_recommendations"):
        lines += ["-" * 76, "  MONITORING / CORRELATION:"]
        lines += [f"    - {item}" for item in report["monitoring_recommendations"]]
    if report.get("critical_alerts"):
        lines += ["-" * 76, "  FLAGS:"]
        lines += [f"    ! {item}" for item in report["critical_alerts"]]
    if report.get("limitations"):
        lines += ["-" * 76, "  LIMITATIONS:"]
        lines += [f"    - {item}" for item in report["limitations"]]
    lines += ["=" * 76, "  Not validated for diagnosis, treatment selection, or patient-specific care."]
    return "\n".join(lines)


def _ask_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    return default if not raw else int(raw)


def _ask_float(prompt: str, default: float) -> float:
    raw = input(f"{prompt} [{default}]: ").strip()
    return default if not raw else float(raw)


def _ask_optional_float(prompt: str) -> Optional[float]:
    raw = input(f"{prompt} [blank = not supplied]: ").strip()
    return None if not raw else float(raw)


def _ask_bool(prompt: str) -> bool:
    raw = input(f"{prompt} (y/n): ").strip().lower()
    if raw in {"y", "yes", "true", "1"}:
        return True
    if raw in {"n", "no", "false", "0", ""}:
        return False
    raise ValueError(f"Expected yes/no for: {prompt}")


def interactive_wizard() -> TransplantCaseInput:
    """Collect a compact surveillance case interactively."""
    print("\n--- Cardiac Transplant Surveillance Heuristic ---")
    case_id = input("Case ID [TX-SURV-01]: ").strip() or "TX-SURV-01"
    patient_id = input("Patient ID (optional): ").strip() or None
    days = _ask_int("Days post-transplant", 180)

    print("\nACR grade: [1] 0R  [2] 1R  [3] 2R  [4] 3R")
    acr = {"1": "0R", "2": "1R", "3": "2R", "4": "3R"}.get(input("Select [1]: ").strip() or "1")
    if acr is None:
        raise ValueError("Invalid ACR selection")

    print("pAMR grade: [1] 0  [2] 1(H+)  [3] 1(I+)  [4] 2  [5] 3")
    pamr = {
        "1": "pAMR 0", "2": "pAMR 1(H+)", "3": "pAMR 1(I+)", "4": "pAMR 2", "5": "pAMR 3"
    }.get(input("Select [1]: ").strip() or "1")
    if pamr is None:
        raise ValueError("Invalid pAMR selection")

    dsa_positive = _ask_bool("DSA reported positive?")
    dsa_mfi = _ask_float("Peak DSA MFI (reporting only)", 0.0) if dsa_positive else 0.0
    dd_cfdna = _ask_float("dd-cfDNA (%)", 0.08)
    allomap = _ask_float("GEP / AlloMap score", 28.0)
    trough = _ask_float("Immunosuppressant trough (ng/mL)", 8.5)
    trough_low = _ask_optional_float("Patient/center trough target low")
    trough_high = _ask_optional_float("Patient/center trough target high")
    lvef = _ask_float("Current LVEF (%)", 62.0)
    baseline_lvef = _ask_float("Baseline LVEF (%)", 65.0)
    compromise = _ask_bool("Hemodynamic compromise present?")

    return TransplantCaseInput(
        case_id=case_id,
        patient_id=patient_id,
        days_post_transplant=days,
        acr_grade=acr,
        pamr_grade=pamr,
        dsa_positive=dsa_positive,
        dsa_class_ii_mfi=dsa_mfi,
        dd_cfdna_pct=dd_cfdna,
        allomap_score=allomap,
        trough_level_ng_ml=trough,
        trough_target_low_ng_ml=trough_low,
        trough_target_high_ng_ml=trough_high,
        lvef_pct=lvef,
        baseline_lvef_pct=baseline_lvef,
        hemodynamic_compromise=compromise,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cardiac-transplant-rejection",
        description="Research/educational heart-allograft surveillance heuristic.",
    )
    sub = parser.add_subparsers(dest="command")

    audit = sub.add_parser("audit", help="Evaluate one case")
    audit.add_argument("--case-id", default="TX-AUDIT-01")
    audit.add_argument("--patient-id", default=None)
    audit.add_argument("--days", type=int, default=180)
    audit.add_argument("--acr", default="0R")
    audit.add_argument("--pamr", default="pAMR 0")
    audit.add_argument("--dsa-positive", action="store_true")
    audit.add_argument("--dsa-mfi", type=float, default=0.0)
    audit.add_argument("--de-novo-dsa", action="store_true")
    audit.add_argument("--dd-cfdna", type=float, default=0.08)
    audit.add_argument("--allomap", type=float, default=28.0)
    audit.add_argument("--drug", default="Tacrolimus")
    audit.add_argument("--trough", type=float, default=8.5)
    audit.add_argument("--trough-low", type=float, default=None)
    audit.add_argument("--trough-high", type=float, default=None)
    audit.add_argument("--lvef", type=float, default=62.0)
    audit.add_argument("--baseline-lvef", type=float, default=65.0)
    audit.add_argument("--compromise", action="store_true")
    audit.add_argument("--json", action="store_true")

    interactive = sub.add_parser("interactive", help="Interactive case entry")
    interactive.add_argument("--json", action="store_true")

    batch = sub.add_parser("batch", help="Process CSV records")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="tx_rejection_results.csv")

    sub.add_parser("guidelines", help="Show classification references and scope notes")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "audit":
            case = TransplantCaseInput(
                case_id=args.case_id,
                patient_id=args.patient_id,
                days_post_transplant=args.days,
                acr_grade=args.acr,
                pamr_grade=args.pamr,
                dsa_positive=args.dsa_positive,
                dsa_class_ii_mfi=args.dsa_mfi,
                de_novo_dsa=args.de_novo_dsa,
                dd_cfdna_pct=args.dd_cfdna,
                allomap_score=args.allomap,
                primary_immunosuppressant=args.drug,
                trough_level_ng_ml=args.trough,
                trough_target_low_ng_ml=args.trough_low,
                trough_target_high_ng_ml=args.trough_high,
                lvef_pct=args.lvef,
                baseline_lvef_pct=args.baseline_lvef,
                hemodynamic_compromise=args.compromise,
            )
            report = evaluate_transplant_rejection(case).to_dict()
            print(json.dumps(report, indent=2) if args.json else format_report_table(report))
            return 0

        if args.command == "interactive":
            report = evaluate_transplant_rejection(interactive_wizard()).to_dict()
            print(json.dumps(report, indent=2) if args.json else format_report_table(report))
            return 0

        if args.command == "batch":
            count = process_batch(args.input, args.output)
            print(f"Processed {count} records -> {args.output}")
            return 0

        if args.command == "guidelines":
            print("ISHLT classification scope used by this tool")
            print("- ACR: revised grades 0R, 1R, 2R, 3R")
            print("- pAMR: pAMR 0, pAMR 1(H+), pAMR 1(I+), pAMR 2, pAMR 3")
            print("- GEP is contextualized by time post-transplant; no single value diagnoses rejection.")
            print("- DSA MFI, dd-cfDNA, and immunosuppressant targets are assay/center/patient specific.")
            print("- The composite 0-100 score is an unvalidated research heuristic, not a guideline score.")
            return 0

        parser.print_help()
        return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
