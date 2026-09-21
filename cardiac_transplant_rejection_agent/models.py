"""Legacy compatibility data models.

These generic models are retained for import compatibility only. New code should use
TransplantCaseInput and TransplantRejectionReport from the package root.
"""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ClinicalCasePayload:
    case_id: str
    patient_synthetic_id: str = ""
    primary_metric: float = 0.0
    secondary_metric: float = 0.0
    status_flag: str = ""
    is_stat: bool = False
    clinical_notes: str = ""
    biomarkers: Dict[str, Any] = field(default_factory=dict)
