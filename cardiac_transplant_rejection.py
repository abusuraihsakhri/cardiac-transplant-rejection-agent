#!/usr/bin/env python3
"""
Cardiac Transplant Rejection & Allograft Surveillance Engine
============================================================
Comprehensive post-heart transplant rejection surveillance decision engine
integrating ISHLT 2004 Acute Cellular Rejection (0R-3R), ISHLT 2013 Pathologic
Antibody-Mediated Rejection (pAMR 0-3), Donor-Specific Anti-HLA Antibodies (DSA MFI),
Donor-Derived Cell-Free DNA (dd-cfDNA %), Gene Expression Profiling (AlloMap),
and Therapeutic Drug Monitoring (Tacrolimus / Cyclosporine / MMF).

Standards & Guidelines:
  - ISHLT 2004 Revised Heart Biopsy Grading
  - ISHLT 2013 Working Formulation for Pathologic Diagnosis of AMR
  - Consensus Guidelines on Non-Invasive Allograft Surveillance (dd-cfDNA & GEP)
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class ACRGrade(str, Enum):
    GRADE_0R = "0R"          # None
    GRADE_1R = "1R"          # Mild (interstitial / perivascular infiltrate, <= 1 focus myocyte damage)
    GRADE_2R = "2R"          # Moderate (>= 2 foci with myocyte damage)
    GRADE_3R = "3R"          # Severe (diffuse infiltrate, extensive myocyte necrosis, edema, hemorrhage)


class pAMRGrade(str, Enum):
    pAMR_0 = "pAMR 0"        # Negative for both histologic and immunopathologic
    pAMR_1_H = "pAMR 1(H+)"  # Histopathologic AMR alone
    pAMR_1_I = "pAMR 1(I+)"  # Immunopathologic AMR alone (positive C4d / C3d)
    pAMR_2 = "pAMR 2"        # Both histopathologic and immunopathologic AMR
    pAMR_3 = "pAMR 3"        # Severe AMR (capillary destruction, microthrombi)


class OverallRejectionTier(str, Enum):
    QUIESCENT = "Quiescent / Normal Allograft"
    MILD_SUSPICION = "Mild Rejection / Surveillance Watch"
    MODERATE_REJECTION = "Moderate Rejection (Active Treatment Indicated)"
    SEVERE_CRITICAL = "Severe Rejection / Hemodynamic Compromise"


class ImmunosuppressantDrug(str, Enum):
    TACROLIMUS = "Tacrolimus"
    CYCLOSPORINE = "Cyclosporine"
    SIROLIMUS = "Sirolimus"
    EVEROLIMUS = "Everolimus"


@dataclass
class TransplantCaseInput:
    """Clinical, biopsy, serologic, and biomarker profile for transplant surveillance."""
    case_id: str = "TX-CASE-001"
    patient_id: Optional[str] = None
    days_post_transplant: int = 180
    
    # Biopsy ISHLT Grading
    acr_grade: Union[ACRGrade, str] = ACRGrade.GRADE_0R
    pamr_grade: Union[pAMRGrade, str] = pAMRGrade.pAMR_0
    c4d_positive: bool = False
    cd68_positive: bool = False
    
    # Donor-Specific Antibodies (DSA)
    dsa_positive: bool = False
    dsa_class_i_mfi: float = 0.0          # Max Class I HLA MFI
    dsa_class_ii_mfi: float = 0.0         # Max Class II HLA MFI (e.g. DQ, DR)
    de_novo_dsa: bool = False
    
    # Non-Invasive Surveillance Biomarkers
    dd_cfdna_pct: Optional[float] = 0.08   # % donor-derived cell-free DNA (threshold 0.12 - 0.20%)
    allomap_score: Optional[float] = 28.0  # GEP score 0 - 40 (threshold 34 at >= 6 mo)
    
    # Therapeutic Drug Monitoring (TDM)
    primary_immunosuppressant: Union[ImmunosuppressantDrug, str] = ImmunosuppressantDrug.TACROLIMUS
    trough_level_ng_ml: float = 8.5       # Tacrolimus (ng/mL) or Cyclosporine (ng/mL)
    mmf_mpa_trough_ug_ml: float = 2.5     # Mycophenolic acid (ug/mL, target 1.5 - 4.0)
    
    # Hemodynamics & Echocardiography
    lvef_pct: float = 62.0                # Current LVEF (%)
    baseline_lvef_pct: float = 65.0       # Baseline post-transplant LVEF
    hemodynamic_compromise: bool = False  # Cardiogenic shock, hypotension, inotrope requirement
    cav_grade: int = 0                    # ISHLT CAV 0, 1, 2, 3


@dataclass
class TransplantRejectionReport:
    """Consolidated allograft rejection surveillance dossier and treatment plan."""
    case_id: str
    patient_id: Optional[str]
    days_post_transplant: int
    rejection_risk_score: float           # 0 - 100
    overall_rejection_tier: str
    acr_status: str
    pamr_status: str
    dsa_status: str
    biomarker_status: str
    tdm_status: str
    graft_function_status: str
    treatment_protocol: List[str] = field(default_factory=list)
    monitoring_recommendations: List[str] = field(default_factory=list)
    critical_alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_acr(grade: Union[ACRGrade, str]) -> str:
    g = grade.value if isinstance(grade, ACRGrade) else str(grade).upper().strip()
    if g in ("0", "0R", "NONE", "GRADE_0R"):
        return "0R"
    elif g in ("1", "1R", "1A", "1B", "GRADE_1R", "1R_MILD"):
        return "1R"
    elif g in ("2", "2R", "GRADE_2R", "2R_MODERATE"):
        return "2R"
    elif g in ("3", "3R", "3A", "3B", "GRADE_3R", "3R_SEVERE"):
        return "3R"
    return "0R"


def normalize_pamr(grade: Union[pAMRGrade, str]) -> str:
    g = grade.value if isinstance(grade, pAMRGrade) else str(grade).upper().strip()
    if "0" in g:
        return "pAMR 0"
    elif "1(H" in g or "1-H" in g:
        return "pAMR 1(H+)"
    elif "1(I" in g or "1-I" in g:
        return "pAMR 1(I+)"
    elif "1" in g:
        return "pAMR 1"
    elif "2" in g:
        return "pAMR 2"
    elif "3" in g:
        return "pAMR 3"
    return "pAMR 0"


def evaluate_transplant_rejection(inp: TransplantCaseInput) -> TransplantRejectionReport:
    """
    Evaluates heart allograft surveillance status across cellular, humoral, biomarker, and TDM domains.
    """
    # Validations
    if inp.days_post_transplant < 0:
        raise ValueError(f"Days post-transplant ({inp.days_post_transplant}) cannot be negative.")
    if inp.lvef_pct < 10.0 or inp.lvef_pct > 90.0:
        raise ValueError(f"LVEF ({inp.lvef_pct}%) is outside physiological limits [10, 90].")
    if inp.trough_level_ng_ml < 0:
        raise ValueError("Immunosuppressant trough level cannot be negative.")

    score = 0.0
    alerts: List[str] = []
    protocol: List[str] = []
    monitoring: List[str] = []

    # 1. Acute Cellular Rejection (ACR) Scoring
    acr_norm = normalize_acr(inp.acr_grade)
    if acr_norm == "0R":
        acr_desc = "0R (No cellular rejection)"
    elif acr_norm == "1R":
        score += 15.0
        acr_desc = "1R (Mild cellular rejection - interstitial infiltrate without significant necrosis)"
    elif acr_norm == "2R":
        score += 45.0
        acr_desc = "2R (Moderate cellular rejection - multiple foci with myocyte damage)"
    else:  # 3R
        score += 75.0
        acr_desc = "3R (Severe cellular rejection - diffuse polymorphous infiltrate with myocyte necrosis/hemorrhage)"

    # 2. Antibody-Mediated Rejection (pAMR) Scoring
    pamr_norm = normalize_pamr(inp.pamr_grade)
    if pamr_norm == "pAMR 0":
        pamr_desc = "pAMR 0 (Negative for histologic and immunopathologic AMR)"
    elif pamr_norm in ("pAMR 1(H+)", "pAMR 1(I+)", "pAMR 1"):
        score += 20.0
        pamr_desc = f"{pamr_norm} (Suspicious / isolated histologic or immunopathologic AMR)"
    elif pamr_norm == "pAMR 2":
        score += 55.0
        pamr_desc = "pAMR 2 (Definite active AMR - concurrent histologic and immunopathologic features)"
    else:  # pAMR 3
        score += 85.0
        pamr_desc = "pAMR 3 (Severe AMR with capillary destruction and microvascular injury)"

    # 3. Donor-Specific Antibodies (DSA)
    max_mfi = max(inp.dsa_class_i_mfi, inp.dsa_class_ii_mfi)
    if inp.dsa_positive or max_mfi > 1000.0:
        if max_mfi >= 10000.0:
            score += 30.0
            dsa_desc = f"Ultra-High DSA Titers (Peak MFI: {max_mfi:.0f}) - High AMR risk"
            alerts.append(f"CRITICAL: Ultra-high donor-specific antibody MFI ({max_mfi:.0f}) detected.")
        elif max_mfi >= 5000.0:
            score += 20.0
            dsa_desc = f"Strong Positive DSA (Peak MFI: {max_mfi:.0f})"
            alerts.append(f"WARNING: Strong DSA MFI ({max_mfi:.0f}) warrants intensified humoral surveillance.")
        else:
            score += 10.0
            dsa_desc = f"Low/Moderate DSA (Peak MFI: {max_mfi:.0f})"
        
        if inp.de_novo_dsa:
            score += 10.0
            alerts.append("WARNING: De novo DSA development indicates heightened graft vulnerability.")
    else:
        dsa_desc = "DSA Negative (MFI < 1000)"

    # 4. Non-Invasive Surveillance Biomarkers (dd-cfDNA & AlloMap)
    bm_items: List[str] = []
    if inp.dd_cfdna_pct is not None:
        if inp.dd_cfdna_pct >= 0.20:
            score += 25.0
            bm_items.append(f"dd-cfDNA markedly elevated ({inp.dd_cfdna_pct:.2f}% >= 0.20% cutoff)")
            alerts.append(f"CRITICAL: High donor-derived cell-free DNA ({inp.dd_cfdna_pct:.2f}%) indicates active allograft injury.")
        elif inp.dd_cfdna_pct >= 0.12:
            score += 12.0
            bm_items.append(f"dd-cfDNA borderline elevated ({inp.dd_cfdna_pct:.2f}%)")
        else:
            bm_items.append(f"dd-cfDNA normal ({inp.dd_cfdna_pct:.2f}% < 0.12%)")

    if inp.allomap_score is not None and inp.days_post_transplant >= 55:
        if inp.allomap_score >= 34.0:
            score += 15.0
            bm_items.append(f"AlloMap GEP elevated ({inp.allomap_score:.1f} >= 34 cutoff)")
            alerts.append(f"WARNING: Elevated AlloMap score ({inp.allomap_score:.1f}) indicates cellular activation.")
        else:
            bm_items.append(f"AlloMap GEP low risk ({inp.allomap_score:.1f} < 34)")

    bm_desc = "; ".join(bm_items) if bm_items else "Biomarkers not performed"

    # 5. Therapeutic Drug Monitoring (TDM)
    drug_name = inp.primary_immunosuppressant.value if isinstance(inp.primary_immunosuppressant, ImmunosuppressantDrug) else str(inp.primary_immunosuppressant)
    # Tacrolimus target windows by time post-transplant
    if "tacrolimus" in drug_name.lower():
        if inp.days_post_transplant <= 90:
            target_range = (8.0, 12.0)
        elif inp.days_post_transplant <= 365:
            target_range = (6.0, 10.0)
        else:
            target_range = (5.0, 8.0)
    else:  # Cyclosporine default
        if inp.days_post_transplant <= 90:
            target_range = (250.0, 350.0)
        else:
            target_range = (150.0, 250.0)

    if inp.trough_level_ng_ml < target_range[0]:
        score += 10.0
        tdm_desc = f"Subtherapeutic {drug_name} Trough ({inp.trough_level_ng_ml:.1f} ng/mL vs Target {target_range[0]}-{target_range[1]})"
        alerts.append(f"WARNING: Subtherapeutic immunosuppression trough elevates rejection susceptibility.")
    elif inp.trough_level_ng_ml > target_range[1] * 1.3:
        tdm_desc = f"Supratherapeutic {drug_name} Trough ({inp.trough_level_ng_ml:.1f} ng/mL) - Nephrotoxicity / Infection Risk"
        alerts.append(f"ADVISORY: Supratherapeutic trough requires dose reduction to avert calcineurin inhibitor nephrotoxicity.")
    else:
        tdm_desc = f"Therapeutic {drug_name} Trough ({inp.trough_level_ng_ml:.1f} ng/mL within Target {target_range[0]}-{target_range[1]})"

    # 6. Graft Hemodynamics
    lvef_drop = inp.baseline_lvef_pct - inp.lvef_pct
    if inp.hemodynamic_compromise or lvef_drop >= 15.0 or inp.lvef_pct < 40.0:
        score += 35.0
        graft_desc = f"Severe Hemodynamic Dysfunction (LVEF {inp.lvef_pct:.0f}%, drop {lvef_drop:+.0f}%)"
        alerts.append("CRITICAL: Hemodynamic compromise or sharp LVEF deterioration detected.")
    elif lvef_drop >= 10.0 or inp.lvef_pct < 50.0:
        score += 15.0
        graft_desc = f"Mild/Moderate LVEF Decline (LVEF {inp.lvef_pct:.0f}%, drop {lvef_drop:+.0f}%)"
    else:
        graft_desc = f"Preserved Graft Function (LVEF {inp.lvef_pct:.0f}%)"

    score = min(100.0, score)

    # 7. Rejection Tier & Action Plan
    if score >= 70.0 or inp.hemodynamic_compromise or acr_norm == "3R" or pamr_norm == "pAMR 3":
        tier = OverallRejectionTier.SEVERE_CRITICAL
        protocol.append("Immediate inpatient cardiac ICU / telemetry admission.")
        protocol.append("High-dose IV Methylprednisolone pulse: 500-1000 mg IV daily x 3 days.")
        if "3R" in acr_norm or acr_norm == "2R":
            protocol.append("Initiate antithymocyte globulin (rATG / Thymoglobulin 1.5 mg/kg/day) for severe/refractory ACR.")
        if pamr_norm in ("pAMR 2", "pAMR 3") or max_mfi >= 5000.0:
            protocol.append("Initiate Plasma Exchange (Plasmapheresis 5-7 sessions) + IVIG (1-2 g/kg).")
            protocol.append("Consider Rituximab (anti-CD20) or Bortezomib (proteasome inhibitor) for plasma cell elimination.")
            protocol.append("Consider Eculizumab (C5 complement inhibitor) if microvascular capillary destruction is evident.")
        monitoring.append("Daily bedside echocardiography and serial cardiac biomarker tracking.")
        monitoring.append("Repeat endomyocardial biopsy in 7-14 days.")

    elif score >= 40.0 or acr_norm == "2R" or pamr_norm == "pAMR 2":
        tier = OverallRejectionTier.MODERATE_REJECTION
        if acr_norm == "2R":
            protocol.append("Intravenous Methylprednisolone pulse: 500-1000 mg IV daily x 3 days followed by oral steroid taper.")
        if pamr_norm == "pAMR 2":
            protocol.append("Plasmapheresis + Intravenous Immunoglobulin (IVIG) protocol for active AMR.")
        protocol.append("Optimize maintenance immunosuppression troughs (target high-therapeutic range).")
        monitoring.append("Repeat endomyocardial biopsy in 2-3 weeks to confirm histologic clearance.")
        monitoring.append("Weekly echocardiogram and DSA MFI trend analysis.")

    elif score >= 20.0 or acr_norm == "1R" or pamr_norm in ("pAMR 1(H+)", "pAMR 1(I+)", "pAMR 1"):
        tier = OverallRejectionTier.MILD_SUSPICION
        protocol.append("Outpatient management without pulse steroids if asymptomatic with preserved LVEF.")
        protocol.append("Adjust and optimize maintenance calcineurin inhibitor and antimetabolite dosing.")
        monitoring.append("Close clinical follow-up; repeat non-invasive dd-cfDNA / GEP in 2-4 weeks.")
        monitoring.append("Consider repeat biopsy in 4 weeks if clinical or biomarker concern persists.")

    else:
        tier = OverallRejectionTier.QUIESCENT
        protocol.append("Continue standard maintenance immunosuppression.")
        monitoring.append("Routine protocol surveillance (quarterly clinic visit, scheduled dd-cfDNA / AlloMap / echo).")

    return TransplantRejectionReport(
        case_id=inp.case_id,
        patient_id=inp.patient_id,
        days_post_transplant=inp.days_post_transplant,
        rejection_risk_score=round(score, 1),
        overall_rejection_tier=tier.value,
        acr_status=acr_desc,
        pamr_status=pamr_desc,
        dsa_status=dsa_desc,
        biomarker_status=bm_desc,
        tdm_status=tdm_desc,
        graft_function_status=graft_desc,
        treatment_protocol=protocol,
        monitoring_recommendations=monitoring,
        critical_alerts=alerts,
    )


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Top-level interface compatible with generic wrappers and batch runners.
    """
    def _float(key: str, default: float) -> float:
        val = kwargs.get(key)
        if val is None:
            return default
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _bool(key: str, default: bool = False) -> bool:
        val = kwargs.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val != 0
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes", "y", "t", "positive", "+")
        return default

    def _str(key: str, default: str) -> str:
        val = kwargs.get(key)
        return str(val) if val is not None else default

    case_id = _str("case_id", _str("id", _str("study_id", "TX-001")))
    patient_id = kwargs.get("patient_id") or kwargs.get("Patient")
    days = int(_float("days_post_transplant", _float("days", 180.0)))
    
    acr = _str("acr_grade", _str("acr", "0R"))
    pamr = _str("pamr_grade", _str("pamr", "pAMR 0"))
    c4d = _bool("c4d_positive", False)
    cd68 = _bool("cd68_positive", False)
    
    dsa_pos = _bool("dsa_positive", False)
    dsa_i = _float("dsa_class_i_mfi", 0.0)
    dsa_ii = _float("dsa_class_ii_mfi", 0.0)
    de_novo = _bool("de_novo_dsa", False)

    cfdna_raw = kwargs.get("dd_cfdna_pct")
    cfdna = float(cfdna_raw) if cfdna_raw is not None else 0.08

    allomap_raw = kwargs.get("allomap_score")
    allomap = float(allomap_raw) if allomap_raw is not None else 28.0

    drug = _str("primary_immunosuppressant", "Tacrolimus")
    trough = _float("trough_level_ng_ml", _float("trough", _float("primary_metric", 8.5)))
    mmf = _float("mmf_mpa_trough_ug_ml", 2.5)

    lvef = _float("lvef_pct", _float("lvef", 62.0))
    base_lvef = _float("baseline_lvef_pct", 65.0)
    compromise = _bool("hemodynamic_compromise", _bool("critical_flag", False))
    cav = int(_float("cav_grade", 0.0))

    inp = TransplantCaseInput(
        case_id=case_id,
        patient_id=str(patient_id) if patient_id is not None else None,
        days_post_transplant=days,
        acr_grade=acr,
        pamr_grade=pamr,
        c4d_positive=c4d,
        cd68_positive=cd68,
        dsa_positive=dsa_pos,
        dsa_class_i_mfi=dsa_i,
        dsa_class_ii_mfi=dsa_ii,
        de_novo_dsa=de_novo,
        dd_cfdna_pct=cfdna,
        allomap_score=allomap,
        primary_immunosuppressant=drug,
        trough_level_ng_ml=trough,
        mmf_mpa_trough_ug_ml=mmf,
        lvef_pct=lvef,
        baseline_lvef_pct=base_lvef,
        hemodynamic_compromise=compromise,
        cav_grade=cav,
    )

    report = evaluate_transplant_rejection(inp)
    res = report.to_dict()
    res["tool"] = "cardiac-transplant-rejection-agent"
    res["score"] = report.rejection_risk_score
    res["classification"] = report.overall_rejection_tier
    res["clinical_recommendation"] = "; ".join(report.treatment_protocol)
    return res


