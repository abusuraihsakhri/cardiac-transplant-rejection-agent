#!/usr/bin/env python3
"""Heart-transplant rejection surveillance helpers.

The module implements a transparent, dependency-free *heuristic* synthesis of
ISHLT biopsy grades and commonly used post-transplant surveillance variables.
It is intended for education, research prototyping, and reproducible data
processing. It is not a validated clinical decision rule and does not prescribe
patient-specific treatment.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ACRGrade(str, Enum):
    GRADE_0R = "0R"
    GRADE_1R = "1R"
    GRADE_2R = "2R"
    GRADE_3R = "3R"


class pAMRGrade(str, Enum):
    pAMR_0 = "pAMR 0"
    pAMR_1_H = "pAMR 1(H+)"
    pAMR_1_I = "pAMR 1(I+)"
    pAMR_2 = "pAMR 2"
    pAMR_3 = "pAMR 3"


class OverallRejectionTier(str, Enum):
    QUIESCENT = "Low concern by heuristic screen"
    MILD_SUSPICION = "Increased concern — correlate clinically"
    MODERATE_REJECTION = "High concern — prompt transplant-team review"
    SEVERE_CRITICAL = "Very high concern — urgent transplant-team review"


class ImmunosuppressantDrug(str, Enum):
    TACROLIMUS = "Tacrolimus"
    CYCLOSPORINE = "Cyclosporine"
    SIROLIMUS = "Sirolimus"
    EVEROLIMUS = "Everolimus"


@dataclass
class TransplantCaseInput:
    """Clinical, pathology, serologic, and biomarker surveillance inputs."""

    case_id: str = "TX-CASE-001"
    patient_id: Optional[str] = None
    days_post_transplant: int = 180

    acr_grade: Union[ACRGrade, str] = ACRGrade.GRADE_0R
    pamr_grade: Union[pAMRGrade, str] = pAMRGrade.pAMR_0
    c4d_positive: bool = False
    cd68_positive: bool = False

    dsa_positive: bool = False
    dsa_class_i_mfi: float = 0.0
    dsa_class_ii_mfi: float = 0.0
    de_novo_dsa: bool = False

    dd_cfdna_pct: Optional[float] = 0.08
    allomap_score: Optional[float] = 28.0

    primary_immunosuppressant: Union[ImmunosuppressantDrug, str] = ImmunosuppressantDrug.TACROLIMUS
    trough_level_ng_ml: float = 8.5
    trough_target_low_ng_ml: Optional[float] = None
    trough_target_high_ng_ml: Optional[float] = None
    mmf_mpa_trough_ug_ml: float = 2.5

    lvef_pct: float = 62.0
    baseline_lvef_pct: float = 65.0
    hemodynamic_compromise: bool = False
    cav_grade: int = 0


@dataclass
class TransplantRejectionReport:
    """Consolidated surveillance summary from the heuristic engine."""

    case_id: str
    patient_id: Optional[str]
    days_post_transplant: int
    rejection_risk_score: float
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
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_acr(grade: Union[ACRGrade, str]) -> str:
    """Normalize revised ISHLT ACR grade notation.

    Legacy 1990 grades are accepted only when unambiguous aliases are supplied.
    Bare numeric grades are treated as revised-grade shorthand, not as 1990
    nomenclature.
    """

    g = (grade.value if isinstance(grade, ACRGrade) else str(grade)).upper().strip()
    aliases = {
        "0": "0R",
        "0R": "0R",
        "NONE": "0R",
        "GRADE_0R": "0R",
        "1": "1R",
        "1R": "1R",
        "GRADE_1R": "1R",
        "1R_MILD": "1R",
        "2": "2R",
        "2R": "2R",
        "GRADE_2R": "2R",
        "2R_MODERATE": "2R",
        "3": "3R",
        "3R": "3R",
        "GRADE_3R": "3R",
        "3R_SEVERE": "3R",
        "1990 1A": "1R",
        "1990 1B": "1R",
        "1990 2": "1R",
        "1990 3A": "2R",
        "1990 3B": "3R",
        "1990 4": "3R",
    }
    try:
        return aliases[g]
    except KeyError as exc:
        raise ValueError(f"Unsupported ACR grade: {grade!r}. Use 0R, 1R, 2R, or 3R.") from exc


def normalize_pamr(grade: Union[pAMRGrade, str]) -> str:
    """Normalize ISHLT pAMR notation and reject unknown values."""

    g = (grade.value if isinstance(grade, pAMRGrade) else str(grade)).upper().strip()
    compact = g.replace(" ", "")
    aliases = {
        "PAMR0": "pAMR 0",
        "0": "pAMR 0",
        "PAMR1(H+)": "pAMR 1(H+)",
        "PAMR1-H": "pAMR 1(H+)",
        "PAMR1H": "pAMR 1(H+)",
        "PAMR1(I+)": "pAMR 1(I+)",
        "PAMR1-I": "pAMR 1(I+)",
        "PAMR1I": "pAMR 1(I+)",
        "PAMR1": "pAMR 1",
        "1": "pAMR 1",
        "PAMR2": "pAMR 2",
        "2": "pAMR 2",
        "PAMR3": "pAMR 3",
        "3": "pAMR 3",
    }
    try:
        return aliases[compact]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported pAMR grade: {grade!r}. Use pAMR 0, pAMR 1(H+), "
            "pAMR 1(I+), pAMR 2, or pAMR 3."
        ) from exc


def _validate_range(name: str, value: float, low: float, high: float) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} ({value}) must be between {low} and {high}.")


def _validate_input(inp: TransplantCaseInput) -> None:
    if inp.days_post_transplant < 0:
        raise ValueError("days_post_transplant cannot be negative.")
    _validate_range("lvef_pct", float(inp.lvef_pct), 0.0, 100.0)
    _validate_range("baseline_lvef_pct", float(inp.baseline_lvef_pct), 0.0, 100.0)
    if inp.trough_level_ng_ml < 0:
        raise ValueError("trough_level_ng_ml cannot be negative.")
    if inp.mmf_mpa_trough_ug_ml < 0:
        raise ValueError("mmf_mpa_trough_ug_ml cannot be negative.")
    if inp.dsa_class_i_mfi < 0 or inp.dsa_class_ii_mfi < 0:
        raise ValueError("DSA MFI values cannot be negative.")
    if inp.dd_cfdna_pct is not None:
        _validate_range("dd_cfdna_pct", float(inp.dd_cfdna_pct), 0.0, 100.0)
    if inp.allomap_score is not None:
        _validate_range("allomap_score", float(inp.allomap_score), 0.0, 40.0)
    if inp.cav_grade not in (0, 1, 2, 3):
        raise ValueError("cav_grade must be one of 0, 1, 2, or 3.")

    low = inp.trough_target_low_ng_ml
    high = inp.trough_target_high_ng_ml
    if (low is None) != (high is None):
        raise ValueError("Provide both trough target bounds or neither.")
    if low is not None and high is not None:
        if low < 0 or high < 0 or low >= high:
            raise ValueError("Trough target bounds must be non-negative with low < high.")


def evaluate_transplant_rejection(inp: TransplantCaseInput) -> TransplantRejectionReport:
    """Evaluate a case with a transparent, non-validated heuristic score."""

    _validate_input(inp)
    score = 0.0
    alerts: List[str] = []
    review_actions: List[str] = []
    monitoring: List[str] = []

    acr_norm = normalize_acr(inp.acr_grade)
    if acr_norm == "0R":
        acr_desc = "0R — no acute cellular rejection on biopsy"
    elif acr_norm == "1R":
        score += 15.0
        acr_desc = "1R — mild acute cellular rejection"
    elif acr_norm == "2R":
        score += 45.0
        acr_desc = "2R — moderate acute cellular rejection"
        alerts.append("HIGH CONCERN: ACR 2R requires clinical correlation by the transplant team.")
    else:
        score += 75.0
        acr_desc = "3R — severe acute cellular rejection"
        alerts.append("URGENT: ACR 3R is severe rejection and warrants urgent specialist assessment.")

    pamr_norm = normalize_pamr(inp.pamr_grade)
    if pamr_norm == "pAMR 0":
        pamr_desc = "pAMR 0 — negative for pathologic AMR"
    elif pamr_norm in ("pAMR 1(H+)", "pAMR 1(I+)"):
        score += 20.0
        pamr_desc = f"{pamr_norm} — one pathologic component of AMR present"
    elif pamr_norm == "pAMR 1":
        score += 20.0
        pamr_desc = "pAMR 1 — subtype not specified; verify H+ versus I+ classification"
        alerts.append("REVIEW: pAMR 1 should be documented with H+ or I+ subtype when available.")
    elif pamr_norm == "pAMR 2":
        score += 55.0
        pamr_desc = "pAMR 2 — pathologic AMR with histologic and immunopathologic findings"
        alerts.append("HIGH CONCERN: pAMR 2 requires prompt transplant-team correlation.")
    else:
        score += 85.0
        pamr_desc = "pAMR 3 — severe pathologic AMR"
        alerts.append("URGENT: pAMR 3 warrants urgent specialist assessment.")

    max_mfi = max(inp.dsa_class_i_mfi, inp.dsa_class_ii_mfi)
    if inp.dsa_positive:
        score += 10.0
        dsa_desc = "DSA reported positive"
        if max_mfi > 0:
            dsa_desc += f" (reported peak MFI {max_mfi:.0f}; assay/center-specific interpretation)"
        if inp.de_novo_dsa:
            score += 10.0
            dsa_desc += "; de novo DSA reported"
            alerts.append("REVIEW: De novo DSA increases concern and should be interpreted with graft findings.")
    else:
        if max_mfi > 0:
            dsa_desc = (
                f"DSA not flagged positive; MFI value {max_mfi:.0f} supplied — verify the laboratory's "
                "assay-specific positivity criteria"
            )
        else:
            dsa_desc = "DSA not reported positive"

    biomarker_items: List[str] = []
    if inp.dd_cfdna_pct is not None:
        value = inp.dd_cfdna_pct
        if value >= 0.20:
            score += 25.0
            biomarker_items.append(
                f"dd-cfDNA {value:.2f}% is above the tool's 0.20% high-concern heuristic threshold"
            )
            alerts.append("REVIEW: Elevated dd-cfDNA indicates allograft injury risk but is not rejection-specific.")
        elif value >= 0.12:
            score += 12.0
            biomarker_items.append(
                f"dd-cfDNA {value:.2f}% is between the tool's 0.12% and 0.20% heuristic thresholds"
            )
        else:
            biomarker_items.append(f"dd-cfDNA {value:.2f}% is below the tool's 0.12% heuristic threshold")

    if inp.allomap_score is not None:
        if inp.days_post_transplant < 60:
            biomarker_items.append(
                f"GEP/AlloMap score {inp.allomap_score:.1f} recorded before 2 months; this tool does not score it"
            )
        elif inp.allomap_score >= 34.0:
            score += 15.0
            biomarker_items.append(
                f"GEP/AlloMap score {inp.allomap_score:.1f} is at/above the tool's 34-point heuristic threshold"
            )
            alerts.append("REVIEW: Interpret GEP only in the validated population and clinical context.")
        else:
            biomarker_items.append(
                f"GEP/AlloMap score {inp.allomap_score:.1f} is below the tool's 34-point heuristic threshold"
            )

    biomarker_desc = "; ".join(biomarker_items) if biomarker_items else "Biomarkers not supplied"

    drug_name = (
        inp.primary_immunosuppressant.value
        if isinstance(inp.primary_immunosuppressant, ImmunosuppressantDrug)
        else str(inp.primary_immunosuppressant).strip() or "Immunosuppressant"
    )
    if inp.trough_target_low_ng_ml is None:
        tdm_desc = (
            f"{drug_name} trough {inp.trough_level_ng_ml:.1f} ng/mL; no patient/center-specific target range supplied"
        )
    else:
        low = float(inp.trough_target_low_ng_ml)
        high = float(inp.trough_target_high_ng_ml)
        if inp.trough_level_ng_ml < low:
            score += 10.0
            tdm_desc = (
                f"{drug_name} trough {inp.trough_level_ng_ml:.1f} ng/mL is below supplied target {low:.1f}-{high:.1f}"
            )
            alerts.append("REVIEW: Immunosuppressant trough is below the supplied target range.")
        elif inp.trough_level_ng_ml > high:
            tdm_desc = (
                f"{drug_name} trough {inp.trough_level_ng_ml:.1f} ng/mL is above supplied target {low:.1f}-{high:.1f}"
            )
            alerts.append("REVIEW: Immunosuppressant trough is above the supplied target range.")
        else:
            tdm_desc = (
                f"{drug_name} trough {inp.trough_level_ng_ml:.1f} ng/mL is within supplied target {low:.1f}-{high:.1f}"
            )

    lvef_drop = inp.baseline_lvef_pct - inp.lvef_pct
    if inp.hemodynamic_compromise or lvef_drop >= 15.0 or inp.lvef_pct < 40.0:
        score += 35.0
        graft_desc = f"Marked graft-function concern (LVEF {inp.lvef_pct:.0f}%, change {-lvef_drop:+.0f} percentage points)"
        alerts.append("URGENT: Hemodynamic compromise or marked graft dysfunction requires urgent clinical assessment.")
    elif lvef_drop >= 10.0 or inp.lvef_pct < 50.0:
        score += 15.0
        graft_desc = f"Graft-function concern (LVEF {inp.lvef_pct:.0f}%, change {-lvef_drop:+.0f} percentage points)"
    else:
        graft_desc = f"No major LVEF decline detected by heuristic screen (LVEF {inp.lvef_pct:.0f}%)"

    score = min(100.0, score)

    if score >= 70.0 or inp.hemodynamic_compromise or acr_norm == "3R" or pamr_norm == "pAMR 3":
        tier = OverallRejectionTier.SEVERE_CRITICAL
        review_actions.extend(
            [
                "Urgent heart-transplant-team assessment; determine need for monitored or inpatient evaluation.",
                "Correlate biopsy pathology with symptoms, hemodynamics, graft function, DSA, biomarkers, infection, and adherence.",
                "Use the transplant center's current protocol for treatment decisions; this tool does not prescribe therapy.",
            ]
        )
        monitoring.extend(
            [
                "Repeat/confirm relevant diagnostic testing at a clinically appropriate interval.",
                "Trend graft function and rejection markers under specialist supervision.",
            ]
        )
    elif score >= 40.0 or acr_norm == "2R" or pamr_norm == "pAMR 2":
        tier = OverallRejectionTier.MODERATE_REJECTION
        review_actions.extend(
            [
                "Prompt heart-transplant-team review and multimodal correlation.",
                "Verify immunosuppression exposure against the patient's prescribed target and assess adherence/interactions.",
                "Follow center-specific treatment and repeat-biopsy strategy if clinically significant rejection is confirmed.",
            ]
        )
        monitoring.append("Trend biopsy, DSA, graft function, and non-invasive biomarkers according to center protocol.")
    elif score >= 20.0 or acr_norm == "1R" or pamr_norm.startswith("pAMR 1"):
        tier = OverallRejectionTier.MILD_SUSPICION
        review_actions.extend(
            [
                "Correlate findings with symptoms, graft function, immunosuppression exposure, and center-specific surveillance protocol.",
                "No treatment recommendation is generated by this tool.",
            ]
        )
        monitoring.append("Consider closer surveillance if abnormalities persist or additional risk signals are present.")
    else:
        tier = OverallRejectionTier.QUIESCENT
        review_actions.append("No rejection treatment recommendation is generated; continue center-specific surveillance.")
        monitoring.append("Continue routine surveillance appropriate to time from transplant and individual risk.")

    limitations = [
        "The 0-100 composite score is a transparent heuristic and has not been externally validated as a clinical prediction rule.",
        "DSA MFI, dd-cfDNA, GEP, and immunosuppressant targets vary by assay, population, center, and clinical context.",
        "Pathology grade and transplant-team assessment take precedence over this synthesized output.",
    ]

    return TransplantRejectionReport(
        case_id=inp.case_id,
        patient_id=inp.patient_id,
        days_post_transplant=inp.days_post_transplant,
        rejection_risk_score=round(score, 1),
        overall_rejection_tier=tier.value,
        acr_status=acr_desc,
        pamr_status=pamr_desc,
        dsa_status=dsa_desc,
        biomarker_status=biomarker_desc,
        tdm_status=tdm_desc,
        graft_function_status=graft_desc,
        treatment_protocol=review_actions,
        monitoring_recommendations=monitoring,
        critical_alerts=alerts,
        limitations=limitations,
    )


def _coerce_float(kwargs: Dict[str, Any], key: str, default: Optional[float]) -> Optional[float]:
    value = kwargs.get(key)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be numeric; received {value!r}.") from exc


def _coerce_bool(kwargs: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = kwargs.get(key)
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "t", "positive", "+"}:
            return True
        if normalized in {"false", "0", "no", "n", "f", "negative", "-"}:
            return False
    raise ValueError(f"{key} must be a boolean value; received {value!r}.")


def _coerce_str(kwargs: Dict[str, Any], key: str, default: str) -> str:
    value = kwargs.get(key)
    return str(value).strip() if value not in (None, "") else default


def calculate_metrics(**kwargs: Any) -> Dict[str, Any]:
    """Dictionary-oriented wrapper used by batch jobs and simple integrations."""

    case_id = _coerce_str(kwargs, "case_id", _coerce_str(kwargs, "id", _coerce_str(kwargs, "study_id", "TX-001")))
    patient_id = kwargs.get("patient_id") or kwargs.get("Patient")
    days = int(_coerce_float(kwargs, "days_post_transplant", _coerce_float(kwargs, "days", 180.0)) or 0)

    cfdna = _coerce_float(kwargs, "dd_cfdna_pct", 0.08)
    allomap = _coerce_float(kwargs, "allomap_score", 28.0)
    trough_low = _coerce_float(kwargs, "trough_target_low_ng_ml", None)
    trough_high = _coerce_float(kwargs, "trough_target_high_ng_ml", None)

    inp = TransplantCaseInput(
        case_id=case_id,
        patient_id=str(patient_id) if patient_id not in (None, "") else None,
        days_post_transplant=days,
        acr_grade=_coerce_str(kwargs, "acr_grade", _coerce_str(kwargs, "acr", "0R")),
        pamr_grade=_coerce_str(kwargs, "pamr_grade", _coerce_str(kwargs, "pamr", "pAMR 0")),
        c4d_positive=_coerce_bool(kwargs, "c4d_positive", False),
        cd68_positive=_coerce_bool(kwargs, "cd68_positive", False),
        dsa_positive=_coerce_bool(kwargs, "dsa_positive", False),
        dsa_class_i_mfi=float(_coerce_float(kwargs, "dsa_class_i_mfi", 0.0) or 0.0),
        dsa_class_ii_mfi=float(_coerce_float(kwargs, "dsa_class_ii_mfi", 0.0) or 0.0),
        de_novo_dsa=_coerce_bool(kwargs, "de_novo_dsa", False),
        dd_cfdna_pct=cfdna,
        allomap_score=allomap,
        primary_immunosuppressant=_coerce_str(kwargs, "primary_immunosuppressant", "Tacrolimus"),
        trough_level_ng_ml=float(
            _coerce_float(
                kwargs,
                "trough_level_ng_ml",
                _coerce_float(kwargs, "trough", _coerce_float(kwargs, "primary_metric", 8.5)),
            )
            or 0.0
        ),
        trough_target_low_ng_ml=trough_low,
        trough_target_high_ng_ml=trough_high,
        mmf_mpa_trough_ug_ml=float(_coerce_float(kwargs, "mmf_mpa_trough_ug_ml", 2.5) or 0.0),
        lvef_pct=float(_coerce_float(kwargs, "lvef_pct", _coerce_float(kwargs, "lvef", 62.0)) or 0.0),
        baseline_lvef_pct=float(_coerce_float(kwargs, "baseline_lvef_pct", 65.0) or 0.0),
        hemodynamic_compromise=_coerce_bool(kwargs, "hemodynamic_compromise", _coerce_bool(kwargs, "critical_flag", False)),
        cav_grade=int(_coerce_float(kwargs, "cav_grade", 0.0) or 0),
    )

    report = evaluate_transplant_rejection(inp)
    result = report.to_dict()
    result["tool"] = "cardiac-transplant-rejection-agent"
    result["score"] = report.rejection_risk_score
    result["classification"] = report.overall_rejection_tier
    result["clinical_recommendation"] = "; ".join(report.treatment_protocol)
    return result


def process_batch(input_csv: str, output_csv: str) -> int:
    """Process CSV rows while preserving row-level validation errors."""

    with open(input_csv, mode="r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    result_fields = [
        "rejection_risk_score",
        "overall_rejection_tier",
        "acr_status",
        "pamr_status",
        "dsa_status",
        "graft_function_status",
        "treatment_protocol",
        "processing_error",
    ]
    output_fields = list(dict.fromkeys(fieldnames + result_fields))

    output_rows: List[Dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        try:
            result = calculate_metrics(**row)
            output.update(
                rejection_risk_score=result["rejection_risk_score"],
                overall_rejection_tier=result["overall_rejection_tier"],
                acr_status=result["acr_status"],
                pamr_status=result["pamr_status"],
                dsa_status=result["dsa_status"],
                graft_function_status=result["graft_function_status"],
                treatment_protocol="; ".join(result["treatment_protocol"]),
                processing_error="",
            )
        except (TypeError, ValueError) as exc:
            for field_name in result_fields[:-1]:
                output.setdefault(field_name, "")
            output["processing_error"] = str(exc)
        output_rows.append(output)

    with open(output_csv, mode="w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows)
