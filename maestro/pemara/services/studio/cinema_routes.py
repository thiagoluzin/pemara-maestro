"""Authenticated project-scoped Cinema API."""
import math
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser
from starlette.requests import ClientDisconnect

import cinema_direction as direction
import scene_workspace as scenes
import video_projects as vp
from cinema_queue import Busy, ChatStore

IMAGE_LIMIT = 8 * 1024**2
UPLOAD_LIMIT = IMAGE_LIMIT + 64 * 1024


class UploadTooLarge(MultiPartException):
    pass


async def limited_upload(request):
    size = 0
    try:
        async for chunk in request.stream():
            size += len(chunk)
            if size > UPLOAD_LIMIT:
                raise UploadTooLarge("A imagem deve ter até 8 MiB.")
            yield chunk
    except ClientDisconnect as exc:
        raise MultiPartException("Envio interrompido.") from exc


def router(root,internal,read_body,start_job,store=None):
    store = store or ChatStore()

    def auth(request: Request):
        if not internal(request): raise HTTPException(403,"Entre pelo Maestro.")
    api = APIRouter(prefix="/api/video-projects/{project_id}/cinema",dependencies=[Depends(auth)])

    def folder(project_id: str):
        try: return direction.folder_for(root,project_id)
        except (ValueError,FileNotFoundError): raise HTTPException(404,"Projeto não encontrado.")

    async def call(func,*args):
        try: return await run_in_threadpool(func,*args)
        except (Busy,direction.Conflict) as exc: raise HTTPException(409,str(exc))
        except FileNotFoundError: raise HTTPException(404,"Fonte ou take indisponível.")
        except (ValueError,TypeError) as exc: raise HTTPException(422,str(exc))

    async def payload(request):
        try: return await read_body(request)
        except ValueError as exc: raise HTTPException(422,str(exc))

    @api.get("/direction")
    async def get_direction(f=Depends(folder)):
        return await call(direction.view,f)

    @api.post("/direction")
    async def change_direction(request: Request,f=Depends(folder)):
        return await call(direction.save,f,await payload(request))

    @api.post("/elements",status_code=201)
    async def upload(request: Request,f=Depends(folder)):
        if request.headers.get("content-type","").partition(";")[0].strip().lower() != "multipart/form-data":
            raise HTTPException(415,"Use um formulário de imagem.")
        try:
            form = await MultiPartParser(request.headers,limited_upload(request),max_files=1,max_fields=3,max_part_size=4096).parse()
        except UploadTooLarge as exc:
            raise HTTPException(413,exc.message)
        except (MultiPartException, ValueError):
            raise HTTPException(422,"Formulário de imagem inválido.")
        try:
            image = form.get("file")
            if not isinstance(image,UploadFile):
                raise HTTPException(422,"Escolha uma imagem.")
            if (image.size or 0) > IMAGE_LIMIT:
                raise HTTPException(413,"A imagem deve ter até 8 MiB.")
            if str(form.get("reviewed","")).lower() not in {"1","true","on","yes","t","y"}:
                raise HTTPException(422,"Confirme a referência para o projeto.")
            name,role = form.get("name"),form.get("role")
            blob = await image.read(IMAGE_LIMIT+1)
        finally:
            await form.close()
        return await call(direction.add_element,f,name,role,blob)

    @api.get("/elements/{element_id}")
    async def element(element_id: str,f=Depends(folder)):
        return FileResponse(await call(direction.element_file,f,element_id),headers={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"})

    @api.get("/chat")
    def history(before: int|None=Query(None,ge=1,le=2**63-1),since: int|None=Query(None,ge=0,le=2**63-1),f=Depends(folder)):
        return store.history(f.name,before,since=since)

    def submit(f,data):
        key = str(UUID(str(data.get("id",""))))
        request = data.get("message")
        if not isinstance(request,str) or not 1<=len(request.strip())<=5000: raise ValueError("Mensagem deve ter de 1 a 5000 caracteres.")
        tid = data.get("takeId") or ""
        version = data.get("versionId") or ""
        sec = data.get("seconds",0)
        if type(sec) not in (int,float) or not math.isfinite(sec) or not 0<=sec<=7200: raise ValueError("Instante inválido.")
        if version and (not tid or not isinstance(version,str) or not re.fullmatch("[a-f0-9]{64}",version)):
            raise ValueError("Versão inválida.")
        snap = {"takeId":tid,"versionId":version,"seconds":round(sec,3) if version else 0}
        context = {"selection":snap}
        look = direction.read(f)
        context["revisionFotografia"] = look["revision"]
        context["fotografiaDoEpisodio"] = look["look"]
        if tid:
            item = direction.visible_take(f,tid)
            if version and not any(v["versionId"]==version for v,_ in scenes.versions(root,f.name,tid)):
                raise direction.Conflict("A versão mudou. Reabra a cena.")
            context["take"] = {"nome":item.get("name") or item.get("slug"),"estado":vp._take_status(item),
                               "direcao":str(item.get("animation_prompt") or item.get("objective") or "")[:6000],
                               "fotografia":look["shots"].get(tid,{})}
            refs = set(context["take"]["fotografia"].get("elements",[]))
            context["referenciasSelecionadas"] = [a["name"] for a in direction.gallery(f,look) if a["id"] in refs]
        return {"id":store.submit(f.name,key,request.strip(),context)}

    @api.post("/chat",status_code=202)
    async def send(request:Request,f=Depends(folder)):
        return await call(submit,f,await payload(request))

    @api.post("/chat/{key}/cancel")
    async def cancel(key:UUID,request:Request,f=Depends(folder)):
        await payload(request)
        await call(store.cancel,f.name,str(key))
        return {"ok":True}

    def apply(f,key,kind,name):
        if kind not in {"correction","shots","photography","produce"}: raise ValueError("Ação desconhecida.")
        if kind=="shots" and (not isinstance(name,str) or not 3<=len(name.strip())<=120):
            raise ValueError("Informe um nome para o modelo.")
        ctx,result = store.reserve_action(f.name,key,kind)
        saved = False
        started = False
        try:
            if kind in {"produce","correction"}:
                tid=ctx["selection"]["takeId"]
                raw=direction.visible_take(f,tid)
                if vp._take_view(raw,f)["generationProfile"] not in vp.MINIMAX_H3_GENERATION_PROFILES:
                    raise direction.Conflict("Selecione o perfil H3 no take antes de produzir.")
                if vp._read_json(f/"project_manifest.json").get("maestro_status")=="COMPLETED":
                    raise direction.Conflict("O projeto está encerrado para produção.")
            if kind=="produce":
                tid=ctx["selection"]["takeId"]
                take=direction.visible_take(f,tid)
                if vp._take_status(take) not in {"PLANNED","ERROR","IN_PRODUCTION"} or vp._take_output_path(f,take):
                    raise direction.Conflict("O take já tem mídia ou produção em andamento.")
                started = True
                detail=start_job(f.name,tid,-1)["jobId"]
            elif kind=="photography":
                proposal=result[kind]
                tid=ctx["selection"]["takeId"] if proposal["scope"]=="take" else ""
                if proposal["scope"]=="take" and not tid: raise ValueError("Selecione um take.")
                data=direction.read(f)
                shot=data["shots"].get(tid,{})
                values=dict(shot.get("values",{}) if tid else data["look"],**proposal["values"])
                started = True
                direction.save(f,{"takeId":tid,"revision":ctx["revisionFotografia"],"values":values,"elements":shot.get("elements",[])})
                detail="Fotografia salva no projeto."
            elif kind=="shots":
                started = True
                record = scenes.save_template(root,name,result["shots"],vp._read_json(f/"project_manifest.json").get("content_kind"))
                detail = record["name"]
            else:
                selection = ctx["selection"]
                tid = selection["takeId"]
                with vp._QUEUE_MUTATION_LOCK:
                    take = direction.visible_take(f,tid)
                    current = vp._take_status(take)
                    if current not in {"READY","APPROVED","REJECTED"} or vp._upscale_candidate_path(f,take,pending_only=True):
                        raise direction.Conflict("O take não está disponível para correção.")
                    pending=vp._latest_director_request(take) or {}
                    if current=="REJECTED" and pending.get("status") in {"PENDING","IN_PROGRESS"}:
                        raise direction.Conflict("O take já tem uma correção em andamento.")
                    first = next(scenes.versions(root,f.name,tid),None)
                    if not first or first[0]["label"]!="Versão atual" or selection["versionId"]!=first[0]["versionId"]:
                        raise direction.Conflict("Selecione a versão atual e envie um novo pedido.")
                    started = True
                    updated = vp.patch_take(root,f.name,tid,{"status":"REJECTED","directorRequest":{"category":"OTHER","reason":result["correction"]}})
                    saved = True
                if not updated.get("canGenerate"):
                    detail = "Direção registrada. Confira os requisitos de produção do take."
                    store.finish_action(key,kind,"direction_saved",detail)
                    return {"detail":detail}
                detail = start_job(f.name,tid,-1)["jobId"]
            store.finish_action(key,kind,"submitted",detail)
            return {"detail":detail}
        except Exception as exc:
            detail = str(exc)[:220] if isinstance(exc,direction.Conflict) else "Confira os requisitos do take e o histórico do projeto."
            message = ("Direção registrada. " if saved else "") + detail
            if started:
                store.finish_action(key,kind,"attention",message)
            else:
                store.release_unstarted_action(key,kind)
            raise direction.Conflict(message)

    @api.post("/chat/{key}/apply/{kind}")
    async def apply_proposal(key:UUID,kind:str,request:Request,f=Depends(folder)):
        body = await payload(request)
        return await call(apply,f,str(key),kind,body.get("name"))
    return api

