"""Maestro project and scene tools over local MCP stdio."""
from typing import Annotated, Literal
import os

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

server = FastMCP("Maestro", instructions="Work with Maestro projects, episode templates and take direction. Human review takes place in Maestro.")
read = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
Project = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
Take = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,31}$")]
Template = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Name = Annotated[str, Field(min_length=3, max_length=120)]
Page = Annotated[int, Field(ge=1)]
Size = Annotated[int, Field(ge=1, le=100)]


class Scene(BaseModel):
    name: Name
    durationSeconds: Annotated[float, Field(gt=0, le=7200, allow_inf_nan=False)]
    direction: Annotated[str, Field(max_length=6000)] = ""


def api(method, route, **kwargs):
    port = int(os.getenv("MAESTRO_STUDIO_PORT", "8029"))
    url = f"http://127.0.0.1:{port}/api/{route}"
    try:
        with httpx.Client(timeout=45, trust_env=False, follow_redirects=False) as client:
            response = client.request(method, url, **kwargs)
    except httpx.RequestError as exc:
        raise ValueError("Studio local indisponível.") from exc
    if not response.is_success:
        raise ValueError(f"Studio HTTP {response.status_code}. Confira o identificador, os dados e o estado do projeto.")
    return response.json()


def subset(data, keys):
    return {k: data[k] for k in keys.split() if k in data}


@server.tool(annotations=read)
def list_projects(page: Page = 1, page_size: Size = 20) -> dict:
    """List Maestro projects with their IDs, status and production type."""
    result = api("GET", "video-projects", params={"page": page, "pageSize": page_size})
    return {"data": [subset(p, "projectId name status contentKind durationSeconds") for p in result["data"]],
            "pagination": result["pagination"]}


@server.tool(annotations=read)
def get_project(project_id: Project) -> dict:
    """Read the objective, status, preview and finishing settings of an episode."""
    return subset(api("GET", f"video-projects/{project_id}"), "projectId name objective status contentKind preview final durationSeconds episodeWorkflow")


@server.tool(annotations=read)
def list_scenes(project_id: Project, page: Page = 1, page_size: Size = 30) -> dict:
    """Read scenes in episode order, with direction and human review status."""
    result = api("GET", f"video-projects/{project_id}/takes", params={"page": page, "pageSize": page_size})
    return {"data": [subset(s, "takeId name status durationSeconds animationPrompt keyframeApproved hasPreview hasUpscalePreview") for s in result["data"]],
            "pagination": result["pagination"]}


@server.tool(annotations=read)
def list_versions(project_id: Project, take_id: Take) -> dict:
    """List available media versions for a scene."""
    return api("GET", f"video-projects/{project_id}/takes/{take_id}/versions")


@server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False))
def set_scene_direction(project_id: Project, take_id: Take, direction: Annotated[str, Field(min_length=20, max_length=6000)]) -> dict:
    """Replace the take's written animation direction via Studio, without starting a job."""
    return subset(api("PATCH", f"video-projects/{project_id}/takes/{take_id}", json={"animationPrompt": direction}),
                  "takeId name status animationPrompt")


@server.tool(annotations=read)
def list_frame_marks(project_id: Project, take_id: Take) -> dict:
    """Read the marked instants and exact source version for a scene."""
    return api("GET", f"video-projects/{project_id}/takes/{take_id}/frame-marks")


@server.tool(annotations=read)
def list_episode_templates() -> dict:
    """Find reusable episode outlines."""
    return api("GET", "episode-templates")


@server.tool(annotations=write)
def save_episode_template(name: Name, content_kind: Literal["animation", "live_action", "mixed"],
                          scenes: Annotated[list[Scene], Field(min_length=1, max_length=300)],
                          stages: list[Literal["direction","references","production","review","finishing"]] | None = None) -> dict:
    """Save a named, reusable workflow of ordered scenes, durations and direction."""
    result = api("POST", "episode-templates", json={"name": name, "contentKind": content_kind,
                 "scenes": [s.model_dump() for s in scenes], "stages": stages})
    return subset(result, "templateId name contentKind createdAt")


@server.tool(annotations=write)
def create_episode_from_template(template_id: Template, name: Name) -> dict:
    """Create a new, separately named episode in PLANNED state from a template."""
    return subset(api("POST", f"episode-templates/{template_id}/episodes", json={"name": name}),
                  "projectId name status contentKind durationSeconds")


if __name__ == "__main__":
    server.run(transport="stdio")

