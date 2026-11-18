# Contrato de prompt por âncora

O analisador visual não deve inferir nome, lore, anatomia oculta, objetos fora
do quadro, ação futura ou texto ilegível. Incerteza permanece explícita.

Fluxo obrigatório:

1. Validar bytes e MIME da imagem.
2. Extrair evidência estruturada.
3. Confrontar evidência com a intenção do usuário.
4. Bloquear divergências graves ou mudanças contra invariantes.
5. Gerar um ID determinístico do contrato.
6. Compilar um dialeto próprio para o motor escolhido.
7. Vincular o job e o recibo ao mesmo ID.

H3 recebe uma descrição multimodal integrada. LTX 2.5 recebe uma narrativa
cronológica com primeiro quadro, fases físicas, câmera, continuidade e regra
`8n+1`. Os dois compiladores compartilham fatos e restrições, mas não o texto
final.
