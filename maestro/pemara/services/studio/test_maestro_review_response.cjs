const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../../app/assets/maestro.js'), 'utf8');
const names = ['applyFilmTakeDecision', 'submitFilmDirectorRequest', 'continueSavedFilmCorrection',
  'refreshFilmProjectData', 'refreshActiveFilmProjectSummary'];
function actualFunction(name) {
  const start = source.indexOf(`async function ${name}(`);
  assert.ok(start >= 0, name);
  const rest = source.slice(start);
  const match = /\n(?:async )?function /g;
  match.lastIndex = 1;
  const next = match.exec(rest);
  return next ? rest.slice(0, next.index) : rest;
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const flush = () => new Promise(resolve => setImmediate(resolve));
function setup() {
  const button = { tagName: 'BUTTON', disabled: false };
  const fields = {
    '#film-director-submit': button,
    '#film-director-take-id': { value: '01' },
    '#film-director-mode': { value: 'correction' },
    '#film-director-category': { value: 'OTHER' },
    '#film-director-reason': { value: 'Preserve the face; correct the movement' },
  };
  const events = [];
  const context = {
    state: { films: { activeProjectId: 'project', activeTakeId: '01', takes: [{ takeId: '01', status: 'READY' }],
      projects: [{ projectId: 'project' }], takeUpdateSequence: 0 } },
    API: { studio: '/studio' },
    $: selector => fields[selector],
    setBusy: (control, busy) => { control.disabled = busy; },
    toast: message => events.push(message),
    closeFilmDirectorDialog: () => events.push('closed'),
    syncFilmTakeAfterUpdate: updated => {
      context.state.films.takeUpdateSequence++;
      context.state.films.takes = [updated];
      events.push('saved:' + updated.status);
    },
    filmAnchorReviewRequestId: () => '',
    filmTakeStatusLabel: status => status,
    advanceFilmReview: () => events.push('advanced'),
    pollFilmTakeJob: () => events.push('polling'),
    loadFilmProductionQueue: async () => {},
    FILM_REQUEST_AWAITING_EXECUTOR_COPY: 'awaiting executor',
    renderFilmProjectList: () => events.push('rendered'),
    renderFilmSummary: () => events.push('rendered'),
    renderFilmTakes: () => events.push('rendered'),
    renderFilmPlayerReview: () => events.push('review rendered'),
    confirm: () => true,
  };
  vm.createContext(context);
  vm.runInContext(names.map(actualFunction).join('\n'), context);
  return { context, events, button, fields };
}

async function run() {
  {
    const { context, events, button } = setup();
    const preparation = deferred(), summary = deferred();
    context.fetchJson = () => summary.promise;
    context.fetchFilmDirectorRequest = (url, options) => {
      if (options.method === 'PATCH') return Promise.resolve({ takeId: '01', status: 'REJECTED', canGenerate: true });
      events.push('preparing');
      return preparation.promise;
    };
    context.refreshFilmProjectData = async () => {};
    await context.submitFilmDirectorRequest({ preventDefault() {} });
    assert.equal(button.disabled, false, 'Control must be released while correction is still preparing');
    assert.ok(events.some(item => item.includes('rejeição e correção salvas')));
    assert.ok(events.indexOf('saved:REJECTED') < events.indexOf('preparing'));
    assert.ok(!events.includes('polling'));
    preparation.resolve({ jobId: 'job' });
    summary.resolve({ projectId: 'project' });
    await flush();
    assert.ok(events.includes('polling'), 'Saved correction must still be submitted automatically');
  }
  {
    const { context, events, button, fields } = setup();
    context.fetchFilmDirectorRequest = async () => { throw new Error('save failed'); };
    await context.submitFilmDirectorRequest({ preventDefault() {} });
    assert.equal(button.disabled, false);
    assert.ok(!events.includes('closed'), 'Failed save must preserve the correction dialog');
    assert.equal(fields['#film-director-reason'].value, 'Preserve the face; correct the movement');
    assert.equal(context.state.films.takes[0].status, 'READY');
  }
  {
    const { context, events, button } = setup();
    const summary = deferred();
    context.fetchJson = url => url.endsWith('/takes/01')
      ? Promise.resolve({ takeId: '01', status: 'APPROVED' }) : summary.promise;
    await context.applyFilmTakeDecision('01', 'APPROVED', button);
    assert.equal(button.disabled, false, 'Approval must not wait for the summary');
    assert.equal(context.state.films.takes[0].status, 'APPROVED');
    assert.ok(events.includes('advanced'));
    summary.resolve({ projectId: 'project' });
    await flush();
  }
  {
    const { context, events } = setup();
    const summary = deferred(), takes = deferred();
    context.fetchFilmMetadata = url => url.includes('/takes?') ? takes.promise : summary.promise;
    const refresh = context.refreshFilmProjectData('project');
    context.syncFilmTakeAfterUpdate({ takeId: '01', status: 'APPROVED' });
    summary.resolve({ projectId: 'project' });
    takes.resolve({ data: [{ takeId: '01', status: 'READY' }] });
    await refresh;
    assert.equal(context.state.films.takes[0].status, 'APPROVED', 'Stale poll cannot undo a saved approval');
    assert.ok(!events.includes('rendered'));
  }
  {
    const { context, events } = setup();
    const saved = deferred();
    context.fetchJson = () => saved.promise;
    const approval = context.applyFilmTakeDecision('01', 'APPROVED');
    context.state.films.activeProjectId = 'other';
    saved.resolve({ takeId: '01', status: 'APPROVED' });
    await approval;
    assert.ok(!events.includes('saved:APPROVED'), 'Old project response cannot replace the current project');
  }
  {
    const { context, events } = setup();
    const saved = deferred();
    let writes = 0;
    context.fetchJson = url => {
      if (url.endsWith('/takes/01')) { writes++; return saved.promise; }
      return Promise.resolve({ projectId: 'project' });
    };
    const approval = context.applyFilmTakeDecision('01', 'APPROVED');
    await context.applyFilmTakeDecision('01', 'APPROVED');
    await context.applyFilmTakeDecision('01', 'REJECTED');
    assert.equal(writes, 1, 'Repeated taps cannot send conflicting decisions');
    assert.equal(context.state.films.takes[0].status, 'READY', 'No approval before server confirmation');
    saved.resolve({ takeId: '01', status: 'APPROVED' });
    await approval;
    assert.equal(context.state.films.pendingDecisions.size, 0);
    assert.ok(events.includes('advanced'));
  }
  {
    const { context, events } = setup();
    const saved = deferred();
    context.fetchJson = url => url.endsWith('/takes/01') ? saved.promise : Promise.resolve({ projectId: 'project' });
    const approval = context.applyFilmTakeDecision('01', 'APPROVED');
    context.state.films.activeTakeId = '02';
    saved.resolve({ takeId: '01', status: 'APPROVED' });
    await approval;
    assert.ok(!events.includes('advanced'), 'Saving the previous take cannot replace a newly selected take');
  }
  console.log('PASS: 7 review response scenarios (real UI functions; no media generation)');
}
run().catch(error => { console.error(error); process.exitCode = 1; });
