const { chromium } = require('E:/Pemara/lingua_em_movimento/Mira/node_modules/playwright');

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  });
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8188', { waitUntil: 'networkidle', timeout: 60000 });
  await page.waitForTimeout(3000);
  const result = await page.evaluate(() => ({
    title: document.title,
    hasApp: Boolean(window.app),
    appKeys: window.app ? Object.keys(window.app).sort() : [],
    methods: window.app ? {
      loadGraphData: typeof window.app.loadGraphData,
      graphToPrompt: typeof window.app.graphToPrompt,
      queuePrompt: typeof window.app.queuePrompt,
      graphConfigure: typeof window.graph?.configure,
      graphSerialize: typeof window.graph?.serialize,
    } : {},
    matchingGlobals: Object.keys(window)
      .filter((key) => /comfy|app|graph|workflow/i.test(key))
      .sort(),
  }));
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  await browser.close();
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
