"""Packaging/import smoke tests."""

import cardiac_transplant_rejection_agent as package
from cardiac_transplant_rejection import OverallRejectionTier


def test_package_reexports_real_engine():
    result = package.calculate_metrics(acr_grade="0R", pamr_grade="pAMR 0", dd_cfdna_pct=0)
    assert result["classification"] == OverallRejectionTier.QUIESCENT.value


def test_package_version_surface_is_dependency_free():
    report = package.evaluate_transplant_rejection(package.TransplantCaseInput(dd_cfdna_pct=0))
    assert report.case_id
