# Avaliação com critérios fixos

Implementação local inspirada no método de [Self-evolve](https://github.com/DaizeDong/self-evolve), sem instalar seu runtime, trocar o motor do Harness ou criar agentes automáticos.

O operador congela a lista explícita de testes do comando `npm test`, todos os arquivos sob `test/`, o `package.json`, os lockfiles existentes, a versão do Node e o hash do avaliador. A mesma lista é executada no candidato. Nenhum comando de shell vindo do contrato é executado: o runner usa o executável Node atual e argumentos de teste validados.

## Criar uma referência antes de editar

No diretório `E:\Pemara\pemara_harness`:

```powershell
npm.cmd run evaluate:freeze -- --output .runtime/evaluations/minha-mudanca-antes
```

Guarde o `sha256` retornado fora do alcance de quem propõe a mudança. O contrato e o recibo da referência são vinculados por SHA-256. Uma pasta existente não é reutilizada.

## Comparar o candidato

```powershell
npm.cmd run evaluate:compare -- --contract .runtime/evaluations/minha-mudanca-antes/contract.json --sha HASH_RETORNADO_AO_CONGELAR
```

Para outro checkout, acrescente `--root E:/caminho/do/candidato`. A lista e os arquivos de testes devem ser idênticos, assim como a versão do Node e os arquivos de configuração congelados. Novos requisitos ou mudanças legítimas nos testes exigem uma nova avaliação; não reescrever o contrato anterior.

## Resultados

- `NO_REGRESSION_REVIEW_REQUIRED`: candidato passou, população de testes mantida e nenhuma nova omissão; ainda exige revisão. `sameSource: true` indica que nenhum código medido mudou.
- `IMPROVEMENT_REVIEW_REQUIRED`: referência tinha falhas e o candidato passou; exige revisão da mudança e da evidência.
- `REGRESSION`: candidato falhou, cancelou testes ou aumentou skips/todos.
- `INVALID_EVIDENCE`: população mudou, timeout, logs excederam o limite ou arquivos de código mudaram durante a execução.
- Mudanças nos arquivos protegidos, no avaliador ou nos hashes interrompem antes de aceitar qualquer resultado.

Sempre `accepted: false`. Não há merge, publicação, reinício de serviços, GPU, avaliação artística, chamada TypeSafe ou geração de mídia. As decisões deste gate são comparações exatas de arquivos e resultados, sem necessidade de inferência semântica.

## Evidência e limites

Os recibos locais guardam hashes dos arquivos de código em `src/`, `bin/`, `dsh/`, `scripts/` e `test/`, configuração do pacote, commit quando disponível, comando, contagens e hashes dos logs. Os logs completos ficam sob a pasta da avaliação em `.runtime`, ignorada pelo Git. O comando não envia dados a provedores externos.

O gate verifica integridade e regressões observáveis. Não é sandbox de sistema operacional: os testes executam com as permissões e o ambiente do operador. Use apenas código autorizado. Ele não comprova ausência de todos os bugs, independência de um revisor ou imutabilidade contra alguém que possa substituir também o hash de confiança. Arquivos de runtime ignorados, serviços externos e dependências não estão integralmente cobertos pelo fingerprint; integrações reais continuam exigindo os testes próprios apropriados.

O timeout limita o runner direto; não oferece isolamento ou garantia de encerramento de todos os descendentes que um teste arbitrário possa criar. Não usar este comando para executar testes desconhecidos ou controlar serviços de produção.

Fonte metodológica consultada em 2026-11-02. A implementação é própria e usa somente bibliotecas do Node.
