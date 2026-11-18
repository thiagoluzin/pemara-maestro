export type VoiceEngine = "auto" | "chatterbox" | "system";

export type VoicePreset =
  | "natural"
  | "intense"
  | "dramatic"
  | "whisper"
  | "joyful"
  | "sad"
  | "angry";

export interface VoiceProfile {
  voiceProfileId: string;
  name: string;
  duration?: number;
  consentConfirmed?: boolean;
}

export interface VoiceCapabilities {
  recommended?: string;
  chatterbox?: {
    installed: boolean;
    supportsVoiceClone: boolean;
    languages: string[];
  };
  system?: {
    installed: boolean;
    voices: string[];
  };
  profiles?: VoiceProfile[];
}

export interface EditorCapabilities {
  voice?: VoiceCapabilities;
  assistant?: {
    ollama: boolean;
    models: string[];
    defaultModel: string;
  };
}

export interface ProjectAsset {
  assetId: string;
  name: string;
  kind: string;
  url?: string;
  duration?: number;
  mediaType?: string;
}

export interface Project {
  projectId: string;
  name: string;
  revision: number;
  assets: ProjectAsset[];
  clips: Array<Record<string, unknown>>;
}

export interface ProjectSummary {
  projectId: string;
  name: string;
  revision: number;
  assetCount?: number;
  clipCount?: number;
  duration?: number;
}

export interface VoiceJob {
  jobId: string;
  projectId?: string;
  kind?: string;
  status: "queued" | "running" | "completed" | "failed" | "canceled" | "canceling" | "interrupted";
  progress?: number;
  message?: string;
  result?: {
    asset?: ProjectAsset;
    project?: Project;
  };
  error?: { message?: string; code?: string };
}

export interface VoiceSpec {
  expectedRevision: number;
  text: string;
  engine: VoiceEngine;
  voiceProfileId?: string;
  systemVoice?: string;
  language: string;
  speed: number;
  preset: VoicePreset;
  intensity: number;
  exaggeration?: number;
  cfgWeight?: number;
  temperature?: number;
  timelineStart: number;
  addToTimeline: boolean;
}
