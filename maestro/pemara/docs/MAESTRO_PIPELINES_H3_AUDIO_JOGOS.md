# Maestro Pemara — vídeo H3, áudio e jogos

Mapa da integração em 13/09/2026. A interface principal é o Maestro em
`http://127.0.0.1:9501`. O login e o proxy autenticado existentes foram preservados.

```mermaid
flowchart TD
  U[Maestro Pemara · interface] --> S[Studio · API autenticada]
  S --> V[Vídeos · escolha explícita H3 ou LTX]
  S --> A[Áudio · vozes, música e efeitos]
  S --> G[Jogos e assets]
  V --> C[ComfyUI existente · porta 8188]
  A --> VO[Voz · Fish, Qwen3-TTS e Chatterbox]
  A --> MU[Música · ACE-Step e reinstrumentação]
  A --> FX[Efeitos · MMAudio e providers existentes]
  VO --> MIX[Mixagem FFmpeg · WAV]
  MU --> MIX
  FX --> MIX
  G --> P[Projetos e briefing]
  P --> IM[Imagens · Qwen, FLUX.2 Klein e Z-Image]
  P --> B[Objetos GLB · Blender · LODs e collider]
  P --> R[Personagens · TokenRig / SkinTokens]
  P --> T[Imagem para 3D · TRELLIS / Pixal3D]
  T --> C
  C --> WORKER[MaestroGame3D · ambiente 3D isolado]
  WORKER --> D[DINOv3 e BiRefNet · instalados]
  WORKER --> O
  IM --> O[Histórico e arquivos do projeto]
  B --> O
  R --> O
  O --> E[Exportação solicitada pelo usuário]
  E --> UNITY[Integração Unity no projeto escolhido]
```

## Produção de vídeo com H3

```mermaid
flowchart LR
  B[Briefing] --> RES[Pesquisa da versão · personagens existentes]
  RES --> REF[Referências e identidade]
  REF --> OK[Avaliação das referências]
  OK --> DIR[Direção do take e prompt]
  DIR --> SPEC[Contrato H3 · SageAttention obrigatório]
  SPEC --> GATE[Conferência de fila e GPU]
  GATE --> RUN[Geração H3]
  RUN --> QC[Revisão visual e de movimento]
  QC --> OWNER[Avaliação do proprietário]
  OWNER --> EDIT[Montagem dos takes aprovados]
  EDIT --> SOUND[Áudio nativo opcional ou acabamento sonoro]
  SOUND --> MASTER[Master para revisão]
```

O Codex opera o serviço ComfyUI exclusivamente pelo MCP. O backend do Maestro
continua autônomo quando o usuário solicita geração pela interface. O mapa não
representa autorização para gerar, aprovar ou publicar uma produção. A integração
de jogos não altera o seletor H3/LTX nem substitui a atenção do H3.

## Organização técnica

| Parte | Local |
| --- | --- |
| Interface principal | `app/index.html`, `app/assets/native-studios.js` |
| APIs de áudio e projetos | `services/studio/zico_audio.py` |
| Processamento GLB e rigging | `services/studio/game_assets.py` |
| Imagens para jogos | `services/studio/game_images.py` |
| Reserva e admissão de GPU | `gpu_lease.py`, `game_gpu_admission.py` |
| Projetos, jobs e exportações | `dados/game_ai` |
| Ambientes maiores de jogos | `D:/PemaraRuntimes/maestro-game-ai` |
| Ambiente Linux do SkinTokens | Ubuntu 24.04 · `/opt/maestro-game-ai/envs/skintokens` |

As gerações de GPU compartilham a reserva do Maestro. O backend só libera cache
ocioso do ComfyUI depois de verificar sua fila; não encerra outros processos.
Objetos estáticos são processados pelo Blender sem renderização de vídeo.

## Estado de ativação

Ativação administrativa concluída em 13/09/2026 às 09:59:45. O Studio 8029 carregou a revisão 2 da integração; sete rotas responderam HTTP 200. FLUX, Z-Image Base/Turbo, TRELLIS e Pixal3D foram anunciados como disponíveis. A revisão visual autenticada ainda depende do login habitual do proprietário.

Os testes 3D produziram GLBs válidos e conferidos no Blender. O fluxo atual gera malhas sem textura; testes técnicos não constituem aprovação artística. Evidência: dados/logs/maestro_native_activation_verified.json.
