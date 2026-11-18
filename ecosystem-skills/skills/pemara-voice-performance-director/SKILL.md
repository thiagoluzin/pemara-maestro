---
name: pemara-voice-performance-director
description: Directs and evaluates narration or dialogue in the Pemara ecosystem, including script, regional accent, delivery, model choice, voice QC, and Maestro handoff. Use for commercial voiceovers or character speech; route music and SFX to game-audio-designer.
---

# Pemara Voice Performance Director

## Atuação vocal dentro da cena

Receba de `pemara-performance-director` o interlocutor, objetivo da fala, subtexto, estímulo e virada. Dirija uma ação por frase — convencer, esconder, interromper, proteger — e marque onde a percepção muda a entrega. Não usar o mesmo grito ou intensidade em toda fala.

Confronte a duração efetiva da voz com os beats do corpo e com o editor, sem cortar fonemas, congelar personagem ou alterar o picture lock para acomodar fala não planejada. Escuta, pausa e respiração precisam servir à cena. Avaliar voz sozinha e no contexto disponível, com evidência do arquivo real; silêncio dirigido permanece silêncio.

O motor vocal e o texto aprovados permanecem; planejar interpretação não autoriza nova voz/clonagem/áudio. Acabamento de vídeo copia o áudio existente; mudança de mix/voz exige escopo próprio e revisão da candidata.

Create a performance that survives listening, not merely intelligible TTS. Route
each line using locale, performance, privacy, availability, and cost evidence.

## Hard Gates

- Do not load Chatterbox or any GPU model unless the user's current request
  explicitly authorizes generation now.
- Keep provider keys server-side. Never place a key in browser code,
  `localStorage`, project manifests, logs, or handoff ZIPs.
- Require explicit consent before creating or using an identifiable voice
  profile. Do not clone a celebrity or an unconsenting third party.
- For Maestro's built-in cloud gateway, keep generation off unless both its
  feature flag and credential are configured. An explicitly requested,
  project-scoped audition may use an existing server-side credential directly;
  never copy the secret into project files or logs.
- When checking credentials, inspect names and configured booleans only. Never
  print `.env` contents or recursively search directories that include secrets
  and generated base64 payloads.
- Treat voice synthesis as billable when a cloud provider is selected. Use a
  short preview before a final render.
- Keep private reference audio under the protected voice-profile store. Export
  only the resulting asset and non-sensitive provenance.

## Route the Performance

1. Use Chatterbox local for private/offline candidates and consented voice
   profiles. A locale-specific checkpoint establishes language intent, not an
   approved accent or professional performance.
2. Use the Windows system voice only as a lightweight fallback or diagnostic.
3. Consider an optional cloud TTS provider for commercial narration only when
   credentialed and a suitable native-locale voice is available. For Gemini
   TTS, inspect the live voice library and choose an actual `pt-BR` voice ID;
   a multilingual prebuilt voice alone does not establish Brazilian accent.
4. Use performance-guided speech-to-speech for the most human result: record an
   authorized guide performance, preserve its timing and emotion, then transfer
   only to an authorized target voice.
5. Use dialogue generation for multi-character scenes; keep each speaker and
   consent record distinct.

Read [references/voice-routing.md](references/voice-routing.md) before changing
provider settings or choosing a performance-transfer path.
For Brazilian Portuguese campaigns, read
[references/pt-br-commercial-voice.md](references/pt-br-commercial-voice.md)
before selecting a voice or promising accent quality.

## Script and Rejection Gate

- Separate script quality from voice quality. Write an actual spoken script from
  the owner's source and fixed brand wording; check the claim, call to action,
  timing, and natural spoken Brazilian Portuguese before synthesis. Avoid filler
  slogans and awkward phrases added only to fill the clip.
- On a human rejection, archive the exact file and stop using it as a candidate.
  Preserve accepted picture and brand. A new seed or stronger emotion control
  alone is not a meaningful correction after repeated rejection of the same
  engine or voice. Change the script and voice route, or surface the missing
  capability for a materially different route.
- Generate a representative whole sentence including difficult names, then a
  continuous complete read. Edit only at natural phrase boundaries after
  listening; concatenating arbitrary timed pieces can create unnatural
  cadence, consonant loss, and voice drift. Keep the untouched whole takes for
  comparison and rollback.