def process_batch(input_csv: str, output_csv: str) -> int:
    """
    Batch process cardiac transplant surveillance registry cases from CSV.
    """
    with open(input_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    out_fields = fieldnames + [
        "rejection_risk_score",
        "overall_rejection_tier",
        "acr_status",
        "pamr_status",
        "dsa_status",
        "graft_function_status",
        "treatment_protocol",
    ]
    dedup_fields = []
    for fn in out_fields:
        if fn not in dedup_fields:
            dedup_fields.append(fn)

    out_rows = []
    for r in rows:
        calc_res = calculate_metrics(**r)
        row_dict = dict(r)
        row_dict["rejection_risk_score"] = calc_res["rejection_risk_score"]
        row_dict["overall_rejection_tier"] = calc_res["overall_rejection_tier"]
        row_dict["acr_status"] = calc_res["acr_status"]
        row_dict["pamr_status"] = calc_res["pamr_status"]
        row_dict["dsa_status"] = calc_res["dsa_status"]
        row_dict["graft_function_status"] = calc_res["graft_function_status"]
        row_dict["treatment_protocol"] = "; ".join(calc_res["treatment_protocol"])
        out_rows.append(row_dict)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dedup_fields)
        writer.writeheader()
        writer.writerows(out_rows)

    return len(out_rows)
