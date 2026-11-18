import type {
  EditorCapabilities,
  Project,
  ProjectSummary,
  VoiceJob,
  VoiceSpec,
} from "../types";

const configuredBase = String(import.meta.env.VITE_MAESTRO_API_BASE || "/api/editor").replace(/\/$/, "");

export class MaestroApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status = 0, code = "") {
    super(message);
    this.name = "MaestroApiError";
    this.status = status;
    this.code = code;
  }
}

function apiUrl(path: string): string {
  return `${configuredBase}${path.startsWith("/") ? path : `/${path}`}`;
}

type MaestroRequest = Omit<RequestInit, "body"> & { body?: unknown };

async function request<T>(path: string, options: MaestroRequest = {}): Promise<T> {
  const { body: rawBody, ...requestOptions } = options;
  const headers = new Headers(requestOptions.headers || {});
  let body = rawBody;
  if (body && typeof body !== "string" && !(body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(body);
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(path), { ...requestOptions, headers, body: body as BodyInit | undefined });
  } catch (error) {
    throw new MaestroApiError(
      "Não foi possível acessar o Studio local. Verifique se o Maestro está em execução.",
    );
  }

  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text();
  if (!response.ok) {
    const validation = Array.isArray(payload?.detail)
      ? payload.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join("; ")
      : "";
    throw new MaestroApiError(
      payload?.error?.message || validation || payload?.detail || response.statusText || "Falha no Studio local.",
      response.status,
      payload?.error?.code || "",
    );
  }
  return payload as T;
}

export async function loadCapabilities(): Promise<EditorCapabilities> {
  return request<EditorCapabilities>("/capabilities");
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const payload = await request<{ items?: ProjectSummary[] }>("/projects?pageSize=100");
  return payload.items || [];
}

export async function createProject(name: string): Promise<Project> {
  const payload = await request<{ project: Project }>("/projects", {
    method: "POST",
    body: { name, width: 1920, height: 1080, fps: 30 },
  });
  return payload.project;
}

export async function getProject(projectId: string): Promise<Project> {
  const payload = await request<{ project: Project }>(`/projects/${encodeURIComponent(projectId)}`);
  return payload.project;
}

export async function loadVoices(): Promise<EditorCapabilities["voice"]> {
  return request<EditorCapabilities["voice"]>("/voices");
}

export async function createVoiceProfile(name: string, file: File): Promise<void> {
  const form = new FormData();
  form.append("name", name);
  form.append("consent", "true");
  form.append("file", file);
  await request("/voices", { method: "POST", body: form });
}

export async function startVoice(projectId: string, spec: VoiceSpec): Promise<VoiceJob> {
  const payload = await request<{ job: VoiceJob }>(
    `/projects/${encodeURIComponent(projectId)}/voices`,
    { method: "POST", body: spec },
  );
  return payload.job;
}

export async function getJob(jobId: string): Promise<VoiceJob> {
  const payload = await request<{ job: VoiceJob }>(`/jobs/${encodeURIComponent(jobId)}`);
  return payload.job;
}

export async function cancelJob(jobId: string): Promise<VoiceJob> {
  const payload = await request<{ job: VoiceJob }>(`/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
  });
  return payload.job;
}

export function resolveContentUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  if (configuredBase.startsWith("http")) {
    return new URL(path, `${configuredBase}/`).toString();
  }
  return path.startsWith("/") ? path : `${configuredBase}/${path}`;
}

export async function downloadAsset(path: string, filename: string): Promise<void> {
  const response = await fetch(resolveContentUrl(path));
  if (!response.ok) throw new MaestroApiError("Não foi possível baixar o WAV.", response.status);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