- ASR confirms approximate words, not accent, emotion, name stress, delivery,
  or seamless edits. Do not register a polished-video candidate based on ASR,
  hashes, or loudness alone when the voice itself remains unlistened.

## Direct the Take

1. Define speaker, listener, objective, subtext, emotional start/end, intensity
   from 0 to 1, pace, and pronunciation exceptions.
2. Split long narration at semantic boundaries. Keep emotional turns in
   separate takes.
3. Choose `natural`, `intense`, `dramatic`, `whisper`, `joyful`, `sad`, or
   `angry`; tune only after listening.
4. Generate a short representative line first.
5. Produce two to four variants for a critical line. Change one control group
   at a time.
6. Select by human listening, then render the complete section.
7. Normalize and inspect the final WAV; generate alignment/SRT when the voice
   enters a video timeline.

## Regional Accent and Useful-End Gate

For Portuguese, `pt-BR` alone is not a sufficient direction when the owner asks for a regional
voice. Record the intended locality (for example, São Paulo capital/Grande São Paulo), the desired
studio register and forbidden markers such as pt-PT cadence, reduced European vowels, caipira
retroflex R or another unwanted region. Keep timbre, accent and acting as separate review axes: an
approved timbre does not approve the accent.

For a critical character line, generate a short representative preview and require human listening
of the exact file/hash before full integration. Prefer grounded contemporary cinematic dubbing.
Reject a thin/young, caricatured, melodramatic, over-enunciated or soap-opera delivery when the scene
calls for restrained naturalism.

Define `useful_audio_end_seconds` and inspect/ASR the whole file through its real end. Any invented
word, repeated phrase, babble, long silence or model continuation after the approved line rejects
the candidate even when the opening sounds excellent. Trim only after the last intended phoneme and
preserve a short natural release; never keep an unusable generated tail merely to retain duration.

Once a voice is approved, bind all downstream dialogue, mix and lipsync work to its exact SHA-256.
Do not rerender a supposedly equivalent version during assembly.

## Dialogue-to-Mouth Gate

Lock the final approved WAV before lipsync. Target only the speaking face, preserve every other
mouth and face, and verify skin/material identity before and after processing. Mouth movement must
follow phoneme timing with restrained jaw motion, close at the end of the line and remain closed
afterward. A lipsync pass may not alter the chosen video engine, camera, anatomy or picture timing;
it is a downstream candidate with its own visual approval gate.

## Tune Chatterbox Local

- Increase `exaggeration` to strengthen emotional conditioning.
- Lower `cfgWeight` moderately to permit more expressive delivery.
- Increase `temperature` carefully to add variation; stop when pronunciation
  or identity drifts.
- Preserve `repetitionPenalty`, `minP`, and `topP` defaults unless repeated
  words or unstable sampling are audible.
- Prefer a clean, consented reference with consistent room tone and delivery.

Do not infer that a more extreme numeric value is better. Compare takes at
matched loudness.

## Quality Gate

Reject or regenerate a take when any of these are present:

- wrong word, name, language, or stress;
- clipped onset, cut ending, repeated phrase, or long accidental silence;
- identity drift between adjacent takes;
- emotion that contradicts the scene;
- pumping, harsh sibilance, metallic resonance, or audible background leak;
- timeline duration or subtitle alignment outside the project's tolerance.
- accent outside the explicitly approved locale or performance register;
- any unrequested speech or unusable audio after the intended line end;
- lipsync applied to the wrong face, a non-speaking character, or a face whose identity/materials drift.

Record engine, model, voice/profile identifier, preset, resolved controls,
language, text hash, audio hash, consent reference, timestamp, and cloud request
metadata that does not reveal credentials.

## Canonical Integration

- Backend: `E:/Pemara/maestro/pemara/services/studio/editor_suite.py`
- Local worker: `E:/Pemara/maestro/pemara/services/studio/chatterbox_cli.py`
- Provider gateway: `E:/Pemara/maestro/pemara/services/studio/voice_providers.py`
- Editor UI: `E:/Pemara/maestro/pemara/app/assets/editor-suite.js`
- Protected assets: `E:/Pemara/maestro/pemara/dados/studio/editor_suite`

Deliver WAV PCM for editing, optional MP3 only for preview, UTF-8 SRT/VTT for
timelines, and a manifest that contains provenance but no secrets or raw
personal reference audio.
