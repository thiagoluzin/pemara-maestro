"""
app.py
Orquestrador Flask do Portal Sprunki.
Rotas web + comunicação com ComfyUI (:8188) via API + WebSocket polling.

Dependências:
    pip install flask flask-cors websocket-client requests
"""

import base64
import binascii
import io
import json
import uuid
import os
import time
import threading
import urllib.request
import urllib.parse
import sys
import warnings
from pathlib import Path

import requests
import websocket
from flask import Flask, request, jsonify, send_from_directory
from PIL import Image, UnidentifiedImageError
from werkzeug.serving import WSGIRequestHandler

from prompt_builder import build_final_prompt

# ─── Configuração ─────────────────────────────────────────────────────────────
COMFYUI_HOST    = os.environ.get("SPRUNKI_COMFYUI_HOST", "127.0.0.1")
COMFYUI_PORT    = int(os.environ.get("SPRUNKI_COMFYUI_PORT", "8188"))
COMFYUI_URL     = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
OUTPUT_DIR      = Path("static/generated")
WORKFLOW_FILE   = "workflow_api.json"
APP_HOST        = os.environ.get("SPRUNKI_HOST", "127.0.0.1")
APP_PORT        = int(os.environ.get("SPRUNKI_PORT", "5005"))
MODEL_MATRIX_FILE = Path("model_matrix.json")
if COMFYUI_HOST.strip().lower() not in {"127.0.0.1", "localhost"}:
    raise RuntimeError("SPRUNKI_COMFYUI_HOST deve permanecer em loopback")
if APP_HOST.strip().lower() not in {"127.0.0.1", "localhost"}:
    raise RuntimeError("SPRUNKI_HOST deve permanecer em loopback")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_IMAGE_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}
ALLOWED_APP_HOSTS = {"127.0.0.1", "localhost", "sprunki.pemaratech.com.br"}


class SprunkiRequestHandler(WSGIRequestHandler):
    server_version = "Sprunki"
    sys_version = ""

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder="static")
app.config.update(
    MAX_CONTENT_LENGTH=12 * 1024 * 1024,
    MAX_FORM_MEMORY_SIZE=10 * 1024 * 1024,
    TRUSTED_HOSTS=["127.0.0.1", "localhost", "sprunki.pemaratech.com.br"],
)

# Armazena status dos jobs em memória (substituir por Redis em produção)
_jobs: dict[str, dict] = {}
_ratings_lock = threading.RLock()


def _validate_image_bytes(raw: bytes) -> str:
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Imagem vazia ou acima do limite de 8 MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                image_format = str(image.format or "").upper()
                width, height = image.size
                if image_format not in ALLOWED_IMAGE_FORMATS:
                    raise ValueError("Formato de imagem nao permitido")
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise ValueError("Dimensoes de imagem nao permitidas")
                image.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ValueError("Arquivo nao e uma imagem valida") from exc
    return ALLOWED_IMAGE_FORMATS[image_format]


def _read_image_upload(file_storage) -> tuple[bytes, str]:
    raw = file_storage.stream.read(MAX_IMAGE_BYTES + 1)
    return raw, _validate_image_bytes(raw)


def _decode_base64_image(value: str) -> tuple[bytes, str]:
    if not isinstance(value, str) or not value:
        raise ValueError("Imagem de referencia invalida")
    if len(value) > ((MAX_IMAGE_BYTES * 4) // 3) + 256:
        raise ValueError("Imagem de referencia acima do limite de 8 MB")
    encoded = value
    if "," in value:
        header, encoded = value.split(",", 1)
        allowed_headers = {
            "data:image/jpeg;base64",
            "data:image/png;base64",
            "data:image/webp;base64",
        }
        if header.lower() not in allowed_headers:
            raise ValueError("Tipo de imagem de referencia nao permitido")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Imagem de referencia base64 invalida") from exc
    return raw, _validate_image_bytes(raw)


def _invalid_text_field(data: dict, limits: dict[str, int] | None = None) -> str:
    limits = limits or {}
    for key, value in data.items():
        if key == "image_ref" or not isinstance(value, str):
            continue
        if len(value) > limits.get(key, 1000):
            return key
    return ""


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"status": "error", "message": "Envio acima do limite permitido"}), 413


