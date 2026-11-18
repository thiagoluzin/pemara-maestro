# Spark

Workflow experimental separado, criado em 12/10/2026 a pedido do proprietário. Nenhum render, instalação de extensão ou reinício foi executado. O workflow oficial permanece preservado.

No ComfyUI, abra a lista de workflows e selecione **Spark**. Após a atualização de 14/10/2026, a cópia no runtime ativo fica em `D:/PemaraRuntimes/state/ComfyUI-v0.40.0-pemara/user/default/workflows/Spark.json`. A cópia anterior permanece preservada. Se a lista ainda não mostrar o arquivo, atualize a página/lista. Também é possível importar `Spark.json` deste diretório.

Configuração inicial: H3 FL2VA pruned INT8 ConvRot, VAE INT8, 1088×608, 10 passos, 124 quadros a 24 FPS, seed fixa, áudio desligado e sem Face Refine. Spark SM120: Top-K 30%, warmup 20%, uma camada densa, strict ligado. Sage/proteção e Spectrum foram mantidos no grafo; a execução conjunta continua não qualificada.

**Estado: rascunho bloqueado para execução no runtime atual.** A validação pelo MCP encontrou um único erro estrutural: o nó `MiniMaxH3SparkAttentionSM120` não está instalado. O serviço central agora usa ComfyUI 0.40.0; a release Spark v0.1.3 ainda declara somente 0.38/0.39 e recomenda 0.39.2. O grafo v0.1.2 deste experimento foi preservado como referência. O pacote Windows SM120 exige seu ambiente Python/CUDA compatível. Um JSON válido ou essa única ausência não comprovam compatibilidade de execução.

Antes do teste posterior, configurar o ambiente isolado e revisar a combinação de atenção: Spark contorna o caminho Sage nos passos esparsos. Este arquivo não promove uma exceção ao workflow oficial nem afirma que ambas as atenções executam juntas. Conferir a avaliação em `E:/Pemara/maestro/pemara/dados/validation/h3_spark_refmod_assessment_20261012/AVALIACAO.md`.

Escolher a âncora exata aprovada, editar o prompt e declarar `content_kind`. O valor inicial `unknown` exige seleção explícita. Ao alterar passos, manter os valores de Spark e BasicScheduler iguais. Saída nativa em `Spark/native`; preservar essa fonte para comparar com o baseline.

O ramo de acabamento live action está **desativado** e foi excluído do JSON API de geração. Ativá-lo somente após revisão da fonte e conferir o contrato vigente: Lanczos + NVENC, RIFE exato 60 e DLSS integral, sem máscaras. Em animação, escolher o perfil SeedVR2 próprio antes do acabamento. Não usar o ramo live action como perfil universal. A geometria/duração/áudio e o resultado real exigem revisão própria.

Arquivos: `Spark.json` para a interface, `Spark.api.json` para futura validação/envio MCP, `manifest.json` com hashes, `validation.json` com a resposta viva de validação. Não houve geração ou medição de ganho.
