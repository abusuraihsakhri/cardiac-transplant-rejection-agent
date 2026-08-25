#!/usr/bin/env python3
"""
Endomyocardial Biopsy Grading for Cardiac Transplant Rejection Agent.
Grades rejection severity from biopsy findings using ISHLT classification.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


ISHLT_GRADING = {
    "0R": {"description": "No rejection", "severity": "none", "action": "No treatment needed"},
    "1R_mild": {"description": "Mild rejection", "severity": "mild",
                "action": "Often managed with observation or minor adjustment"},
    "2R_moderate": {"description": "Moderate rejection", "severity": "moderate",
                    "action": "Pulse-dose steroids. Consider augmented immunosuppression."},
    "3R_severe": {"description": "Severe rejection", "severity": "severe",
                  "action": "Aggressive pulse-dose steroids. Consider OKT3 or ATG."},
    "pAMR1": {"description": "Possible AMR", "severity": "mild",
              "action": "Correlate with DSA. Consider treatment if clinical concern."},
    "pAMR2": {"description": "Active AMR", "severity": "moderate",
              "action": "IVIG, plasmapheresis, rituximab. Consider bortezomib."},
    "pAMR3": {"description": "Severe AMR", "severity": "severe",
              "action": "Aggressive AMR protocol. Consider complement inhibition."},
}


@dataclass
class BiopsyFinding:
    """Endomyocardial biopsy finding."""
    grade: str
    lymphocyte_infiltrate: bool
    myocyte_necrosis: bool
    edema: bool
    hemorrhage: bool
    capillary_destruction: bool
    cd68_positive_cells: bool = False
    c4d_deposition: bool = False


def grade_biopsy(finding: BiopsyFinding, days_post_transplant: int) -> Dict[str, Any]:
    """Grade endomyocardial biopsy using ISHLT criteria."""
    if finding.grade in ISHLT_GRADING:
        grade_info = ISHLT_GRADING[finding.grade]
    else:
        grade_info = {"description": "Unknown grade", "severity": "unknown", "action": "Review pathology"}

    rejection_type = "cellular" if "R" in finding.grade else "antibody" if "AMR" in finding.grade else "unknown"

    severity_score = {"none": 0, "mild": 1, "moderate": 2, "severe": 3}.get(grade_info["severity"], 0)

    features_present = []
    if finding.lymphocyte_infiltrate:
        features_present.append("lymphocyte_infiltrate")
    if finding.myocyte_necrosis:
        features_present.append("myocyte_necrosis")
    if finding.edema:
        features_present.append("edema")
    if finding.hemorrhage:
        features_present.append("hemorrhage")
    if finding.capillary_destruction:
        features_present.append("capillary_destruction")
    if finding.cd68_positive_cells:
        features_present.append("cd68_positive_cells")
    if finding.c4d_deposition:
        features_present.append("c4d_deposition")

    monitoring = ["Repeat biopsy in 2-4 weeks"]
    if severity_score >= 2:
        monitoring.append("Frequent hemodynamic monitoring")
    if rejection_type == "antibody":
        monitoring.append("Monitor DSA levels")
        monitoring.append("Complement levels (C3, C4, CH50)")

    return {
        "grade": finding.grade,
        "description": grade_info["description"],
        "rejection_type": rejection_type,
        "severity": grade_info["severity"],
        "severity_score": severity_score,
        "action": grade_info["action"],
        "features": features_present,
        "monitoring": monitoring,
        "days_post_transplant": days_post_transplant,
    }


class BiopsyGradingAgent:
    """Sub-agent for biopsy grading."""

    def __init__(self):
        self.agent_name = "BiopsyGradingAgent"

    def evaluate(self, finding: BiopsyFinding, days_post_transplant: int) -> Dict[str, Any]:
        """Evaluate biopsy grade."""
        result = grade_biopsy(finding, days_post_transplant)
        alerts = []

        if result["severity"] == "severe":
            alerts.append({
                "type": "SEVERE_REJECTION", "severity": "CRITICAL",
                "message": f"ISHLT {result['grade']}: {result['description']}.",
                "recommendation": result["action"]
            })
        elif result["severity"] == "moderate":
            alerts.append({
                "type": "MODERATE_REJECTION", "severity": "WARNING",
                "message": f"ISHLT {result['grade']}: {result['description']}.",
                "recommendation": result["action"]
            })

        if result["rejection_type"] == "antibody" and finding.c4d_deposition:
            alerts.append({
                "type": "AMR_WITH_C4D", "severity": "CRITICAL",
                "message": "C4d deposition positive: active antibody-mediated rejection.",
                "recommendation": "Initiate AMR treatment protocol."
            })

        return {"biopsy_result": result, "alerts": alerts}
