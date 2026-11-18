# -*- coding: utf-8 -*-
"""
Serviao: Histarico    porta 8004
Responsavel por: registrar e consultar o histarico de documentos processados + logs.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from shared.database import get_conn, init_db
from shared.config import LOGS_DIR, PORTA_HISTORICO

app = FastAPI(title="Pemara  Histarico", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    init_db()
    logging.info("Serviao Histarico iniciado.")


#  Schema 
class RegistroCreate(BaseModel):
    arquivo: str
    operacao: str


#  Endpoints 
@app.get("/registros", summary="Lista histarico de documentos processados")
def listar_registros(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, arquivo, operacao, data_hora FROM historico ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/registros", status_code=201, summary="Registra uma operaaao no histarico")
def criar_registro(body: RegistroCreate):
    conn = get_conn()
    conn.execute(
        "INSERT INTO historico (arquivo, operacao, data_hora) VALUES (?,?,?)",
        (body.arquivo, body.operacao, datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    logging.info(f"Histarico: {body.operacao} | {body.arquivo}")
    return {"ok": True}


@app.delete("/registros", summary="Limpa todo o histarico")
def limpar_historico():
    conn = get_conn()
    conn.execute("DELETE FROM historico")
    conn.commit()
    conn.close()
    return {"ok": True, "mensagem": "Histarico limpo."}


@app.get("/logs", summary="Retorna as altimas linhas do log do dia")
def obter_logs(linhas: int = 100):
    log_file = LOGS_DIR / f"pemara_{datetime.now().strftime('%Y%m%d')}.log"
    if not log_file.exists():
        return {"conteudo": "", "arquivo": str(log_file.name)}
    texto = log_file.read_text(encoding="utf-8", errors="replace")
    todas = texto.strip().split("\n")
    recentes = "\n".join(todas[-linhas:]) if len(todas) > linhas else texto
    return {"conteudo": recentes, "arquivo": log_file.name, "total_linhas": len(todas)}


@app.get("/logs/arquivos", summary="Lista arquivos de log disponaveis")
def listar_logs():
    arquivos = sorted(LOGS_DIR.glob("*.log"), reverse=True)
    return [{"nome": f.name, "tamanho_kb": round(f.stat().st_size / 1024, 1)} for f in arquivos]


@app.get("/status")
def status():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM historico").fetchone()[0]
    conn.close()
    return {"servico": "historico", "ok": True, "total_registros": total}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_HISTORICO, reload=False)

