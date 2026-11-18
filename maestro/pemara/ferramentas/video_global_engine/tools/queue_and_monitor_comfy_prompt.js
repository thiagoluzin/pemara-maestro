const fs = require('fs');
const crypto = require('crypto');

const [promptPath, runPath] = process.argv.slice(2);
if (!promptPath || !runPath) {
  process.stderr.write('Usage: node queue_and_monitor_comfy_prompt.js <prompt.json> <run.json>\n');
  process.exit(2);
}

const baseUrl = 'http://127.0.0.1:8188';
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const readJson = (file) => JSON.parse(fs.readFileSync(file, 'utf8'));
const writeJson = (file, value) => fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');

async function getJson(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.text();
  let parsed;
  try { parsed = body ? JSON.parse(body) : {}; } catch { parsed = { raw: body }; }
  if (!response.ok) throw new Error(`HTTP ${response.status} ${url}: ${JSON.stringify(parsed)}`);
  return parsed;
}

(async () => {
  const queueBefore = await getJson(`${baseUrl}/queue`);
  if ((queueBefore.queue_running || []).length || (queueBefore.queue_pending || []).length) {
    throw new Error('Comfy queue is not empty; refusing to mix this serial take with another job.');
  }

  const prompt = readJson(promptPath);
  const run = readJson(runPath);
  if (run.queue_status !== 'NOT_QUEUED') throw new Error(`Run status is ${run.queue_status}, expected NOT_QUEUED.`);
  const clientId = `vejito-${String(run.take_id || 'take').toLowerCase()}-${crypto.randomUUID()}`;
  const queued = await getJson(`${baseUrl}/prompt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, client_id: clientId }),
  });
  if (!queued.prompt_id) throw new Error(`Comfy did not return prompt_id: ${JSON.stringify(queued)}`);

  run.queue_status = 'QUEUED';
  run.prompt_id = queued.prompt_id;
  run.client_id = clientId;
  run.queued_at = new Date().toISOString();
  writeJson(runPath, run);
  process.stdout.write(`${JSON.stringify({ event: 'queued', prompt_id: queued.prompt_id, number: queued.number })}\n`);

  const started = Date.now();
  let transientFailures = 0;
  while (Date.now() - started < 4 * 60 * 60 * 1000) {
    await sleep(10000);
    try {
      const history = await getJson(`${baseUrl}/history/${queued.prompt_id}`);
      const item = history[queued.prompt_id];
      if (item) {
        run.completed_at = new Date().toISOString();
        run.elapsed_seconds = Math.round((Date.now() - started) / 1000);
        run.comfy_status = item.status || {};
        run.outputs = item.outputs || {};
        const failed = (item.status?.messages || []).some((message) => Array.isArray(message) && message[0] === 'execution_error');
        run.queue_status = failed ? 'FAILED' : 'COMPLETED';
        writeJson(runPath, run);
        process.stdout.write(`${JSON.stringify({
          event: failed ? 'failed' : 'completed',
          prompt_id: queued.prompt_id,
          elapsed_seconds: run.elapsed_seconds,
          status: item.status,
          outputs: item.outputs,
        }, null, 2)}\n`);
        process.exitCode = failed ? 1 : 0;
        return;
      }
      const queue = await getJson(`${baseUrl}/queue`);
      process.stdout.write(`${JSON.stringify({
        event: 'progress',
        elapsed_seconds: Math.round((Date.now() - started) / 1000),
        running: (queue.queue_running || []).length,
        pending: (queue.queue_pending || []).length,
      })}\n`);
      transientFailures = 0;
    } catch (error) {
      transientFailures += 1;
      process.stderr.write(`${JSON.stringify({ event: 'poll_error', transientFailures, error: String(error.message || error) })}\n`);
      if (transientFailures >= 12) throw error;
    }
  }
  throw new Error('Timed out waiting four hours for the serial Comfy take.');
})().catch((error) => {
  try {
    const run = readJson(runPath);
    run.queue_status = run.queue_status === 'NOT_QUEUED' ? 'QUEUE_REJECTED' : 'MONITOR_FAILED';
    run.failure_at = new Date().toISOString();
    run.failure = String(error.stack || error);
    writeJson(runPath, run);
  } catch {}
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
