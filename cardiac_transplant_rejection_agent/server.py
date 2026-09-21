"""Optional FastAPI wrapper around the same surveillance engine used by the CLI."""

from __future__ import annotations

from typing import Optional

from cardiac_transplant_rejection import TransplantCaseInput, evaluate_transplant_rejection


def create_app():
    """Create the optional FastAPI application, or return None if FastAPI is absent."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, ConfigDict
    except ImportError:
        return None

    class AuditRequest(BaseModel):
        model_config = ConfigDict(extra="forbid")
        case_id: str = "TX-API-01"
        patient_id: Optional[str] = None
        days_post_transplant: int = 180
        acr_grade: str = "0R"
        pamr_grade: str = "pAMR 0"
        dsa_positive: bool = False
        dsa_class_i_mfi: float = 0.0
        dsa_class_ii_mfi: float = 0.0
        de_novo_dsa: bool = False
        dd_cfdna_pct: Optional[float] = 0.08
        allomap_score: Optional[float] = 28.0
        primary_immunosuppressant: str = "Tacrolimus"
        trough_level_ng_ml: float = 8.5
        trough_target_low_ng_ml: Optional[float] = None
        trough_target_high_ng_ml: Optional[float] = None
        lvef_pct: float = 62.0
        baseline_lvef_pct: float = 65.0
        hemodynamic_compromise: bool = False
        cav_grade: int = 0

    app = FastAPI(
        title="Cardiac Transplant Rejection Surveillance",
        description=(
            "Research/educational API for a transparent surveillance heuristic. "
            "It is not validated for diagnosis or treatment selection."
        ),
        version="2.1.0",
    )

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "2.1.0", "clinical_use": False}

    @app.post("/api/audit")
    def audit(req: AuditRequest):
        try:
            report = evaluate_transplant_rejection(TransplantCaseInput(**req.model_dump()))
            return report.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app
