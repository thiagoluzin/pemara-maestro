# -*- coding: utf-8 -*-
"""
Pemara Universal  Frontend Unificado (Streamlit)
APENAS interface de usuario. Toda lagica vive nos microserviaos.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import requests

from shared.config import (
    URL_CADASTRO, URL_PREENCHIMENTO,
    URL_CONVERSOR, URL_HISTORICO,
    URL_STUDIO, URL_ORGANIZADOR,
)

TIMEOUT_PROC = 600  # Evita travamento infinito, mas permite processos longos

def _req(method, url, *, timeout=8, **kw):
    try:
        r = getattr(requests, method)(url, timeout=timeout, **kw)
        r.raise_for_status()
        return r
    except requests.exceptions.ReadTimeout:
        st.warning(" A tarefa esta demorando mais que o esperado, mas segue processando no backend.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f" Serviao offline: `{url}`")
        return None
    except Exception as e:
        st.error(f" {e}")
        return None

_get  = lambda u, **k: _req("get",    u, **k)
_post = lambda u, **k: _req("post",   u, **k)
_put  = lambda u, **k: _req("put",    u, **k)
_del  = lambda u, **k: _req("delete", u, **k)

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=DM+Mono&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#0f1117;color:#e8eaf0;}
[data-testid="stSidebar"]{background:#161b27!important;border-right:1px solid #2a2f3e;}
.hdr{background:linear-gradient(135deg,#1a2236,#0f1117);border:1px solid #2a3850;border-radius:12px;padding:22px 28px;margin-bottom:22px;}
.hdr h1{font-size:1.65rem;font-weight:700;color:#e8eaf0;margin:0 0 4px;}
.hdr .sub{color:#5a7fa8;font-size:.8rem;font-family:'DM Mono',monospace;}
.sc{background:#161b27;border:1px solid #2a3850;border-radius:10px;padding:13px 17px;margin-bottom:11px;}
.sc .lb{color:#5a7fa8;font-size:.71rem;text-transform:uppercase;letter-spacing:.9px;}
.sc .vl{color:#e8eaf0;font-size:1rem;font-weight:600;margin-top:3px;}
.sb{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.67rem;font-weight:700;}
.ok{background:#0d2119;color:#3fb950;border:1px solid #238636;}
.er{background:#2d0e0e;color:#f85149;border:1px solid #da3633;}
.stButton>button{background:#1e6feb!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;transition:all .18s!important;}
.stButton>button:hover{background:#388bfd!important;transform:translateY(-1px)!important;}
.bd button{background:#da3633!important;}.bs button{background:#238636!important;}
.stTextInput>div>div>input,.stSelectbox>div>div>div,.stTextArea>div>div>textarea{background:#1a2035!important;color:#e8eaf0!important;border:1px solid #2a3850!important;border-radius:8px!important;}
[data-testid="stFileUploaderDropzone"]{background:#161b27!important;border:2px dashed #2a3850!important;border-radius:12px!important;}
.stTabs [data-baseweb="tab-list"]{background:transparent!important;gap:4px;}
.stTabs [data-baseweb="tab"]{background:#161b27!important;color:#8b949e!important;border:1px solid #2a3850!important;border-radius:8px!important;font-weight:600!important;padding:8px 16px!important;}
.stTabs [aria-selected="true"]{background:#1e6feb!important;color:#fff!important;border-color:#1e6feb!important;}
.rc{background:#0d1117;border:1px solid #238636;border-radius:8px;padding:10px 14px;margin:4px 0;font-family:'DM Mono',monospace;font-size:.77rem;color:#3fb950;}
hr{border-color:#2a3850!important;}
::-webkit-scrollbar{width:5px;}::-webkit-scrollbar-track{background:#0f1117;}::-webkit-scrollbar-thumb{background:#2a3850;border-radius:3px;}
</style>"""

st.set_page_config(page_title="Pemara Universal", page_icon="", layout="wide", initial_sidebar_state="expanded")
st.markdown(CSS, unsafe_allow_html=True)

