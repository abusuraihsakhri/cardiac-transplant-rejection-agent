"""Compatibility coordinator backed by the repository's actual transplant engine."""

from __future__ import annotations

from typing import Any, Dict

from cardiac_transplant_rejection import TransplantCaseInput, evaluate_transplant_rejection


class TransplantCoordinator:
    """Small compatibility facade; does not maintain patient data or hidden state."""

    def process_case(self, case: TransplantCaseInput) -> Dict[str, Any]:
        if not isinstance(case, TransplantCaseInput):
            raise TypeError("process_case expects TransplantCaseInput")
        return evaluate_transplant_rejection(case).to_dict()
