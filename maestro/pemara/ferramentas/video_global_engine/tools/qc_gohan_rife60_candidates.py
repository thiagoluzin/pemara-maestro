from __future__ import annotations

import sys

import qc_gohan_overnight_sources as qc


qc.TAKE_IDS = ("01", "02", "03", "04", "05", "06")
qc.QC_DIR = qc.PROJECT / "qc" / "rife60_candidates"
qc.SHEET_LABEL = "RIFE60 REVIEW CANDIDATE QC"
qc.COMBINED_BASENAME = "all_six_rife60_candidates_contact_sheet.jpg"
qc.REPORT_BASENAME = "rife60_candidates_qc_report.json"
qc.EXPECTED_FPS = 60.0


if __name__ == "__main__":
    sys.argv = [sys.argv[0]]
    raise SystemExit(qc.main())
