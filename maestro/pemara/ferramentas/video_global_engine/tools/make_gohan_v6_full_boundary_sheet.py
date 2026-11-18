"""Create a 5x13 sheet covering every V6 boundary at 60 fps."""

import json
import subprocess
from pathlib import Path


PROJECT = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1")
MANIFEST = PROJECT / "edit" / "gohan_ssj2_cell_continuous_v6_motion_source.json"
VIDEO = PROJECT / "deliveries" / "gohan_ssj2_cell_filme_continuo_v6_720p60.mp4"
OUTPUT = PROJECT / "qc" / "gohan_ssj2_cell_filme_continuo_v6_720p60_boundaries_full_65.jpg"


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    cumulative = 0
    frames = []
    for item in data["timeline"][:-1]:
        cumulative += int(item["editFrames"])
        center = cumulative * 2
        frames.extend((center - 2, center - 1, center, center + 1, center + 2))
    selection = "+".join(f"eq(n\\,{frame})" for frame in frames)
    subprocess.run([
        "ffmpeg", "-hide_banner", "-y", "-i", str(VIDEO), "-vf",
        f"select={selection},scale=320:-1,tile=5x13", "-fps_mode", "passthrough",
        "-frames:v", "1", str(OUTPUT),
    ], check=True)
    print(json.dumps({"ok": True, "frames": len(frames), "output": str(OUTPUT)}))


if __name__ == "__main__":
    main()
