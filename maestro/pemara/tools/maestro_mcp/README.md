# MCP do Maestro

O servidor roda no computador que hospeda o Maestro. O cliente inicia o processo por stdio e ele usa a API local do Studio na porta 8029. A variável opcional `MAESTRO_STUDIO_PORT` seleciona outra porta local.

## Usar

No painel **Takes**, abra a bancada para revisar cenas, marcar quadros e assistir a versões em sequência. Em **Modelos de episódio**, salve o planejamento de um projeto ou abra um novo episódio com as cenas do modelo. As etapas de direção, referência, produção, revisão e acabamento apontam para as operações do Maestro. Um quadro de vídeo aprovado pode ser levado ao formulário **Animar foto** como origem de movimento. A foto canônica continua orientando a identidade.

Em um cliente MCP, peça por exemplo “Liste os takes do meu episódio e indique quais aguardam minha revisão” ou “Salve um modelo de animação com abertura de 3 segundos, apresentação de 6 e encerramento de 3. Crie um episódio chamado Piloto de sábado a partir dele”. O servidor pode consultar projetos, cenas, versões, instantes marcados e modelos, editar a direção textual, salvar modelos e criar episódios em planejamento. A revisão artística e a geração continuam no painel de produção.

## Conectar outro cliente neste computador

O chat integrado fica em **Takes → Abrir Cinema Studio → Codex**. Ele usa o login do Maestro no navegador e o login ChatGPT do operador Windows no computador remoto. A tarefa agendada `Pemara-Maestro-Cinema-Codex` inicia o operador ao entrar no Windows. O computador precisa ficar ligado e a sessão do operador pode ficar bloqueada. A conversa, o instante da cena e os identificadores de produção são guardados no servidor. O histórico pode ser aberto em outro navegador autenticado.

O App Server se comunica por stdio. O operador consulta o MCP do Maestro para compor o contexto textual e usa Gemini Decision para conferir propostas. Produção e correção passam pelos controles do take. Em **Fotografia**, luz e paleta do episódio podem receber exceções por plano. As imagens selecionadas entram como referências adicionais em takes já configurados para Ref2VA, dentro do limite de nove imagens do perfil. Nos outros perfis elas compõem a ficha visual e a descrição de continuidade.

### Configuração do cliente

Configure o transporte **stdio** com os seguintes valores.

| Campo | Valor |
| --- | --- |
| Executável | `%LOCALAPPDATA%\Pemara\maestro-mcp\venv\Scripts\python.exe` |
| Primeiro argumento | `E:\Pemara\maestro\pemara\tools\maestro_mcp\server.py` |

Codex usa `codex mcp add maestro -- EXECUTAVEL SCRIPT`. Claude Code lê a entrada `maestro` no arquivo `.mcp.json` do workspace. OpenCode usa uma entrada local em `mcp.maestro`, com `command` contendo o executável e o script. Reabra o cliente ou reconecte o servidor para carregar as ferramentas.

Para instalar em outra máquina que hospeda o Studio, crie um ambiente Python 3.11, instale `requirements.txt` e configure o cliente com os caminhos locais.

