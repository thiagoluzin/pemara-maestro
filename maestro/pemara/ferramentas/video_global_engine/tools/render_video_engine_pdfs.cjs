const fs = require("fs");
const path = require("path");
const { pathToFileURL } = require("url");
const { chromium } = require("playwright");
const { marked } = require("marked");

const engineRoot = String.raw`E:\Pemara\maestro\pemara\ferramentas\video_global_engine`;
const readmePath = path.join(engineRoot, "README.md");
const outputDir = path.join(engineRoot, "docs", "pdf");
const edgePath = String.raw`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`;

const readmePdf = path.join(outputDir, "visao_motor_video_global_engine.pdf");
const chainPdf = path.join(outputDir, "cadeia_geracao_videos_maestro.pdf");
const readmePreview = path.join(outputDir, "_preview_visao_motor.png");
const chainPreview = path.join(outputDir, "_preview_cadeia.png");

const diagram = String.raw`flowchart TD
    A["Pedido ou direção criativa"] --> B["Projeto no Video Global Engine"]
    B --> B1["project_manifest.json<br/>objetivo, duração e fila ativa"]
    B --> B2["take_queue.json<br/>ou fila indicada pelo manifesto"]

    B2 --> C["Cada take"]
    C --> C1["Contrato da cena<br/>prompt, negativos, câmera, duração e perfil"]
    C --> C2["Imagem-base + JSON lateral"]

    C2 --> D{"Imagem-base aprovada<br/>approved_for_video?"}
    D -- "Não" --> E["Pedido ao diretor<br/>categoria ANCHOR"]
    E --> E1["Candidato de imagem-âncora"]
    E1 --> E2{"Revisão humana"}
    E2 -- "Reprovada" --> E
    E2 -- "Aprovada" --> D

    D -- "Sim" --> F["Job persistente no Maestro"]
    F --> F1["QUEUED"]
    F1 --> F2["Espera GPU, ComfyUI e gates"]
    F2 --> G["Workflow I2V Wan2.2 A14B"]

    G --> G1["Identity Locked"]
    G --> G2["Motion"]
    G --> G3["Fun Camera"]

    G1 --> H["MP4 bruto + JSON + proveniência"]
    G2 --> H
    G3 --> H

    H --> I["Cópia canônica em<br/>takes/maestro_generated"]
    I --> J["Proxy de revisão em CPU + QC"]
    J --> K{"Decisão humana do take"}

    K -- "Reprovado" --> L["Pedido ao diretor<br/>motivo e categoria exatos"]
    L --> M["Corrigir prompt, âncora<br/>movimento ou composição"]
    M --> C

    K -- "Aprovado" --> N["Take APPROVED"]
    N --> O{"Upscale FHD necessário?"}

    O -- "Sim" --> P["UltraSharp / pós-processamento<br/>candidato em qc/upscaled"]
    P --> Q{"Revisão humana do FHD"}
    Q -- "Reprovado" --> N
    Q -- "Aprovado" --> R["output_active passa a apontar<br/>para o candidato FHD"]

    O -- "Não" --> R
    R --> S{"Takes necessários aprovados?"}

    S -- "Não" --> C
    S -- "Sim" --> T["Finalizador FFmpeg"]

    T --> T1["Normaliza 24/30 fps"]
    T1 --> T2["Ordena e concatena os takes"]
    T2 --> T3["Preserva 16:9 em 1920×1080"]
    T3 --> T4["Música + loudness"]
    T4 --> T5["Legendas PT-BR embutidas"]
    T5 --> T6["Logo oficial no encerramento"]
    T6 --> U["MP4 final + ASS + SRT + JSON + contact sheet"]
    U --> V["Google Drive<br/>Takes Finais"]

    N -. "Opcional" .-> W["Exportação de aprovados<br/>para dataset e treinos futuros"]`;

const sharedCss = `
  :root {
    color-scheme: light;
    --ink: #17233c;
    --muted: #52627f;
    --blue: #0a67d1;
    --cyan: #00b8e6;
    --paper: #ffffff;
    --wash: #f3f7fc;
    --line: #d8e3f1;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: var(--paper); color: var(--ink); }
  body {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.52;
  }
`;

