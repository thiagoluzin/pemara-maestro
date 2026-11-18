"""One short CUDA load probe; only its own child can be terminated."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PROJECT_TOOLS = Path(__file__).resolve().parents[2] / "ferramentas/video_global_engine/projetos/scorpion_johnny_cage_living_forest_h3_80s_liveaction_v1/tools"
sys.path.insert(0, str(PROJECT_TOOLS))
from r17_gpu_thermal_guard import read_sample, validate_sample


def worker():
    import torch
    torch.set_num_threads(2)
    with torch.inference_mode():
        a = torch.randn((4096, 4096), device="cuda", dtype=torch.float16)
        b = torch.randn_like(a)
        c = torch.empty_like(a)
        for seconds, duty in ((10, 0.25), (15, 0.5), (20, 1.0)):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                start = time.monotonic()
                torch.mm(a, b, out=c)
                torch.cuda.synchronize()
                if duty < 1:
                    time.sleep((time.monotonic() - start) * (1 / duty - 1))
    print("BOUNDED_LOAD_COMPLETE", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker()
        return 0
    initial = read_sample()
    validate_sample(initial, starting=True)
    if initial["utilizationPercent"] > 5:
        raise RuntimeError("GPU is not idle; refusing probe")
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=initial["uuid"])
    proc = subprocess.Popen([sys.executable, __file__, "--worker"], env=env,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    started = time.monotonic()
    report = {"startedAt": datetime.now().astimezone().isoformat(),
              "status": "RUNNING", "childPid": proc.pid, "samples": [initial],
              "scope": "Short bounded probe, not long-render stability certification"}
    try:
        while proc.poll() is None:
            reading = read_sample()
            report["samples"].append(reading)
            validate_sample(reading, starting=False)
            if reading["temperatureC"] >= 78:
                raise RuntimeError("PROBE_TEMPERATURE_LIMIT_78C")
            if time.monotonic() - started > 90:
                raise RuntimeError("PROBE_DEADLINE")
            print(json.dumps(reading), flush=True)
            time.sleep(2)
        if proc.returncode:
            raise RuntimeError(f"Probe worker exited {proc.returncode}")
        if max(s["powerDrawWatts"] for s in report["samples"]) < 250:
            raise RuntimeError("Insufficient measured load; do not infer load stability")
        report["status"] = "PASS_SHORT_BOUNDED_LOAD"
    except BaseException as exc:
        report.update(status="BLOCKED", error=str(exc))
        raise
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        report["elapsedSeconds"] = round(time.monotonic() - started, 2)
        report["maxTemperatureC"] = max(s["temperatureC"] for s in report["samples"])
        report["maxPowerDrawWatts"] = max(s["powerDrawWatts"] for s in report["samples"])
        state = Path(__file__).resolve().parent / "state"
        report_path = state / ("load-probe-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
        with report_path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(json.dumps({"report": str(report_path), **{k: v for k, v in report.items() if k != "samples"}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
