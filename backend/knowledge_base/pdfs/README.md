# Knowledge Base PDFs – Folder Guide

## Folder Structure

```
knowledge_base/pdfs/
│
├── README.md                        ← This file
│
├── [ACTIVE – ingested by PDF pipeline]
├── (removed; use refund_policy.md)           ← Fees refund rules (general)
├── PPR_Online BBA.pdf               ← Programme & Pedagogy Report – Online BBA
├── PPR_Online BCA.pdf               ← Programme & Pedagogy Report – Online BCA
├── PPR_Online MBA.pdf               ← Programme & Pedagogy Report – Online MBA
├── PPR_Online MCA.pdf               ← Programme & Pedagogy Report – Online MCA
│
└── source_documents/                ← Reference copies ONLY (NOT re-ingested)
    ├── Online BCA Syllabus 2025-26.pdf    → Converted to: bca_syllabus_2025_26.md
    ├── Online MCA Syllabus 2025-26.pdf    → Converted to: mca_syllabus_2025_26.md
    ├── 2.1.18 EOA Report 2024-2025 AICTE BBA MBA.pdf → eoa_report_bba_mba.md
    ├── 2.1.18 EOA Report 2024-2025 AICTE BCA MCA.pdf → eoa_report_bca_mca.md
    ├── ONLINE_EXAMINATION.pdf             → Converted to: online_examination.md
    └── UGC_20240319151157_1.pdf           → Converted to: ugc_public_notice.md
```

## How PDF Ingestion Works

- The **PDF pipeline** (`pdf_ingestion.py`) scans **only the root `pdfs/` folder** (not subfolders)
- PDFs in `source_documents/` are **NOT automatically re-ingested** – they are stored here as reference copies
- PDFs already converted to Markdown (`.md`) files are indexed via the **Markdown pipeline** instead
- This avoids double-counting the same document in the vector store

## Active Markdown Files (converted from PDFs)

| PDF Source | MD File in knowledge_base/ |
|---|---|
| Online BCA Syllabus 2025-26.pdf | `bca_syllabus_2025_26.md` |
| Online MCA Syllabus 2025-26.pdf | `mca_syllabus_2025_26.md` |
| EOA Report AICTE BBA MBA.pdf | `eoa_report_bba_mba.md` |
| EOA Report AICTE BCA MCA.pdf | `eoa_report_bca_mca.md` |
| ONLINE_EXAMINATION.pdf | `online_examination.md` |
| UGC_20240319151157_1.pdf | `ugc_public_notice.md` |
