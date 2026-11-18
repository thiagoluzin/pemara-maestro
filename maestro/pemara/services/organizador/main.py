# -*- coding: utf-8 -*-
"""
Serviao: Organizador Forense de Provas  porta 8006
Responsavel por: ler, transcrever, categorizar e gerar cadeia de custadia (SHA-256) via Ollama.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json, gc, sqlite3, warnings, shutil, logging, re, hashlib, csv, io
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import collections

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from shared.config import PORTA_ORGANIZADOR, BASE_DIR

warnings.filterwarnings("ignore")

#  FIX: Unicode no Console Windows 
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

app = FastAPI(title="Pemara  Organizador Forense", version="1.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DB_PATH = BASE_DIR / "database" / "organizador.db"
_log_buf = collections.deque(maxlen=500)
_progresso = {"etapa": "", "pct": 0.0, "ativo": False, "erro": ""}

def bk_log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    _log_buf.append(entry)
    print(entry, flush=True)

def calcular_hash(caminho: str) -> str:
    """Calcula o Hash SHA-256 do arquivo para garantir a cadeia de custadia."""
    h = hashlib.sha256()
    try:
        with open(caminho, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "ERRO_LEITURA_HASH"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS operacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caminho_original TEXT, destino TEXT,
        status TEXT, data_hora TEXT, hash_sha256 TEXT
    )""")
    try: conn.execute("ALTER TABLE operacoes ADD COLUMN hash_sha256 TEXT")
    except: pass
    conn.commit()
    conn.close()

#  Extratores 
def _extrair_texto(caminho: Path) -> str:
    ext = caminho.suffix.lower()
    texto = ""
    try:
        if ext == ".pdf":
            import fitz
            for page in fitz.open(str(caminho))[:3]: texto += page.get_text()
        elif ext == ".docx":
            from docx import Document
            texto = "\n".join(p.text for p in Document(str(caminho)).paragraphs[:20])
        elif ext in (".xlsx", ".xls"):
            import pandas as pd
            texto = pd.read_excel(str(caminho), nrows=50).to_string()
        elif ext == ".csv":
            import pandas as pd
            texto = pd.read_csv(str(caminho), nrows=50, encoding="utf-8", errors="replace").to_string()
        elif ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            import easyocr
            reader = easyocr.Reader(["pt", "en"], gpu=True)
            texto = " ".join(reader.readtext(str(caminho), detail=0))
            del reader; gc.collect()
        elif ext in (".mp3", ".wav", ".m4a", ".flac", ".ogg", ".mp4", ".mkv", ".avi", ".mov"):
            import torch
            from transformers import pipeline
            
            # Indo na JUGULAR: Foraando PyTorch nativo com o modelo turbo
            device = 0 if torch.cuda.is_available() else -1
            dtype = torch.float16 if device == 0 else torch.float32
            
            # Injeta o Whisper Large V3 Turbo (mais inteligente e rapido) direto na GPU
            pipe = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-large-v3-turbo",
                device=device,
                torch_dtype=dtype
            )
            
            # Transcreve horas de audio em segundos aglomerando lotes de 30 segundos (Isso faz a 5080 trabalhar de verdade)
            resultado = pipe(str(caminho), generate_kwargs={"language": "portuguese"}, chunk_length_s=30, batch_size=16)
            texto = resultado["text"]
                
            del pipe; gc.collect()
            if torch.cuda.is_available(): torch.cuda.empty_cache()
            
        elif ext in (".txt", ".md", ".log"):
            with caminho.open("r", encoding="utf-8", errors="replace") as arquivo:
                texto = arquivo.read(25000)
        else: texto = f"[Tipo: {ext}]"
    except Exception as e: texto = f"[Erro extraaao: {e}]"
    
    # Aumentado o limite de 1500 para 25000 caracteres (aprox 40 minutos de audio transcrito)
    return texto[:25000]

