#!/usr/bin/env python3
"""Legacy immune-marker summarizer for research/educational use.

The previous module assigned unsupported rejection-risk points to lymphocyte
counts. This version reports supplied markers without treating them as a
validated rejection prediction rule.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ImmuneMarkers:
    cd4_count: float
    cd8_count: float
    cd4_cd8_ratio: float
    donor_specific_antibodies: bool
    dsa_mfi: float = 0.0
    immunosuppression_level: str = "not supplied"
    viral_reactivation: bool = False
    cmv_status: str = "not supplied"
    ebv_status: str = "not supplied"


def assess_immune_risk(markers: ImmuneMarkers, days_post_transplant: int) -> Dict[str, Any]:
    if days_post_transplant < 0:
        raise ValueError("days_post_transplant cannot be negative")
    if min(markers.cd4_count, markers.cd8_count, markers.cd4_cd8_ratio, markers.dsa_mfi) < 0:
        raise ValueError("immune-marker numeric values cannot be negative")

    flags = []
    if markers.donor_specific_antibodies:
        flags.append("DSA reported positive; interpret with assay-specific criteria and graft findings")
    if markers.viral_reactivation:
        flags.append("Viral reactivation reported; requires clinical review in immunosuppression context")
    if markers.immunosuppression_level not in {"", "not supplied", "therapeutic"}:
        flags.append(
            f"Immunosuppression status reported as {markers.immunosuppression_level!r}; "
            "verify against prescribed targets"
        )

    return {
        "risk_score": None,
        "risk_classification": "not calculated — no validated rule implemented",
        "flags": flags,
        "days_post_transplant": days_post_transplant,
        "cd4_count": markers.cd4_count,
        "cd8_count": markers.cd8_count,
        "cd4_cd8_ratio": markers.cd4_cd8_ratio,
        "dsa_positive": markers.donor_specific_antibodies,
        "dsa_mfi": markers.dsa_mfi,
    }


class ImmuneMonitoringAgent:
    def evaluate(self, markers: ImmuneMarkers, days_post_transplant: int) -> Dict[str, Any]:
        result = assess_immune_risk(markers, days_post_transplant)
        return {"immune_result": result, "alerts": result["flags"]}
