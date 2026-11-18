# -*- coding: utf-8 -*-
"""
Serviao: Conversor    porta 8003
Responsavel por: conversaes de formato (PDFDOCX, DOCXPDF, extraaao de texto).
Isolado para permitir trocar a lib de conversao sem tocar em nada mais.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
import tempfile
import subprocess
import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from shared.config import PORTA_CONVERSOR

app = FastAPI(title="Pemara  Conversor", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


#  Conversores 
def _libreoffice_exe() -> str | None:
    candidatos = [
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for candidato in candidatos:
        if candidato and os.path.exists(candidato):
            return candidato
    return None


def _pdf_para_docx(pdf_bytes: bytes, nome: str) -> bytes | None:
    try:
        from pdf2docx import Converter
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
            tmp_in.write(pdf_bytes)
            tmp_in_path = tmp_in.name
        tmp_out_path = tmp_in_path.replace(".pdf", ".docx")
        cv = Converter(tmp_in_path)
        cv.convert(tmp_out_path, start=0, end=None)
        cv.close()
        with open(tmp_out_path, "rb") as f:
            result = f.read()
        os.unlink(tmp_in_path)
        os.unlink(tmp_out_path)
        logging.info(f"PDFDOCX: {nome}")
        return result
    except Exception as e:
        logging.error(f"Erro PDFDOCX ({nome}): {e}")
        return None


def _docx_para_pdf(docx_bytes: bytes, nome: str) -> bytes | None:
    try:
        libreoffice = _libreoffice_exe()
        if not libreoffice:
            logging.error("LibreOffice nao encontrado para DOCXPDF.")
            return None
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            tmp.write(docx_bytes)
            tmp_path = tmp.name
        out_dir = str(Path(tmp_path).parent)
        subprocess.run(
            [libreoffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, tmp_path],
            capture_output=True, timeout=60, check=False
        )
        pdf_path = tmp_path.replace(".docx", ".pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                result = f.read()
            os.unlink(tmp_path)
            os.unlink(pdf_path)
            logging.info(f"DOCXPDF: {nome}")
            return result
        os.unlink(tmp_path)
        return None
    except Exception as e:
        logging.error(f"Erro DOCXPDF ({nome}): {e}")
        return None


#  Endpoints 
@app.post("/pdf-para-docx", summary="Converte PDF em Word (.docx)")
async def pdf_para_docx(arquivo: UploadFile = File(...)):
    if not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo .pdf")
    pdf_bytes = await arquivo.read()
    result = _pdf_para_docx(pdf_bytes, arquivo.filename)
    if not result:
        raise HTTPException(500, "Falha na conversao. Verifique os logs.")
    nome_saida = arquivo.filename.replace(".pdf", ".docx")
    return Response(
        content=result,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{nome_saida}"'}
    )


@app.post("/docx-para-pdf", summary="Converte Word (.docx) em PDF (requer LibreOffice)")
async def docx_para_pdf(arquivo: UploadFile = File(...)):
    if not arquivo.filename.lower().endswith(".docx"):
        raise HTTPException(400, "Envie um arquivo .docx")
    docx_bytes = await arquivo.read()
    result = _docx_para_pdf(docx_bytes, arquivo.filename)
    if not result:
        raise HTTPException(500, "Falha. Certifique-se de ter o LibreOffice instalado.")
    nome_saida = arquivo.filename.replace(".docx", ".pdf")
    return Response(
        content=result,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_saida}"'}
    )


@app.get("/status")
def status():
    libreoffice_path = _libreoffice_exe()
    return {
        "servico": "conversor",
        "ok": True,
        "libreoffice_disponivel": libreoffice_path is not None,
        "libreoffice_path": libreoffice_path
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_CONVERSOR, reload=False)

