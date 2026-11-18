# Brazilian Portuguese commercial voice selection

Research checked 2026-09-25. Recheck provider support and local availability before a new job.

## Decision

For a short paid-quality campaign, prefer a Brazilian human narrator when the
owner requires a convincingly human performance and has rejected several
synthetic reads. An AI model can produce a strong candidate, but none warrants
a promise of a perfect accent or performance before listening to the exact take.

If using AI, first audition a voice recorded or designed for `pt-BR`, then the
model. Keep both the text and voice ID fixed in a small comparison. Select on
natural cadence, name stress, sibilants, vowel reduction, warmth, and the last
phoneme. A voice advertised as multilingual or Brazilian is not automatically
fit for a commercial read.

## Candidate routes

| Route | Why consider it | What to verify |
| --- | --- | --- |
| Google Gemini 3.8 Flash TTS with an Extended Voice Library `pt-BR` voice | Text-only exact-recitation input, structured style control, Brazilian voice IDs, and strong commercial-voice candidates; the existing Lyria MCP may already hold a Gemini Developer API key | Verify the key against the live TTS model list, select a `pt-BR` voice rather than a generic prebuilt one, check current pricing/tier, generate a short full-sentence audition, and listen for name stress and acting. Lyria generates music; Gemini TTS is a separate model and endpoint. The Lyria MCP `call_lyria_raw` uses bearer auth, so it is not a drop-in TTS route for a Gemini API key. |
| Azure Speech MAI Voice 2 HD, `pt-BR` voice | Microsoft lists Brazilian voices such as Luana, Pedro, Rafael and Caio with expressive styles | Region, account, price, exact voice availability, API output, performance; currently a public preview without a production SLA, so audition only until provider terms and reliability are accepted; no Azure credential is assumed. The 2026-09-25 region table does not list MAI voices in `brazilsouth` |
| ElevenLabs Multilingual v2 or Eleven v3 with a genuinely native `pt-BR` voice | Official guidance says the voice's source accent determines the result; v3 offers performance tags | Feature flag, credential, voice rights, cost; v3 can drift in accent, so compare v2 and v3 on the same text |
| OpenAI `gpt-4o-mini-tts` | Can follow spoken-style and accent instructions | Built-in voices are optimized for English; treat as an audition, not a guaranteed Brazilian voice; API credential and billing needed |
| Local Chatterbox single-language `pt-br` | Dedicated regional checkpoint, private execution | Owner listening: locale and ASR do not guarantee naturalness; do not repeat a human-rejected voice unchanged |
| Local Qwen3-TTS/Fish Speech | Existing project tooling | Prior owner-rejected takes and reported Portuguese accent/intonation issues; require materially different evidence before reuse |

Do not use a stranger's sample as a voice reference merely because it sounds
Brazilian. Cloning or performance transfer needs an authorized speaker and a
consent record. Spoken copy and provider transfer must also respect the current
project's privacy and billing choices.

## Evidence

- [Gemini TTS guide](https://ai.google.dev/gemini-api/docs/speech-generation): current 3.8 schema, structured style, prebuilt and extended voices.
- [Gemini API prices](https://ai.google.dev/gemini-api/docs/pricing): Gemini 3.8 Flash TTS free and paid tiers; recheck before estimating a request.
- [Gemini 3.8 release note](https://ai.google.dev/gemini-api/docs/changelog): 2026-09-22 general availability.
- [Gemini developer forum: voice and accent inconsistency](https://discuss.ai.google.dev/t/gemini-tts-gemini-3-1-flash-tts-in-production-voice-consistency-across-runs-long-input-cutoffs-accent-drift-emotional-range-guidance-roadmap/182191): firsthand report for the earlier 3.1 model; do not assume that a 3.8 model card proves a perfect regional performance.
- [Azure Speech language and voice support](https://learn.microsoft.com/pt-br/azure/ai-services/speech-service/language-support?tabs=tts): named `pt-BR` Neural HD voices and styles.
- [MAI-Voice overview](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/mai-voices): prebuilt voice prerequisites and public-preview limitation.
- [Azure Speech region table](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions): current MAI voice availability by resource region.
- [ElevenLabs voice selection guide](https://elevenlabs.io/docs/eleven-creative/playground/text-to-speech): matching the native voice to the target accent; v3 versus Multilingual v2.
- [ElevenLabs model best practices](https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices): voice selection and v3 stability tradeoffs.
- [Firsthand Eleven v3 Brazilian accent report](https://www.reddit.com/r/ElevenLabs/comments/1wnpr9m/eleven_v3_problemas_com_sotaque/): one user's accent drift; treat as a warning, not a universal benchmark.
- [OpenAI TTS guide](https://developers.openai.com/api/docs/guides/text-to-speech): instruction control and English-optimized built-in voices.
- [Chatterbox Brazilian checkpoint](https://huggingface.co/ResembleAI/Chatterbox-Multilingual-pt-br): locale-specific model.
- [Qwen3-TTS Portuguese accent report](https://github.com/QwenLM/Qwen3-TTS/discussions/332) and [Chatterbox Portuguese intonation issue](https://github.com/resemble-ai/chatterbox/issues/368): firsthand failure reports.
