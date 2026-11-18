const fs = require('fs');
const path = require('path');
const { chromium } = require('E:/Pemara/lingua_em_movimento/Mira/node_modules/playwright');

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) {
  process.stderr.write('Usage: node export_comfy_subgraph_workflow_api.js <editor-workflow.json> <api-prompt.json>\n');
  process.exit(2);
}

(async () => {
  const workflow = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8188', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForFunction(() => window.app && typeof window.app.loadGraphData === 'function', null, { timeout: 30000 });
  const promptResult = await page.evaluate(async (graphData) => {
    await window.app.loadGraphData(graphData);
    return window.app.graphToPrompt();
  }, workflow);
  await browser.close();

  if (!promptResult || !promptResult.output || typeof promptResult.output !== 'object') {
    throw new Error('Comfy frontend did not return an API prompt.');
  }
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(promptResult.output, null, 2)}\n`, 'utf8');
  const counts = {};
  for (const node of Object.values(promptResult.output)) {
    const type = String(node.class_type || 'UNKNOWN');
    counts[type] = (counts[type] || 0) + 1;
  }
  process.stdout.write(`${JSON.stringify({
    ok: true,
    input: inputPath,
    output: outputPath,
    nodes: Object.keys(promptResult.output).length,
    class_types: counts,
  }, null, 2)}\n`);
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
