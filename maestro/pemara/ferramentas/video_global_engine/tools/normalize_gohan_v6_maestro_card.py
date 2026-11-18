import json
import os
from pathlib import Path


queue_path = Path(r"E:\Pemara\maestro\pemara\ferramentas\video_global_engine\projetos\gohan_ssj2_android16_cell_6x10s_liveaction_v1\take_queue.json")
queue = json.loads(queue_path.read_text(encoding="utf-8-sig"))
takes = queue.get("takes", [])
if len(takes) != 1 or takes[0].get("id") != "FILME_V6":
    raise SystemExit("catálogo ativo não está consolidado em FILME_V6")

take = takes[0]
take["name"] = "GOHAN SSJ2 — FILME CONTÍNUO V6 — 60 FPS"
take["slug"] = "GOHAN SSJ2 — FILME CONTÍNUO V6 — 60 FPS"
take["stage"] = "FINAL_CONTINUOUS_FILM_REVIEW"
take["video_generation"] = {
    "engine": "Montagem contínua + Practical-RIFE 4.25",
    "profile": "continuous_picture_lock_candidate_720p60",
    "width": 1280,
    "height": 720,
    "fps": 60,
    "frames": 3612,
    "render_authorized": False,
    "visual_only_pass": True,
    "native_audio_authorized": False,
}

tmp = queue_path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(tmp, queue_path)
print("FILME_V6 card normalized")
