# Contrato de qualidade da produção — 2026-10-08

Este é um guia de decisões e evidências para agentes. Não é um novo schema do backend, classificador automático de qualidade nem autorização de geração. O pedido e o AGENTS vigente prevalecem.

## O que deve existir antes do prompt

Uma ficha curta por take, ligada à sequência:

```text
Take / versão / papel na sequência:
O público deve perceber ou sentir:
Estado inicial → estímulo/interferência → resposta → estado final:
Personagens: objetivo, tática, olhar, ação dominante e recuperação:
Geografia: posições, distâncias relativas, eixo e direção de tela:
Fotografia: escala, ponto de vista, trajetória motivada, luz e material:
Beats 0–30%, 30–70%, 70–100% (duração real e grade do modo escolhido):
Identidade: ficha original; âncoras aprovadas; estados antes/depois:
Som: áudio existente, silêncio ou criação explicitamente autorizada:
Corte: informação/vetor entregue ao próximo; por que termina aqui:
Risco dominante / controle suportado / critério observável de sucesso:
Limites e aspectos já aprovados que não podem mudar:
```

Não completar campos com palavras como 'épico', 'realista', 'qualidade máxima' ou com o nome do próprio campo. Escrever o que deve acontecer e aparecer. Não exigir o mesmo número de takes ou a mesma duração de toda cena; preserve o contrato específico e a qualificação temporal do motor.

## Revisão por dimensões

Use `PASS`, `FAIL`, `PENDING` ou `NOT_APPLICABLE` justificado. PASS do agente é parecer com evidência, nunca aprovação do proprietário. Não calcular média geral que esconda uma falha crítica.

| Dimensão | Evidência procurada | Falha que impede selecionar a fonte |
|---|---|---|
| História/clareza | estímulo, mudança e consequência legíveis | repetição, promessa não cumprida ou ação sem causa |
| Atuação | objetivo legível, escuta, olhar e resposta ao evento | reação antecipada, tiques, gesto vazio ou emoção incompatível |
| Ação/física | apoio, impulso, contato/evasão, deslocamento, recuperação | voo sem causa, pés deslizando, força sem massa |
| Fotografia | foco de atenção, geografia, perspectiva e luz coerentes | câmera gratuita, contato escondido, espaço/luz mudando sem causa |
| Identidade/arte | comparação com ficha original e versão correta | rosto, escala, roupa, anatomia, poder ou material divergentes |
| Continuidade | intervalos móveis dos dois lados e estado persistente | reset, dano desaparecendo, vetor ou proprietário trocado |
| Montagem/ritmo | progressão compreensível no filme completo | cortes redundantes, cauda sem informação, reação mutilada |
| Som, quando houver | reprodução/escuta e relação com a ação | voz errada, fala inventada, clipping, impacto antecipado |
| Integridade técnica | decode, hash, duração, FPS, frames, streams e recibos | corrupção, incompatibilidade ou acabamento ausente |

Inspecione o MP4 inteiro em velocidade normal e todos os beats críticos/junções em revisão temporal densa. Índices 0/25/50/75/100% e contact sheets orientam a inspeção; não bastam para aprovar física, atuação ou ritmo. Verifique o que foi efetivamente visto/escutado. Se a ferramenta só permite imagens, marque movimento/escuta como pendentes.

Não inventar evidência de compreensão do público ou de escuta humana. Diferencie 'parecer do agente' de 'avaliação do proprietário'. Ao entregar para avaliação, declarar pendências e limitar a afirmação ao que foi observado.

## Revisão que produz uma correção

```text
Arquivo/path/hash e take/versão:
Dimensão / PASS|FAIL|PENDING|NOT_APPLICABLE:
Timestamp ou intervalo observado:
Observação concreta (o que aparece/soa):
Consequência para a cena:
Hipótese de causa (marcada como hipótese):
Correção prioritária e controles que mudarão:
Aspectos aprovados preservados:
Condição de reavaliação e pendências:
```

Uma ficha preenchida, um hash certo ou uma validação de grafo não demonstra qualidade artística. Não registrar PASS com base só no prompt. Reprovação do proprietário autoriza substituta no mesmo escopo, preservada a tentativa rejeitada; não autoriza montagem, publicação, motor novo ou expansão.

## Regras operacionais atuais do Maestro

