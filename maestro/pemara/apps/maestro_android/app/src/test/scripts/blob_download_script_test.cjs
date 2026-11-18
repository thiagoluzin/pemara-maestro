const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../../main/java/com/pemaratech/maestrostudio');
const source = fs.readFileSync(path.join(root, 'MainActivity.java'), 'utf8');
const method = source.slice(source.indexOf('private void streamBlobFromWebView('));
const expression = method.slice(method.indexOf('String script ='), method.indexOf('webView.evaluateJavascript'));
let script = '';
for (const line of expression.split(/\r?\n/)) {
    const strings = line.match(/"(?:[^"\\]|\\.)*"/g) || [];
    strings.forEach((literal, index) => {
        script += JSON.parse(literal);
        if (index === 0 && line.includes('JSONObject.quote(blobUrl)')) script += JSON.stringify('blob:test');
    });
}
async function scenario(lengthHeader, actualSize, refuseChunk = false) {
    let expected = -1, written = 0, completed = false, failed = false;
    const bytes = new Uint8Array(actualSize);
    const reader = new ReadableStream({start(c) {c.enqueue(bytes); c.close();}});
    const bridge = {
        begin(size) {expected = size; return true;},
        writeChunk(s) {
            if (refuseChunk) return false;
            written += Buffer.from(s, 'base64').length; return true;
        },
        complete() {assert.equal(written, expected); completed = true;},
        fail() {failed = true;}
    };
    await vm.runInNewContext(script, {
        fetch: async () => ({ok: true, headers: {get: () => lengthHeader}, body: reader,
            blob: async () => new Blob([bytes])}),
        MaestroNativeBlob: bridge, btoa: s => Buffer.from(s, 'binary').toString('base64')
    });
    return {expected, written, completed, failed};
}
(async () => {
    assert.deepEqual(await scenario('120001', 120001),
        {expected:120001,written:120001,completed:true,failed:false});
    assert.deepEqual(await scenario(null, 120001),
        {expected:120001,written:120001,completed:true,failed:false});
    const short = await scenario('120001', 100);
    assert.equal(short.completed, false); assert.equal(short.failed, true);
    const refused = await scenario('120001', 120001, true);
    assert.equal(refused.completed, false); assert.equal(refused.failed, true);
    console.log('PASS: 4 WebView blob script scenarios');
})().catch(error => {console.error(error); process.exitCode = 1;});
