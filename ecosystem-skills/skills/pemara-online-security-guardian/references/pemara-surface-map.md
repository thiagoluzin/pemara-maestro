# Mapa de superfície Pemara

Este mapa é uma pista de roteamento, não uma fotografia garantida. Ler `E:\Pemara\PEMARA_PROJECT_MAP.md` e verificar processos, portas, túneis e DNS atuais antes de agir.

| Sistema | Código canônico | Origem conhecida | Superfície pública/estado a revalidar |
|---|---|---|---|
| Loja | `E:\Pemara\loja` | `127.0.0.1:5000` | `pemaratech.com.br`, `www.pemaratech.com.br` |
| Maestro gateway | `E:\Pemara\maestro\pemara` | `127.0.0.1:9501` | `maestro.pemaratech.com.br` e ferramentas protegidas |
| Studio | `E:\Pemara\maestro\pemara\services\studio` | `127.0.0.1:8029` | API pública deve permanecer fechada salvo decisão explícita |
| Sprunki | `E:\Pemara\maestro\pemara\ferramentas\gerador_sprunki` | `127.0.0.1:5005` | `sprunki.pemaratech.com.br` atrás do gateway |
| ComfyUI | `E:\Pemara\maestro\pemara\ferramentas\ComfyUI` | `127.0.0.1:8188` | somente por gateway autenticado quando exposto |
| PODD | `E:\Pemara\PODD-CAA-recovery` | origem local a verificar | superfície pública e rota familiar possuem decisões distintas |
| Língua em Movimento | `E:\Pemara\lingua_em_movimento\web_ts` | `127.0.0.1:5001` | `applinguia.pemaratech.com.br` |
| CICL-ND/Jornada | `D:\plataforma_multidiscilinar_logitudinal\cicl-nd` | API/gateway locais a verificar | publicação clínica permanece gate separado |
| IA local | `E:\Pemara\local_ai_qwen` e containers relacionados | loopback | não expor diretamente à LAN/Internet |

## Evidências e automação existentes

- Auditoria leve da superfície: `E:\Pemara\security\Test-PemaraOnlineSurface.ps1`.
- Relatórios: `E:\Pemara\logs\security_audit`.
- Relatório-base de 12/08/2026: `E:\Pemara\security\RELATORIO_HARDENING_2026-08-12.md`.
- Tarefa recorrente: `Pemara-Security-Surface-Audit-User`.

## Regras de inventário

1. Associar hostname -> DNS/túnel -> gateway -> origem -> processo/tarefa.
2. Confirmar se a origem escuta apenas em loopback.
3. Testar Host inválido e acesso direto sem gateway.
4. Diferenciar `200` da aplicação, `200` da tela de login e quarentena esperada.
5. Não remover ou publicar camada pública com base somente em um arquivo de configuração.
