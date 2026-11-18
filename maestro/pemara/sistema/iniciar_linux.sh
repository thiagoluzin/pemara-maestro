#!/usr/bin/env bash
# Pemara Universal v3.1 - Linux/macOS
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
PY=$(command -v python3 || command -v python)
PIP=$(command -v pip3 || command -v pip)
echo -e "\n    Pemara Universal v3.1\n  Documental + Studio Pro + Org IA\n"
echo "  [1/3] Dependencias..."
$PIP install -q streamlit fastapi "uvicorn[standard]" httpx requests pydantic PyMuPDF pdf2docx python-docx faster-whisper pydub soundfile scipy numpy Pillow nvidia-ml-py imageio-ffmpeg realesrgan basicsr "rembg[gpu]" onnxruntime-gpu demucs easyocr pandas openpyxl google-generativeai python-dotenv ollama 2>/dev/null || true
echo "   OK"
mkdir -p database logs saida entrada
rm -f /tmp/pemara_pids.txt
svc() { local N=$1 P=$2 D=$3; echo "   $N  :$P"; (cd "$DIR"; PYTHONPATH="$DIR" $PY -m uvicorn main:app --host 0.0.0.0 --port $P --log-level warning --app-dir $D >> logs/svc_$N.log 2>&1) & echo $! >> /tmp/pemara_pids.txt; }
echo "  [2/3] Microservicos..."
svc cadastro      8001 services/cadastro
svc preenchimento 8002 services/preenchimento
svc conversor     8003 services/conversor
svc historico     8004 services/historico
svc studio        8005 services/studio
svc organizador   8006 services/organizador
sleep 3
echo "   OK"
cleanup() { echo -e "\n  Encerrando..."; [ -f /tmp/pemara_pids.txt ] && while IFS= read -r p; do kill "$p" 2>/dev/null; done < /tmp/pemara_pids.txt; rm -f /tmp/pemara_pids.txt; exit 0; }
trap cleanup SIGINT SIGTERM
echo -e "\n  [3/3] Frontend...\n\n    http://localhost:8501\n  Ctrl+C para encerrar\n"
PYTHONPATH="$DIR" $PY -m streamlit run frontend/app.py --server.port 8501 --browser.gatherUsageStats false