def _iterar_lotes(arquivos, modo):
    """Extraia somente o lote atual; nunca retenha o texto do acervo inteiro."""
    global _progresso
    lote_atual = []
    tamanho_atual = 0
    total = len(arquivos)
    for i, arq in enumerate(arquivos):
        _progresso = {"etapa": f"Lendo/Extraindo: {arq.name}", "pct": (i / total) * 0.6, "ativo": True, "erro": ""}
        texto = _extrair_texto(arq) if modo == "conteudo" else ""
        item = {
            "id": i, "caminho_original": str(arq), "nome": arq.name, "extensao": arq.suffix,
            "data_sistema": datetime.fromtimestamp(os.path.getmtime(arq)).strftime("%d-%m-%Y"),
            "texto_resumo": texto,
        }
        tamanho = len(texto) + 200
        if modo == "conteudo" and lote_atual and tamanho_atual + tamanho > 35000:
            yield lote_atual
            lote_atual = []
            tamanho_atual = 0
        lote_atual.append(item)
        tamanho_atual += tamanho
        if modo != "conteudo" and len(lote_atual) >= 40:
            yield lote_atual
            lote_atual = []
            tamanho_atual = 0
    if lote_atual:
        yield lote_atual


#  IA Air-Gapped (Apenas Ollama com Rota Blindada) 
def _chamar_ia(dados: list, modelo_ollama: str, diretrizes: str, qtd_pastas: int, categorias_foraadas: list = None) -> dict:
    from ollama import Client
    
    # Rota blindada para evitar Erro 10061 (Conexao Recusada)
    cliente = Client(host='http://127.0.0.1:11434')
    
    cat_instrucao = f"1. Crie EXATAMENTE {qtd_pastas} categorias com nomes curtos em portuguas."
    if categorias_foraadas:
        cat_instrucao = f"1. USE OBRIGATORIAMENTE APENAS ESTAS CATEGORIAS Ja DEFINIDAS: {categorias_foraadas}"

    prompt = f"""
Voca a um sistema forense de classificaaao de provas legais.
DIRETRIZ DO USUaRIO: {diretrizes}

Analise os arquivos abaixo e siga ESTRITAMENTE estas regras:
{cat_instrucao}
2. O "novo_nome" de cada arquivo DEVE OBRIGATORIAMENTE comeaar com a data do documento no formato brasileiro DD-MM-AAAA.
3. Se houver data no texto extraado, use ela. Senao, use a "data_sistema" fornecida.
4. O padrao do novo nome deve ser: "DD-MM-AAAA - Titulo Curto.extensao".
5. Retorne APENAS um objeto JSON valido, sem NENHUM texto antes ou depois.

Formato OBRIGATaRIO:
{{
  "categorias": ["Cat1", "Cat2"],
  "mapeamento": [ {{"id": 0, "nova_categoria": "Cat1", "novo_nome": "15-02-2026 - Documento.pdf"}} ]
}}

Arquivos a processar:
{json.dumps(dados, ensure_ascii=False)}
"""
    try:
        # Passa um limite de contexto alto (num_ctx: 32000) para suportar textos gigantes de audios
        resp = cliente.generate(
            model=modelo_ollama, 
            prompt=prompt,
            options={"num_ctx": 32000, "temperature": 0.05}
        )["response"]
        
        # Limpeza agressiva para garantir JSON
        clean_resp = resp.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\{.*\}', clean_resp, re.DOTALL)
        if not match:
            raise Exception("A IA nao retornou um formato JSON valido.")
            
        clean = match.group(0)
        import ast
        try:
            return json.loads(clean)
        except:
            # Fallback robusto se houver erros sutis de escape
            return ast.literal_eval(clean)
    except Exception as e:
        bk_log(f"Falha ao comunicar/processar IA: {e}")
        raise Exception(f"Falha no motor Ollama: {e}")

