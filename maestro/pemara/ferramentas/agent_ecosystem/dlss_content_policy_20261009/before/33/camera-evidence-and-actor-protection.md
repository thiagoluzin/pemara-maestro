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

## DLSS seletivo

Em novas âncoras com atores reais, preservar personagens completos e usar o resultado DLSS apenas no cenário. Proteger também mortos, cabelo, mãos, traje, equipamentos e, conforme a imagem, reflexos/sombras. Usar a fonte anterior ao primeiro tratamento. Comparar original, NR integral intermediário e composição; não usar aparência já artificial como referência canônica.

`skin` e `auto_mask` não garantem exclusão dos personagens. Implementação local: `services/studio/actor_protection.py` + `dlss5_finishing.finish_file(..., protect_actors=True, protection_manifest=...)`. Seletivo tem perfil separado e jamais cai silenciosamente no integral. A máscara é explícita; não há segmentação automática habilitada.

Para imagens, usar PNG/WebP sem perdas e uma máscara PNG L 8-bit com geometria idêntica: branco preserva fonte, preto usa DLSS, cinza mistura bordas em luz linear sRGB. Ambas regiões precisam existir. O interior branco é comparado pixel a pixel; cobertura correta, cabelos e halo precisam de revisão visual. O nó ComfyUI `PemaraSaveActorProtectedImage` recebe IMAGE + MASK + sujeitos + parecer de cobertura e salva com acabamento/recibo. Disponível após recarregar a extensão; não anunciar que o runtime já foi recarregado sem verificar. O builder `actor_protection.build_anchor_workflow` e o template `ferramentas/video_global_engine/workflows/upscaling_obrigatorio/dlss5_actor_protected_anchor.template.api.json` usam `ImageToMask(red)`: a saída MASK de `LoadImage` lê alpha invertido e não representa automaticamente a máscara cinza de um PNG opaco. O template começa com cobertura não conferida e não deve ser enviado sem revisão e arquivos reais.

Alternativamente, colocar ao lado da saída `<arquivo>.dlss5.protection.json`, com:

```json
{
  "schema_version": "1.0",
  "mode": "background_only_actor_protected_v1",
  "source_sha256": "SHA256_DA_FONTE_ANTES_DO_DLSS",
  "protected_subjects": ["Jill", "Barry", "zumbi", "Kenneth"],
  "mask_review": {"status": "PASS", "reviewer": "revisor real", "note": "observacao real da cobertura"},
  "masks": [{"path": "mascara.png", "sha256": "SHA256_DA_MASCARA"}]
}
```

Não tomar este exemplo como revisão realizada. Em vídeo, há uma entrada `masks` por quadro de apresentação, sem repetir automaticamente a máscara da foto. Preparar/rastrear/refinar externamente, conferir oclusão, motion blur e mudança de corte. Compor sobre a fonte imediatamente anterior ao DLSS, já com SeedVR2/RIFE na geometria/cadência final. Essa proteção não desfaz alterações anteriores. No vídeo com perdas, a igualdade vale antes do encode; não prometer pixels idênticos no MP4.

Preservar nativo, intermediário NR, contrato, máscaras e recibos com hashes. Mascaramento tem perfil `dlss5_natural_background_actor_protected_v1`; montagens mistas registram modalidades por fonte, sem fingir NR integral. Visual seletivo ainda exige comparação em mídia real; testes sintéticos de composição não qualificam aparência dos atores nem rastreamento temporal.

Não adicionar API ou supor que TypeSafe vê vídeos: regras/hashes ficam em código; parecer semântico futuro recebe evidências explícitas, com incerteza separada. Fontes consultadas: [TypeSafe](https://docs.typesafe.ai/llms.txt), [utilitário DLSS](https://github.com/DaniilSokolyuk/video2dlssnr).