- MiniMax H3 é a escolha vigente; LTX foi removido por ordem do proprietário em 2026-10-08. Não reinstalar nem oferecer como fallback. Preserve materiais e histórico antigos.
- H3 exige SageAttention + Spectrum efetivamente no caminho de amostragem; use o contrato atual de `services/studio/h3_spectrum_master20.json`. Não empilhar FirstBlockCache nem reduzir passos/resolução para fingir sucesso.
- Operação ComfyUI pelo Codex usa somente MCP `comfyui-local`, começando por `server_info`; conferir runtime, fila, VRAM, pausas, nodes e validar o grafo exato antes do envio. Backend autônomo Maestro mantém seu canal autorizado.
- Personagens recorrentes em novas produções exigem `identityContinuityRequired: true` e o contrato `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/docs/IDENTITY_CONTINUITY.md`. Animação avulsa de foto fica fora desse gate. Personagem existente exige pesquisa da versão antes de ficha/prompts/âncoras.
- Referência original fixa identidade; último quadro fixa pose/movimento. Frame derivado de vídeo aprovado não ganha automaticamente aprovação canônica. Referências rejeitadas não alimentam geração ou seleção.
- Corte cinético direto é preferível quando válido. Conector é somente para fontes boas, quando permitido; `generatedConnectorAllowed: false` bloqueia emenda. Preservar quatro pilares e contratos específicos, inclusive FFVIII V8.
- Acabamento de vídeo: fonte/picture lock aprovados → SeedVR2 3B int8 → RIFE 4.25 em timestamps j/60 → DLSS 5 Natural → candidato. Usar `E:/Pemara/maestro/pemara/services/studio/upscaling_required.py` e perfis aprovados; copiar o áudio existente. Não adicionar Foley a fonte silenciosa por conta própria.
- Perfil DLSS: NR 1x, intensidade 0.5, estrutura 0.5, tom 0, pele 0.25, detalhe 0.5, cor 0, auto-mask ligado. Preservar geometria, duração, áudio e transparência; formatos não qualificados bloqueiam, sem conversão silenciosa.
- Toda nova saída visual precisa de tratamento DLSS com recibo/hashes; herança válida evita aplicar duas vezes em cópia/mux/proxy/concat. Integridade do recibo não aprova aparência.
- Preservar nativo, reprovados, fontes aprovadas e recibos. Projeto encerrado não reabre por auditoria. Nunca transferir aprovação entre takes, acabamentos ou projetos.

## Tipos de vídeo

| Tipo | Decisão anterior à decupagem | Evidência no filme |
|---|---|---|
| Ficção/live action | desejo, obstáculo, virada e consequência | mudança percebida através da atuação |
| Combate | iniciativa, golpe pertencente ao personagem e resultado | contato/evasão, massa, resposta e recuperação |
| Educação | objetivo de aprendizagem e erro comum | exemplo claro, contraste explicado e pausa interativa quando útil |
| Publicidade | promessa, prova e ação final | demonstração fiel de produto/marca sem alegação inventada |
| Animação | estilo, personalidade e lógica do movimento | timing, silhueta e ação coerentes com esse mundo |

Não forçar desastre, luta, explosão ou texto longo a um tipo que não precisa disso. Texto gráfico deve ser curto e inserido deterministicamente quando a fidelidade exigir; nunca pedir que o vídeo invente logotipo ou frase exata.

## Responsabilidades pesquisadas

Referências consultadas em 2026-10-08; adaptações para agentes e geração local são escolhas desta implementação:

- [Diretor — ScreenSkills](https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/development-film-and-tv-drama-job-profiles/director-film-and-tv-drama/): articulação da visão, blocking dos atores e colaboração entre departamentos ao longo da produção.
- [Fotografia — ScreenSkills](https://www.screenskills.com/skills-checklists/scripted-film-and-tv/camera-department/director-of-photography-skills/): responsabilidade pela imagem e coordenação de câmera/luz com a direção.
- [Montador — ScreenSkills](https://www.screenskills.com/job-profiles/browse/film-and-tv-drama/post-production/editor-film-and-tv-drama/): construir história e performance com o material, refinar com o diretor até picture lock.
- [TypeSafe — documentação viva](https://docs.typesafe.ai/llms.txt): ponto de descoberta consultado. Aplicação local: regras exatas e autorizações não devem ser substituídas por parecer semântico; este pacote não adiciona chamada de API nem envio de dados.
