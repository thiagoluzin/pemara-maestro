import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import cinema_direction as cd
import cinema_codex
from cinema_queue import ChatStore
from cinema_routes import router
import scene_workspace
import video_projects as vp


class CinemaTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.store=ChatStore(self.root/"state.db")
        app=FastAPI()
        self.jobs=[]
        def start(pid,tid,seed):
            self.jobs.append((pid,tid))
            return {"jobId":"fixture-job"}
        app.include_router(router(self.root,lambda r:r.headers.get("x-owner")=="yes",lambda r:r.json(),start,self.store))
        self.client=TestClient(app,headers={"x-owner":"yes"})
        vp.create_project(self.root,name="Cinema teste",project_id="piloto",content_kind="animation")
        self.folder=self.root/"piloto"
        self.url="/api/video-projects/piloto/cinema"
        self.video=self.folder/"takes"/"media.mp4"
        self.video.write_bytes(b"fixture")
        q=vp._queue(self.folder)
        q["takes"]=[{"id":"T01","name":"Cena","target_duration_seconds":5,"maestro_status":"READY","video":{"output_active":str(self.video)}}]
        vp._atomic_json_write(vp._queue_path(self.folder),q)

    def test_reference_inheritance_and_revision(self):
        u=self.url
        self.assertEqual(self.client.get(u+"/direction",headers={"x-owner":"no"}).status_code,403)
        d=self.client.post(u+"/direction",json={"revision":0,"values":{"lighting":"Luz da manhã","palette":"Âmbar"}}).json()
        image=io.BytesIO()
        Image.new("RGB",(24,16)).save(image,"PNG")
        response=self.client.post(u+"/elements",files={"file":("fixture.png",image.getvalue(),"image/png")},
                                  data={"reviewed":"true","role":"cenário","name":"Corredor"})
        self.assertEqual(response.status_code,201,response.text)
        item=response.json()["elements"][0]
        self.assertEqual(self.client.get(u+"/elements/"+item["id"]).content,image.getvalue())
        req={"revision":d["revision"],"takeId":"T01","values":{"palette":"Fria","lens":"50 mm"},"elements":[item["id"]]}
        self.assertEqual(self.client.post(u+"/direction",json=req).status_code,409)
        req["revision"]=response.json()["revision"]
        self.assertEqual(self.client.post(u+"/direction",json=req).status_code,200)
        prompt=cd.prompt_direction(self.folder,"T01")
        for token in ["Luz da manhã","Fria","50 mm","Corredor"]: self.assertIn(token,prompt)
        self.assertNotIn("Âmbar",prompt)
        control={"mode":"ref2va_motion","referenceImages":[],"referenceDefinitions":[],"referenceSubjects":[]}
        cd.prompt_direction(self.folder,"T01",control)
        self.assertEqual(control["referenceImages"][0].read_bytes(),image.getvalue())
        self.assertEqual(control["referenceSubjects"][0]["sources"],["<Picture 1>"])

    def test_chat_replay_and_application(self):
        source=next(scene_workspace.versions(self.root,"piloto","T01"))[0]["versionId"]
        req={"id":str(uuid4()),"message":"Prepare um roteiro","takeId":"T01","seconds":2,"versionId":source}
        for _ in range(2):self.assertEqual(self.client.post(self.url+"/chat",json=req).status_code,202)
        self.assertEqual(self.client.post(self.url+"/chat",json=req|{"id":str(uuid4())}).status_code,409)
        row=self.store.claim()
        result={"answer":"Dois planos.","correction":"","photography":{"scope":"take","values":{"movement":"Dolly"}},
                "shots":[{"name":"Janela","durationSeconds":4,"direction":"Abrir a janela.","photography":{"lens":"35 mm"}}],
                "triage":{"choice":"aligned"}}
        self.store.update(row["id"],"done","Concluído",result)
        for action in ["shots","photography"]:
            url=self.url+"/chat/"+row["id"]+"/apply/"+action
            self.assertEqual(self.client.post(url,json={"name":"Modelo piloto"}).status_code,200)
            self.assertEqual(self.client.post(url,json={"name":"Modelo piloto"}).status_code,409)
        self.assertIn("Dolly",cd.prompt_direction(self.folder,"T01"))
        models=scene_workspace.templates(self.root)
        p=scene_workspace.instantiate(self.root,models[0]["templateId"],"Próximo teste")
        self.assertIn("35 mm",cd.prompt_direction(self.root/p["projectId"],"T01"))
        logs=self.client.get(self.url+"/chat").json()["items"]
        self.assertEqual(len(logs),1)
        self.assertEqual(logs[0]["selection"]["seconds"],2)
        self.assertEqual(self.jobs,[])

    def test_upload_limit_precedes_reference_registration(self):
        image=io.BytesIO()
        Image.new("RGB",(2,2)).save(image,"PNG")
        with patch("cinema_routes.UPLOAD_LIMIT",100):
            response=self.client.post(self.url+"/elements",files={"file":("ref.png",image.getvalue(),"image/png")},
                                      data={"name":"Céu","role":"cenário","reviewed":"true"})
        self.assertEqual(response.status_code,413)
        self.assertEqual(cd.read(self.folder)["elements"],[])

    def test_restart_and_cancel(self):
        req={"id":str(uuid4()),"message":"teste"}
        self.client.post(self.url+"/chat",json=req)
        self.store.claim()
        self.store.recover()
        self.assertEqual(self.store.history("piloto")["items"][0]["status"],"interrupted")
        key=str(uuid4())
        self.client.post(self.url+"/chat",json=req|{"id":key})
        self.client.post(self.url+"/chat/"+key+"/cancel",json={})
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.history("piloto")["items"][-1]["status"],"cancelled")

    def test_conditional_history_and_worker_status(self):
        url=self.url+"/chat"
        empty=self.client.get(url).json()
        self.store.heartbeat()
        check=self.client.get(url,params={"since":empty["revision"]}).json()
        self.assertEqual(check,{"unchanged":True,"workerOnline":True,"revision":empty["revision"]})
        key=str(uuid4())
        self.client.post(url,json={"id":key,"message":"Prepare dois planos"})
        self.store.claim()
        self.store.update(key,"done","Concluído",{"shots":[{}],"triage":{"choice":"aligned"}})
        latest=self.client.get(url,params={"since":empty["revision"]}).json()
        self.assertEqual(latest["items"][0]["id"],key)
        self.store.reserve_action("piloto",key,"shots")
        reserved=self.client.get(url,params={"since":latest["revision"]}).json()
        self.assertEqual(reserved["items"][0]["actions"]["shots"]["state"],"reserved")
        self.store.finish_action(key,"shots","submitted","Modelo")
        done=self.client.get(url,params={"since":reserved["revision"]}).json()
        self.assertEqual(done["items"][0]["actions"]["shots"]["state"],"submitted")
        self.assertEqual(self.store.history("piloto",before=done["items"][0]["seq"],since=done["revision"])["items"],[])

    def test_account_environment_keeps_only_runtime_fields(self):
        with patch.dict("os.environ",{"USERPROFILE":"profile","TEMP":"tmp","UNRELATED_SETTING":"example",
                                      "STUDIO_INTERNAL_TOKEN":"dummy","GEMINI_API_KEY":"dummy"},clear=True):
            self.assertEqual(cinema_codex.runtime_environment(),{"USERPROFILE":"profile","TEMP":"tmp"})

    def test_production_delegates_once_after_owner_click(self):
        queue=vp._queue(self.folder)
        queue["takes"][0].update(video={},maestro_status="PLANNED",video_generation={"profile":vp.MINIMAX_H3_PROFILE})
        vp._atomic_json_write(vp._queue_path(self.folder),queue)
        key=str(uuid4())
        self.assertEqual(self.client.post(self.url+"/chat",json={"id":key,"message":"Produza esta cena","takeId":"T01"}).status_code,202)
        self.store.claim()
        self.store.update(key,"done","Concluído",{"answer":"Proposta pronta","produce":True,"triage":{"choice":"aligned"}})
        self.assertEqual(self.jobs,[])
        endpoint=self.url+"/chat/"+key+"/apply/produce"
        with patch.object(cd,"visible_take",side_effect=cd.Conflict("Confira a seleção.")):
            self.assertEqual(self.client.post(endpoint,json={}).status_code,409)
        self.assertEqual(self.jobs,[])
        self.assertEqual(self.store.history("piloto")["items"][0]["actions"],{})
        self.assertEqual(self.client.post(endpoint,json={}).status_code,200)
        self.assertEqual(self.client.post(endpoint,json={}).status_code,409)
        self.assertEqual(self.jobs,[("piloto","T01")])


if __name__=="__main__":
    unittest.main()

