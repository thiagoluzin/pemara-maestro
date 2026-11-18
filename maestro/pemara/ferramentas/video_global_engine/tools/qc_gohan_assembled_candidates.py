from __future__ import annotations

import sys

import qc_gohan_overnight_sources as qc


qc.TAKE_IDS = ("01", "02", "03", "04", "05", "06")
qc.QC_DIR = qc.PROJECT / "qc" / "assembled_candidates"
qc.SHEET_LABEL = "ASSEMBLED CANDIDATE QC"
qc.COMBINED_BASENAME = "all_six_assembled_candidates_contact_sheet.jpg"
qc.REPORT_BASENAME = "assembled_candidates_report.json"


if __name__ == "__main__":
    sys.argv = [sys.argv[0]]
    raise SystemExit(qc.main())
