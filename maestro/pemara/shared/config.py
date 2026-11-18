# -*- coding: utf-8 -*-
"""
Configuraaaes centrais do Pemara Universal.
Altere as portas aqui para refletir em todo o sistema.
"""
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

#  Paths 
DB_PATH     = BASE_DIR / "database" / "pemara.db"
LOGS_DIR    = BASE_DIR / "logs"
SAIDA_DIR   = BASE_DIR / "saida"
ENTRADA_DIR = BASE_DIR / "entrada"

for d in [DB_PATH.parent, LOGS_DIR, SAIDA_DIR, ENTRADA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

#  Portas dos microserviaos 
PORTA_CADASTRO       = 8001
PORTA_PREENCHIMENTO  = 8002
PORTA_CONVERSOR      = 8003
PORTA_HISTORICO      = 8004
PORTA_STUDIO         = 8029   # Studio Pro: audio, video, imagem (GPU)
PORTA_ORGANIZADOR    = 8006   # Organizador inteligente de arquivos (IA)
PORTA_FRONTEND       = 8501

#  URLs base (usadas pelo frontend) 
def url(porta: int) -> str:
    return f"http://localhost:{porta}"

URL_CADASTRO      = url(PORTA_CADASTRO)
URL_PREENCHIMENTO = url(PORTA_PREENCHIMENTO)
URL_CONVERSOR     = url(PORTA_CONVERSOR)
URL_HISTORICO     = url(PORTA_HISTORICO)
URL_STUDIO        = url(PORTA_STUDIO)
URL_ORGANIZADOR   = url(PORTA_ORGANIZADOR)

PORTA_DASHBOARD    = 8007   # Hardware monitor
URL_DASHBOARD      = url(PORTA_DASHBOARD)

# Portas dos novos modulos externos (abertos no browser pelo frontend)
PORTA_ANYTHING_LLM = 3001   # NotebookLM++
PORTA_PERPLEXICA   = 3002   # DeepSearch
PORTA_COMFYUI      = 8188   # FLUX.1 imagens
PORTA_TRIPOSG      = 7860   # Gerador 3D

URL_ANYTHING_LLM   = url(PORTA_ANYTHING_LLM)
URL_PERPLEXICA     = url(PORTA_PERPLEXICA)
URL_COMFYUI        = url(PORTA_COMFYUI)
URL_TRIPOSG        = url(PORTA_TRIPOSG)
