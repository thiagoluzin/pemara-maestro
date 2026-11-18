# Download MP3 no Maestro — 2026-10-05

O áudio gerado tinha URL sem extensão e era reproduzido em FLAC. O menu de salvar de alguns clientes podia usar `.bin`; o link anterior também não convertia para MP3.

Agora o chat e o histórico usam uma URL terminada em `.mp3`, com reprodução inline e botão **Baixar MP3**. A entrega declara `audio/mpeg` e `Content-Disposition` com nome ASCII e nome UTF-8. Áudios locais compatíveis são convertidos por FFmpeg/libmp3lame a 320 kbps, em CPU, sem alterar a fonte nem gerar uma nova composição. MP3 existente é reutilizado. O cache fica em `dados/studio/audio_downloads`, fora do catálogo de resultados.

A rota autenticada `/api/generative/audio-export/{filename}` aceita somente URLs conhecidas de resultados locais. Fontes remotas, caminhos fora da raiz e arquivos de vídeo são recusados. Resultados do Comfy são lidos exclusivamente do armazenamento local; não há consulta ao serviço nessa rota. Conversão usa arquivo temporário, publicação atômica e bloqueios para evitar duplicação concorrente. Os cabeçalhos são preservados pelo proxy existente.

## Validação

- 13 testes passaram: cinco de entrega MP3 e oito de criação musical. Os testes de entrega incluem codificação real, cache, preservação da fonte, falha sem arquivo parcial, caminhos e nomes seguros, tipo MIME, download e Range 206.
- `node --check app/assets/maestro.js` passou.
- Download pela página pública autenticada no Edge salvou `C:\Users\admin_remoto\Downloads\Midnight Masquerade.mp3`; FFprobe confirmou MP3, estéreo, 320000 bit/s e 180 segundos. Hash igual à cópia de entrega: `7dbeded0c7ad2078012942d15f20498ffd64d05af01998a2a7f6264389550c89`.
- Player público carregou 180 segundos, readyState 4, sem erro. A reprodução do chat e do histórico usa a nova URL.
- Original FLAC permanece com SHA256 `056f1a08dd28b2022e862e7fe035f0d14b1daef56a27e2b01a4d6f395b7bd20a`.
- Aparelho físico do proprietário não foi operado; a verificação de download ocorreu no navegador desktop.

Build: `20261005-mp3-download-v1`. Arquivos anteriores preservados em `backups/mp3_download_20261005_094543`. Studio reiniciado pelo supervisor autorizado após confirmar ausência de trabalhos ativos e lease de GPU livre. Nenhum motor foi alterado.

Entrega e captura: `outputs/music_midnight_masquerade_20261005/Midnight_Masquerade.mp3` e `maestro_download_mp3.jpg`.
