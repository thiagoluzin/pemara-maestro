from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size,bit_rate:stream=width,height,r_frame_rate,avg_frame_rate,nb_frames",
        "-of",
        "json",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True, encoding="utf-8")
    return json.loads(out)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: qc_motion_probe.py <video.mp4> [...]", file=sys.stderr)
        return 2

    for arg in sys.argv[1:]:
        path = Path(arg)
        data = ffprobe(path)
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        stream = streams[0] if streams else {}
        duration = float(fmt.get("duration") or 0)
        size = int(fmt.get("size") or 0)
        bitrate = int(fmt.get("bit_rate") or 0)
        mb = size / (1024 * 1024)
        kbps = bitrate / 1000
        print(
            json.dumps(
                {
                    "file": str(path),
                    "duration_seconds": round(duration, 2),
                    "size_mb": round(mb, 2),
                    "bitrate_kbps": round(kbps, 1),
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "avg_frame_rate": stream.get("avg_frame_rate"),
                    "nb_frames": stream.get("nb_frames"),
                    "note": "Low bitrate can indicate weak motion, but visual QC is mandatory.",
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