@app.before_request
def validate_request_host():
    request_host = request.host.split(":", 1)[0].strip().lower()
    if request_host not in ALLOWED_APP_HOSTS:
        return jsonify({"status": "error", "message": "Host nao permitido"}), 421


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'none'; frame-ancestors 'self'; "
        "form-action 'self'; object-src 'none'; img-src 'self' data: blob:; "
        "media-src 'self' blob:; connect-src 'self' ws: wss:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'"
    )
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ─── ComfyUI: envio e polling ─────────────────────────────────────────────────

def resolve_workflow_file(workflow_file: str | None = None, model_key: str | None = None) -> str:
    if model_key and MODEL_MATRIX_FILE.exists():
        try:
            matrix = json.loads(MODEL_MATRIX_FILE.read_text(encoding="utf-8"))
            model = matrix.get("models", {}).get(model_key)
            if model and model.get("workflow"):
                workflow_file = model["workflow"]
        except Exception as e:
            print(f"[!] Erro lendo model_matrix.json: {e}")

    workflow_file = workflow_file or os.environ.get("SPRUNKI_WORKFLOW_FILE") or WORKFLOW_FILE
    workflow_path = Path(workflow_file)
    if workflow_path.is_absolute():
        raise ValueError("workflow_file deve ser relativo a pasta do gerador")
    if workflow_path.name != workflow_file or not workflow_path.name.startswith("workflow") or workflow_path.suffix != ".json":
        raise ValueError(f"workflow_file nao permitido: {workflow_file}")
    return workflow_file


def load_workflow(workflow_file: str | None = None, model_key: str | None = None) -> dict:
    with open(resolve_workflow_file(workflow_file, model_key), "r") as f:
        data = json.load(f)
    # Remove qualquer comentário ou chave que não seja dicionário (evita quebrar o validador do ComfyUI)
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def inject_prompt(workflow: dict, prompt_text: str, negative_text: str, params: dict, comfy_filename: str = None) -> dict:
    """
    Injeta o prompt no workflow do ComfyUI.
    IDs de nós baseados no workflow_api.json padrão Flux.1-dev.
    Ajuste os IDs conforme seu workflow exportado.
    """
    wf = json.loads(json.dumps(workflow))  # deep copy

    # Nó de prompt positivo (CLIPTextEncode)
    if "6" in wf:
        wf["6"]["inputs"]["text"] = prompt_text

    # Nó de prompt negativo (FLUX não usa prompt negativo desta forma)
    if "7" in wf:
        del wf["7"]

    # Nó FluxGuidance para guiar a escala do prompt
    if "12" in wf:
        wf["12"]["inputs"]["guidance"] = params.get("guidance_scale", 3.5)

    # Parâmetros de Sampling do FLUX
    if "15" in wf:
        wf["15"]["inputs"]["steps"] = params.get("num_inference_steps", 28)
    if "16" in wf:
        wf["16"]["inputs"]["noise_seed"] = params.get("seed", int(time.time()) % 2**32)

    # EmptyLatentImage
    if "5" in wf:
        wf["5"]["inputs"]["width"]   = params.get("width",  1024)
        wf["5"]["inputs"]["height"]  = params.get("height", 1024)

    # SaveImage — salva com prefixo rastreável
    if "9" in wf:
        wf["9"]["inputs"]["filename_prefix"] = "sprunki_"

    # Injeção dinâmica de imagem de referência (Img2Img) se comfy_filename for fornecido
    if comfy_filename:
        print(f"[IA] Customizando workflow para Img2Img usando imagem de referencia: {comfy_filename}")
        # Nó 30: LoadImage (Evitar colisão com os nós 15 e 16 do FLUX)
        wf["30"] = {
            "class_type": "LoadImage",
            "inputs": {
                "image": comfy_filename,
                "upload": "image"
            }
        }
        # Nó 31: VAEEncode
        wf["31"] = {
            "class_type": "VAEEncode",
            "inputs": {
                "pixels": ["30", 0],
                "vae": ["11", 0]
            }
        }
        # Conecta no SamplerCustomAdvanced (nó 3) substituindo EmptyLatentImage
        if "3" in wf:
            wf["3"]["inputs"]["latent_image"] = ["31", 0]
        # Configura o denoise no BasicScheduler (nó 15)
        if "15" in wf:
            wf["15"]["inputs"]["denoise"] = params.get("denoise", 0.65)

    return wf


