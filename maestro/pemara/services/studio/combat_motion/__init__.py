"""Maestro's local motion preparation, native Fun Control graph and 2D diagnostics.

ComfyUI built-ins do inference. These helpers do not send or retry jobs.
"""
from .graph import build,pose_graph,frontend,prompt_contract
from .diagnostics import analyze_file,compare_poses
from .prepare import prepare_reference,plan_short_takes
