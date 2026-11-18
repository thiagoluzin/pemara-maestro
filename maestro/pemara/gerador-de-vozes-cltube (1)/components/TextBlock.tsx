import React from "react";
import Spinner from "./Spinner";

interface Props {
  index: number;
  value: string;
  audioUrl?: string;
  onChange: (index: number, value: string) => void;
  onGenerateIndividual: () => void;
  onDownloadIndividual: () => void;
  isProcessing: boolean;
  charLimit: number;
}

const TextBlock: React.FC<Props> = ({ index, value, audioUrl, onChange, onGenerateIndividual, onDownloadIndividual, isProcessing, charLimit }) => {
  const overLimit = value.length > charLimit;
  return <article className="space-y-3 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-xs font-bold uppercase tracking-widest text-zinc-500">Bloco #{index + 1}</span><div className="flex gap-2"><button onClick={onGenerateIndividual} disabled={isProcessing || !value.trim() || overLimit} className="rounded-lg border border-zinc-700 px-3 py-1.5 text-xs disabled:opacity-40">{isProcessing ? <Spinner /> : "Gerar"}</button>{audioUrl && <button onClick={onDownloadIndividual} className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-bold">WAV</button>}</div></div>
    <div className="relative"><textarea value={value} onChange={(event) => onChange(index, event.target.value)} disabled={isProcessing} className={`min-h-32 w-full resize-y rounded-xl border bg-zinc-900 p-3 text-sm outline-none ${overLimit ? "border-red-500" : "border-zinc-800 focus:border-red-500"}`} /><span className={`absolute bottom-2 right-3 text-[10px] ${overLimit ? "text-red-400" : "text-zinc-600"}`}>{value.length} / {charLimit}</span></div>
    {audioUrl && <audio controls src={audioUrl} className="h-9 w-full" />}
  </article>;
};

export default TextBlock;