def submit_to_comfyui(prompt_text: str, negative_text: str, params: dict, comfy_filename: str = None, workflow_file: str = None, model_key: str = None) -> str:
    """
    Submete o workflow ao ComfyUI e retorna o prompt_id.
    """
    workflow = load_workflow(workflow_file=workflow_file, model_key=model_key)
    workflow = inject_prompt(workflow, prompt_text, negative_text, params, comfy_filename)

    # Fallback dinâmico se a LoRA não existir no disco
    lora_dir = Path(__file__).parent.parent / "ComfyUI" / "models" / "loras"
    lora_name = workflow.get("2", {}).get("inputs", {}).get("lora_name", "sprunki_lora.safetensors")
    lora_path = lora_dir / lora_name
    alternate_lora = lora_dir / "sprunki_lora.safetensors"
    if not lora_path.exists() and alternate_lora.exists() and "2" in workflow:
        workflow["2"]["inputs"]["lora_name"] = alternate_lora.name
        lora_path = alternate_lora
    if not lora_path.exists():
        print(f"[!] LoRA não encontrada em {lora_path}. Aplicando fallback para modelo base.")
        if "2" in workflow:
            del workflow["2"]
        if "6" in workflow and workflow["6"]["inputs"].get("clip") == ["2", 1]:
            workflow["6"]["inputs"]["clip"] = ["10", 0]
        if "13" in workflow and workflow["13"]["inputs"].get("model") == ["2", 0]:
            workflow["13"]["inputs"]["model"] = ["14", 0]
        if "14" in workflow and workflow["14"]["inputs"].get("model") == ["2", 0]:
            workflow["14"]["inputs"]["model"] = ["1", 0]

    client_id = str(uuid.uuid4())
    payload   = json.dumps({
        "prompt":    workflow,
        "client_id": client_id,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    prompt_id = data["prompt_id"]
    _jobs[prompt_id] = {
        "status":    "queued",
        "client_id": client_id,
        "output":    None,
    }
    return prompt_id


def poll_job(prompt_id: str, client_id: str) -> None:
    """
    Thread de polling via WebSocket do ComfyUI.
    Atualiza _jobs[prompt_id] quando a geração termina.
    """
    ws_url = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws?clientId={client_id}"

    def on_message(ws, message):
        data = json.loads(message)
        mtype = data.get("type")

        if mtype == "executing":
            node = data["data"].get("node")
            if node is None:  # execução concluída
                # Busca o arquivo gerado via API de histórico
                try:
                    hist = requests.get(
                        f"{COMFYUI_URL}/history/{prompt_id}", timeout=10
                    ).json()

                    outputs = hist.get(prompt_id, {}).get("outputs", {})
                    for node_id, node_out in outputs.items():
                        images = node_out.get("images", [])
                        if images:
                            img_info   = images[0]
                            filename   = str(img_info["filename"])
                            subfolder  = img_info.get("subfolder", "")

                            img_resp  = requests.get(
                                f"{COMFYUI_URL}/view",
                                params={"filename": filename, "subfolder": subfolder, "type": "output"},
                                timeout=30,
                            )
                            img_resp.raise_for_status()
                            image_extension = _validate_image_bytes(img_resp.content)
                            dest_name = f"{prompt_id}_{uuid.uuid4().hex}{image_extension}"
                            dest      = OUTPUT_DIR / dest_name
                            dest.write_bytes(img_resp.content)

                            _jobs[prompt_id]["output"] = f"/static/generated/{dest_name}"
                            _jobs[prompt_id]["status"] = "done"
                            break
                except Exception as e:
                    _jobs[prompt_id]["status"] = "error"
                    _jobs[prompt_id]["error"]  = str(e)

                ws.close()

        elif mtype == "progress":
            value = data["data"].get("value", 0)
            max_v = data["data"].get("max", 1)
            _jobs[prompt_id]["progress"] = round(value / max_v * 100)
            _jobs[prompt_id]["status"]   = "generating"

        elif mtype == "status":
            queue_rem = data["data"].get("status", {}).get("exec_info", {}).get("queue_remaining", 0)
            if queue_rem > 0:
                _jobs[prompt_id]["status"] = "queued"

    def on_error(ws, error):
        _jobs[prompt_id]["status"] = "error"
        _jobs[prompt_id]["error"]  = str(error)

    ws_app = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
    )
    ws_app.run_forever()


# ─── Rotas ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/health")
def health():
    """Endpoint barato para watchdogs e balanceadores."""
    comfyui_ok = False
    try:
        resp = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
        comfyui_ok = resp.ok
    except requests.RequestException:
        comfyui_ok = False

    return jsonify({
        "status": "ok",
        "service": "sprunki",
        "comfyui": "ok" if comfyui_ok else "unavailable",
        "jobs": len(_jobs),
        "port": APP_PORT,
        "workflow": os.environ.get("SPRUNKI_WORKFLOW_FILE") or WORKFLOW_FILE,
    })


@app.route("/oc")
def oc_maker():
    return send_from_directory("static", "oc_maker.html")


@app.route("/brand")
def brand_analyzer():
    return send_from_directory("static", "brand_analyzer.html")


@app.route("/studio")
def game_studio():
    return send_from_directory("static", "game_studio.html")


@app.route("/api/studio/upload", methods=["POST"])
def studio_upload():
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "Nenhum arquivo enviado"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "Nenhum arquivo selecionado"}), 400
    
    try:
        raw, extension = _read_image_upload(file)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    filename = f"upload_{uuid.uuid4().hex}{extension}"
    dest = OUTPUT_DIR / filename
    dest.write_bytes(raw)
    return jsonify({"status": "success", "url": f"/static/generated/{filename}"})



