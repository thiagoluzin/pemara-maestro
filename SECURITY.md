# Segurança

## Escopo desta distribuição

O repositório é deliberadamente stateless. Modelos, credenciais, bancos,
uploads, projetos, outputs, logs, sessões e recibos operacionais devem permanecer
fora do Git.

## Regras de implantação

- Mantenha ComfyUI e os serviços de inferência em loopback.
- Coloque autenticação e autorização no gateway antes de qualquer exposição.
- Valide tipo real, tamanho, nome e destino de uploads.
- Nunca aceite paths arbitrários, IDs de outro usuário ou campos sensíveis
  fornecidos pelo cliente.
- Use uma lease exclusiva para jobs de GPU e não mate processos que não
  pertencem ao job atual.
- Não exponha manifestos locais que contenham paths, hostname ou inventário de
  hardware.
- Faça rotação imediata de qualquer segredo que tenha sido commitado.

Relate vulnerabilidades pelo recurso privado **Security Advisories** do GitHub.
Não publique credenciais ou dados pessoais em issues.
