# -*- coding: utf-8 -*-
"""
Serviao: Cadastro    porta 8001
Responsavel por: CRUD completo dos dados pessoais do usuario.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from shared.database import get_conn, init_db

app = FastAPI(title="Pemara  Cadastro", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    init_db()
    logging.info("Serviao Cadastro iniciado.")


#  Schemas 
class CampoUpdate(BaseModel):
    valor: str

class CampoCreate(BaseModel):
    categoria: str
    campo: str
    valor: Optional[str] = ""


#  Endpoints 
@app.get("/campos", summary="Lista todos os campos do cadastro")
def listar_campos():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, categoria, campo, valor FROM cadastro ORDER BY categoria, campo"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/campos/{id}", summary="Retorna um campo especafico")
def obter_campo(id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM cadastro WHERE id=?", (id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Campo nao encontrado")
    return dict(row)


@app.put("/campos/{id}", summary="Atualiza o valor de um campo")
def atualizar_campo(id: int, body: CampoUpdate):
    conn = get_conn()
    affected = conn.execute(
        "UPDATE cadastro SET valor=? WHERE id=?", (body.valor, id)
    ).rowcount
    conn.commit()
    conn.close()
    if not affected:
        raise HTTPException(status_code=404, detail="Campo nao encontrado")
    logging.info(f"Campo {id} atualizado.")
    return {"ok": True, "id": id, "valor": body.valor}


@app.post("/campos", status_code=201, summary="Adiciona novo campo ao cadastro")
def criar_campo(body: CampoCreate):
    conn = get_conn()
    cursor = conn.execute(
        "INSERT INTO cadastro (categoria, campo, valor) VALUES (?,?,?)",
        (body.categoria, body.campo, body.valor)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    logging.info(f"Campo '{body.campo}' criado na categoria '{body.categoria}'.")
    return {"ok": True, "id": new_id}


@app.delete("/campos/{id}", summary="Remove um campo do cadastro")
def deletar_campo(id: int):
    conn = get_conn()
    affected = conn.execute("DELETE FROM cadastro WHERE id=?", (id,)).rowcount
    conn.commit()
    conn.close()
    if not affected:
        raise HTTPException(status_code=404, detail="Campo nao encontrado")
    logging.info(f"Campo {id} removido.")
    return {"ok": True, "id": id}


@app.get("/mapa", summary="Retorna mapa campovalor para uso no preenchimento")
def obter_mapa():
    conn = get_conn()
    rows = conn.execute(
        "SELECT campo, valor FROM cadastro WHERE valor != ''"
    ).fetchall()
    conn.close()
    return {r["campo"]: r["valor"] for r in rows}


@app.get("/status")
def status():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM cadastro").fetchone()[0]
    preenchidos = conn.execute(
        "SELECT COUNT(*) FROM cadastro WHERE valor != ''"
    ).fetchone()[0]
    conn.close()
    return {"total": total, "preenchidos": preenchidos}


if __name__ == "__main__":
    import uvicorn
    from shared.config import PORTA_CADASTRO
    uvicorn.run("main:app", host="127.0.0.1", port=PORTA_CADASTRO, reload=False)

