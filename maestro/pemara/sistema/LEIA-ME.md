# Pemara Universal v3.1
## Motor Documental · Studio Pro · Organizador IA · Microserviços

---

### Instalação (primeira vez)

**Windows:**
```
Duplo clique em INSTALAR_WINDOWS.bat
```
Detecta GPU automaticamente, instala PyTorch com CUDA correto, instala todas as dependências e cria os atalhos `INICIAR.bat` e `PARAR.bat`.

**Linux / macOS:**
```bash
bash iniciar_linux.sh
```
Instala tudo e já sobe o sistema em seguida.

---

### Iniciar após instalado

**Windows:** `INICIAR.bat`
**Linux:**   `bash iniciar_linux.sh`

Acesse: **http://localhost:8501**

---

### Módulos disponíveis

| Módulo | Descrição |
|---|---|
| 📑 Pemara Documental | Auto-preenchimento de PDF, cadastro de dados, conversor PDF↔Word, histórico |
| 🎛️ Studio Pro | Conversor de áudio, transcrição Whisper IA, DSP forense, isolamento de voz, editor de vídeo, upscale ESRGAN, processamento de imagem |
| 🗂️ Organizador IA | Lê e entende o conteúdo de qualquer arquivo, cria 5 categorias dinâmicas e organiza a pasta automaticamente (Gemini ou Ollama) |

---

### Arquitetura

```
pemara_universal/
│
├── INSTALAR_WINDOWS.bat    ← Instalação completa (só roda uma vez)
├── INICIAR.bat             ← Inicia o sistema (criado pelo instalador)
├── PARAR.bat               ← Encerra todos os serviços
├── iniciar_linux.sh        ← Instala + inicia no Linux/macOS
│
├── frontend/
│   └── app.py              ← Streamlit (porta 8501) — só UI
│
├── services/
│   ├── cadastro/main.py    ← FastAPI (porta 8001) — CRUD dados pessoais
│   ├── preenchimento/main.py ← FastAPI (porta 8002) — Motor PDF PyMuPDF
│   ├── conversor/main.py   ← FastAPI (porta 8003) — PDF↔DOCX
│   ├── historico/main.py   ← FastAPI (porta 8004) — Logs e registros
│   ├── studio/main.py      ← FastAPI (porta 8005) — Áudio/Vídeo/Imagem GPU
│   └── organizador/main.py ← FastAPI (porta 8006) — Org. inteligente IA
│
├── shared/
│   ├── config.py           ← Portas, URLs e paths centralizados
│   └── database.py         ← Camada SQLite compartilhada
│
├── database/pemara.db      ← Banco de dados SQLite
├── logs/                   ← Log separado por serviço
├── saida/                  ← Arquivos gerados
└── entrada/                ← Pasta de entrada (opcional)
```

---

### Documentação das APIs (Swagger automático)

| Serviço | URL | Swagger |
|---|---|---|
| Cadastro | http://localhost:8001 | /docs |
| Preenchimento | http://localhost:8002 | /docs |
| Conversor | http://localhost:8003 | /docs |
| Histórico | http://localhost:8004 | /docs |
| Studio Pro | http://localhost:8005 | /docs |
| Organizador | http://localhost:8006 | /docs |

---

### Requisitos

- Python 3.10+
- GPU NVIDIA (recomendado para Studio Pro e Organizador IA — funciona em CPU também)
- FFmpeg (instalado automaticamente pelo INSTALAR_WINDOWS.bat via winget)
- LibreOffice (opcional — necessário apenas para conversão DOCX→PDF)
- Ollama (opcional — necessário se escolher motor local no Organizador)

---

### Organizador IA: chave do Gemini

Para usar o motor Gemini no Organizador, acesse:
https://aistudio.google.com/app/apikey

A chave é informada diretamente na interface, sem necessidade de arquivo .env.
Para usar o Ollama (100% local, sem internet), execute:
```bash
ollama pull llama3
```

---

### Acesso remoto

**Cloudflare Tunnel (gratuito):**
```bash
cloudflared tunnel --url http://localhost:8501
```

**Tailscale:** instale no PC e no celular — acesse pelo IP da rede privada.

---

### Manutenção: reiniciar um serviço isolado

```bash
# Exemplo: reiniciar apenas o Studio Pro sem derrubar os demais
PYTHONPATH=. python -m uvicorn main:app --port 8005 --app-dir services/studio
```

### Adicionar novo serviço

1. Crie `services/novo/main.py` com FastAPI
2. Adicione a porta em `shared/config.py`
3. Adicione a URL no `frontend/app.py`
4. Adicione o `start_svc` no `INICIAR.bat` e `iniciar_linux.sh`
