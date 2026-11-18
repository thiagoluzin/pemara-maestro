# Voice Routing Reference

## Decision Matrix

| Requirement | Preferred route | Important constraint |
|---|---|---|
| Private/offline narration candidate | Chatterbox local with a relevant regional checkpoint | GPU generation needs current authorization; locale label is not proof of accent or acting |
| Fast diagnostic | Windows system voice | Low emotional range |
| Expressive commercial TTS | Optional cloud model with a native target-locale voice | Feature flag, credential, approved voice, cost, data transfer, listening gate |
| Gemini commercial audition | Gemini 3.8 Flash TTS with a live-catalog `pt-BR` voice | An existing Lyria Gemini API key can authenticate, but Lyria music and TTS are separate models; project-scoped auditions still need exact-file listening |
| Native Brazilian delivery when synthetic takes keep failing | Human Brazilian narrator, or an authorized guide performance with consented speech-to-speech | Validate exact recorded performance; preserve rights and source provenance |
| Stable long narration | Stable multilingual cloud model or local approved take | Split at semantic boundaries |
| Exact human cadence/emotion | Authorized guide performance plus speech-to-speech | Consent for guide and target voice |
| Multi-character scene | Dialogue endpoint or separate per-speaker takes | Keep identities and consent separate |
| Video delivery | WAV plus alignment/SRT | Verify duration and timeline start |

## Local Presets

The backend resolves preset plus intensity into bounded Chatterbox controls.
Explicit advanced overrides win:

- `exaggeration`: 0.0–1.0
- `cfgWeight`: 0.0–1.0
- `temperature`: 0.05–2.0
- `repetitionPenalty`: 1.0–3.0
- `minP`: 0.0–1.0
- `topP`: 0.05–1.0

Start from `natural`. Use `intense` or `dramatic` for stronger acting. Use
`whisper`, `joyful`, `sad`, or `angry` as direction, then judge the audio rather
than the numeric settings.

## Cloud Boundary

Require:

1. `MAESTRO_VOICE_CLOUD_ENABLED=true`;
2. a server-side provider credential;
3. an approved provider voice;
4. text appropriate for transfer to that provider;
5. a cost-aware preview/final choice.

Never expose the provider credential in capability responses. Return only
`configured`, `enabled`, model/voice identifiers, safe labels, and non-sensitive
request metadata.
For Maestro's cloud gateway, no enabled flag or credential means cloud models
are research options, not executable routes through that gateway. A user-requested
project audition with an existing server-side credential is a separate route;
never persist the key in the campaign folder. Do not substitute a generic local
voice and label it a final-quality commercial performance.

## Performance Brief

Capture:

```text
speaker:
listener:
scene objective:
subtext:
emotion start -> end:
intensity 0..1:
pace:
pronunciation notes:
forbidden delivery:
```

For a performance guide, record in a quiet environment without music or
effects. Keep the guide and target voice authorization alongside the private
production record, not in public delivery packages.

## Acceptance

Listen at matched loudness and verify:

1. text accuracy and pronunciation;
2. emotional intent and intensity arc;
3. natural pauses, breath, cadence, and emphasis;
4. identity continuity;
5. absence of clipping, repeated phrases, metallic artifacts, and excess
   silence;
6. WAV integrity and subtitle/timeline alignment.
