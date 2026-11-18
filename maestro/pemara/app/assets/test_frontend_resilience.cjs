const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, 'frontend-resilience.js'), 'utf8');
function setup(fetch) {
  const context = vm.createContext({ window: {}, fetch, AbortController, setTimeout, clearTimeout, document: { hidden: false }, navigator: { onLine: true } });
  vm.runInContext(source, context);
  return context.window.MaestroResilience;
}
const response = (status, body) => ({ status, ok: status >= 200 && status < 300, text: async () => body });
(async () => {
  let calls = 0;
  const api = setup(async () => { calls++; return response(200, '<html>Login</html>'); });
  await assert.rejects(api.requestJson('/api/studio'), e => e.code === 'INVALID_RESPONSE');
  assert.equal(calls, 1);
  const broken = setup(async () => { calls++; throw new Error('socket lost'); });
  const before = calls;
  await assert.rejects(broken.requestJson('/approval', { method: 'PATCH', body: '{}' }), e => e.code === 'NETWORK_ERROR');
  assert.equal(calls, before + 1, 'A failed write must never be replayed');
  assert.equal(broken.pendingWrites, 0);
  const expired = setup(async () => response(401, '{"erro":"private"}'));
  await assert.rejects(expired.requestJson('/api/studio'), e => e.status === 401 && /sessão expirou/.test(e.message));
  const good = setup(async () => response(200, '{"saved":true}'));
  assert.equal((await good.requestJson('/data')).saved, true);
  const slow = setup((url, options) => new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new Error('abort')))));
  await assert.rejects(slow.requestJson('/data', { timeoutMs: 10 }), e => e.code === 'TIMEOUT');
  const external = new AbortController();
  const waiting = slow.requestJson('/data', { signal: external.signal }); external.abort();
  await assert.rejects(waiting, e => e.code === 'ABORTED');
  let finish, active = 0, started = 0;
  const poll = good.createPoller(() => { started++; active++; return new Promise(resolve => { finish = () => { active--; resolve(true); }; }); }, 1000);
  const first = poll.run(); const second = poll.run();
  assert.equal(first, second); assert.equal(started, 1); assert.equal(active, 1);
  finish(); await first; poll.stop();
  const inputs = { 'gen-prompt': { value: 'Nao perder este texto' }, 'film-director-reason': { value: 'Corrigir a camera' }, 'password': { value: 'must-not-store' } };
  const storage = new Map(), timers = new Map(), delays = [];
  let sequence = 0;
  const sandbox = vm.createContext({window:{},document:{hidden:false,getElementById:id=>inputs[id]},navigator:{onLine:true},AbortController,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    setTimeout:(fn,ms)=>{delays.push(ms);timers.set(++sequence,fn);return sequence;},clearTimeout:id=>timers.delete(id)});
  vm.runInContext(source,sandbox);const recovery=sandbox.window.MaestroResilience;
  recovery.saveDraft('gen-prompt');inputs['gen-prompt'].value='';recovery.restoreDraft('gen-prompt');
  assert.equal(inputs['gen-prompt'].value,'Nao perder este texto');
  recovery.saveDraft('password');assert.equal(storage.size,1);
  recovery.saveDraft('film-director-reason','project-a/take-1');inputs['film-director-reason'].value='';
  recovery.restoreDraft('film-director-reason','project-b/take-1');assert.equal(inputs['film-director-reason'].value,'');
  recovery.restoreDraft('film-director-reason','project-a/take-1');assert.equal(inputs['film-director-reason'].value,'Corrigir a camera');
  recovery.forgetDraft('film-director-reason','project-a/take-1');inputs['film-director-reason'].value='';
  recovery.restoreDraft('film-director-reason','project-a/take-1');assert.equal(inputs['film-director-reason'].value,'');
  let reads=0;const retry=recovery.createPoller(async()=>{reads++;return false;},1000);
  await retry.run();assert.equal(delays.at(-1),2000);
  await retry.run();assert.equal(delays.at(-1),4000);
  sandbox.document.hidden=true;await retry.run();assert.equal(reads,2);
  sandbox.document.hidden=false;sandbox.navigator.onLine=false;await retry.run();assert.equal(reads,2);
  retry.stop();
  console.log('PASS: serialized polling, backoff, hidden/offline pause, scoped drafts and credential exclusion');
  console.log('PASS: JSON validation, session expiry, timeout, cancellation and write without retry');
})().catch(e => { console.error(e); process.exitCode = 1; });
