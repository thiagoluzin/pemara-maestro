const fs = require('fs');

const promptPath = process.argv[2];
if (!promptPath) {
  process.stderr.write('Usage: node validate_comfy_api_prompt.js <api-prompt.json>\n');
  process.exit(2);
}

(async () => {
  const prompt = JSON.parse(fs.readFileSync(promptPath, 'utf8'));
  const response = await fetch('http://127.0.0.1:8188/object_info');
  if (!response.ok) throw new Error(`Comfy object_info HTTP ${response.status}`);
  const objectInfo = await response.json();
  const errors = [];
  const classCounts = {};

  for (const [id, node] of Object.entries(prompt)) {
    const type = String(node.class_type || '');
    classCounts[type] = (classCounts[type] || 0) + 1;
    const schema = objectInfo[type];
    if (!schema) {
      errors.push(`${id}: unknown class_type ${type}`);
      continue;
    }
    const required = schema.input?.required || {};
    for (const name of Object.keys(required)) {
      const inputs = node.inputs || {};
      const hasDynamicChildren = Object.keys(inputs).some((key) => key.startsWith(`${name}.`));
      if (!Object.prototype.hasOwnProperty.call(inputs, name) && !hasDynamicChildren) {
        errors.push(`${id} ${type}: missing required input ${name}`);
      }
    }
    for (const [name, value] of Object.entries(node.inputs || {})) {
      if (Array.isArray(value) && value.length === 2 && typeof value[0] === 'string') {
        if (!prompt[value[0]]) errors.push(`${id}.${name}: broken link to ${value[0]}`);
      }
    }
  }

  if (classCounts.LTXVAddGuide !== 2) errors.push('Expected exactly two LTXVAddGuide nodes.');
  if (classCounts.LTXVCropGuides !== 2) errors.push('Expected exactly two LTXVCropGuides nodes.');
  if (classCounts.LoadImage !== 2) errors.push('Expected exactly two approved LoadImage anchors.');
  if (prompt['5511']?.inputs?.value !== 24) errors.push('FPS must be 24.');
  if (prompt['5512']?.inputs?.value !== 5) errors.push('Duration must be 5 seconds.');
  if (prompt['5514:3059']?.inputs?.width !== 512 || prompt['5514:3059']?.inputs?.height !== 288) {
    errors.push('Stage-1 dimensions must be 512x288 for the 1024x576 pilot.');
  }
  if (Object.prototype.hasOwnProperty.call(prompt['5518:4849']?.inputs || {}, 'audio')) {
    errors.push('Visual pilot CreateVideo must not contain audio.');
  }
  if (Object.values(prompt).some((node) => /TextGenerateLTX2Prompt|GemmaAPITextEncode/.test(String(node.class_type)))) {
    errors.push('Optional prompt enhancer/API nodes must be absent.');
  }
  for (const id of ['9101', '9102']) {
    if (prompt[id]?.inputs?.frame_idx !== -1) errors.push(`${id}: final guide must use frame_idx -1.`);
    if (prompt[id]?.inputs?.strength !== 0.9) errors.push(`${id}: final guide strength must be 0.9.`);
  }
  if (prompt['5517:4975']?.inputs?.samples?.[0] !== '9201') errors.push('Stage 2 must consume cropped stage-1 latent.');
  if (prompt['5518:5538']?.inputs?.samples?.[0] !== '9202') errors.push('Decoder must consume cropped stage-2 latent.');

  const result = {
    ok: errors.length === 0,
    prompt: promptPath,
    nodes: Object.keys(prompt).length,
    class_counts: classCounts,
    errors,
  };
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  if (errors.length) process.exitCode = 1;
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