function escapeHtml(text) {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function renderReadme(browser) {
  const markdown = fs.readFileSync(readmePath, "utf8");
  marked.setOptions({ gfm: true, breaks: false });
  const content = marked.parse(markdown);
  const page = await browser.newPage({ viewport: { width: 1240, height: 1754 }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html>
  <html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <base href="${pathToFileURL(engineRoot + path.sep).href}">
    <style>
      ${sharedCss}
      @page { size: A4; margin: 18mm 16mm 18mm 18mm; }
      main { max-width: 178mm; margin: 0 auto; }
      h1, h2, h3, h4 { color: #103c73; line-height: 1.2; break-after: avoid; }
      h1 {
        margin: 0 0 10mm;
        padding-bottom: 5mm;
        font-size: 26pt;
        border-bottom: 3px solid var(--cyan);
      }
      h2 { margin: 9mm 0 3mm; font-size: 17pt; border-bottom: 1px solid var(--line); padding-bottom: 2mm; }
      h3 { margin: 6mm 0 2mm; font-size: 13pt; }
      h4 { margin: 4mm 0 2mm; font-size: 11.5pt; }
      p { margin: 0 0 3.2mm; }
      ul, ol { margin: 1.5mm 0 4mm; padding-left: 7mm; }
      li { margin-bottom: 1.2mm; }
      code {
        font-family: Consolas, "Cascadia Mono", monospace;
        font-size: 8.7pt;
        color: #13345d;
        overflow-wrap: anywhere;
      }
      pre {
        margin: 3mm 0 5mm;
        padding: 4mm;
        border: 1px solid var(--line);
        border-left: 4px solid var(--blue);
        border-radius: 4px;
        background: var(--wash);
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        break-inside: avoid;
      }
      table { width: 100%; border-collapse: collapse; margin: 4mm 0 6mm; font-size: 9pt; }
      th, td { border: 1px solid var(--line); padding: 2.4mm; vertical-align: top; }
      th { background: #eaf3ff; color: #103c73; }
      blockquote {
        margin: 4mm 0;
        padding: 2mm 4mm;
        border-left: 4px solid var(--cyan);
        color: var(--muted);
        background: #f8fbff;
      }
      a { color: #075fbf; text-decoration: none; overflow-wrap: anywhere; }
      img { max-width: 100%; height: auto; }
      hr { border: 0; border-top: 1px solid var(--line); margin: 7mm 0; }
    </style>
  </head>
  <body><main>${content}</main></body>
  </html>`, { waitUntil: "load" });
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: readmePdf,
    format: "A4",
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: `<div style="font:8px 'Segoe UI',Arial;color:#6b7890;width:100%;padding:0 16mm;text-align:right;">Video Global Engine · Pemara</div>`,
    footerTemplate: `<div style="font:8px 'Segoe UI',Arial;color:#6b7890;width:100%;padding:0 16mm;display:flex;justify-content:space-between;"><span>README técnico</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
    margin: { top: "18mm", right: "16mm", bottom: "18mm", left: "18mm" }
  });
  await page.emulateMedia({ media: "screen" });
  await page.screenshot({ path: readmePreview, fullPage: false });
  await page.close();
}

async function renderChain(browser) {
  const page = await browser.newPage({ viewport: { width: 1680, height: 2376 }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html>
  <html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <style>
      ${sharedCss}
      @page { size: A1 portrait; margin: 0; }
      body {
        width: 594mm;
        height: 841mm;
        overflow: hidden;
        min-height: 100vh;
        background:
          radial-gradient(circle at 18% 10%, rgba(0,184,230,.10), transparent 28%),
          linear-gradient(180deg, #f8fbff 0%, #ffffff 22%, #f5f9ff 100%);
      }
      main {
        width: 594mm;
        height: 841mm;
        padding: 9mm 10mm 7mm;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      header { margin: 0 0 7mm; text-align: center; }
      h1 { margin: 0; color: #0e376b; font-size: 24pt; line-height: 1.15; letter-spacing: .2px; }
      .subtitle { margin-top: 2mm; color: var(--muted); font-size: 10.5pt; }
      .diagram-frame {
        flex: 1 1 auto;
        min-height: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        padding: 7mm;
        border: 1px solid #cbdbea;
        border-radius: 10px;
        background: rgba(255,255,255,.94);
        box-shadow: 0 5px 18px rgba(26,72,124,.08);
      }
      .mermaid { width: 100%; height: 100%; display: flex; justify-content: center; align-items: center; }
      .mermaid svg {
        display: block;
        width: 100% !important;
        height: 100% !important;
        max-width: 100%;
        max-height: 780mm;
      }
      footer { flex: 0 0 auto; margin-top: 3mm; text-align: right; color: #6d7a91; font-size: 8.5pt; }
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Cadeia de geração de vídeos</h1>
        <div class="subtitle">Video Global Engine · Maestro · da direção criativa à entrega final</div>
      </header>
      <section class="diagram-frame">
        <div class="mermaid">${escapeHtml(diagram)}</div>
      </section>
      <footer>Fluxo operacional — Pemara</footer>
    </main>
  </body>
  </html>`, { waitUntil: "load" });

  await page.addScriptTag({ url: "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js" });
  await page.evaluate(async () => {
    mermaid.initialize({
      startOnLoad: false,
      theme: "base",
      securityLevel: "loose",
      flowchart: { curve: "basis", htmlLabels: true, nodeSpacing: 24, rankSpacing: 28, useMaxWidth: true },
      themeVariables: {
        fontFamily: "Segoe UI, Arial, sans-serif",
        fontSize: "13px",
        primaryColor: "#edf6ff",
        primaryTextColor: "#17233c",
        primaryBorderColor: "#2878c8",
        lineColor: "#4d6f96",
        secondaryColor: "#e8fbff",
        tertiaryColor: "#f6f9fd",
        edgeLabelBackground: "#ffffff",
        clusterBkg: "#ffffff",
        clusterBorder: "#b9cce0"
      }
    });
    await mermaid.run({ querySelector: ".mermaid" });
  });
  await page.waitForSelector(".mermaid svg");
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: chainPdf,
    width: "594mm",
    height: "841mm",
    pageRanges: "1",
    printBackground: true,
    preferCSSPageSize: true,
    margin: { top: "0", right: "0", bottom: "0", left: "0" }
  });
  await page.emulateMedia({ media: "screen" });
  await page.screenshot({ path: chainPreview, fullPage: true });
  await page.close();
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: edgePath });
  try {
    await renderReadme(browser);
    await renderChain(browser);
  } finally {
    await browser.close();
  }
  process.stdout.write(JSON.stringify({ readmePdf, chainPdf, readmePreview, chainPreview }));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
