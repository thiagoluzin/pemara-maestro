# -*- coding: utf-8 -*-
"""
Banco de dados compartilhado - SQLite.
CORRIGIDO: zero codigo executavel no import.
Chame init_db() no startup de cada servico.
"""
import sqlite3
import logging
from datetime import datetime
from pathlib import Path

from shared.config import DB_PATH, LOGS_DIR


def configurar_log():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"pemara_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS cadastro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT NOT NULL,
        campo TEXT NOT NULL,
        valor TEXT NOT NULL DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS historico (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        arquivo TEXT, operacao TEXT, data_hora TEXT
    )""")
    if c.execute("SELECT COUNT(*) FROM cadastro").fetchone()[0] == 0:
        dados = [
            ("Pessoal","Nome Completo",""),("Pessoal","CPF",""),
            ("Pessoal","RG",""),("Pessoal","Data de Nascimento",""),
            ("Pessoal","Telefone",""),("Pessoal","E-mail",""),
            ("Endereco","Rua",""),("Endereco","Numero",""),
            ("Endereco","Bairro",""),("Endereco","Cidade",""),
            ("Endereco","Estado",""),("Endereco","CEP",""),("Endereco","Pais",""),
            ("Profissional","Empresa",""),("Profissional","Cargo",""),
            ("Profissional","Matricula",""),("Familia","Esposa",""),
            ("Familia","Filho 1 - Nome",""),("Familia","Filho 1 - Nascimento",""),
            ("Familia","Filho 2 - Nome",""),("Familia","Filho 2 - Nascimento",""),
            ("Familia","Filho 3 - Nome",""),("Familia","Filho 3 - Nascimento",""),
            ("Familia","Filho 4 - Nome",""),("Familia","Filho 4 - Nascimento",""),
            ("Familia","Filho 5 - Nome",""),("Familia","Filho 5 - Nascimento",""),
        ]
        c.executemany("INSERT INTO cadastro (categoria,campo,valor) VALUES (?,?,?)", dados)
    conn.commit()
    conn.close()

