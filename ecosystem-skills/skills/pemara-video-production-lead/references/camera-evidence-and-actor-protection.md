# Câmera verificável e atores preservados — 2026-10-09

Aplica-se a novas sequências live action com múltiplos planos. Mantenha contratos específicos aprovados, os motores e o escopo. Uma auditoria de método não reabre a mídia entregue.

## Antes do lote

Produza um mapa único do cenário, ligado por caminho/hash: espaços, portas, marcos, personagens e percursos. Defina poucas posições de câmera reconhecíveis; cada uma tem eixo, trajetória ou posição fixa e informação que revela. Não impor movimento a um plano que precisa sustentar contato, disparo ou reação. Câmera fixa dirigida é diferente de congelar o vídeo; a ação interna continua conforme o beat. Contratos específicos de movimento aprovados permanecem válidos.

Registre `sequence_camera_contract.json` na raiz do projeto Maestro. O backend transmite esse contrato ao worker e valida antes da fila; a montagem também exige a revisão das fontes exatas e das fronteiras. Validador: `E:/Pemara/maestro/pemara/services/studio/sequence_camera_contract.py`. O arquivo é opt-in para o backend para preservar projetos históricos; criar o contrato é a regra de direção para novas sequências deste escopo.

O contrato usa `schema_version: "1.0"`, `map: {path, sha256}`, `spaces: [id]`, `cameras`, `takes`, `joins` e `pilot_take_ids`. Caminhos de evidências são absolutos. Consulte o template em `E:/Pemara/maestro/pemara/ferramentas/video_global_engine/templates/sequence_camera_contract.template.json`; seus pareceres começam pendentes. Não preencher PASS para conseguir gerar.

- Câmera: `id`, `space`, `axis`, `landmarks`, `purpose`, `trajectory`.
- Take: `id`, `camera_id`, `purpose`, `method_id`, `initial_state`, `final_state`, `attempts` e `review`.
- Estado: `space`, `body_ids` dos corpos conhecidos naquele espaço e `characters`. Cada personagem tem `id`, `position`, `screen_direction`, `gaze`, `action_phase`, `support`, `props`. Mudança de corpos exige `body_change_cause`.
- Fronteira: `from`, `to`, `decision`, `reason`, `review`. Todas as fronteiras adjacentes precisam existir. Conector requer `generatedConnectorAllowed: true` e `missing_causal_action`; geografia quebrada pede fonte corrigida.
- Revisão temporal: `status`, `reviewer`, `note`, `observation_mode: "temporal_video"`, `artifact: {path, sha256}` e `interval_seconds: [in, out]`. Para montagem, a revisão do take deve apontar para os bytes selecionados. Filme inteiro tem `sequence_review`.

Escolha um bloco piloto com pelo menos uma fronteira do maior risco. Seus takes podem gerar dentro da autorização vigente; o restante exige `pilot_review` temporal PASS registrado. Pré-visualização simples testa lógica prevista, sem provar movimento. Quadros isolados deixam movimento e ritmo pendentes. O validador confere vínculos e registro de observações, não interpreta pixels nem concede aprovação humana.

## Reparos

Registre por tentativa `status`, `failure_class`, `method_id`, observação e artefato/hash. Duas falhas equivalentes do mesmo método bloqueiam repeti-lo. Alterar `method_id` exige mudança real documentada de staging, câmera, cobertura ou controle e `method_change: {reason, artifact: {path, sha256}}`; renomear método ou trocar seed não resolve. Preserve tudo que foi aprovado e os rejeitados como rollback.

Inspecione saída e entrada em intervalos densos, incluindo velocidade e fase da ação. Corte compatível usa material existente. Conector serve ao acontecimento ausente; nunca virar padrão para todas as emendas. Verifique separadamente que a ameaça percorreu o espaço: corrida da vítima não demonstra chegada do perseguidor.

Casos de regressão: personagem surge na porta; perseguidor muda de posição sem percurso; corpo extra; cenário/piso/porta trocam sem passagem; pose recomposta; reação antes do contato; tiro sem alvo/queda; câmera perde o contato; pele plástica. Use evidência real por timestamp, sem nota média que esconda falha crítica.

## Evidência nas âncoras

Para carregar PNG/WebP com alfa exato, preserve `PemaraLoadLosslessImage`. Compare a fonte e a âncora integral observando rosto, mãos, traje, objetos, criatura e cenário. Examine movimento e continuidade nos takes. Os parâmetros e recibos exigidos estão no [contrato de âncoras e acabamento de vídeo](dlss5-full-frame-required.md).
