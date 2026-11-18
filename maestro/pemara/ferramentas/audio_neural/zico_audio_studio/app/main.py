"""Standalone local entrypoint for the same Maestro ZICO router."""
from pathlib import Path
import sys
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
root=Path(__file__).resolve().parents[1]
project=root.parents[2]
sys.path.insert(0,str(project/'services/studio'))
from zico_audio import create_zico_router, capabilities
app=FastAPI(title='ZICO no Maestro',version='1.0.0-maestro')
def internal(request):
    return request.client is not None and request.client.host in {'127.0.0.1','::1'} and not request.headers.get('x-forwarded-for') and request.headers.get('host','').split(':')[0] in {'127.0.0.1','localhost'}
app.include_router(create_zico_router(internal))
@app.get('/')
def root_page():
    return RedirectResponse('/api/zico')
@app.get('/health')
def health():
    return {'status':'ok','integration':'maestro','gpuInferenceRunning':False}
