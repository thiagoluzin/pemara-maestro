"""Run the owner-authorized, minimal LTX 2.5 GPU smoke and write its receipt.

The smoke exercises the real anchor contract, LTX 2.5 prompt compiler, pinned
ComfyUI API graph and output decoder.  It never selects another engine and it
does not promote the generated clip as owner-approved media.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE_ROOT = SCRIPT_PATH.parents[3]
STUDIO_ROOT = WORKSPACE_ROOT / "services" / "studio"
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from anchor_intelligence.compiler_ltx25 import compile_ltx25_prompt  # noqa: E402
from anchor_intelligence.schema import build_anchor_contract  # noqa: E402
from gpu_lease import GpuLeaseRegistry  # noqa: E402
from ltx25_workflow import build_ltx25_i2v_workflow  # noqa: E402
from video_engines.ltx25 import (  # noqa: E402
    LTX25_NODE_COMMIT,
    LTX25_VERSION,
    OFFICIAL_WORKFLOWS,
    Ltx25VideoEngine,
)


COMFY_URL = "http://127.0.0.1:8188"
INPUT_ROOT = WORKSPACE_ROOT / "ferramentas" / "ComfyUI" / "input"
OUTPUT_ROOT = WORKSPACE_ROOT / "ferramentas" / "ComfyUI" / "output"
RECEIPT_ROOT = WORKSPACE_ROOT / "ferramentas" / "video_global_engine" / "receipts"
LEASE_PATH = WORKSPACE_ROOT / "dados" / "studio" / "gpu_lease.json"
WORKFLOW_ID = OFFICIAL_WORKFLOWS[0]


class SmokeFailure(RuntimeError):
    """The smoke failed a preflight, execution or technical QC gate."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _api_json(path: str, *, method: str = "GET", payload: Any = None, timeout: int = 30) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{COMFY_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"ComfyUI API failed for {method} {path}: {exc}") from exc


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def _write_test_anchor(path: Path, *, width: int = 960, height: int = 544) -> None:
    """Write a deterministic RGB PNG without an image-generation dependency."""

    rows: list[bytes] = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            background = 52 + (x * 42 // max(1, width - 1))
            inside = width // 3 <= x < (2 * width) // 3 and height // 3 <= y < (2 * height) // 3
            if inside:
                row.extend((205, 58 + (y % 24), 48))
            else:
                row.extend((background, background + 6, background + 12))
        rows.append(bytes(row))
    payload = b"".join(rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header)
    png += _png_chunk(b"IDAT", zlib.compress(payload, level=9)) + _png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def _queue_is_empty() -> bool:
    queue = _api_json("/queue")
    return not queue.get("queue_running") and not queue.get("queue_pending")


def _validate_node_catalog(workflow: dict[str, Any]) -> None:
    catalog = _api_json("/object_info", timeout=60)
    required = {
        str(node.get("class_type") or "")
        for node in workflow.values()
        if isinstance(node, dict)
    }
    missing = sorted(item for item in required if item and item not in catalog)
    if missing:
        raise SmokeFailure(f"ComfyUI is missing workflow node types: {', '.join(missing)}")


def _running_prompt_ids(queue: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in queue.get("queue_running") or []:
        if isinstance(item, list) and len(item) > 1:
            ids.add(str(item[1]))
    return ids


def _interrupt_own_prompt(prompt_id: str) -> None:
    try:
        queue = _api_json("/queue")
        if prompt_id in _running_prompt_ids(queue):
            _api_json("/interrupt", method="POST", payload={})
        else:
            _api_json("/queue", method="POST", payload={"delete": [prompt_id]})
    except SmokeFailure:
        return


def _monitor(prompt_id: str, *, timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    last_report = -1
    while time.monotonic() - started < timeout_seconds:
        history = _api_json(f"/history/{prompt_id}")
        item = history.get(prompt_id) if isinstance(history, dict) else None
        if isinstance(item, dict):
            messages = (item.get("status") or {}).get("messages") or []
            errors = [message for message in messages if isinstance(message, list) and message and message[0] == "execution_error"]
            if errors:
                detail = errors[-1][1] if len(errors[-1]) > 1 else "unknown execution error"
                raise SmokeFailure(f"LTX 2.5 execution error: {json.dumps(detail, ensure_ascii=False)}")
            return item
        elapsed = int(time.monotonic() - started)
        if elapsed // 15 != last_report:
            queue = _api_json("/queue")
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "elapsed_seconds": elapsed,
                        "running": len(queue.get("queue_running") or []),
                        "pending": len(queue.get("queue_pending") or []),
                    }
                ),
                flush=True,
            )
            last_report = elapsed // 15
        time.sleep(5)
    _interrupt_own_prompt(prompt_id)
    raise SmokeFailure(f"LTX 2.5 smoke timed out after {timeout_seconds} seconds")


