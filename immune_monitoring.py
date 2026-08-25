#!/usr/bin/env python3
"""
Immune Monitoring Agent for Cardiac Transplant Rejection Agent.
Monitors immune markers and predicts rejection risk from immune parameters.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class ImmuneMarkers:
    """Immune monitoring markers post-transplant."""
    cd4_count: float
    cd8_count: float
    cd4_cd8_ratio: float
    donor_specific_antibodies: bool
    dsa_mfi: float = 0.0
    immunosuppression_level: str = "therapeutic"
    viral_reactivation: bool = False
    cmv_status: str = "negative"
    ebv_status: str = "negative"


def assess_immune_risk(markers: ImmuneMarkers, days_post_transplant: int) -> Dict[str, Any]:
    """Assess immune rejection risk from monitoring markers."""
    risk_score = 0
    risk_factors = []

    if markers.cd4_count < 200:
        risk_score += 2
        risk_factors.append(f"Low CD4 count ({markers.cd4_count:.0f}): infection risk")
    elif markers.cd4_count > 1000:
        risk_score += 1
        risk_factors.append(f"Elevated CD4 ({markers.cd4_count:.0f}): possible over-immunosuppression")

    if markers.cd8_count > 800:
        risk_score += 1
        risk_factors.append(f"Elevated CD8 ({markers.cd8_count:.0f}): cellular rejection risk")

    if markers.cd4_cd8_ratio < 0.5 or markers.cd4_cd8_ratio > 3.0:
        risk_score += 1
        risk_factors.append(f"Abnormal CD4/CD8 ratio ({markers.cd4_cd8_ratio:.2f})")

    if markers.donor_specific_antibodies:
        risk_score += 3
        risk_factors.append(f"DSA positive (MFI: {markers.dsa_mfi:.0f}): antibody-mediated rejection risk")

    if markers.immunosuppression_level == "subtherapeutic":
        risk_score += 2
        risk_factors.append("Subtherapeutic immunosuppression: rejection risk")
    elif markers.immunosuppression_level == "supratherapeutic":
        risk_score += 1
        risk_factors.append("Supratherapeutic: infection and malignancy risk")

    if markers.viral_reactivation:
        risk_score += 2
        risk_factors.append("Viral reactivation: reduce immunosuppression")

    if days_post_transplant <= 30:
        risk_score += 1
        risk_factors.append("Early post-transplant: highest rejection window")

    if risk_score >= 6:
        rejection_risk = "HIGH"
        recommendation = "Urgent endomyocardial biopsy. Consider treatment for rejection."
    elif risk_score >= 3:
        rejection_risk = "MODERATE"
        recommendation = "Schedule endomyocardial biopsy. Optimize immunosuppression."
    elif risk_score >= 1:
        rejection_risk = "LOW"
        recommendation = "Continue current regimen. Monitor closely."
    else:
        rejection_risk = "MINIMAL"
        recommendation = "Standard monitoring protocol."

    return {
        "immune_risk_score": risk_score,
        "rejection_risk": rejection_risk,
        "risk_factors": risk_factors,
        "recommendation": recommendation,
        "days_post_transplant": days_post_transplant,
        "cd4_count": markers.cd4_count,
        "cd8_count": markers.cd8_count,
        "dsa_positive": markers.donor_specific_antibodies,
    }


class ImmuneMonitoringAgent:
    """Sub-agent for immune monitoring."""

    def __init__(self):
        self.agent_name = "ImmuneMonitoringAgent"

    def evaluate(self, markers: ImmuneMarkers, days_post_transplant: int) -> Dict[str, Any]:
        """Evaluate immune monitoring."""
        result = assess_immune_risk(markers, days_post_transplant)
        alerts = []

        if result["rejection_risk"] in ("HIGH", "MODERATE"):
            alerts.append({
                "type": "REJECTION_RISK", "severity": "CRITICAL" if result["rejection_risk"] == "HIGH" else "WARNING",
                "message": f"Rejection risk: {result['rejection_risk']} "
                           f"(score: {result['immune_risk_score']}).",
                "recommendation": result["recommendation"]
            })

        if markers.donor_specific_antibodies:
            alerts.append({
                "type": "DSA_POSITIVE", "severity": "CRITICAL",
                "message": f"DSA positive (MFI: {markers.dsa_mfi:.0f}).",
                "recommendation": "Evaluate for antibody-mediated rejection. Consider DSA monitoring trend."
            })

        if markers.viral_reactivation:
            alerts.append({
                "type": "VIRAL_REACTIVATION", "severity": "WARNING",
                "message": "Viral reactivation detected. Risk of graft injury.",
                "recommendation": "Reduce immunosuppression. Consider antiviral therapy."
            })

        return {"immune_result": result, "alerts": alerts}