# ── OC Maker ──────────────────────────────────────────────────────────────────

def extract_dominant_colors_from_bytes(image_data: bytes) -> list[str]:
    import colorsys
    
    try:
        img = Image.open(io.BytesIO(image_data))
        
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        img.thumbnail((100, 100))
        
        def get_color_name(r, g, b):
            h, l, s = colorsys.rgb_to_hls(r/255.0, g/255.0, b/255.0)
            h *= 360
            
            if l < 0.15:
                return "black"
            if l > 0.85:
                return "white"
            if s < 0.15:
                return "gray"
            
            if h < 20 or h >= 340:
                return "red"
            elif h < 45:
                return "orange"
            elif h < 75:
                return "yellow"
            elif h < 160:
                return "green"
            elif h < 200:
                return "cyan"
            elif h < 250:
                return "blue"
            elif h < 290:
                return "purple"
            else:
                return "pink"
        
        color_counts = {}
        pixels = img.getdata()
        for r, g, b, a in pixels:
            if a > 80:
                cname = get_color_name(r, g, b)
                if cname not in ["black", "white", "gray"]:
                    color_counts[cname] = color_counts.get(cname, 0) + 1
        
        if not color_counts:
            for r, g, b, a in pixels:
                if a > 80:
                    cname = get_color_name(r, g, b)
                    color_counts[cname] = color_counts.get(cname, 0) + 1
        
        sorted_colors = sorted(color_counts.items(), key=lambda item: item[1], reverse=True)
        return [item[0] for item in sorted_colors[:3]]
    except Exception as e:
        print(f"[!] Erro ao extrair cores dominantes: {e}")
        return []


