// Read-only reproduction against the real browser event projection.
// Run from repository root: node docs/evidence/merged-2026-09-25/probe_browser.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('demo/index.html', 'utf8');
const begin = html.indexOf('function show(event) {');
const end = html.indexOf('function renderResponse(event)', begin);
assert.ok(begin >= 0 && end > begin);
const nodes = new Map();
const context = {
  document: { querySelector(id) {
    if (!nodes.has(id)) nodes.set(id, {
      textContent: '', classList: { add() {}, remove() {} },
    });
    return nodes.get(id);
  } },
};
vm.createContext(context);
vm.runInContext(`
let runInProgress = true;
let requestSourceIds = new Set(['submitted-audio']);
let requestEventIds = new Map();
let pendingAnswers = [];
let inputsDispatched = true;
let cancelledPlayback = 0;
function announce(e) { return e.kind; }
function renderResponse() {}
function finishRun() { runInProgress = false; }
function cancelSpeech() { cancelledPlayback++; }
${html.slice(begin, end)}
`, context);
vm.runInContext(`show({kind:'error', payload:{
  caused_by_event_id:'server-generated-audio-id',
  code:'backend_failure', detail:'RuntimeError'
}})`, context);
const result = {
  mode: 'real_show_function_with_synthetic_events_not_live_browser',
  pre_observation_failure: {
    run_still_pending: vm.runInContext('runInProgress', context),
    error_displayed: Boolean(nodes.get('#answer-error')?.textContent),
    known_event_ids: vm.runInContext('requestEventIds.size', context),
  },
};
vm.runInContext(`show({kind:'acknowledge', payload:{
  caused_by_event_id:'current-input', text:'Stopped.', stop_output:true
}})`, context);
result.controller_output_stop = {
  playback_cancellations: vm.runInContext('cancelledPlayback', context),
};
assert.equal(result.pre_observation_failure.run_still_pending, true);
assert.equal(result.pre_observation_failure.error_displayed, false);
assert.equal(result.controller_output_stop.playback_cancellations, 0);
console.log(JSON.stringify(result, null, 2));
