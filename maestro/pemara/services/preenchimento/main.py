# -*- coding: utf-8 -*-
"""
Serviao: Preenchimento    porta 8002
Responsavel por: receber PDF + mapa de dados  devolver PDF preenchido.
Isolado para que atualizaaaes no motor PyMuPDF nao afetem o resto do sistema.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import fitz  # PyMuPDF

from shared.config import URL_CADASTRO, PORTA_PREENCHIMENTO

app = FastAPI(title="Pemara  Preenchimento", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


#  Motor de preenchimento 
def _preencher_acroform(pdf_bytes: bytes, mapa: dict) -> tuple[bytes, list]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    log = []
    for pagina in doc:
        for widget in list(pagina.widgets() or []):
            nome = (widget.field_name or "").strip()
            for chave, valor in mapa.items():
                if chave.lower() in nome.lower() or nome.lower() in chave.lower():
                    widget.field_value = valor
                    widget.update()
                    log.append(f"{nome}  {valor}")
                    break
    return doc.tobytes(), log


def _preencher_coordenadas(pdf_bytes: bytes, mapa: dict) -> tuple[bytes, list]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    log = []
    for pagina in doc:
        for bloco in pagina.get_text("dict").get("blocks", []):
            for linha in bloco.get("lines", []):
                for span in linha.get("spans", []):
                    texto = span["text"].strip()
                    bbox  = span["bbox"]
                    for chave, valor in mapa.items():
                        if (chave.lower().replace("-", " ").strip() in
                                texto.lower().rstrip(":").strip()):
                            x = bbox[2] + 8
                            y = bbox[1] + (bbox[3] - bbox[1]) * 0.75
                            pagina.insert_text(
                                fitz.Point(x, y), str(valor),
                                fontsize=10, fontname="helv",
                                color=(0.05, 0.15, 0.55)
                            )
                            log.append(f'"{texto}"  {valor}')
                            break
    return doc.tobytes(), log


def _processar(pdf_bytes: bytes, mapa: dict) -> tuple[bytes, list, str]:
    doc_test = fitz.open(stream=pdf_bytes, filetype="pdf")
    tem_acroform = any(list(p.widgets()) for p in doc_test)
    doc_test.close()

    if tem_acroform:
        resultado, log = _preencher_acroform(pdf_bytes, mapa)
        modo = "AcroForm"
    else:
        resultado, log = _preencher_coordenadas(pdf_bytes, mapa)
        modo = "Coordenadas"

    return resultado, log, modo


def _extrair_texto(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    texto = ""
    for i, pag in enumerate(doc):
        texto += f"\n--- Pagina {i+1} ---\n{pag.get_text()}"
    return texto


#  Endpoints 
@app.post("/preencher", summary="Recebe PDF e devolve PDF preenchido com dados do cadastro")
async def preencher(arquivo: UploadFile = File(...)):
    pdf_bytes = await arquivo.read()
    if not pdf_bytes:
        raise HTTPException(400, "Arquivo vazio")

    # Busca o mapa do serviao de cadastro
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{URL_CADASTRO}/mapa")
            resp.raise_for_status()
            mapa = resp.json()
    except Exception as e:
        raise HTTPException(503, f"Serviao de cadastro indisponavel: {e}")

    if not mapa:
        raise HTTPException(422, "Cadastro vazio. Preencha seus dados primeiro.")

    pdf_final, campos_log, modo = _processar(pdf_bytes, mapa)
    logging.info(f"PDF '{arquivo.filename}' processado. Modo={modo}, {len(campos_log)} campos.")

    headers = {
        "X-Modo": modo,
        "X-Campos": str(len(campos_log)),
        "X-Campos-Log": " | ".join(campos_log[:20]),
    }
    return Response(
        content=pdf_final,
        media_type="application/pdf",
        headers=headers
    )


@app.post("/extrair-texto", summary="Extrai o texto bruto de um PDF")
async def extrair_texto(arquivo: UploadFile = File(...)):
    pdf_bytes = await arquivo.read()
    if not pdf_bytes:
        raise HTTPException(400, "Arquivo vazio")
    texto = _extrair_texto(pdf_bytes)
    return {"texto": texto, "caracteres": len(texto)}


@app.get("/status")
def status():
    return {"servico": "preenchimento", "ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_PREENCHIMENTO, reload=False)

