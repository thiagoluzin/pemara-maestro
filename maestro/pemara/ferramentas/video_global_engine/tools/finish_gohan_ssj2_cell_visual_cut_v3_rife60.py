import finish_gohan_ssj2_cell_visual_cut_v2_rife60 as finish


PROJECT = finish.PROJECT
finish.SOURCE = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_motion_source_720p24.mp4"
finish.SOURCE_MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_motion_source.json"
finish.OUTPUT = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.mp4"
finish.MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60.json"
finish.CONTACT_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60_contact_32.jpg"
finish.BOUNDARY_SHEET = PROJECT / "qc" / "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60_boundaries_35.jpg"
finish.SCHEMA_VERSION = "gohan_ssj2_cell_visual_cut_v3_new_take02_720p60"
finish.SUPERSEDES_CANDIDATE = PROJECT / "deliveries" / "gohan_ssj2_cell_visual_cut_v2_fast_720p60.mp4"


if __name__ == "__main__":
    finish.main()