@app.route("/api/generate_oc", methods=["POST"])
def generate_oc():
    """
    Gera Sprunki via OC Maker.
    Body JSON: { body_color, eyes, mouth, hat, accessory, theme, extra_desc,
                 body_character, eyes_character, mouth_character, hat_character, accessory_character, image_ref }
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "JSON invalido"}), 400
    invalid_field = _invalid_text_field(
        data,
        {"model_key": 128, "workflow_file": 128, "extra_desc": 1000},
    )
    if invalid_field:
        return jsonify({"status": "error", "message": f"Campo muito longo: {invalid_field}"}), 400
    
    image_ref = data.get("image_ref")
    model_key = data.get("model_key")
    workflow_file = data.get("workflow_file")
    
    image_data = None
    # Injeta cores dominantes no extra_desc antes de criar o prompt final
    if image_ref:
        try:
            image_data, image_extension = _decode_base64_image(image_ref)
            detected_colors = extract_dominant_colors_from_bytes(image_data)
            if detected_colors:
                detected_colors_str = f"color palette of {', '.join(detected_colors)}"
                print(f"[IA] Cores dominantes extraidas da referencia: {detected_colors_str}")
                orig_extra = data.get("extra_desc", "")
                if orig_extra:
                    data["extra_desc"] = f"{orig_extra}, {detected_colors_str}"
                else:
                    data["extra_desc"] = detected_colors_str
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

    result = build_final_prompt("oc_maker", data)

    # Força denoise dinâmico de 0.48 para o fluxo Img2Img
    if image_ref:
        if "params" not in result:
            result["params"] = {}
        result["params"]["denoise"] = 0.48
        print("[IA] Ajustado denoise dinamico para 0.48 para fidelidade cromatica.")

    comfy_filename = None
    if image_ref:
        try:
            print("[IA] Decodificando image_ref base64 enviada pelo canvas...")
            # Envia a imagem de referência para o ComfyUI
            image_mime = {
                ".jpg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }[image_extension]
            reference_name = f"reference_oc_{uuid.uuid4().hex}{image_extension}"
            files = {"image": (reference_name, image_data, image_mime)}
            upload_resp = requests.post(f"{COMFYUI_URL}/upload/image", files=files, data={"overwrite": "true"}, timeout=15)
            
            if upload_resp.status_code == 200:
                upload_json = upload_resp.json()
                comfy_filename = upload_json.get("name")
                print(f"[IA] Upload concluido para o ComfyUI: {comfy_filename}")
            else:
                print(f"[!] Erro no upload da imagem para o ComfyUI: {upload_resp.status_code} - {upload_resp.text}")
        except Exception as e:
            print(f"[!] Erro ao processar imagem de referencia: {e}")

    try:
        prompt_id = submit_to_comfyui(
            result["prompt"],
            result["negative_prompt"],
            result["params"],
            comfy_filename=comfy_filename,
            workflow_file=workflow_file,
            model_key=model_key,
        )
        # Inicia polling em background
        t = threading.Thread(
            target=poll_job,
            args=(prompt_id, _jobs[prompt_id]["client_id"]),
            daemon=True,
        )
        t.start()

        return jsonify({
            "status":    "queued",
            "prompt_id": prompt_id,
            "prompt":    result["prompt"],
        })

    except Exception as exc:
        print(f"[!] Erro interno ao gerar OC: {exc}")
        return jsonify({"status": "error", "message": "Falha interna ao iniciar a geracao"}), 500



# ── Brand Analyzer ─────────────────────────────────────────────────────────────

@app.route("/api/analyze_brand", methods=["POST"])
def analyze_brand_route():
    """
    Analisa marca e gera Sprunki.
    Aceita multipart/form-data com 'image' + JSON fields.
    """
    import tempfile
    from brand_analyzer import analyze_brand

    brand_name = request.form.get("brand_name", "custom")
    image_file = request.files.get("image")

    if not image_file:
        return jsonify({"status": "error", "message": "Imagem não enviada"}), 400

    # Salva imagem temporariamente
    invalid_field = _invalid_text_field(
        dict(request.form),
        {"brand_name": 120, "extra_desc": 1000, "model_key": 128, "workflow_file": 128},
    )
    if invalid_field:
        return jsonify({"status": "error", "message": f"Campo muito longo: {invalid_field}"}), 400
    try:
        image_data, suffix = _read_image_upload(image_file)
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(image_data)
        tmp_path = tmp.name

    try:
        # Análise de marca
        analysis = analyze_brand(tmp_path, brand_name)

        # Monta dados para o prompt builder
        pdata = {
            "brand_name":    analysis["brand_name"],
            "palette":       analysis["palette"],
            "style_tags":    analysis["style"].get("top_style_tags", []),
            "has_mascot":    "has mascot" in analysis["style"].get("top_style_tags", []),
            "is_food_brand": "food brand" in analysis["style"].get("top_style_tags", []),
            "is_drink_brand":"drink brand" in analysis["style"].get("top_style_tags", []),
            "extra_desc":    request.form.get("extra_desc", ""),
        }
        result = build_final_prompt("brand_analyzer", pdata)

        prompt_id = submit_to_comfyui(
            result["prompt"],
            result["negative_prompt"],
            result["params"],
            workflow_file=request.form.get("workflow_file"),
            model_key=request.form.get("model_key"),
        )
        t = threading.Thread(
            target=poll_job,
            args=(prompt_id, _jobs[prompt_id]["client_id"]),
            daemon=True,
        )
        t.start()

        return jsonify({
            "status":    "queued",
            "prompt_id": prompt_id,
            "prompt":    result["prompt"],
            "palette":   analysis["palette"],
            "style_tags": analysis["style"].get("top_style_tags", []),
        })

    except Exception as exc:
        print(f"[!] Erro interno ao analisar marca: {exc}")
        return jsonify({"status": "error", "message": "Falha interna ao analisar a imagem"}), 500

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Status de job ──────────────────────────────────────────────────────────────

@app.route("/api/status/<prompt_id>")
def job_status(prompt_id: str):
    """Polling de status — frontend chama a cada 1s."""
    try:
        uuid.UUID(prompt_id)
    except ValueError:
        return jsonify({"status": "not_found"}), 404
    job = _jobs.get(prompt_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify({
        "status":   job["status"],
        "progress": job.get("progress", 0),
        "output":   job.get("output"),
        "error":    job.get("error"),
    })


# ── Serve arquivos gerados ─────────────────────────────────────────────────────

@app.route("/static/generated/<filename>")
def serve_generated(filename):
    if Path(filename).name != filename or Path(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return jsonify({"status": "not_found"}), 404
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/organized/<path:filepath>")
def serve_organized(filepath):
    return send_from_directory("organized", filepath)


# ── Dataset LoRA e Galeria ────────────────────────────────────────────────────

@app.route("/lora_dataset/<filename>")
def serve_lora_dataset(filename):
    if Path(filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return jsonify({"status": "not_found"}), 404
    return send_from_directory("lora_dataset/img/20_sprunki_char", filename)


@app.route("/lora_gallery")
def serve_lora_gallery():
    return send_from_directory("static", "lora_gallery.html")


@app.route("/api/lora_samples")
def get_lora_samples():
    dataset_dir = Path("lora_dataset/img/20_sprunki_char")
    if not dataset_dir.exists():
        return jsonify([])
    samples = []
    jpg_files = sorted(list(dataset_dir.glob("*.jpg")), key=lambda p: p.name)
    
    # Carrega avaliações salvas
    ratings = {}
    ratings_file = dataset_dir / "ratings.json"
    if ratings_file.exists():
        try:
            ratings = json.loads(ratings_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    for p in jpg_files:
        txt_p = p.with_suffix(".txt")
        tags = ""
        if txt_p.exists():
            try:
                tags = txt_p.read_text(encoding="utf-8")
            except Exception:
                pass
        samples.append({
            "name": p.name,
            "image_url": f"/lora_dataset/{p.name}",
            "tags": tags,
            "rating": ratings.get(p.name, 0)
        })
    return jsonify(samples)


@app.route("/api/save_rating", methods=["POST"])
def save_rating():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "JSON invalido"}), 400
    name = data.get("name")
    rating = data.get("rating", 0)
    if not isinstance(name, str) or Path(name).name != name or len(name) > 180:
        return jsonify({"status": "error", "message": "Nome de arquivo invalido"}), 400
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Avaliacao invalida"}), 400
    if rating < 1 or rating > 5:
        return jsonify({"status": "error", "message": "Avaliacao invalida"}), 400
    
    dataset_dir = Path("lora_dataset/img/20_sprunki_char")
    ratings_file = dataset_dir / "ratings.json"
    sample_file = dataset_dir / name
    if sample_file.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"} or not sample_file.is_file():
        return jsonify({"status": "error", "message": "Amostra desconhecida"}), 404
    try:
        with _ratings_lock:
            ratings = {}
            if ratings_file.exists():
                try:
                    ratings = json.loads(ratings_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    ratings = {}
            ratings[name] = rating
            temp_file = ratings_file.with_suffix(".tmp")
            temp_file.write_text(json.dumps(ratings, indent=2), encoding="utf-8")
            os.replace(temp_file, ratings_file)
        return jsonify({"status": "success"})
    except OSError as exc:
        print(f"[!] Erro interno ao salvar avaliacao: {exc}")
        return jsonify({"status": "error", "message": "Falha interna ao salvar avaliacao"}), 500


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print(f"  Portal Sprunki — Flask :{APP_PORT}")
    print(f"  ComfyUI esperado em {COMFYUI_URL}")
    print("=" * 50)
    app.run(
        host=APP_HOST,
        port=APP_PORT,
        debug=False,
        threaded=True,
        request_handler=SprunkiRequestHandler,
    )
