# -*- coding: utf-8 -*-
"""
Servico: Dashboard Hardware  -  porta 8007
CPU, GPU, RAM, NVMe, temperatura, clock, consumo - todos em tempo real.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import time, logging, threading
from datetime import datetime
from collections import deque
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.config import PORTA_DASHBOARD

app = FastAPI(title="Pemara  Dashboard Hardware", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Historico circular (ultimos 5 minutos a 2s = 150 amostras)
_historico = {
    "cpu_pct":   deque(maxlen=150),
    "ram_pct":   deque(maxlen=150),
    "gpu_load":  deque(maxlen=150),
    "gpu_temp":  deque(maxlen=150),
    "vram_pct":  deque(maxlen=150),
    "timestamps": deque(maxlen=150),
}

#  GPU via pynvml 
_HAS_GPU = False
_pynvml  = None
_gpu_handle = None
_gpu_last_error = None
_gpu_lock = threading.RLock()

def _set_gpu_error(error):
    global _HAS_GPU, _gpu_handle, _gpu_last_error
    message = str(error) or type(error).__name__
    should_log = message != _gpu_last_error
    _HAS_GPU = False
    _gpu_handle = None
    _gpu_last_error = message
    if should_log:
        logging.warning("pynvml: %s", message)


def _init_gpu(force=False):
    """Inicializa o NVML e sempre renova o handle depois de uma falha do driver."""
    global _HAS_GPU, _pynvml, _gpu_handle, _gpu_last_error
    with _gpu_lock:
        try:
            if _pynvml is None:
                import pynvml as pv
                _pynvml = pv
            pv = _pynvml

            if force:
                try:
                    pv.nvmlShutdown()
                except Exception:
                    # Uma sessao invalidada pelo driver pode recusar o shutdown.
                    pass

            pv.nvmlInit()
            _gpu_handle = pv.nvmlDeviceGetHandleByIndex(0)
            _HAS_GPU = True
            _gpu_last_error = None
            return True
        except Exception as e:
            _set_gpu_error(e)
            return False

_init_gpu()

def _nvml_optional(callback):
    try:
        return callback()
    except Exception:
        return None


def _read_gpu_dados():
    pv = _pynvml
    h = _gpu_handle
    temp = pv.nvmlDeviceGetTemperature(h, pv.NVML_TEMPERATURE_GPU)
    util = pv.nvmlDeviceGetUtilizationRates(h)
    mem = pv.nvmlDeviceGetMemoryInfo(h)
    nome = pv.nvmlDeviceGetName(h)
    if isinstance(nome, bytes):
        nome = nome.decode("utf-8", errors="replace")

    dados = dict(
        nome=nome,
        temp=temp,
        load=util.gpu,
        mem_load=util.memory,
        vram_u=round(mem.used / 1024**3, 2),
        vram_t=round(mem.total / 1024**3, 2),
        vram_pct=round(mem.used / mem.total * 100, 1) if mem.total else 0,
    )

    # Sensores opcionais nao existem em todos os modelos NVIDIA.
    dados["fan"] = _nvml_optional(lambda: pv.nvmlDeviceGetFanSpeed(h))
    dados["power_w"] = _nvml_optional(
        lambda: round(pv.nvmlDeviceGetPowerUsage(h) / 1000, 1)
    )
    dados["power_max"] = _nvml_optional(
        lambda: round(pv.nvmlDeviceGetEnforcedPowerLimit(h) / 1000, 1)
    )
    if dados["power_w"] is not None and dados["power_max"] is not None:
        dados["power_pct"] = round(
            dados["power_w"] / max(dados["power_max"], 1) * 100,
            1,
        )
    else:
        dados["power_pct"] = None
    dados["clock_gpu"] = _nvml_optional(
        lambda: pv.nvmlDeviceGetClockInfo(h, pv.NVML_CLOCK_GRAPHICS)
    )
    dados["clock_mem"] = _nvml_optional(
        lambda: pv.nvmlDeviceGetClockInfo(h, pv.NVML_CLOCK_MEM)
    )
    capability = _nvml_optional(
        lambda: pv.nvmlDeviceGetCudaComputeCapability(h)
    )
    dados["compute"] = (
        f"sm_{capability[0]}{capability[1]}"
        if isinstance(capability, tuple) and len(capability) == 2
        else None
    )
    return dados


def _gpu_dados():
    global _HAS_GPU, _gpu_last_error
    with _gpu_lock:
        if not _HAS_GPU and not _init_gpu(force=_pynvml is not None):
            return {"erro": _gpu_last_error or "NVML indisponivel"}

        try:
            return _read_gpu_dados()
        except Exception as first_error:
            # Handles NVML ficam invalidos depois de reset/TDR/upgrade do driver.
            # Refaz a sessao e a leitura uma vez, sem exigir reinicio do Maestro.
            if _init_gpu(force=True):
                try:
                    return _read_gpu_dados()
                except Exception as retry_error:
                    _set_gpu_error(retry_error)
                    return {"erro": _gpu_last_error}
            return {"erro": _gpu_last_error or str(first_error)}


#  CPU / RAM / Disco via psutil 
def _sistema_dados():
    try:
        import psutil
        # Disk and network counters share the existing CPU sampling window.
        # Keep failures independent so one unsupported sensor does not hide the rest.
        d1 = n1 = None
        try:
            d1 = psutil.disk_io_counters()
            disk_started = time.monotonic()
        except Exception:
            pass
        try:
            n1 = psutil.net_io_counters()
            network_started = time.monotonic()
        except Exception:
            pass
        cpu_pct  = psutil.cpu_percent(interval=0.2)
        cpu_freq = psutil.cpu_freq()
        ram      = psutil.virtual_memory()

        # Temperatura CPU (Windows pode nao ter)
        cpu_temp = 0
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for sensor in ("coretemp", "k10temp", "cpu_thermal"):
                    if sensor in temps:
                        cpu_temp = round(temps[sensor][0].current, 1)
                        break
        except Exception:
            pass

        # NVMe / Disco - velocidade atual
        nvme_leitura = nvme_escrita = 0
        try:
            if d1 is not None:
                d2 = psutil.disk_io_counters()
                elapsed = max(time.monotonic() - disk_started, 1e-9)
                nvme_leitura = round(max(0, d2.read_bytes - d1.read_bytes) / elapsed / 1024**2, 1)
                nvme_escrita = round(max(0, d2.write_bytes - d1.write_bytes) / elapsed / 1024**2, 1)
        except Exception:
            pass

        # Network I/O
        net_sent = net_recv = 0
        try:
            if n1 is not None:
                n2 = psutil.net_io_counters()
                elapsed = max(time.monotonic() - network_started, 1e-9)
                net_sent = round(max(0, n2.bytes_sent - n1.bytes_sent) / elapsed / 1024, 1) # KB/s
                net_recv = round(max(0, n2.bytes_recv - n1.bytes_recv) / elapsed / 1024, 1) # KB/s
        except:
            pass

        return dict(
            cpu_pct      = cpu_pct,
            cpu_cores    = psutil.cpu_count(logical=False),
            cpu_threads  = psutil.cpu_count(logical=True),
            cpu_freq_mhz = round(cpu_freq.current, 0) if cpu_freq else 0,
            cpu_temp     = cpu_temp,
            ram_total_gb = round(ram.total   / 1024**3, 1),
            ram_used_gb  = round(ram.used    / 1024**3, 1),
            ram_pct      = ram.percent,
            nvme_leit_mbs= nvme_leitura,
            nvme_esc_mbs = nvme_escrita,
            net_sent_kbs = net_sent,
            net_recv_kbs = net_recv
        )
    except ImportError:
        return {"erro": "psutil nao instalado"}
    except Exception as e:
        return {"erro": str(e)}


#  Endpoints 
@app.get("/snapshot", summary="Snapshot completo de todos os sensores")
def snapshot():
    ts   = datetime.now().strftime("%H:%M:%S")
    gpu  = _gpu_dados()
    sys_ = _sistema_dados()

    # Acumula historico
    _historico["timestamps"].append(ts)
    _historico["cpu_pct"].append(sys_.get("cpu_pct", 0))
    _historico["ram_pct"].append(sys_.get("ram_pct", 0))
    _historico["gpu_load"].append(gpu.get("load", 0))
    _historico["gpu_temp"].append(gpu.get("temp", 0))
    _historico["vram_pct"].append(gpu.get("vram_pct", 0))

    return {
        "ts":     ts,
        "gpu":    gpu,
        "sistema": sys_,
        "gpu_disponivel": bool(gpu) and "erro" not in gpu,
    }


@app.get("/historico", summary="Historico dos ultimos 5 minutos")
def historico():
    return {
        "timestamps": list(_historico["timestamps"]),
        "cpu_pct":    list(_historico["cpu_pct"]),
        "ram_pct":    list(_historico["ram_pct"]),
        "gpu_load":   list(_historico["gpu_load"]),
        "gpu_temp":   list(_historico["gpu_temp"]),
        "vram_pct":   list(_historico["vram_pct"]),
    }


@app.get("/alertas", summary="Alertas de temperatura e uso excessivo")
def alertas():
    gpu = _gpu_dados()
    sis = _sistema_dados()
    alts = []

    if gpu.get("temp", 0) > 85:
        alts.append({"nivel": "critico", "msg": f"GPU temperatura critica: {gpu['temp']}C"})
    elif gpu.get("temp", 0) > 75:
        alts.append({"nivel": "aviso", "msg": f"GPU temperatura elevada: {gpu['temp']}C"})

    if gpu.get("vram_pct", 0) > 90:
        alts.append({"nivel": "aviso", "msg": f"VRAM quase cheia: {gpu['vram_pct']}%"})

    if sis.get("ram_pct", 0) > 90:
        alts.append({"nivel": "aviso", "msg": f"RAM quase cheia: {sis['ram_pct']}%"})

    if sis.get("cpu_pct", 0) > 95:
        alts.append({"nivel": "aviso", "msg": f"CPU sobrecarregada: {sis['cpu_pct']}%"})

    return {"alertas": alts, "total": len(alts)}


@app.get("/status")
def status():
    return {
        "servico": "dashboard",
        "ok": True,
        "gpu": _HAS_GPU,
        "gpu_erro": _gpu_last_error,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_DASHBOARD, reload=False)

