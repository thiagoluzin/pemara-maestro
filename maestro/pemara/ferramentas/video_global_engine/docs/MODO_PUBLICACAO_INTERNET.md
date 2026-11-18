# Publicação na internet — operação local

Implementado em 2026-08-31. Perfil editorial `social_v1` no Maestro/Studio.
Não é uma reprodução dos algoritmos das plataformas nem uma promessa de alcance.

## Como usar

Em **Takes → Adicionar outro projeto**, escreva no objetivo:

> Esse vídeo será feito para publicação na internet. [Descreva a cena e suas restrições.]

Mantenha **Destino do vídeo → Detectar pelo objetivo**. A prévia confirma a detecção antes
de criar. Também é possível selecionar **Publicação na internet** explicitamente. Frases
negadas, citadas, blocos de código e exemplos reportados não devem ativar o modo; a detecção
é uma heurística conservadora e o seletor explícito resolve ambiguidades.

No projeto ativo, abra **Publicação na internet**. Em projetos antigos o modo continua
desativado até uma alteração explícita. O modo não converte formato nem reduz duração.

1. **Direção:** escrever público, promessa, emoção, abertura recomendada, alternativa escrita,
   progressão, recompensa final, enquadramento, compreensão sem som e restrições.
   O diretor usa essas escolhas antes do roteiro/âncoras. Salvar rascunhos é permitido.
2. **Geração habitual:** a especificação de geração exige os nove campos editoriais essenciais
   preenchidos (mínimo local de oito caracteres por campo). Esse teste mede completude;
   não avalia qualidade artística, não aprova âncoras e não concede GPU.
3. **Revisão:** continuam valendo H3, identidade, continuidade, gates técnicos e aprovação humana
   do artefato exato. A abertura entra apenas no primeiro take; o desfecho apenas no último.
   A alternativa fica escrita, sem renderização automática de uma segunda versão.
4. **Pacote:** após aprovação do master, escolher destino, título, descrição, segundo da capa
   e legendas SRT opcionais. **Preparar ZIP local** cria uma entrega separada para revisão.
5. **Resultados:** depois de você publicar, registrar o link, a janela em horas e os números
   agregados disponíveis no painel da plataforma. Deixar campos indisponíveis em branco.

Alterar título do projeto, objetivo, duração ou formato invalida a completude anterior até
revisar e salvar novamente a direção. Alternar o modo não reescreve takes nem masters.
Rascunhos na interface resistem à atualização periódica; **Descartar rascunho e recarregar**
é a ação explícita para substituí-los. Rascunhos ainda não salvos não sobrevivem ao fechamento
da página. Escritas concorrentes usam revisão e retornam conflito, sem sobrescrever em silêncio.

## O que o pacote contém

- Cópia do vídeo aprovado com SHA-256 conferido, sem recorte, conversão ou hardlink.
- `capa.jpg`, extraída de um quadro real do próprio master com FFmpeg em CPU.
- `titulo.txt`, `descricao.txt`, `direcao.txt`, `manifest.json` e `LEIA-ME.txt`.
- `legendas.srt`, quando fornecidas; não são gravadas sobre a imagem.

Estado: `PENDING_PUBLICATION_REVIEW`. A aprovação do vídeo não aprova metadados novos.
Uma falha preserva os arquivos parciais como `FAILED` e bloqueia seu download pelo painel.
O download também recusa ZIP adulterado, aprovação revogada ou master substituído.

Limites deste exportador: master até 1 GiB; duração até 7200 s; até 100 pacotes/projeto.
Para Shorts/Reels/TikTok, o exportador recusa master horizontal e pede uma fonte com o
enquadramento revisado; não faz recorte automático. Fontes quadradas são aceitas. O pacote
não garante elegibilidade a todos os limites e recursos de cada plataforma. Texto “4K” no
título exige dimensão mínima real de 2160 px no menor lado. Legendas precisam estar em SRT
simples e continuam exigindo revisão humana de conteúdo e sincronização.

## Resultados e limites da análise

Os dados são declarados pelo proprietário (`owner_reported`), associados ao pacote, ao hash,
à plataforma, ao link, à duração e à janela desde a publicação. Não há login social, scraping,
telemetria individual, cookies de espectadores ou contagem a partir do player do Maestro.

