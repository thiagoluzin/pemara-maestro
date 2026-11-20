"""Private Studio routes for the episode workspace."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

import scene_workspace as scenes


def router(root, internal, read_body):
    def require_internal(request: Request):
        if not internal(request):
            raise HTTPException(403, "Use o painel Maestro.")
    api = APIRouter(prefix="/api", dependencies=[Depends(require_internal)])

    async def run(func, *args):
        try:
            return await run_in_threadpool(func, *args)
        except FileNotFoundError:
            raise HTTPException(404, "Projeto, take, modelo ou versão indisponível.")
        except FileExistsError:
            raise HTTPException(409, "Já existe um episódio com esse nome.")
        except (ValueError, TypeError):
            raise HTTPException(422, "Confira o nome, o tipo da produção e a duração das cenas.")

    @api.get("/episode-templates")
    def list_templates():
        return {"data": [{k: v for k, v in t.items() if k != "scenes"} | {"sceneCount": len(t["scenes"])}
                         for t in scenes.templates(root)]}

    @api.post("/episode-templates", status_code=201)
    async def save(request: Request):
        body = await read(request)
        if "sourceProjectId" in body:
            return await run(scenes.save_project_template, root, body["sourceProjectId"], body.get("name"))
        return await run(scenes.save_template, root, body.get("name"), body.get("scenes"), body.get("contentKind"), body.get("stages"))

    async def read(request):
        try:
            return await read_body(request)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @api.post("/episode-templates/{template_id}/episodes", status_code=201)
    async def create(template_id: str, request: Request):
        body = await read(request)
        return await run(scenes.instantiate, root, template_id, body.get("name"))

    @api.get("/video-projects/{project_id}/takes/{take_id}/versions")
    async def versions(project_id: str, take_id: str):
        return await run(lambda: {"data": [v for v, _ in scenes.versions(root, project_id, take_id)]})

    @api.get("/video-projects/{project_id}/takes/{take_id}/frame-marks")
    async def marks(project_id: str, take_id: str):
        return {"data": await run(scenes.list_marks, root, project_id, take_id)}

    @api.post("/video-projects/{project_id}/takes/{take_id}/frame-marks", status_code=201)
    async def mark(project_id: str, take_id: str, request: Request):
        body = await read(request)
        return await run(scenes.mark_frame, root, project_id, take_id, body.get("versionId"), body.get("seconds"))

    @api.api_route("/video-projects/{project_id}/takes/{take_id}/versions/{version_id}", methods=["GET", "HEAD"])
    async def version(project_id: str, take_id: str, version_id: str):
        def locate():
            for item, path in scenes.versions(root, project_id, take_id):
                if item["versionId"] == version_id:
                    return path
            raise FileNotFoundError
        return FileResponse(await run(locate), headers={"Cache-Control": "private, no-store"})

    return api