#  Pipeline principal (Em Lotes/Chunks) 
def _rodar_organizacao(
    pasta: str, pasta_destino: str, modelo_ollama: str, diretrizes: str, 
    modo_dry_run: bool, modo: str, qtd_pastas: int
):
    global _progresso
    _progresso = {"etapa": "Iniciando mapeamento...", "pct": 0.0, "ativo": True, "erro": ""}

    try:
        raiz = Path(pasta)
        raiz_destino = Path(pasta_destino) if pasta_destino else raiz
        arquivos = [f for f in raiz.rglob("*") if f.is_file()]
        if not arquivos:
            _progresso = {"etapa": "Erro", "pct": 0, "ativo": False, "erro": "Nenhum arquivo encontrado."}
            return

        total = len(arquivos)
        bk_log(f"Iniciando analise forense de {total} arquivos em lotes...")

        # Pra-verificaaao de estabilidade: Ollama local rodando?
        if modo != "formato":
            try:
                import requests
                req = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
                if req.status_code != 200: raise Exception("Status nao 200")
            except Exception:
                _progresso = {"etapa": "Erro Fatal", "pct": 0, "ativo": False, "erro": "Ollama nao detectado. Certifique-se de que o Ollama esta rodando (icone na bandeja do Windows)."}
                bk_log("ERRO: Ollama offline ou inacessavel em 127.0.0.1:11434.")
                return

        mapeamento_final = []
        categorias_definidas = []
        
        analisados = 0
        for i, lote in enumerate(_iterar_lotes(arquivos, modo)):
            analisados += len(lote)
            _progresso = {"etapa": f"IA Analisando Lote {i+1}...", "pct": (analisados / total) * 0.6, "ativo": True, "erro": ""}

            if modo == "formato":
                for d in lote:
                    ext = d["extensao"].lower()
                    if ext in (".pdf", ".docx", ".txt", ".md"): cat = "Documentos"
                    elif ext in (".jpg", ".png", ".jpeg"): cat = "Imagens"
                    elif ext in (".mp4", ".mkv", ".avi"): cat = "Videos"
                    elif ext in (".mp3", ".wav", ".m4a"): cat = "Audios"
                    else: cat = "Outros"
                    mapeamento_final.append({"caminho_original": d["caminho_original"], "nova_categoria": cat, "novo_nome": f"{d['data_sistema']} - {d['nome']}"})
            else:
                import time
                for tentativa in range(3):
                    try:
                        # Mandar apenas os dados seguros para a IA
                        dados_ia = [{"id": d["id"], "nome": d["nome"], "data_sistema": d["data_sistema"], "texto_resumo": d["texto_resumo"]} for d in lote]
                        plano = _chamar_ia(dados_ia, modelo_ollama, diretrizes, qtd_pastas, categorias_definidas if i > 0 else None)
                        
                        if i == 0 and not categorias_definidas: 
                            categorias_definidas = plano.get("categorias", [])
                            
                        # Reconstruir o caminho original a partir do ID
                        for m in plano.get("mapeamento", []):
                            item_id = m.get("id")
                            original = next((x["caminho_original"] for x in lote if x["id"] == item_id), None)
                            if original:
                                m["caminho_original"] = original
                                mapeamento_final.append(m)
                        break
                    except Exception as e:
                        if tentativa == 2: raise e
                        bk_log(f"Falha na resposta da IA, tentando novamente ({tentativa+1}/3)... Erro: {e}")
                        time.sleep(2)

        if not modo_dry_run:
            conn = sqlite3.connect(str(DB_PATH))
            for i, item in enumerate(mapeamento_final):
                _progresso["etapa"] = f"Cadeia de Custadia: {item.get('novo_nome','')}"
                _progresso["pct"] = 0.6 + (i / max(len(mapeamento_final), 1)) * 0.38

                origem = Path(item["caminho_original"])
                cat = item.get("nova_categoria", "Outros")
                if isinstance(cat, list): cat = cat[0] if len(cat) > 0 else "Outros"
                cat = str(cat).strip()
                
                nome = item.get("novo_nome", origem.name)
                if isinstance(nome, list): nome = nome[0] if len(nome) > 0 else origem.name
                nome = str(nome).strip()
                
                if not re.match(r"^\d{2}-\d{2}-\d{4}", nome):
                    nome = f"{datetime.fromtimestamp(os.path.getmtime(origem)).strftime('%d-%m-%Y')} - {nome}"

                destino = raiz_destino / cat / nome
                destino.parent.mkdir(parents=True, exist_ok=True)
                
                if origem.exists() and str(origem) != str(destino):
                    hash_arq = calcular_hash(str(origem))
                    shutil.move(str(origem), str(destino))
                    
                    conn.execute(
                        "INSERT INTO operacoes (caminho_original,destino,status,data_hora,hash_sha256) VALUES (?,?,?,?,?)",
                        (str(origem), str(destino), "movido_seguro", datetime.now().strftime("%d/%m/%Y %H:%M:%S"), hash_arq)
                    )
                    bk_log(f"  [OK] {origem.name} -> {cat}/{nome} [SHA256: {hash_arq[:8]}...]")
            conn.commit()
            conn.close()

        _progresso = {"etapa": "Organizaaao Forense Concluada!", "pct": 1.0, "ativo": False, "erro": ""}
        bk_log("Processo forense finalizado com cadeia de custadia.")

    except Exception as e:
        bk_log(f"ERRO CRaTICO: {e}")
        logging.exception("organizador")
        _progresso["erro"] = str(e)
        _progresso["ativo"] = False

