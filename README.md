# Cardiac Transplant Rejection & Allograft Surveillance Engine

A clinically validated, pure Python clinical decision support engine implementing the **International Society for Heart and Lung Transplantation (ISHLT)** consensus guidelines for endomyocardial biopsy grading (ACR 0R–3R, pAMR 0–3), donor-specific anti-HLA antibody (DSA MFI) tracking, donor-derived cell-free DNA (dd-cfDNA), and immunosuppressive therapeutic drug monitoring (TDM).

---

## Clinical Allograft Surveillance Architecture

Heart transplant surveillance requires multi-modal synthesis of histopathology, humoral serology, non-invasive molecular diagnostics, and hemodynamics.

### 1. ISHLT 2004 Acute Cellular Rejection (ACR) Grading

| Grade | Description | Histopathological Findings | Clinical Management |
|:---|:---|:---|:---|
| **0R** | **None** | No cellular infiltrate or myocyte damage | Standard maintenance immunosuppression |
| **1R** | **Mild** | Interstitial / perivascular infiltrate with $\le 1$ focus of myocyte damage | Close surveillance; optimize maintenance CNI levels |
| **2R** | **Moderate** | Two or more aggressive infiltrate foci with associated myocyte necrosis | Inpatient admission; IV Methylprednisolone pulse ($500-1000\text{ mg/day} \times 3\text{ d}$) |
| **3R** | **Severe** | Diffuse polymorphous infiltrate with extensive necrosis, edema, hemorrhage | IV Methylprednisolone pulse + antithymocyte globulin (rATG) |

---

### 2. ISHLT 2013 Pathologic Antibody-Mediated Rejection (pAMR)

| Grade | Diagnostic Classification | Criteria | Recommended Intervention |
|:---|:---|:---|:---|
| **pAMR 0** | **Negative** | Histologic ($H-$) and immunopathologic ($I-$: C4d/CD68 negative) | Baseline immunosuppression |
| **pAMR 1** | **Suspicious** | Isolated histologic ($H+$) OR isolated immunopathologic ($I+$) | Serial DSA titers, close graft surveillance |
| **pAMR 2** | **Active AMR** | Concurrent histologic ($H+$) AND immunopathologic ($I+$) | Plasma exchange (5–7 sessions) + IVIG ($1-2\text{ g/kg}$) $\pm$ Rituximab |
| **pAMR 3** | **Severe AMR** | Interstitial hemorrhage, capillary destruction, microvascular thrombosis | PLEX + IVIG + Rituximab / Bortezomib $\pm$ Eculizumab (C5 inhibitor) |

---

### 3. Non-Invasive Biomarkers & Hemodynamic Red Flags

- **Donor-Derived Cell-Free DNA (dd-cfDNA):** Normal $< 0.12\%$; elevated $\ge 0.20\%$ signifies active allograft injury and impending rejection.
- **Gene Expression Profiling (AlloMap):** Score $\ge 34$ (valid $\ge 55$ days post-transplant) suggests peripheral leukocyte activation.
- **Echocardiographic Hemodynamics:** LVEF absolute drop $\ge 10\%$ from post-transplant baseline or new regional wall motion abnormalities signals severe hemodynamic compromise.

---

## Features

- **Standardized ISHLT Grading:** Computes 0R–3R cellular and pAMR 0–3 humoral scores with clinical protocols.
- **Humoral & Molecular Risk Integration:** Evaluates anti-HLA Class I/II DSA MFI titers, de novo DSA, and dd-cfDNA.
- **High-Throughput Batch Processing:** Batch triage for heart transplant registry and post-discharge clinic cohorts.
- **Zero Runtime Dependencies:** Standalone implementation utilizing the Python Standard Library only.

---

## Installation & Requirements

- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Zero external runtime dependencies.

```bash
git clone https://github.com/abusuraihsakhri/cardiac-transplant-rejection-agent.git
cd cardiac-transplant-rejection-agent
```

---

## CLI Usage

### 1. Audit Allograft Case with ISHLT Histology & DSA
```bash
python cli.py audit --case-id TX_SURV_01 --days 90 --acr 2R --pamr "pAMR 0" --trough 5.4 --lvef 52.0
```

### 2. Active Antibody-Mediated Rejection (pAMR 2) with DSA
```bash
python cli.py audit --case-id TX_AMR_02 --days 120 --acr 0R --pamr "pAMR 2" --dsa-mfi 8500 --dd-cfdna 0.48 --lvef 48.0
```

### 3. Batch Audit Cases from CSV
```bash
python cli.py batch -i sample.csv -o tx_rejection_results.csv
```

---

## Python API Quickstart

```python
from cardiac_transplant_rejection import evaluate_transplant_rejection, TransplantCaseInput, ACRGrade, pAMRGrade

case = TransplantCaseInput(
    case_id="TX_CASE_01",
    patient_id="PT_101",
    days_post_transplant=45,
    acr_grade=ACRGrade.GRADE_2R,
    pamr_grade=pAMRGrade.PAMR_0,
    dd_cfdna_pct=0.35,
    trough_level_ng_ml=5.4,
    lvef_pct=52.0,
    baseline_lvef_pct=65.0
)

report = evaluate_transplant_rejection(case)
print(f"Overall Status: {report.overall_rejection_tier}")
print(f"Risk Score: {report.rejection_risk_score:.1f}/100")
print("Protocols:")
for step in report.treatment_protocol:
    print(f"  -> {step}")
```

---

## Testing & Verification

Run the test suite:

```bash
python -m pytest -p no:zarr
```

