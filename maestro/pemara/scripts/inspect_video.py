"""Terminal entry point: no browser, server, OpenAI API, GPU or ComfyUI required."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import uuid
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "services" / "studio"))
from decision_provider import DecisionClient
from editor_suite import EditorSuite
from video_inspection import InspectionService, InspectionSpec, Explanations


def main():
    parser = argparse.ArgumentParser(description="PEMARA — Decision inspeciona, Codex explica, sem regeneração")
    parser.add_argument("--data-root", type=Path, default=BASE / "dados" / "studio")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("--source", required=True, type=Path)
    analyze.add_argument("--content-kind", choices=["animation", "live_action", "mixed"], required=True)
    analyze.add_argument("--reference", action="append", default=[], type=Path)
    analyze.add_argument("--expected-state", default="")
    analyze.add_argument("--fps", type=int, choices=[2, 12, 24], default=12)
    analyze.add_argument("--max-calls", type=int, default=40)
    analyze.add_argument("--request-id", default=None)
    for name in ["status", "cancel", "explain", "recover"]:
        command = commands.add_parser(name)
        command.add_argument("--job", required=True)
        if name == "explain":
            command.add_argument("--file", required=True, type=Path)
    commands.add_parser("capabilities")
    args = parser.parse_args()
    suite = EditorSuite(args.data_root / "editor_suite", recover_jobs=False)
    service = InspectionService(suite)
    if args.command == "capabilities":
        print(json.dumps(service.capabilities(), ensure_ascii=False, indent=2))
        return 0
    if args.command in {"status", "cancel", "explain", "recover"}:
        record = service.read(args.job)
        if args.command == "cancel" and record["status"] in {"QUEUED", "RUNNING", "CANCELING"}:
            (service.folder(args.job) / "cancel.requested").touch()
            service.update(args.job, status="CANCELING")
        elif args.command == "recover":
            # Explicit reconciliation only; no calls are replayed or media regenerated.
            import os
            pid = record.get("workerPid")
            if pid:
                try:
                    import psutil
                    alive = psutil.pid_exists(pid)
                except ImportError:
                    try: os.kill(pid, 0); alive = True
                    except OSError: alive = False
                if alive:
                    raise ValueError("O processo ainda existe; não é seguro marcar a execução como interrompida.")
            if record["status"] not in {"QUEUED", "RUNNING", "CANCELING"}:
                raise ValueError("A execução já é terminal.")
            service.update(args.job, status="INTERRUPTED", error="WORKER_STOPPED_NO_AUTOMATIC_RETRY")
        elif args.command == "explain":
            service.explain(args.job, Explanations.model_validate_json(args.file.read_text(encoding="utf-8-sig")))
        print(json.dumps(service.get(args.job), ensure_ascii=False, indent=2))
        return 0
    if not DecisionClient().ready():
        raise ValueError("Configure GEMINI_API_KEY no arquivo privado gemini.env.")
    job_id = args.request_id or uuid.uuid4().hex
    if (service.folder(job_id) / "record.json").exists():
        old = service.get(job_id)
        from editor_suite import _sha256_file
        same = (_sha256_file(args.source.resolve(strict=True)) == old["sourceSha256"] and
                old["request"]["contentKind"] == args.content_kind and old["request"]["sampleFps"] == args.fps and
                old["request"]["expectedState"] == args.expected_state and old["request"]["maxDecisionCalls"] == args.max_calls and
                [_sha256_file(p.resolve(strict=True)) for p in args.reference] == [r["sha256"] for r in old["references"]])
        if not same:
            raise ValueError("Este identificador já foi usado com outra fonte ou parâmetros. Consulte status; nenhuma chamada foi repetida.")
        print(json.dumps(old, ensure_ascii=False, indent=2))
        return 0
    opened = []
    def upload(path):
        path = path.resolve(strict=True)
        stream = path.open("rb"); opened.append(stream)
        import mimetypes
        return SimpleNamespace(filename=path.name, content_type=mimetypes.guess_type(path.name)[0], file=stream)
    started = time.perf_counter()
    stop = threading.Event()
    samples = {"processPeakMiB": 0., "childrenPeakMiB": 0.}
    def measure():
        try:
            import psutil
            process = psutil.Process()
            while not stop.is_set():
                samples["processPeakMiB"] = max(samples["processPeakMiB"], process.memory_info().rss / 2**20)
                children = process.children(recursive=True)
                samples["childrenPeakMiB"] = max(samples["childrenPeakMiB"], sum(p.memory_info().rss for p in children if p.is_running()) / 2**20)
                stop.wait(.05)
        except (ImportError, OSError):
            samples["measurementUnavailable"] = True
    meter = threading.Thread(target=measure, daemon=True); meter.start()
    try:
        prepared = service.prepare(upload(args.source), [upload(p) for p in args.reference])
        spec = InspectionSpec(requestId=job_id, **{k: prepared[k] for k in ("projectId", "clipId", "expectedRevision", "referenceAssetIds")},
                              contentKind=args.content_kind, expectedState=args.expected_state, sampleFps=args.fps, maxDecisionCalls=args.max_calls)
        record = service.start(spec, synchronous=True)
    finally:
        for stream in opened: stream.close()
        stop.set(); meter.join(timeout=1)
    from editor_suite import _atomic_json
    samples.update({"wallSeconds": round(time.perf_counter() - started, 3), "browserOpened": False, "gpuModelLoaded": any(k in sys.modules for k in ("torch", "tensorflow")),
                    "openaiApiUsed": False})
    _atomic_json(service.folder(job_id) / "terminal_metrics.json", samples)
    print(json.dumps({"ok": record["status"] in {"AWAITING_CODEX", "REVIEW_READY"}, "job": job_id, "status": record["status"],
                      "error": record["error"], "markers": len(record["markers"]), "decisionCalls": record["decisionCalls"],
                      "codexRequestPath": record["codexRequestPath"], "reportPath": record["reportPath"], "metrics": samples}, ensure_ascii=False, indent=2))
    return 0 if record["status"] in {"AWAITING_CODEX", "REVIEW_READY"} else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Do not dump provider exceptions or local credential contents.
        from fastapi import HTTPException
        message = str(exc.detail) if isinstance(exc, HTTPException) else str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
