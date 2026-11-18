"""Optional local H3 Rewriter. Output is always an unapplied proposal."""
from .ir import CreativeError, digest


def workflow(prompt, duration, seed):
    if not isinstance(prompt,str) or not prompt.strip() or len(prompt)>16000:
        raise CreativeError('REWRITER_PROMPT','Brief deve conter até 16.000 caracteres.')
    if type(seed) is not int or not 0 <= seed < 2**63:
        raise CreativeError('REWRITER_SEED','Informe seed explícita.')
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not 4 <= duration <= 15:
        raise CreativeError('REWRITER_DURATION','Duração H3 deve ficar entre 4 e 15 segundos.')
    return {
        '1':{'class_type':'MiniMaxH3PromptWriterOmni','inputs':{
            'reference_layout':'{}','task':'T2AV','resolution':'16:9','duration':duration,'prompt':prompt,
            'model':'Qwen2.5-Omni-7B GGUF Q4_K_M · 6.2 GB download · ~9 GB with the adapter and a 12k context',
            'quantization':'nf4','greedy':True,'seed':seed,'keep_model_loaded':False,'options':['2',0]}},
        '2':{'class_type':'MiniMaxH3RewriterOptions','inputs':{
            'max_new_tokens':1024,'temperature':0.7,'top_p':0.8,'top_k':20,'repetition_penalty':1.05,
            'attn_implementation':'sdpa','adapter':'MiniMax-H3-Prompt-Rewriter-LoRA-Omni-F16.gguf · 0.65 GB download',
            'gguf_runtime':'llama.cpp','llama_backend':'cuda','device':'cuda:0','auto_download':False,'n_ctx':8192}},
        '3':{'class_type':'PreviewAny','inputs':{'source':['1',0]}}}


def execute(ns, prompt, duration, seed, *, progress_cb=None,cancel_event=None,prompt_id_cb=None,resume_prompt_id=''):
    """Maestro worker transport; Codex must use its MCP tools instead."""
    graph=workflow(prompt,duration,seed)
    prompt_id,outputs=ns['_queue_comfy_workflow'](graph,timeout=900,progress_cb=progress_cb,
        cancel_event=cancel_event,prompt_id_cb=prompt_id_cb,resume_prompt_id=resume_prompt_id)
    texts=[o['text'] for o in outputs if o.get('kind')=='text' and o.get('node')=='3']
    if len(texts)!=1 or not texts[0].strip(): raise CreativeError('REWRITER_OUTPUT','Rewriter não entregou uma sugestão única.')
    return {'ok':True,'mode':'prompt_rewrite','engine_id':'minimax_h3','prompt_id':prompt_id,
        'text':texts[0],'outputs':outputs,'seed':seed,'message':'Sugestão pronta para revisão; texto original preservado.',
        'rewriter':{'workflow_hash':digest(graph),'source_prompt_hash':digest(prompt),'applied':False,
            'semantic_constraints_verified':False,'human_verdict':None}}


def qualification(root,nodes,runtime):
    import json
    from pathlib import Path
    from .assets import file_hash
    try:
        record=json.loads((Path(root)/'rewriter_qualification_20260907.json').read_text(encoding='utf-8'))
        if record.get('technical_status')!='PASS' or not record.get('code_files'): return None
        if (runtime.get('system') or {}).get('comfyui_version')!='0.34.2': return None
        if not {'MiniMaxH3PromptWriterOmni','MiniMaxH3RewriterOptions','PreviewAny'} <= set(nodes): return None
        if any(file_hash(p)!=sha for p,sha in record['code_files'].items()): return None
        return {'integrated':True,'enabled':True,'experimental':True,'auto_apply':False,
            'scope':'Text-only H3 T2AV prompt proposal; cached local weights; human review required',
            'reason':'PINNED_LOCAL_REWRITER_BENCHMARK_PASS'}
    except (OSError,ValueError,KeyError): return None