Taxas só são calculadas quando numerador e denominador foram informados e o denominador é
maior que zero. Exemplos: quem chegou aos 3 s / inícios elegíveis; conclusões / inícios
elegíveis; compartilhamentos / contas alcançadas. Percentual médio assistido pode exceder
100% por repetição e é guardado separadamente. Métricas indisponíveis permanecem `null`.

Repetir uma observação do mesmo post não soma as visualizações. Identificadores comuns do
YouTube e parâmetros de compartilhamento são normalizados para evitar duplicação; links
encurtados não são resolvidos externamente. A análise usa o registro mais recente por post.

Comparações são internas ao projeto e descritivas: mesma plataforma, duração e janela
aproximadas, com pelo menos três outros posts com retenção comparável. São critérios locais
de comparação, não regras dos algoritmos. Sem base comparável, o resultado é `INCONCLUSIVE`.
Tema, público, distribuição e pouca exposição continuam sendo fatores de confusão. Não há
otimização automática de prompts, causalidade inferida, score universal ou previsão de views.

## Interface de integração

Todas as rotas usam a proteção existente do Studio e o proxy autenticado do Maestro.
No navegador o prefixo é `/api/studio`; diretamente no Studio, loopback `127.0.0.1:8029`.
Bodies JSON dos novos endpoints, criação e edição de projeto têm limite de 64 KiB.

| Método e rota no Studio | Uso |
|---|---|
| `POST /api/video-projects/briefing-preview` | Detectar `brief` e `distributionMode`, sem persistir |
| `POST /api/video-projects` | Criar com `objective`, `distributionMode` e `platforms` opcionais |
| `PATCH /api/video-projects/{id}` | Alterar `distributionMode` ou registrar `publicationBrief` sem substituir o objetivo |
| `GET /api/video-projects/{id}/internet-publication` | Ler contrato, checklist, pacotes e resultados |
| `POST .../internet-publication/plan` | Salvar `{expectedRevision, plan}` |
| `POST .../internet-publication/packages` | Preparar pacote local do master aprovado |
| `GET .../internet-publication/packages/{packageId}/download` | Baixar com nova verificação de integridade/aprovação |
| `POST .../internet-publication/measurements` | Registrar observação manual de um pacote da mesma plataforma |

Para agentes/direção, o helper é somente leitura por padrão:

```powershell
python ferramentas/video_global_engine/tools/prepare_internet_publication.py --project <id-exato> --brief-file <pedido.txt>
```

Com alteração do projeto já autorizada, adicionar `--apply` e, se disponível,
`--plan-file <direcao.json>`. O arquivo contém somente os campos editoriais listados acima
com as chaves: `audience`, `promise`, `emotion`, `opening`, `alternativeOpening`, `progression`,
`payoff`, `mobileFraming`, `silentComprehension`, `constraints`.
O helper usa a API como escritor único, não segue redirecionamentos e aceita apenas loopback.
Não armazena credenciais. Não usa o gatilho como autorização para renderizar ou publicar.

## Persistência, verificação e rollback

- Intenção: `project_manifest.json → distribution_intent`.
- Direção/histórico/resultados: `edit/internet_publication.json`, com gravação atômica,
  revisão e fingerprint do briefing. Limites: 100 revisões, 1000 observações e 4 MiB/arquivo.
- Entregas: `edit/internet_packages/{uuid}/`. Nunca substituem `output/`.
- Código: `services/studio/internet_publication.py`, rotas em `main.py`, integração em
  `video_projects.py`, interface em `app/assets/internet-publication.{js,css}`.
- Skill: `pemara-cinematic-take-director`, intenção aplicada antes do roteiro.

Testes em `services/studio`: `test_internet_publication.py`,
`test_internet_publication_api.py`, `test_internet_publication_browser.py`.
O navegador usa API real em raiz temporária, vídeo sintético e startup desativado.

O backup anterior à implantação está em
`E:/Pemara/scratch/internet_mode_20260831_062240/before`, com hashes em `backup_manifest.json`.
Evidências e recibo de segurança ficam no subdiretório `validation` desse backup.
Para desativar por projeto, selecionar **Fluxo habitual**; os dados e pacotes permanecem.
Para rollback de código, revisar as diferenças contra o backup e restaurar somente este
escopo, preservando alterações posteriores. Reiniciar apenas o Studio após confirmar filas
ociosas. Não restaurar projetos, masters ou histórico de trabalhos a partir do backup de código.
