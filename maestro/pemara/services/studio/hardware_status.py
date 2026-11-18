import json
import os
import urllib.request
from typing import Any, Dict, Optional, Tuple


DASHBOARD_SNAPSHOT_URL = os.environ.get(
    "MAESTRO_DASHBOARD_SNAPSHOT_URL",
    "http://127.0.0.1:8007/snapshot",
)


def dashboard_gpu_snapshot(
    snapshot_url: str = DASHBOARD_SNAPSHOT_URL,
    timeout: float = 2.0,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Le a telemetria do coletor canonico, sempre pelo loopback."""
    try:
        with urllib.request.urlopen(snapshot_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        gpu = payload.get("gpu")
        if not isinstance(gpu, dict):
            return {}, "Dashboard nao retornou o objeto GPU"
        if payload.get("gpu_disponivel") is False or gpu.get("erro"):
            return {}, str(gpu.get("erro") or "Sensores NVIDIA indisponiveis")
        required = ("load", "vram_u", "vram_t", "temp")
        if any(gpu.get(field) is None for field in required):
            return {}, "Dashboard retornou telemetria GPU incompleta"
        return gpu, None
    except Exception as error:
        return {}, str(error) or type(error).__name__
