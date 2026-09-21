#!/usr/bin/env python3
"""Descriptive helper for ISHLT biopsy grades.

This legacy module reports classification and review flags only. It does not
prescribe treatment.
"""

from dataclasses import dataclass
from typing import Any, Dict

from cardiac_transplant_rejection import normalize_acr, normalize_pamr


@dataclass
class BiopsyFinding:
    grade: str
    lymphocyte_infiltrate: bool = False
    myocyte_necrosis: bool = False
    edema: bool = False
    hemorrhage: bool = False
    capillary_destruction: bool = False
    cd68_positive_cells: bool = False
    c4d_deposition: bool = False


def grade_biopsy(finding: BiopsyFinding, days_post_transplant: int) -> Dict[str, Any]:
    if days_post_transplant < 0:
        raise ValueError("days_post_transplant cannot be negative")
    if "AMR" in finding.grade.upper():
        grade = normalize_pamr(finding.grade)
        rejection_type = "antibody-mediated"
        severity = {
            "pAMR 0": "none",
            "pAMR 1(H+)": "increased concern",
            "pAMR 1(I+)": "increased concern",
            "pAMR 1": "increased concern",
            "pAMR 2": "high concern",
            "pAMR 3": "very high concern",
        }[grade]
    else:
        grade = normalize_acr(finding.grade)
        rejection_type = "acute cellular"
        severity = {"0R": "none", "1R": "increased concern", "2R": "high concern", "3R": "very high concern"}[grade]

    features = [
        name
        for name, present in {
            "lymphocyte_infiltrate": finding.lymphocyte_infiltrate,
            "myocyte_necrosis": finding.myocyte_necrosis,
            "edema": finding.edema,
            "hemorrhage": finding.hemorrhage,
            "capillary_destruction": finding.capillary_destruction,
            "cd68_positive_cells": finding.cd68_positive_cells,
            "c4d_deposition": finding.c4d_deposition,
        }.items()
        if present
    ]
    return {
        "grade": grade,
        "rejection_type": rejection_type,
        "severity": severity,
        "features": features,
        "days_post_transplant": days_post_transplant,
        "review": "Correlate the pathology grade with the transplant team's clinical assessment and center protocol.",
    }


class BiopsyGradingAgent:
    def evaluate(self, finding: BiopsyFinding, days_post_transplant: int) -> Dict[str, Any]:
        result = grade_biopsy(finding, days_post_transplant)
        alerts = (
            []
            if result["severity"] == "none"
            else [{"type": "BIOPSY_REVIEW", "severity": result["severity"], "message": result["review"]}]
        )
        return {"biopsy_result": result, "alerts": alerts}
