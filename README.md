# Cardiac Transplant Rejection Agent

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Cardiac Transplant Rejection Agent** is an advanced analytical and computational platform implementing ISHLT Biopsy Grade (0R-3R) & Donor-Specific Antibody (DSA) Tracker.

Cardiac Transplant Rejection & Allograft Surveillance Engine
============================================================
Comprehensive post-heart transplant rejection surveillance decision engine
integrating ISHLT 2004 Acute Cellular Rejection (0R-3R), ISHLT 2013 Pathologic
Antibody-Mediated Rejection (pAMR 0-3), Donor-Specific Anti-HLA Antibodies (DSA MFI),
Donor-Derived Cell-Free DNA (dd-cfDNA %), Gene Expression Profiling (AlloMap),
and Therapeutic Drug Monitoring (Tacrolimus / Cyclosporine / MMF).

Standards & Guidelines:
  - ISHLT 2004 Revised Heart Biopsy Grading
  - ISHLT 2013 Working Formulation for Pathologic Diagnosis of AMR
  - Consensus Guidelines on Non-Invasive Allograft Surveillance (dd-cfDNA & GEP)

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`BiopsyFinding`**: Endomyocardial biopsy finding.
- **`BiopsyGradingAgent`**: Sub-agent for biopsy grading.
- **`ACRGrade`** — dedicated module for a c r grade evaluation and state verification.
- **`pAMRGrade`** — dedicated module for p a m r grade evaluation and state verification.
- **`OverallRejectionTier`** — dedicated module for overall rejection tier evaluation and state verification.
- **`ImmunosuppressantDrug`** — dedicated module for immunosuppressant drug evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  - ISHLT 2013 Working Formulation for Pathologic Diagnosis of AMR
  score = 0.0
  score = min(100.0, score)
  calc_res = calculate_metrics(**r)
  calculate_metrics,
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --- <value> --case-id <value> --patient-id <value> --days <value>
```

### Parameter Reference
- `---`: Specifies input measurement or parameter value.
- `--case-id`: Specifies input measurement or parameter value.
- `--patient-id`: Specifies input measurement or parameter value.
- `--days`: Specifies input measurement or parameter value.
- `--acr`: Specifies input measurement or parameter value.
- `--pamr`: Specifies input measurement or parameter value.
- `--dsa-positive`: Specifies input measurement or parameter value.
- `--dsa-mfi`: Specifies input measurement or parameter value.
- `--de-novo-dsa`: Specifies input measurement or parameter value.
- `--dd-cfdna`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t cardiac-transplant-rejection-agent .
docker run -p 8000:8000 cardiac-transplant-rejection-agent
```