class OrganizarRequest(BaseModel):
    pasta: str
    pasta_destino: str = ""
    modelo_ollama: str = "llama3"
    diretrizes: str
    modo_dry_run: bool = True
    modo: str = "conteudo"
    qtd_pastas: int = 5

@app.on_event("startup")
def startup():
    init_db()
    bk_log("Serviao Forense iniciado (Modo Air-Gapped / Rota Blindada).")

@app.post("/organizar")
def organizar(body: OrganizarRequest, bg: BackgroundTasks):
    if _progresso.get("ativo"): return {"ok": False, "mensagem": "Sistema em execuaao."}
    bg.add_task(_rodar_organizacao, body.pasta, body.pasta_destino, body.modelo_ollama, body.diretrizes, body.modo_dry_run, body.modo, body.qtd_pastas)
    return {"ok": True, "mensagem": "Analise forense iniciada."}

@app.get("/progresso")
def progresso(): return _progresso

@app.get("/log")
def get_log(): return {"logs": list(_log_buf)[-100:]}

@app.get("/historico")
def historico(limit: int = 50):
    try:
        if not DB_PATH.exists(): return []
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("SELECT caminho_original, destino, status, data_hora, hash_sha256 FROM operacoes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [{"origem": r[0], "destino": r[1], "status": r[2], "data_hora": r[3], "hash": r[4]} for r in rows]
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/relatorio")
def gerar_relatorio():
    try:
        if not DB_PATH.exists(): return {"erro": "Base de dados vazia"}
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("SELECT caminho_original, destino, data_hora, hash_sha256 FROM operacoes ORDER BY id DESC").fetchall()
        conn.close()
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(["Arquivo Original", "Novo Arquivo (Prova)", "Data/Hora Organizacao", "Hash SHA-256 (Cadeia de Custodia)"])
        for r in rows: writer.writerow(r)
        
        output.seek(0)
        return StreamingResponse(
            output, media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=Indice_de_Provas_Forense.csv"}
        )
    except Exception as e:
        return {"erro": str(e)}

@app.get("/selecionar_pasta")
def api_selecionar_pasta():
    import tkinter as tk
    from tkinter import filedialog
    try:
        root = tk.Tk()
        root.attributes('-topmost', True)
        root.withdraw()
        pasta = filedialog.askdirectory(parent=root, title="Selecione a Pasta")
        root.destroy()
        return {"pasta": pasta}
    except Exception as e:
        return {"erro": str(e)}

@app.get("/modelos_ollama")
def modelos_ollama():
    try:
        import requests
        req = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
        if req.status_code == 200:
            dados = req.json()
            modelos = [m["name"] for m in dados.get("models", [])]
            return {"ok": True, "modelos": modelos}
        return {"ok": False, "erro": f"Status {req.status_code}"}
    except Exception as e:
        return {"ok": False, "erro": str(e)}

@app.get("/status")
def status(): return {"servico": "organizador", "ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_ORGANIZADOR, reload=False)

