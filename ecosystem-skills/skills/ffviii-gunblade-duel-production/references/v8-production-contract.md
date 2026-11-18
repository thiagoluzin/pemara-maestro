# Contrato operacional V8 — duelo M08–M16

## Autoridade e limites

Projeto:

`E:/Pemara/maestro/pemara/ferramentas/video_global_engine/projetos/ffviii_clones_liveaction_intro_faithful_v1`

Rota: `M08_V8_H3_ACTING_PLATE_DETERMINISTIC_GUNBLADES_20260822`.

O proprietário aprovou em 2026-08-22 a mudança de método V8 e pediu a execução de todos os takes do
duelo. Isso autoriza a produção do lote, mas cada novo rig, âncora, vídeo, composição e montagem
continua candidato até a aprovação humana do artefato exato.

Fontes locais de evidência:

- `docs/M08_V8_ROUTE_RECALC_20260822.md`;
- `analysis/M08_V8_ROUTE_RECALC_20260822.json`;
- `production_manifest.json` e `take_queue.json` para o estado operacional vivo.

Se a narrativa desta referência divergir do arquivo vivo, não edite evidência retroativamente:
registre a decisão do proprietário por atualização reversível e rode novamente os gates da etapa.

## Divisão determinística da imagem

| Camada | Responsabilidade | Não pode fazer |
|---|---|---|
| MiniMax H3 | clones, atuação, mãos, roupas, chuva, costa, profundidade e câmera; um receptor rígido assimétrico de tracking 3D por lutador | desenhar, completar ou reinterpretar a Gunblade final |
| OpenGL local determinístico | geometria, escala, transformação rígida, colisão, luz, sombra e motion blur de Revolver/Hyperion | alterar atuação, identidade ou câmera para esconder uma placa ruim |
| Compositor | remover proxies, resolver oclusão/depth e integrar os passes por quadro | usar máscara, blur ou oclusão para ocultar morph, pausa ou empunhadura errada |

A placa inteira precisa passar corpo, mãos, física, tracking e cauda antes de receber os rigs. Uma
composição bonita não salva uma placa reprovada.

A rota Unity foi tentada e permanece preservada como evidência bloqueada por ausência de licença do
Editor. O backend de rig é o renderizador OpenGL local determinístico; isso não troca nem flexibiliza
o MiniMax H3 selecionado pelo proprietário.

Receptor, marcador, bastão, cage, placa bruta e prova de rig são artefatos técnicos internos. Eles
nunca podem ser publicados no Maestro, apresentados como vídeo candidato ou chegar à montagem. O
Maestro recebe somente a composição final limpa que já passou os gates técnicos.

## Locks das Gunblades

### Squall — `RIG_SQUALL_REVOLVER_V8`

Referência imutável:

`weapon_identity/prop_lock_v4/squall_revolver_cinematic_prop_lock_v4.png`

SHA-256: `8D6EC0E20E686ABF535D5494C121EFA39BFAFE65A687D43AA2F5EBE27A69BDB6`

Invariantes: 1,40 m; lâmina larga prateada polida; gravação do leão; cilindro exposto; guarda de
gatilho; empunhadura preta; corrente curta física. Reprovar se virar espada comum, cutelo, lâmina
preta, objeto curto ou “canivete”.

### Seifer — `RIG_SEIFER_HYPERION_V8`

Referência imutável:

`weapon_identity/prop_lock_v3/seifer_hyperion_cinematic_prop_lock_v3.png`

SHA-256: `90924A5E9D0FCFED00F0CC68DC1F2BD3D278AA66A0E442EB7C1D849DA2CA082E`

Invariantes: corpo preto de pistola semiautomática; lâmina longa prateada afilada; recorte inferior
curvo e profundo; exatamente três furos circulares. Reprovar se curta, genérica, espelhada ao
Revolver ou sem esses mecanismos.

### Anatomia e propriedade

Em todos os quadros, Squall possui somente o Revolver e Seifer somente o Hyperion. O ponto de pegada,
eixo do punho, pulso e antebraço precisam formar uma cadeia funcional; dedos fecham sobre a área real
da empunhadura e o comprimento/peso produz alavanca, antecipação, follow-through e recuperação
coerentes. Uma arma correta em mão impossível continua reprovada.

Antes da placa, cada rig exige turntable, comparação de escala humana e teste de eixo anatômico. O
arquivo e SHA-256 aprovados entram no manifesto e não são regenerados silenciosamente.

