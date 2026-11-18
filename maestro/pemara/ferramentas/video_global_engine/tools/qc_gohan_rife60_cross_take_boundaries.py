from __future__ import annotations

import qc_gohan_cross_take_boundaries as qc


qc.QC_DIR = qc.PROJECT / "qc" / "rife60_candidates" / "cross_take_boundaries"
qc.SHEET_BASENAME = "rife60_cross_take_boundaries_contact_sheet.jpg"
qc.REPORT_BASENAME = "rife60_cross_take_boundaries_report.json"


if __name__ == "__main__":
    raise SystemExit(qc.main())
