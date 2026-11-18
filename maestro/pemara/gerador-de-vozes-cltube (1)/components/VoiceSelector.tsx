import React from "react";
import type { VoiceCapabilities, VoiceEngine } from "../types";

interface Props {
  capabilities?: VoiceCapabilities;
  engine: VoiceEngine;
  onEngineChange: (engine: VoiceEngine) => void;
  profileId: string;
  onProfileChange: (id: string) => void;
  systemVoice: string;
  onSystemVoiceChange: (voice: string) => void;
  onPreview: () => void;
}

const VoiceSelector: React.FC<Props> = ({ capabilities, engine, onEngineChange, profileId, onProfileChange, systemVoice, onSystemVoiceChange, onPreview }) => (
  <section className="rounded-3xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
    <div><h2 className="text-lg font-black italic">3. Motor de voz</h2><p className="mt-1 text-xs text-zinc-500">A voz é processada pelo Maestro local.</p></div>
    <label className="text-sm">Engine<select value={engine} onChange={(event) => onEngineChange(event.target.value as VoiceEngine)} className="mt-1 w-full rounded-xl border border-zinc-700 bg-zinc-950 p-2"><option value="auto">Automático</option>{capabilities?.chatterbox?.installed && <option value="chatterbox">Chatterbox Multilingual V3</option>}{capabilities?.system?.installed && <option value="system">Voz do Windows</option>}</select></label>
    {engine !== "system" && <label className="text-sm">Perfil autorizado<select value={profileId} onChange={(event) => onProfileChange(event.target.value)} className="mt-1 w-full rounded-xl border border-zinc-700 bg-zinc-950 p-2"><option value="">Sem clonagem</option>{(capabilities?.profiles || []).map((profile) => <option key={profile.voiceProfileId} value={profile.voiceProfileId}>{profile.name}</option>)}</select></label>}
    {engine === "system" && <label className="text-sm">Voz do Windows<select value={systemVoice} onChange={(event) => onSystemVoiceChange(event.target.value)} className="mt-1 w-full rounded-xl border border-zinc-700 bg-zinc-950 p-2"><option value="">Automática</option>{(capabilities?.system?.voices || []).map((voice) => <option key={voice} value={voice}>{voice}</option>)}</select></label>}
    <button onClick={onPreview} className="w-full rounded-xl border border-zinc-700 px-3 py-2 text-sm hover:border-red-500">Ouvir prévia local</button>
    <p className="text-[11px] leading-relaxed text-zinc-500">A clonagem exige uma amostra autorizada. O áudio de referência fica protegido no armazenamento do Maestro.</p>
  </section>
);

export default VoiceSelector;
