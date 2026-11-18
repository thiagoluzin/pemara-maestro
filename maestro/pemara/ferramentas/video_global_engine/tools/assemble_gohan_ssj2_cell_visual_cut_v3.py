from pathlib import Path

import assemble_gohan_ssj2_cell_visual_cut_v2 as assembly


PROJECT = assembly.PROJECT
assembly.OUTPUT = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_motion_source_720p24.mp4"
assembly.MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_motion_source.json"
assembly.CONTACT_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v3_motion_source_contact_32.jpg"
assembly.BOUNDARY_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v3_motion_source_boundaries_21.jpg"
assembly.SCHEMA_VERSION = "gohan_ssj2_cell_visual_cut_v3_motion_source"
assembly.SUPERSEDES_CANDIDATE = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"
assembly.TRANSITION_DESCRIPTION = (
    "hard cuts only; approved new-footage Take 02 V3 replaces the rejected slow interval; "
    "measured static tails remain removed from the other approved takes"
)
assembly.EDIT = [
    {"take_id": "01", "start_frame": 0, "end_frame": 215, "reason": "remove measured static tail from 8.916667s"},
    {"take_id": "02", "start_frame": 0, "end_frame": 96, "reason": "use all 4.0s of owner-approved new-footage V3 motion cut"},
    {"take_id": "03", "start_frame": 12, "end_frame": 226, "reason": "remove frozen opening and measured static tail"},
    {"take_id": "04", "start_frame": 0, "end_frame": 240, "reason": "approved motion-retimed take; no freeze detected"},
    {"take_id": "05", "start_frame": 0, "end_frame": 227, "reason": "remove measured static tail from 9.416667s"},
    {"take_id": "06", "start_frame": 0, "end_frame": 240, "reason": "approved corrected magic-slap take; no freeze detected"},
    {"take_id": "07", "start_frame": 0, "end_frame": 240, "reason": "approved frenetic multi-anchor take; no freeze detected"},
    {"take_id": "08", "start_frame": 0, "end_frame": 240, "reason": "approved motion-retimed Kamehameha take; no freeze detected"},
]


if __name__ == "__main__":
    assembly.main()