### Transformação 3D e receptor

Cada arma usa o receptor assimétrico `FFVIII_GUNBLADE_G_R_U_Z_T_V8`, com os pontos distinguíveis
`G/R/U/Z/T`, incluindo o ponto distante `T`. Exigir câmera calibrada, no mínimo quatro observações
não coplanares, baseline de pelo menos 18 px, área de triângulo de pelo menos 80 px², `solvePnP` com
refinamento temporal, profundidade positiva e erro de reprojeção RMS de no máximo 2 px. A saída deve
registrar matriz 4×4, quaternion, translação, calibração, observações, resíduos e hashes.

Dois pontos, yaw fixo, escala fixa, ponte planar, `mirror_x`, espelhamento, escala negativa ou matriz
com determinante negativo reprovam automaticamente. O rig final precisa manter determinante positivo
e escala física derivada da profundidade em todos os quadros.

A prova anatômica exige uma mão visível envolvendo a área real da empunhadura, contato mensurável e
ausência de penetração entre mão, punho e arma. Bloco, bastão ou antebraço aproximado não servem como
prova. A corrente do Revolver deve formar uma cadeia geometricamente conectada e apresentar resposta
temporal à gravidade, inércia e colisão; barras soltas ou corrente estática reprovam.

## Placas, duração e liberdade de atuação

- Motor selecionado: MiniMax H3 FL2VA pruned INT8 ConvRot; substituição proibida sem decisão humana.
- Formato de produção: 1280×720, 24 fps; H3 na grade `17k+5`, entre 124 e 362 quadros.
- Todo clipe é usado integralmente. Não aparar cabeça/cauda, acelerar, desacelerar ou interpolar.
- O H3 recebe corpos cinéticos e proxies simples com ponto de pegada/eixo legíveis. A coreografia
  pode ficar livre, mas deve preservar massa, tração, centro de gravidade, causa, evasão/contato,
  deslocamento, reação e recuperação.
- Movimento útil de lutadores, proxies, roupas, ambiente e câmera deve existir em `0–30%`, `30–70%`
  e `70–100%`, inclusive no último quadro.
- Roleta de seed não é correção. Após repetição do mesmo defeito, mudar o controle dentro da rota;
  qualquer troca de engine volta ao proprietário.

## Fronteiras móveis e microtakes

Cada saída e entrada registra:

- posição mundial dos dois lutadores;
- vetores corporais e centros de massa;
- ponto de pegada, eixo e velocidade angular de cada proxy/rig;
- pose, orientação, posição e velocidade da câmera;
- rochas, costa, chuva, spray, profundidade, luz e dano persistente.

O corte seco acontece enquanto a ação ainda progride. Se os vetores não conectarem, o take seguinte
é reprovado e uma ligação física nova deve ser gerada. Hold, freeze, frame duplicado, trim, retime,
RIFE, crossfade e oclusão de disfarce são falha automática.

Um microtake também é fonte gerada e precisa de método temporal válido. O H3 treinado começa em 124
quadros; não prometer um conector H3 menor que isso. Um controle curto diferente exige autorização
explícita, e sua saída continua sujeita aos mesmos passes e aprovação humana.

## QC integral e estado

Para a placa e para a composição final, separadamente:

1. verificar decodificação, FPS, contagem, duração, dimensões, codec e SHA-256;
2. revisar todos os quadros, com inspeção ampliada de mãos, armas, contatos e fronteiras;
3. reproduzir o MP4 completo em velocidade normal e, quando necessário, quadro a quadro;
4. validar arte live action, identidade, geografia, física, movimento e integridade técnica em passes
   independentes;
5. comparar rigs e primeira composição com as referências imutáveis, incluindo escala e mecanismo;
6. confirmar que não há pausa perceptível, cauda estática, morph, troca de dono, proxy residual,
   oclusão falsa ou drift de arma/corpo/câmera/cenário.

Ordem de estado: `ART_DIRECTION_PASS` → `CINEMATIC_PASS` → `MOTION_PASS` → `TECHNICAL_PASS` →
`HUMAN_APPROVED`.

Falha em qualquer passe reprova o artefato inteiro. Preserve caminho, hash, logs e diagnóstico;
marque `may_feed_next_take=false`, `may_assemble=false` e `may_promote=false`. Gere uma correção do
mesmo item sem apagar a rejeitada. Somente a aprovação explícita do proprietário para o arquivo e
SHA-256 revisados libera alimentação, montagem ou promoção.
