"""Loopback-only disposable UI fixture. Never imports Studio or submits GPU work."""
import json
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RECORD={'id':'fixture_generation','engine_id':'minimax_h3','human_verdict':None,'status':'done',
        'ir':{'content':{'description':'TESTE ISOLADO — pátio neutro do benchmark'}},
        'artifacts':[{'kind':'video','sha256':'fixture_hash'}]}
attached=False
shot={}; proposal={}; rewrite_events=[]; timeline_events=[]; control_events=[]; all_in_one_events=[]; semantic_events=[]

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def send(self,data,mime='application/json'):
  data=data if isinstance(data,bytes) else json.dumps(data).encode()
  self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if self.path=='/':
   self.send(b'<html><meta charset="utf-8"><title>Creative OS UI fixture</title><body style="background:#17202c;color:#eee;font:16px sans-serif;padding:24px"><h1>Teste isolado da interface</h1><p>Nenhuma acao neste ambiente gera ou aprova midia de producao.</p><label>Prompt de teste<textarea id="gen-prompt">Original de teste</textarea></label><input id="gen-mode" value="text_video" type="hidden"><input id="gen-engine-id" value="minimax_h3" type="hidden"><label>Duracao<input id="gen-video-duration" value="5" type="number"></label><div class="gen-workspace"></div><script src="/creative-os.js"></script></body></html>','text/html; charset=utf-8')
  elif self.path=='/creative-os.js': self.send((ROOT/'app/assets/creative-os.js').read_bytes(),'text/javascript')
  elif '/artifacts/' in self.path: self.send((ROOT/'dados/creative_os/benchmarks/20260907/h3_outputs/a4de437b_000.mp4').read_bytes(),'video/mp4')
  elif '/generative/jobs' in self.path: self.send({'items':[{'job_id':'fixture_job','mode':'video','engine_id':'minimax_h3','status':'done','prompt':'Patio neutro'}]})
  elif self.path.endswith('/generations'): self.send([RECORD] if attached else [])
  elif '/generations/' in self.path: self.send(RECORD)
  elif self.path.endswith('/semantic-jobs'): self.send([{'id':'fixture_semantic','generation_id':RECORD['id'],'artifact_sha256':'fixture_hash'}] if semantic_events else [])
  elif '/semantic-jobs/' in self.path: self.send({'id':'fixture_semantic','state':'DONE','review':{'summary':'Consulta visual de teste; nenhuma aprovacao.','observations':{'identity':{'status':'uncertain','evidence':'Sem referencia.'}}}})
  elif self.path.endswith('/hq'): self.send({'jobs':[],'profiles':{}})
  elif '/rewriter-jobs/' in self.path: self.send({'id':'fixture_rewriter','state':'DONE','proposal_id':'fixture_proposal'})
  elif '/prompt-proposals/' in self.path: self.send(proposal)
  elif self.path=='/fixture/state': self.send({'rewrite_events':rewrite_events,'timeline_events':timeline_events,'control_events':control_events,'all_in_one_events':all_in_one_events,'semantic_events':semantic_events,'proposal':proposal,'production_submissions':0,'production_approvals':0})
  else: self.send({})
 def do_POST(self):
  global attached,shot,proposal
  raw=self.rfile.read(int(self.headers.get('Content-Length','0')))
  if self.path.endswith('/control-assets'):
   control_events.append('uploaded_fixture');self.send({'id':'fixture_control','project_id':'maestro_control'});return
  data=json.loads(raw or b'{}')
  if self.path.endswith('/shots'):
   shot={'id':'fixture_shot','ir':data};self.send(shot)
  elif self.path.endswith('/timeline-plan'):
   timeline_events.append('prepared');self.send({'segment_count':2,'output_frames':226})
  elif self.path.endswith('/timeline-generate'):
   timeline_events.append('submitted_fixture');self.send({'status':'queued','id':'fixture_timeline'})
  elif self.path.endswith('/control-generate'):
   control_events.append('submitted_fixture');self.send({'status':'queued','id':'fixture_control_job'})
  elif self.path.endswith('/generate'):
   all_in_one_events.append(data.get('bindings'));self.send({'status':'queued','id':'fixture_all_in_one'})
  elif self.path.endswith('/rewrite'):
   proposal={'id':'fixture_proposal','original_description':shot['ir']['content']['description'],'suggestion':'Candidato de teste revisavel','suggestion_hash':'fixture_suggestion_hash','status':'PENDING_HUMAN_REVIEW'}
   rewrite_events.append('rewrite_requested');self.send({'id':'fixture_rewriter','state':'QUEUED'})
  elif '/prompt-proposals/' in self.path and self.path.endswith('/verdict'):
   rewrite_events.append(data['decision']);proposal['status']=data['decision'].upper();self.send(proposal)
  elif '/prompt-proposals/' in self.path and self.path.endswith('/apply'):
   rewrite_events.append('applied');proposal['status']='APPLIED';self.send(proposal)
  elif self.path.endswith('/semantic-review'): semantic_events.append('requested_fixture');self.send({'id':'fixture_semantic'})
  elif self.path.endswith('/attach'): attached=True; self.send(RECORD)
  elif self.path.endswith('/evaluate'): self.send({'technical_pass':True,'human_approved':False})
  elif self.path.endswith('/verdict'): RECORD['human_verdict']=data['decision']; self.send(RECORD)
  else: self.send({'fixture':True})

if __name__=='__main__': HTTPServer(('127.0.0.1',8098),Handler).serve_forever()
