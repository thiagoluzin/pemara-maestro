import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  EditorCapabilities,
  Project,
  ProjectSummary,
  ProjectAsset,
  VoiceEngine,
  VoiceJob,
  VoicePreset,
} from "./types";
import {
  cancelJob,
  createProject,
  createVoiceProfile,
  downloadAsset,
  getJob,
  getProject,
  listProjects,
  loadCapabilities,
  loadVoices,
  resolveContentUrl,
  startVoice,
  MaestroApiError,
} from "./services/maestroService";
import VoiceSelector from "./components/VoiceSelector";
import TextBlock from "./components/TextBlock";

const CHAR_LIMIT = 5000;
const TOTAL_BLOCKS = 50;
const TERMINAL = new Set(["completed", "failed", "canceled", "interrupted"]);

interface TextBlockData {
  id: number;
  text: string;
  audioUrl?: string;
  asset?: ProjectAsset;
}

function splitText(text: string, limit: number): string[] {
  const chunks: string[] = [];
  let current = "";
  const parts = text.match(/[^.!?\n]+[.!?\n]?/g) || [];
  for (const part of parts) {
    const sentence = part.trim();
    if (!sentence) continue;
    if (sentence.length > limit) {
      if (current) chunks.push(current);
      current = "";
      for (let offset = 0; offset < sentence.length; offset += limit) {
        const piece = sentence.slice(offset, offset + limit).trim();
        if (piece.length === limit) chunks.push(piece);
        else current = piece;
      }
      continue;
    }
    if (current && `${current} ${sentence}`.length > limit) {
      chunks.push(current);
      current = sentence;
    } else {
      current = current ? `${current} ${sentence}` : sentence;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

function wait(milliseconds: number) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

const App: React.FC = () => {
  const [capabilities, setCapabilities] = useState<EditorCapabilities | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const projectRef = useRef<Project | null>(null);
  const [mainScript, setMainScript] = useState("");
  const [scriptChunks, setScriptChunks] = useState<string[]>([]);
  const [blocks, setBlocks] = useState<TextBlockData[]>([]);
  const [splitLimit, setSplitLimit] = useState(5000);
  const [engine, setEngine] = useState<VoiceEngine>("auto");
  const [profileId, setProfileId] = useState("");
  const [systemVoice, setSystemVoice] = useState("");
  const [language, setLanguage] = useState("pt");
  const [preset, setPreset] = useState<VoicePreset>("natural");
  const [intensity, setIntensity] = useState(0.5);
  const [speed, setSpeed] = useState(1);
  const [temperature, setTemperature] = useState(0.8);
  const [exaggeration, setExaggeration] = useState(0.5);
  const [cfgWeight, setCfgWeight] = useState(0.5);
  const [timelineStart, setTimelineStart] = useState(0);
  const [addToTimeline, setAddToTimeline] = useState(true);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [activeJob, setActiveJob] = useState<VoiceJob | null>(null);
  const stopRef = useRef(false);

  const voice = capabilities?.voice;
  const hasLocalEngine = Boolean(voice?.chatterbox?.installed || voice?.system?.installed);

  const updateProject = useCallback((next: Project) => {
    projectRef.current = next;
    setProject(next);
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [loadedCapabilities, loadedProjects, loadedVoices] = await Promise.all([
          loadCapabilities(),
          listProjects(),
          loadVoices(),
        ]);
        if (!mounted) return;
        const merged = { ...loadedCapabilities, voice: loadedVoices || loadedCapabilities.voice };
        setCapabilities(merged);
        setProjects(loadedProjects);
        const first = loadedProjects[0];
        if (first) updateProject(await getProject(first.projectId));
        else updateProject(await createProject("CLTube Voice Generator"));
      } catch (cause) {
        if (mounted) setError(cause instanceof Error ? cause.message : "Falha ao iniciar o gerador.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [updateProject]);

  useEffect(() => {
    const preferred = voice?.chatterbox?.installed ? "chatterbox" : voice?.system?.installed ? "system" : "auto";
    setEngine((current) => current === "auto" || current === "chatterbox" || current === "system" ? current : preferred);
  }, [voice]);

  const refreshProjects = useCallback(async () => {
    const items = await listProjects();
    setProjects(items);
  }, []);

  const selectProject = async (projectId: string) => {
    if (!projectId) return;
    setError("");
    try { updateProject(await getProject(projectId)); setBlocks([]); } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível abrir o projeto.");
    }
  };

  const newProject = async () => {
    const name = window.prompt("Nome do projeto", "CLTube Voice Generator");
    if (!name?.trim()) return;
    try {
      const created = await createProject(name.trim());
      updateProject(created);
      await refreshProjects();
      setBlocks([]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível criar o projeto."); }
  };

  const handleSplit = () => {
    const chunks = splitText(mainScript, splitLimit);
    setScriptChunks(chunks);
    setBlocks([]);
    setProgress(`${chunks.length} bloco(s) pronto(s) para revisão.`);
  };

  const distribute = () => {
    setBlocks(scriptChunks.slice(0, TOTAL_BLOCKS).map((text, id) => ({ id, text })));
    setProgress(scriptChunks.length > TOTAL_BLOCKS ? `Limite aplicado: ${TOTAL_BLOCKS} blocos.` : "Blocos distribuídos.");
  };

  const updateBlock = (index: number, text: string) => {
    setBlocks((current) => current.map((block, itemIndex) => itemIndex === index ? { ...block, text, audioUrl: undefined, asset: undefined } : block));
  };

  const poll = useCallback(async (job: VoiceJob): Promise<VoiceJob> => {
    setActiveJob(job);
    let current = job;
    while (!TERMINAL.has(current.status)) {
      if (stopRef.current) {
        current = await cancelJob(current.jobId);
        break;
      }
      await wait(1000);
      current = await getJob(current.jobId);
      setActiveJob(current);
      setProgress(current.message || `${Math.round(current.progress || 0)}%`);
    }
    setActiveJob(current);
    if (current.status !== "completed") {
      throw new MaestroApiError(current.error?.message || current.message || "A geração foi interrompida.");
    }
    if (current.result?.project) updateProject(current.result.project);
    return current;
  }, [updateProject]);

  const makeVoice = useCallback(async (text: string, start: number, add: boolean) => {
    const currentProject = projectRef.current;
    if (!currentProject) throw new MaestroApiError("Abra um projeto antes de gerar áudio.");
    const job = await startVoice(currentProject.projectId, {
      expectedRevision: currentProject.revision,
      text,
      engine,
      voiceProfileId: profileId || undefined,
      systemVoice: systemVoice || undefined,
      language,
      speed,
      preset,
      intensity,
      exaggeration: engine === "system" ? undefined : exaggeration,
      cfgWeight: engine === "system" ? undefined : cfgWeight,
      temperature: engine === "system" ? undefined : temperature,
      timelineStart: start,
      addToTimeline: add,
    });
    const finished = await poll(job);
    return finished.result?.asset;
  }, [cfgWeight, engine, exaggeration, intensity, language, poll, preset, profileId, speed, systemVoice, temperature]);

  const generateOne = async (index: number) => {
    const block = blocks[index];
    if (!block?.text.trim() || block.text.length > CHAR_LIMIT) return;
    setBusy(true); setError(""); setProgress(`Gerando bloco ${index + 1}...`); stopRef.current = false;
    try {
      const asset = await makeVoice(block.text, timelineStart, addToTimeline);
      if (asset?.url) setBlocks((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, asset, audioUrl: resolveContentUrl(asset.url!) } : item));
      setProgress(`Bloco ${index + 1} concluído.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Falha ao gerar o bloco."); }
    finally { setBusy(false); setActiveJob(null); }
  };

  const generateAll = async () => {
    const items = blocks.map((block, index) => ({ block, index })).filter(({ block }) => block.text.trim());
    if (!items.length) return setError("Distribua o roteiro em blocos antes de gerar.");
    if (items.some(({ block }) => block.text.length > CHAR_LIMIT)) return setError("Há blocos acima do limite de caracteres.");
    setBusy(true); setError(""); stopRef.current = false;
    let cursor = timelineStart;
    try {
      for (let position = 0; position < items.length; position += 1) {
        if (stopRef.current) break;
        const { block, index } = items[position];
        setProgress(`Gerando ${position + 1} de ${items.length}...`);
        const asset = await makeVoice(block.text, cursor, addToTimeline);
        if (asset?.url) {
          setBlocks((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, asset, audioUrl: resolveContentUrl(asset.url!) } : item));
          cursor += asset.duration || 0;
        }
      }
      if (!stopRef.current) setProgress("Todas as narrações foram concluídas e salvas no projeto.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Falha durante a geração em lote."); }
    finally { setBusy(false); setActiveJob(null); stopRef.current = false; }
  };

  const stopGeneration = async () => {
    stopRef.current = true;
    setProgress("Cancelando job atual...");
    if (activeJob && !TERMINAL.has(activeJob.status)) {
      try { await cancelJob(activeJob.jobId); } catch { /* o polling resolve o estado final */ }
    }
  };

  const previewVoice = async () => {
    if (busy) return;
    setBusy(true); setError(""); setProgress("Gerando prévia..."); stopRef.current = false;
    try {
      const asset = await makeVoice("Esta é uma demonstração da voz local do Maestro.", 0, false);
      if (asset?.url) setProgress(`Prévia pronta: ${resolveContentUrl(asset.url)}`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível gerar a prévia."); }
    finally { setBusy(false); setActiveJob(null); }
  };

  const createProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get("file");
    if (!(file instanceof File) || !file.size) return setError("Escolha uma amostra de voz.");
    try {
      await createVoiceProfile(String(data.get("name") || "Voz autorizada"), file);
      const refreshedVoice = await loadVoices();
      setCapabilities((current) => current ? { ...current, voice: refreshedVoice } : current);
      form.reset(); setProgress("Perfil de voz salvo localmente.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Não foi possível salvar o perfil."); }
  };

  const overLimit = useMemo(() => blocks.some((block) => block.text.length > CHAR_LIMIT), [blocks]);

  if (loading) return <div className="min-h-screen bg-zinc-950 text-white grid place-items-center">Conectando ao Maestro local...</div>;

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-4 md:p-8 font-sans">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-red-500">Pemara Maestro · CLTube</p>
              <h1 className="mt-2 text-3xl font-black italic tracking-tight md:text-5xl">Gerador de Vozes Local</h1>
              <p className="mt-2 max-w-2xl text-sm text-zinc-400">Roteiro em blocos, prévia e narração neural salvos diretamente no projeto do Maestro. Sem Gemini, sem chave API e sem enviar o texto para a nuvem.</p>
            </div>
            <div className={`rounded-full border px-4 py-2 text-xs font-bold ${hasLocalEngine ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-amber-500/40 bg-amber-500/10 text-amber-300"}`}>
              {voice?.chatterbox?.installed ? "Chatterbox V3 local disponível" : voice?.system?.installed ? "Fallback: voz do Windows" : "Instale um motor local"}
            </div>
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <select value={project?.projectId || ""} onChange={(event) => selectProject(event.target.value)} className="min-w-64 rounded-xl border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm">
              {projects.map((item) => <option key={item.projectId} value={item.projectId}>{item.name}</option>)}
              {project && !projects.some((item) => item.projectId === project.projectId) && <option value={project.projectId}>{project.name}</option>}
            </select>
            <button onClick={newProject} className="rounded-xl border border-zinc-700 px-4 py-2 text-sm hover:border-red-500">Novo projeto</button>
            <span className="text-xs text-zinc-500">Projeto atual: {project?.name || "nenhum"}</span>
          </div>
        </header>

        <main className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <section className="space-y-6">
            <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6">
              <div className="flex items-center justify-between gap-3"><h2 className="text-lg font-black italic">1. Roteiro</h2><span className="text-xs text-zinc-500">{mainScript.length} caracteres</span></div>
              <textarea value={mainScript} onChange={(event) => setMainScript(event.target.value)} placeholder="Cole o roteiro completo aqui..." className="mt-4 min-h-64 w-full rounded-2xl border border-zinc-800 bg-zinc-950 p-4 text-sm text-zinc-200 outline-none focus:border-red-500" />
              <div className="mt-4 flex flex-wrap items-end gap-3">
                <label className="text-xs text-zinc-400">Limite por bloco<input type="number" min="300" max={CHAR_LIMIT} value={splitLimit} onChange={(event) => setSplitLimit(Number(event.target.value))} className="mt-1 block w-28 rounded-lg border border-zinc-700 bg-zinc-950 p-2 text-white" /></label>
                <button onClick={handleSplit} className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold hover:bg-red-500">Dividir roteiro</button>
                <button onClick={distribute} disabled={!scriptChunks.length} className="rounded-xl border border-zinc-700 px-4 py-2 text-sm font-bold disabled:opacity-40">Distribuir {scriptChunks.length ? `(${scriptChunks.length})` : "blocos"}</button>
              </div>
              {progress && <p className="mt-3 text-xs text-zinc-400">{progress}</p>}
            </section>

            {blocks.length > 0 && <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6"><div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-black italic">2. Revisão e geração</h2><span className="text-xs text-zinc-500">{blocks.length} bloco(s)</span></div><div className="space-y-4">{blocks.map((block, index) => <TextBlock key={block.id} index={index} value={block.text} audioUrl={block.audioUrl} onChange={updateBlock} onGenerateIndividual={() => generateOne(index)} onDownloadIndividual={() => block.asset?.url && downloadAsset(block.asset.url, `narracao_${index + 1}.wav`)} isProcessing={busy && activeJob?.projectId === project?.projectId} charLimit={CHAR_LIMIT} />)}</div></section>}
          </section>

          <aside className="space-y-6">
            <VoiceSelector capabilities={voice} engine={engine} onEngineChange={setEngine} profileId={profileId} onProfileChange={setProfileId} systemVoice={systemVoice} onSystemVoiceChange={setSystemVoice} onPreview={previewVoice} />
            <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-5 space-y-4"><h2 className="text-lg font-black italic">Direção da performance</h2><label>Preset<select value={preset} onChange={(event) => setPreset(event.target.value as VoicePreset)} className="mt-1 w-full rounded-xl border border-zinc-700 bg-zinc-950 p-2"><option value="natural">Natural</option><option value="intense">Intenso</option><option value="dramatic">Dramático</option><option value="whisper">Sussurro</option><option value="joyful">Alegre</option><option value="sad">Triste</option><option value="angry">Irritado</option></select></label><label className="text-sm">Intensidade <span className="float-right text-zinc-400">{intensity.toFixed(2)}</span><input type="range" min="0" max="1" step="0.05" value={intensity} onChange={(event) => setIntensity(Number(event.target.value))} className="w-full" /></label><div className="grid grid-cols-2 gap-3"><label className="text-sm">Velocidade<input type="number" min="0.5" max="2" step="0.05" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-2" /></label><label className="text-sm">Idioma<select value={language} onChange={(event) => setLanguage(event.target.value)} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-2"><option value="pt">Português</option><option value="en">Inglês</option><option value="es">Espanhol</option><option value="fr">Francês</option><option value="de">Alemão</option><option value="it">Italiano</option></select></label></div>{engine !== "system" && <div className="grid grid-cols-2 gap-3"><label className="text-sm">Expressividade<input type="number" min="0" max="1" step="0.05" value={exaggeration} onChange={(event) => setExaggeration(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-2" /></label><label className="text-sm">Fidelidade<input type="number" min="0" max="1" step="0.05" value={cfgWeight} onChange={(event) => setCfgWeight(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-2" /></label></div>}<label className="text-sm">Posição inicial (s)<input type="number" min="0" step="0.1" value={timelineStart} onChange={(event) => setTimelineStart(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 p-2" /></label><label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={addToTimeline} onChange={(event) => setAddToTimeline(event.target.checked)} /> adicionar ao projeto Maestro</label></section>
            <details className="rounded-3xl border border-zinc-800 bg-zinc-900 p-5"><summary className="cursor-pointer font-bold">Criar perfil de voz autorizado</summary><form onSubmit={createProfile} className="mt-4 space-y-3"><input name="name" required placeholder="Nome do perfil" className="w-full rounded-xl border border-zinc-700 bg-zinc-950 p-2" /><input name="file" type="file" accept="audio/*,video/*" required className="w-full text-xs" /><label className="flex gap-2 text-xs text-zinc-400"><input name="consent" type="checkbox" required /> Confirmo que tenho autorização para usar esta voz.</label><button className="w-full rounded-xl border border-zinc-700 px-3 py-2 text-sm">Salvar perfil local</button></form></details>
            {error && <div className="rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">{error}</div>}
            {overLimit && <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-300">Existe bloco acima do limite de {CHAR_LIMIT} caracteres.</div>}
            <div className="space-y-3"><button onClick={generateAll} disabled={busy || !blocks.length || overLimit || !hasLocalEngine} className="w-full rounded-2xl bg-red-600 px-4 py-4 font-black italic disabled:bg-zinc-800 disabled:text-zinc-600">{busy ? "GERANDO..." : "GERAR TODAS AS NARRAÇÕES"}</button>{busy && <button onClick={stopGeneration} className="w-full rounded-xl border border-zinc-700 px-3 py-2 text-sm text-red-300">Parar geração</button>}</div>
          </aside>
        </main>
      </div>
    </div>
  );
};

export default App;