def _output_candidates(history: dict[str, Any]) -> list[Path]:
    found: list[Path] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            filename = value.get("filename")
            if isinstance(filename, str) and filename:
                kind = str(value.get("type") or "output")
                if kind == "output":
                    relative = Path(str(value.get("subfolder") or "")) / filename
                    found.append(OUTPUT_ROOT / relative)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(history.get("outputs") or {})
    unique: list[Path] = []
    for path in found:
        if path not in unique:
            unique.append(path)
    return unique


def _ffprobe(path: Path) -> dict[str, Any]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-count_frames",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        raise SmokeFailure(f"ffprobe failed for generated output: {exc}") from exc
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not isinstance(video, dict):
        raise SmokeFailure("Generated artifact has no video stream")
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    duration = float(video.get("duration") or (payload.get("format") or {}).get("duration") or 0)
    frames = int(video.get("nb_read_frames") or video.get("nb_frames") or 0)
    if width <= 0 or height <= 0 or duration <= 0 or frames < 1:
        raise SmokeFailure(
            f"Generated video failed technical QC: {width}x{height}, {duration}s, {frames} frames"
        )
    return {
        "codec": str(video.get("codec_name") or ""),
        "width": width,
        "height": height,
        "duration_seconds": duration,
        "frames": frames,
        "avg_frame_rate": str(video.get("avg_frame_rate") or ""),
        "audio_streams": sum(1 for item in streams if item.get("codec_type") == "audio"),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_smoke(*, timeout_seconds: int) -> dict[str, Any]:
    if not _queue_is_empty():
        raise SmokeFailure("ComfyUI queue is not empty; refusing to mix the smoke with another GPU job")
    engine = Ltx25VideoEngine(WORKSPACE_ROOT, comfy_online=True)
    before = engine.readiness()
    if before.get("state") != "READY_FOR_GPU_SMOKE" or not before.get("ready"):
        raise SmokeFailure(f"LTX 2.5 preflight state is {before.get('state')}: {before.get('message')}")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    relative_anchor = Path("maestro_smoke") / f"ltx25_anchor_{run_id}.png"
    anchor_path = INPUT_ROOT / relative_anchor
    _write_test_anchor(anchor_path)

    contract = build_anchor_contract(
        evidence={
            "subjects": [
                {
                    "id": "test_cube",
                    "count": 1,
                    "visible_identity_markers": ["single red rectangular subject"],
                    "screen_position": "center",
                    "confidence": 1.0,
                }
            ],
            "objects": [],
            "environment": {"background": "neutral gray gradient"},
            "composition": {"shot": "static centered technical test frame"},
            "visible_text": [],
            "uncertainties": [],
        },
        intent={
            "action": "The red subject moves a few pixels to the right with one smooth, continuous motion.",
            "preserve": ["subject count", "red color", "neutral background", "centered composition"],
            "explicit_changes": ["small horizontal movement only"],
            "new_elements_allowed": [],
            "sound": "No audio.",
        },
        invariants=["exactly one red subject", "no text", "no new objects", "same neutral background"],
        allowed_transformations=["small rightward translation"],
        negative_constraints=["no duplication", "no redesign", "no camera cut", "no scene change"],
        temporal_plan=[
            {"phase": "0-50%", "rule": "start from the exact anchor and begin a small rightward move"},
            {"phase": "50-100%", "rule": "complete the same move smoothly without adding elements"},
        ],
        camera_plan={"movement": "locked", "axis": "unchanged"},
        source={"kind": "synthetic_technical_fixture", "contains_personal_data": False},
    )
    compiled = compile_ltx25_prompt(contract, duration_seconds=1.0, fps=24.0, width=960, height=544)
    prefix = f"maestro_smoke/ltx25/{run_id}"
    workflow = build_ltx25_i2v_workflow(
        prompt=compiled["prompt"],
        negative=compiled["negative_prompt"],
        base_image_name=relative_anchor.as_posix(),
        width=960,
        height=544,
        frames=compiled["parameters"]["num_frames"],
        fps=24.0,
        seed=250902,
        filename_prefix=prefix,
        include_native_audio=False,
    )
    _validate_node_catalog(workflow)

    lease = GpuLeaseRegistry(LEASE_PATH)
    job_id = f"ltx25-smoke-{run_id}"
    acquired = lease.acquire(owner="maestro-ltx25-smoke", operation="ltx25_gpu_smoke", job_id=job_id)
    prompt_id = ""
    started_at = _utc_now()
    started = time.monotonic()
    try:
        queued = _api_json(
            "/prompt",
            method="POST",
            payload={"prompt": workflow, "client_id": f"maestro-ltx25-smoke-{uuid.uuid4()}"},
            timeout=60,
        )
        prompt_id = str(queued.get("prompt_id") or "")
        if not prompt_id:
            raise SmokeFailure(f"ComfyUI did not return prompt_id: {queued}")
        print(json.dumps({"event": "queued", "prompt_id": prompt_id, "run_id": run_id}), flush=True)
        history = _monitor(prompt_id, timeout_seconds=timeout_seconds)
        candidates = [path for path in _output_candidates(history) if path.is_file() and path.stat().st_size > 0]
        if not candidates:
            raise SmokeFailure("ComfyUI completed but no generated output file was found")
        output = max(candidates, key=lambda item: item.stat().st_mtime_ns)
        qc = _ffprobe(output)
        output_sha256 = _sha256(output)
        receipt = {
            "schema_version": 1,
            "status": "PASS",
            "engine_id": "ltx_2_5",
            "model_version": LTX25_VERSION,
            "node_commit": LTX25_NODE_COMMIT,
            "workflow_id": WORKFLOW_ID,
            "anchor_contract_id": contract["contract_id"],
            "prompt_compiler_version": compiled["compiler_version"],
            "prompt_id": prompt_id,
            "started_at": started_at,
            "completed_at": _utc_now(),
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "input": {
                "kind": "synthetic_technical_fixture",
                "contains_personal_data": False,
                "sha256": _sha256(anchor_path),
            },
            "generation": {
                "width": 960,
                "height": 544,
                "fps": 24.0,
                "frames": compiled["parameters"]["num_frames"],
                "seed": 250902,
                "native_audio": False,
                "fallback_allowed": False,
                "fallback_used": False,
            },
            "output_relative_path": output.relative_to(OUTPUT_ROOT).as_posix(),
            "output_bytes": output.stat().st_size,
            "output_sha256": output_sha256,
            "technical_qc": qc,
            "technical_qc_pass": True,
            "owner_approval_state": "PENDING_HUMAN_REVIEW",
            "lease": {
                "owner": acquired.get("owner"),
                "operation": acquired.get("operation"),
                "job_id": job_id,
            },
        }
        _write_json_atomic(RECEIPT_ROOT / "ltx25_gpu_smoke.json", receipt)
        after = engine.readiness()
        if after.get("state") != "READY" or not after.get("production_ready"):
            raise SmokeFailure(f"Receipt was written but readiness did not promote: {after.get('state')}")
        print(json.dumps({"event": "pass", "receipt": str(RECEIPT_ROOT / "ltx25_gpu_smoke.json"), "output": str(output), "qc": qc}, ensure_ascii=False), flush=True)
        return receipt
    except Exception:
        if prompt_id:
            _interrupt_own_prompt(prompt_id)
        raise
    finally:
        lease.release(job_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()
    try:
        run_smoke(timeout_seconds=max(300, args.timeout_seconds))
    except Exception as exc:
        print(json.dumps({"event": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
