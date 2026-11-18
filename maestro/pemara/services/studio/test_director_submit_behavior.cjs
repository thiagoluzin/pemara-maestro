const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(require('node:path').join(__dirname, '../../app/assets/maestro.js'), 'utf8').replace(/\r\n/g, '\n');
function extract(name) {
  const start = source.indexOf(`async function ${name}(`);
  assert(start >= 0, name);
  const end = source.indexOf('\n}\n', start);
  return source.slice(start, end + 3);
}
function setup(fetchJson) {
  const fields = {
    '#film-director-take-id': {value: 'R04_A03'},
    '#film-director-mode': {value: 'correction'},
    '#film-director-category': {value: 'PROGRESSION'},
    '#film-director-reason': {value: 'Comeca robotizado e lento'},
    '#film-director-submit': {},
  };
  const events = [];
  const context = vm.createContext({AbortController, setTimeout, clearTimeout, fetchJson,
    state: {films: {activeProjectId: 'cupcake', takes: [{takeId: 'R04_A03'}]}},
    $: key => fields[key], API: {studio: '/api/studio'},
    setBusy: (_, busy) => events.push(['busy', busy]),
    closeFilmDirectorDialog: () => events.push(['close']),
    syncFilmTakeAfterUpdate: () => events.push(['sync']),
    filmAnchorReviewRequestId: () => null,
    toast: message => events.push(['toast', message]),
    refreshActiveFilmProjectSummary: async () => {},
    advanceFilmReview: () => {}, FILM_REQUEST_AWAITING_EXECUTOR_COPY: 'Pedido registrado; aguardando executor',
  });
  vm.runInContext(extract('fetchFilmDirectorRequest') + extract('submitFilmDirectorRequest'), context);
  return {context, fields, events};
}
(async () => {
  const calls = [];
  const successful = setup(async (url, options) => {
    calls.push([url, options]);
    return {takeId: 'R04_A03', status: 'REJECTED', canGenerate: false};
  });
  await successful.context.submitFilmDirectorRequest({preventDefault() {}});
  assert.equal(calls.length, 1, 'externally coordinated take must not start an independent job');
  assert.equal(JSON.parse(calls[0][1].body).directorRequest.reason, 'Comeca robotizado e lento');
  assert(successful.events.some(e => e[0] === 'close'));
  assert.deepEqual(successful.events.at(-1), ['busy', false]);
  const timeout = setup((_, options) => new Promise((resolve, reject) => {
    options.signal.addEventListener('abort', () => reject(new Error('aborted')), {once: true});
  }));
  const request = timeout.context.fetchFilmDirectorRequest;
  timeout.context.fetchFilmDirectorRequest = (url, options) => request(url, options, 5);
  await timeout.context.submitFilmDirectorRequest({preventDefault() {}});
  assert.deepEqual(timeout.events.at(-1), ['busy', false], 'timeout must release Enviando');
  assert.equal(timeout.fields['#film-director-reason'].value, 'Comeca robotizado e lento');
  assert(timeout.events.some(e => e[0] === 'toast' && e[1].includes('texto foi preservado')));
  assert(!timeout.events.some(e => e[0] === 'close'), 'unconfirmed save retains editable form');
  console.log('PASS: saved rejection, no duplicate render, timeout releases button and preserves reason');
})().catch(error => { console.error(error); process.exitCode = 1; });