#  SIDEBAR 
with st.sidebar:
    st.markdown('<div style="padding:12px 0 8px"><div style="font-size:1.1rem;font-weight:700;color:#e8eaf0"> Pemara Universal</div><div style="font-size:.68rem;color:#5a7fa8;font-family:monospace">Documental  Studio  Org IA</div></div>', unsafe_allow_html=True)
    st.divider()
    r = _get(f"{URL_CADASTRO}/status")
    if r:
        d = r.json()
        st.markdown(f'<div class="sc"><div class="lb">Cadastro</div><div class="vl">{d["preenchidos"]}/{d["total"]} campos</div></div>', unsafe_allow_html=True)
    r2 = _get(f"{URL_HISTORICO}/status")
    if r2:
        d2 = r2.json()
        st.markdown(f'<div class="sc"><div class="lb">Docs Processados</div><div class="vl">{d2["total_registros"]}</div></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown('<div style="color:#5a7fa8;font-size:.68rem;margin-bottom:7px">MICROSERVIaOS</div>', unsafe_allow_html=True)
    for nome, url in [("Cadastro", f"{URL_CADASTRO}/status"), ("Preenchimento", f"{URL_PREENCHIMENTO}/status"),
                       ("Conversor", f"{URL_CONVERSOR}/status"), ("Histarico", f"{URL_HISTORICO}/status"),
                       ("Studio Pro", f"{URL_STUDIO}/api/status"), ("Organizador", f"{URL_ORGANIZADOR}/status")]:
        try: ok = requests.get(url, timeout=2).status_code == 200
        except: ok = False
        cls, lbl = ("ok","online") if ok else ("er","offline")
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px"><span style="color:#8b949e;font-size:.78rem">{nome}</span><span class="sb {cls}"> {lbl}</span></div>', unsafe_allow_html=True)

#  HEADER 
st.markdown('<div class="hdr"><h1> Pemara Universal</h1><div class="sub">Motor Documental  Studio Pro (audio/Vadeo/Imagem GPU)  Organizador IA  Arquitetura Microserviaos</div></div>', unsafe_allow_html=True)

modulo = st.radio("", [" Pemara Documental", " Studio Pro", " Organizador IA"], horizontal=True, label_visibility="collapsed")
st.divider()

#  MaDULO 1  PEMARA DOCUMENTAL 
if modulo == " Pemara Documental":
    aba1, aba2, aba3, aba4 = st.tabs([" Auto-Preencher", " Meus Dados", " Conversor", " Histarico & Logs"])

    with aba1:
        st.markdown("### Preenchimento Automatico de PDF")
        c1, c2 = st.columns([3, 2])
        with c1:
            arq = st.file_uploader("Selecione o PDF", type=["pdf"], key="up1")
        with c2:
            st.markdown('<div class="sc"><div class="lb">Serviao</div><div class="vl" style="font-size:.85rem">Preenchimento (porta 8002)</div></div>', unsafe_allow_html=True)
        if arq:
            pdf = arq.read()
            st.success(f" {arq.name} ({len(pdf)//1024} KB)")
            with st.expander(" Pravia do texto"):
                r = _post(f"{URL_PREENCHIMENTO}/extrair-texto", files={"arquivo": (arq.name, pdf, "application/pdf")})
                if r: st.text_area("", r.json().get("texto","")[:3000], height=160)
            st.divider()
            if st.button(" Auto-Preencher Agora", use_container_width=True):
                with st.spinner("Processando..."):
                    r = _post(f"{URL_PREENCHIMENTO}/preencher", files={"arquivo": (arq.name, pdf, "application/pdf")}, timeout=TIMEOUT_PROC)
                    if r:
                        modo = r.headers.get("X-Modo","?"); qtd = r.headers.get("X-Campos","0")
                        items = [i for i in r.headers.get("X-Campos-Log","").split(" | ") if i]
                        st.success(f" Modo: **{modo}** | {qtd} campo(s)")
                        if items:
                            with st.expander(" Campos"):
                                for i in items: st.markdown(f'<div class="rc"> {i}</div>', unsafe_allow_html=True)
                        else:
                            st.warning(" Nenhum campo correspondente encontrado.")
                        st.download_button(" Baixar PDF Preenchido", data=r.content, file_name=f"Pemara_{arq.name}", mime="application/pdf", use_container_width=True)
                        _post(f"{URL_HISTORICO}/registros", json={"arquivo": arq.name, "operacao": f"Auto-Preenchimento ({modo})"})

    with aba2:
        st.markdown("### Cadastro de Identidade Digital")
        r = _get(f"{URL_CADASTRO}/campos")
        if r:
            rows = r.json()
            for cat in sorted(set(ro["categoria"] for ro in rows)):
                campos = [ro for ro in rows if ro["categoria"] == cat]
                with st.expander(f"{cat}    {sum(1 for ro in campos if ro['valor'].strip())}/{len(campos)} preenchidos", expanded=True):
                    for ro in campos:
                        c1, c2, c3 = st.columns([3,4,1])
                        c1.markdown(f'<div style="padding-top:9px;color:#8b949e;font-size:.82rem">{ro["campo"]}</div>', unsafe_allow_html=True)
                        with c2:
                            nv = st.text_input(ro["campo"], value=ro["valor"], key=f"c{ro['id']}", label_visibility="collapsed")
                            if nv != ro["valor"]: _put(f"{URL_CADASTRO}/campos/{ro['id']}", json={"valor": nv})
                        with c3:
                            st.markdown('<div class="bd">', unsafe_allow_html=True)
                            if st.button("", key=f"d{ro['id']}"): _del(f"{URL_CADASTRO}/campos/{ro['id']}"); st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)
            st.divider()
            st.markdown("####  Novo campo")
            with st.form("nf", clear_on_submit=True):
                cats = sorted(set(ro["categoria"] for ro in rows))
                c1, c2 = st.columns([2,3])
                nc = c1.selectbox("Categoria", cats + ["Nova..."])
                ncc = c1.text_input("Nova categoria", placeholder="Ex: Saade")
                nm = c2.text_input("Nome do campo", placeholder="Ex: Tipo Sanguaneo")
                nv = c2.text_input("Valor inicial", value="")
                if st.form_submit_button("Adicionar") and nm.strip():
                    cf = ncc.strip() if nc == "Nova..." and ncc.strip() else nc
                    _post(f"{URL_CADASTRO}/campos", json={"categoria": cf, "campo": nm.strip(), "valor": nv.strip()}); st.rerun()

    with aba3:
        st.markdown("### Conversor de Documentos")
        modo = st.radio("Tipo", ["PDF  Word", "Word  PDF"], horizontal=True)
        arq = st.file_uploader("Selecione", type=["pdf"] if "PDF " in modo else ["docx"], key="uc")
        if arq:
            cb = arq.read()
            st.success(f" {arq.name} ({len(cb)//1024} KB)")
            if "PDF " in modo:
                if st.button(" Converter para Word", use_container_width=True):
                    with st.spinner("Convertendo..."):
                        r = _post(f"{URL_CONVERSOR}/pdf-para-docx", files={"arquivo":(arq.name,cb,"application/pdf")}, timeout=TIMEOUT_PROC)
                        if r: st.success(""); st.download_button(" Baixar Word", data=r.content, file_name=arq.name.replace(".pdf",".docx"), mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            else:
                if st.button(" Converter para PDF", use_container_width=True):
                    with st.spinner("Convertendo (LibreOffice necessario)..."):
                        r = _post(f"{URL_CONVERSOR}/docx-para-pdf", files={"arquivo":(arq.name,cb,"application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, timeout=TIMEOUT_PROC)
                        if r: st.success(""); st.download_button(" Baixar PDF", data=r.content, file_name=arq.name.replace(".docx",".pdf"), mime="application/pdf", use_container_width=True)

    with aba4:
        ch, cl = st.columns(2)
        with ch:
            st.markdown("###  Histarico")
            if st.button(" Limpar"): _del(f"{URL_HISTORICO}/registros"); st.rerun()
            r = _get(f"{URL_HISTORICO}/registros")
            if r:
                for it in r.json(): st.markdown(f'<div class="sc" style="margin-bottom:7px"><div style="color:#8b949e;font-size:.69rem">{it["data_hora"]}</div><div style="color:#e8eaf0;font-size:.83rem;font-weight:600">{it["arquivo"]}</div><div style="color:#58a6ff;font-size:.75rem">{it["operacao"]}</div></div>', unsafe_allow_html=True)
        with cl:
            st.markdown("###  Logs")
            r = _get(f"{URL_HISTORICO}/logs", params={"linhas":80})
            if r:
                d = r.json(); st.text_area("", d.get("conteudo",""), height=380)
                if d.get("conteudo"): st.download_button(" Log", data=d["conteudo"].encode(), file_name=d.get("arquivo","log.txt"))


#  MaDULO 2  STUDIO PRO 
elif modulo == " Studio Pro":
    r = _get(f"{URL_STUDIO}/api/status")
    if r:
        hw = r.json()
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("GPU", hw.get("device","CPU")[:20])
        c2.metric("Temp", f"{hw['temp']}C" if hw.get("temp") is not None else "--")
        c3.metric(
            "VRAM",
            f"{hw['vram_u']}/{hw['vram_t']} GB"
            if hw.get("vram_u") is not None and hw.get("vram_t") is not None
            else "--",
        )
        c4.metric("Uso GPU", f"{hw['load']}%" if hw.get("load") is not None else "--")
        st.divider()

    t1,t2,t3,t4,t5,t6 = st.tabs([" Conversor audio"," Transcriaao IA"," DSP Forense"," Isolar Voz"," Editor Vadeo"," Imagem"])

    with t1:
        st.markdown("### Conversor de audio Universal")
        arqs = st.file_uploader("Arquivo(s) de audio", type=["mp3","wav","flac","aac","ogg","opus","m4a","wma"], accept_multiple_files=True, key="ac")
        c1,c2 = st.columns(2)
        fmt = c1.selectbox("Formato saada", ["mp3","wav","flac","aac","ogg","opus","m4a"])
        qual = c2.selectbox("Qualidade", ["320k","256k","192k","128k"])
        if arqs and st.button(" Converter", use_container_width=True, key="bac"):
            with st.spinner(f"Convertendo  {fmt}..."):
                files = [("files",(f.name,f.read(),f.type or "audio/mpeg")) for f in arqs]
                r = _post(f"{URL_STUDIO}/api/audio/converter", files=files, data={"formato_saida":fmt,"qualidade":qual}, timeout=TIMEOUT_PROC)
                if r:
                    nome = "Audio_Convertido.zip" if len(arqs)>1 else f"{arqs[0].name.rsplit('.',1)[0]}.{fmt}"
                    st.success(""); st.download_button(" Baixar", data=r.content, file_name=nome, use_container_width=True)

    with t2:
        st.markdown("### Transcriaao com Whisper IA")
        arqs = st.file_uploader("Arquivo(s) de audio/vadeo", type=["mp3","wav","m4a","flac","ogg","opus","mp4","mkv"], accept_multiple_files=True, key="tr")
        c1,c2,c3 = st.columns(3)
        mod_wh = c1.selectbox("Modelo", ["large-v3","medium","small","base"])
        idi_wh = c2.selectbox("Idioma", ["pt","en","es","auto"])
        fmt_tr = c3.selectbox("Formato", ["txt","srt","vtt"])
        if arqs and st.button(" Transcrever", use_container_width=True, key="btr"):
            with st.spinner(f"Transcrevendo com {mod_wh}..."):
                files = [("files",(f.name,f.read(),f.type or "audio/mpeg")) for f in arqs]
                r = _post(f"{URL_STUDIO}/api/audio/transcrever", files=files, data={"modelo":mod_wh,"idioma":idi_wh,"formato_saida":fmt_tr}, timeout=TIMEOUT_PROC)
                if r:
                    nome = "Transcricoes.zip" if len(arqs)>1 else f"{arqs[0].name.rsplit('.',1)[0]}.{fmt_tr}"
                    st.success(" Transcriaao concluada!")
                    if len(arqs)==1: st.text_area("Resultado", r.content.decode("utf-8","replace"), height=280)
                    st.download_button(" Baixar", data=r.content, file_name=nome, use_container_width=True)

    with t3:
        st.markdown("### Tratamento Forense DSP")
        arq = st.file_uploader("Arquivo de audio", type=["mp3","wav","m4a","flac","ogg"], accept_multiple_files=False, key="dsp")
        c1,c2 = st.columns(2)
        nr_a = c1.toggle("Reduaao de Ruado", True)
        nr_i = c1.slider("Intensidade NR", 0.5, 3.0, 1.4, 0.1)
        nr_f = c1.slider("Floor NR", 0.05, 0.6, 0.28, 0.01)
        hpf  = c1.slider("Corte HPF (Hz)", 50, 500, 100, 10)
        eq1h = c2.slider("EQ Banda 1 - Hz", 500, 5000, 2500, 50)
        eq1d = c2.slider("EQ Banda 1 - dB", -6.0, 12.0, 5.0, 0.5)
        eq2h = c2.slider("EQ Banda 2 - Hz", 1000, 7000, 4000, 50)
        eq2d = c2.slider("EQ Banda 2 - dB", -6.0, 12.0, 4.0, 0.5)
        vol  = c2.slider("Volume alvo (dBFS)", -20.0, -3.0, -8.5, 0.5)
        if arq and st.button(" Processar DSP", use_container_width=True, key="bdsp"):
            with st.spinner("Pipeline DSP..."):
                arq.seek(0)
                r = _post(f"{URL_STUDIO}/api/audio/forense_custom",
                          files={"file":(arq.name,arq.read(),"audio/mpeg")},
                          data={"nr_intensidade":nr_i,"nr_floor":nr_f,"nr_ativo":str(nr_a).lower(),
                                "hpf_hz":hpf,"box_cut_hz":0,"box_cut_db":-4,
                                "eq1_hz":eq1h,"eq1_db":eq1d,"eq2_hz":eq2h,"eq2_db":eq2d,
                                "eq3_hz":7000,"eq3_db":3,"volume_target":vol},
                          timeout=TIMEOUT_PROC)
                if r: st.success(""); st.download_button(" Baixar WAV Tratado", data=r.content, file_name=f"TRATADO_{arq.name.rsplit('.',1)[0]}.wav", use_container_width=True)

    with t4:
        st.markdown("### Isolamento de Voz (Demucs IA)")
        st.caption("Separa voz de instrumentos e ruados usando redes neurais. Requer GPU.")
        arq = st.file_uploader("Arquivo de audio", type=["mp3","wav","m4a","flac"], key="iso")
        if arq and st.button(" Isolar Voz", use_container_width=True, key="biso"):
            with st.spinner("Demucs processando (pode demorar)..."):
                arq.seek(0)
                r = _post(f"{URL_STUDIO}/api/audio/isolar", files={"file":(arq.name,arq.read(),"audio/mpeg")}, timeout=TIMEOUT_PROC)
                if r: st.success(""); st.download_button(" Baixar Voz Isolada", data=r.content, file_name=f"VOZ_{arq.name.rsplit('.',1)[0]}.wav", use_container_width=True)

    with t5:
        st.markdown("### Editor & Conversor de Vadeo")
        arq = st.file_uploader("Arquivo de vadeo", type=["mp4","mkv","mov","avi","webm"], accept_multiple_files=False, key="vid")
        c1,c2 = st.columns(2)
        fmt_v  = c1.selectbox("Formato saada", ["mp4","mkv","mov","webm","avi"])
        codec_v = c1.selectbox("Codec", ["auto","extreme","nvenc_h264","nvenc_h265","h264","h265"])
        crf_v   = c2.slider("CRF (menor=melhor)", 15, 35, 23)
        ini_v   = c2.number_input("Inacio corte (s)", 0.0)
        fim_v   = c2.number_input("Fim corte (s, 0=final)", 0.0)
        ext_aud = st.checkbox("Extrair apenas audio (MP3)")
        if arq:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(" Processar Vadeo", use_container_width=True, key="bvid"):
                    with st.spinner("FFmpeg..."):
                        arq.seek(0)
                        r = _post(f"{URL_STUDIO}/api/video/editor",
                                  files={"file":(arq.name,arq.read(),"video/mp4")},
                                  data={"formato_saida":"mp3" if ext_aud else fmt_v,"codec":codec_v,"crf":crf_v,"inicio":ini_v,"fim":fim_v,"extrair_audio":str(ext_aud).lower()},
                                  timeout=TIMEOUT_PROC)
                        if r:
                            ext = "mp3" if ext_aud else fmt_v
                            st.success(""); st.download_button(" Baixar", data=r.content, file_name=f"{arq.name.rsplit('.',1)[0]}_editado.{ext}", use_container_width=True)
            with col2:
                esc_r = st.selectbox("Escala upscale", [2,4], key="escr")
                mod_r = st.selectbox("Modo", ["rapido","ai"], key="modr", help="ai = Real-ESRGAN frame a frame (lento)")
                if st.button(" Remasterizar (Upscale IA)", use_container_width=True, key="brem"):
                    with st.spinner("Real-ESRGAN processando..."):
                        arq.seek(0)
                        r = _post(f"{URL_STUDIO}/api/video/remasterizar",
                                  files={"file":(arq.name,arq.read(),"video/mp4")},
                                  data={"escala":esc_r,"modo":mod_r,"denoise":"false"},
                                  timeout=TIMEOUT_PROC)
                        if r: st.success(""); st.download_button(" Baixar", data=r.content, file_name=f"{arq.name.rsplit('.',1)[0]}_remasterizado.mp4", use_container_width=True)

    with t6:
        st.markdown("### Processador de Imagem")
        arq = st.file_uploader("Selecione a imagem", type=["jpg","jpeg","png","webp","bmp"], key="img")
        fmt_img = st.selectbox("Formato saada", ["png","jpg","webp","tiff"])
        acao = st.radio("Aaao", ["Remover Fundo (IA)","Upscale 4K (ESRGAN)","Ajustes Manuais","Redimensionar"], horizontal=True)
        params_json = "{}"
        if acao == "Ajustes Manuais":
            c1,c2 = st.columns(2)
            br=c1.slider("Brilho",0.2,2.0,1.0,0.05); co=c1.slider("Contraste",0.2,2.0,1.0,0.05)
            sa=c2.slider("Saturaaao",0.0,2.0,1.0,0.05); ni=c2.slider("Nitidez",0.0,2.0,1.0,0.05)
            rot=st.select_slider("Rotaaao",[0,90,180,270])
            params_json=f'{{"brilho":{br},"contraste":{co},"saturacao":{sa},"nitidez":{ni},"rotacao":{rot}}}'
        elif acao == "Redimensionar":
            c1,c2=st.columns(2)
            la=c1.number_input("Largura (px)",value=1920); al=c2.number_input("Altura (px)",value=1080)
            params_json=f'{{"largura":{int(la)},"altura":{int(al)}}}'
        acao_map={"Remover Fundo (IA)":"rembg","Upscale 4K (ESRGAN)":"upscale","Ajustes Manuais":"ajustar","Redimensionar":"redimensionar"}
        if arq and st.button(" Processar Imagem", use_container_width=True, key="bimg"):
            with st.spinner("Processando imagem..."):
                arq.seek(0)
                r = _post(f"{URL_STUDIO}/api/imagem/processar",
                          files={"file":(arq.name,arq.read(),"image/jpeg")},
                          data={"acao":acao_map[acao],"params_json":params_json,"formato_saida":fmt_img},
                          timeout=TIMEOUT_PROC)
                if r:
                    nome=f"{arq.name.rsplit('.',1)[0]}_proc.{fmt_img}"
                    st.success(""); st.image(r.content,caption=nome,use_column_width=True)
                    st.download_button(" Baixar Imagem",data=r.content,file_name=nome,mime=f"image/{fmt_img}",use_container_width=True)


#  MaDULO 3  ORGANIZADOR IA 
elif modulo == " Organizador IA":
    st.markdown("### Organizador Inteligente de Arquivos")
    st.caption("La PDF, Word, Excel, imagens, audio e vadeo  organiza em 5 categorias com IA.")
    c1,c2 = st.columns([1,1])
    with c1:
        pasta = st.text_input(" Pasta raiz", placeholder="Ex: C:\\Documentos ou /home/user/docs")
        motor = st.radio(" Motor IA", ["Gemini", "Claude", "Ollama (Local)", "API Customizada (OpenAI/Local)"], horizontal=True)
        api_key, base_url, modelo = "", "", ""

        if motor == "Gemini":
            api_key = st.text_input(" Chave Gemini", type="password", placeholder="aistudio.google.com")
        elif motor == "Claude":
            api_key = st.text_input(" Chave Anthropic", type="password", placeholder="sk-ant-...")
        elif motor == "Ollama (Local)":
            modelo = st.text_input("Nome do Modelo", value="llama3")
        elif motor == "API Customizada (OpenAI/Local)":
            base_url = st.text_input("URL Base da API", value="http://localhost:1234/v1")
            modelo = st.text_input("Nome do Modelo", placeholder="Ex: gpt-4o, local-model...")
            api_key = st.text_input("API Key (opcional)", type="password")

        dirs = st.text_area(" Diretrizes (obrigatario)", placeholder="Ex: Organize por assunto, priorize documentos fiscais...", height=90)
        dry = st.checkbox(" Pra-visualizaaao (nao move arquivos)", value=True)
        st.info(" Em pra-visualizaaao a IA mostra o plano sem executar.")
        if st.button(" Iniciar Organizaaao", use_container_width=True, disabled=not pasta or not dirs):
            r = _post(f"{URL_ORGANIZADOR}/organizar",
                      json={"pasta":pasta,"motor":motor,"api_key":api_key,"base_url":base_url,"modelo":modelo,"diretrizes":dirs,"modo_dry_run":dry})
            if r: st.success(" Iniciado! Acompanhe ao lado.")

    with c2:
        r = _get(f"{URL_ORGANIZADOR}/progresso")
        if r:
            p = r.json()
            pct = p.get("pct",0.0); etapa = p.get("etapa",""); ativo = p.get("ativo",False); erro = p.get("erro","")
            if ativo: st.progress(pct, text=etapa); st.info(f" {etapa}")
            elif erro: st.error(f" {erro}")
            elif etapa=="Concluado!": st.success(" Concluado!"); st.progress(1.0)
            else: st.caption("Aguardando inacio...")
        r = _get(f"{URL_ORGANIZADOR}/log")
        if r: st.text_area("Log", "\n".join(reversed(r.json().get("logs",[])[-30:])), height=280)

    st.divider()
    st.markdown("###  Histarico de Operaaaes")
    r = _get(f"{URL_ORGANIZADOR}/historico")
    if r:
        hist = r.json()
        if hist:
            for it in hist[:20]:
                st.markdown(f'<div class="sc" style="margin-bottom:6px"><div style="color:#8b949e;font-size:.69rem">{it["data_hora"]}</div><div style="color:#56d364;font-size:.78rem;font-family:monospace">{it["destino"]}</div><div style="color:#8b949e;font-size:.7rem"> {it["origem"]}</div></div>', unsafe_allow_html=True)
        else:
            st.info("Nenhuma operaaao registrada ainda.")

