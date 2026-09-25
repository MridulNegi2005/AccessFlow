const assert = require("node:assert/strict");
const LiveVoice = require("../../demo/live-voice.js");

function harness(timing = {}) {
  let now = 0;
  let ticker;
  const sent = { status: [], previews: [], finals: [], states: [], errors: [] };
  const resources = { tracksStopped: 0, contextsClosed: 0, portsClosed: 0 };
  const stream = {
    getTracks: () => [{ stop() { resources.tracksStopped += 1; } }],
  };
  const context = {
    sampleRate: 16000,
    audioWorklet: { addModule: async () => {} },
    destination: {},
    createMediaStreamSource: () => ({ connect() {}, disconnect() {} }),
    createGain: () => ({ gain: { value: 1 }, connect() {}, disconnect() {} }),
    async close() { resources.contextsClosed += 1; },
  };
  const voice = new LiveVoice({
    timing,
    getUserMedia: async () => stream,
    createAudioContext: () => context,
    createRecorder: () => ({
      port: { onmessage: null, close() { resources.portsClosed += 1; } },
      connect() {}, disconnect() {},
    }),
    now: () => now,
    setInterval: (callback) => { ticker = callback; return 1; },
    clearInterval: () => { ticker = null; },
    encodeWav: (chunks) => new Uint8Array(chunks.reduce((count, chunk) => count + chunk.length, 44)),
    sendStatus: (...args) => { sent.status.push(args); return true; },
    sendPreview: (...args) => { sent.previews.push(args); return true; },
    sendFinal: (...args) => { sent.finals.push(args); return true; },
    onSpeechStart: () => {},
    onPreview: () => {},
    onState: (value) => sent.states.push(value),
    onError: (value) => sent.errors.push(value),
  });
  return {
    voice, sent, resources,
    feed(ms, active) {
      for (let elapsed = 0; elapsed < ms; elapsed += 20) {
        now += 20;
        voice.acceptSamples(new Float32Array(320).fill(active ? 0.12 : 0));
        ticker?.();
      }
    },
    advance(ms) { now += ms; ticker?.(); },
  };
}

(async () => {
  const live = harness();
  assert.equal(await live.voice.start(), true);
  live.feed(1500, true);
  assert.deepEqual(live.sent.status[0].slice(1), [0, "pending"]);
  assert.equal(live.sent.previews.length, 1, "one bounded preview starts during speech");
  assert.equal(live.sent.finals.length, 0, "preview is not a final request");
  const id = live.sent.status[0][0];
  assert.equal(live.sent.previews[0][0], id);
  assert.equal(live.voice.previewResult(id, 1, "Tuesday at three", null), true);
  live.advance(1000);
  assert.equal(live.sent.finals.length, 0, "internal pause cannot finish a request");
  live.feed(400, true);
  assert.equal(live.sent.previews.length, 2, "speech after pause supersedes preview");
  assert.equal(live.voice.previewResult(id, 1, "stale Tuesday", null), false);
  assert.equal(live.voice.previewResult(id, 2, "actually Wednesday at five", null), true);
  live.advance(2200);
  assert.equal(live.sent.finals.length, 1);
  assert.equal(live.sent.finals[0][0], id);
  assert.equal(live.sent.finals[0][1], 3);
  assert.equal(live.voice.active, true, "automatic turn completion keeps the session open");

  const delayed = harness();
  assert.equal(await delayed.voice.start(), true);
  delayed.feed(1500, true);
  const delayedId = delayed.sent.status[0][0];
  assert.equal(delayed.sent.previews[0][1], 1);
  delayed.feed(600, false);
  delayed.feed(400, true);
  assert.equal(delayed.voice.previewResult(delayedId, 1, "stale Tuesday", null), false,
    "resumed speech invalidates an in-flight preview before its callback arrives");
  assert.equal(delayed.voice.turn.previewText, null);
  delayed.feed(600, true);
  assert.equal(delayed.sent.previews.length, 2);
  const freshRevision = delayed.sent.previews[1][1];
  assert.ok(freshRevision > 1);
  assert.equal(delayed.voice.previewResult(delayedId, freshRevision,
    "actually Wednesday at five", null), true);
  assert.equal(delayed.voice.previewResult(delayedId, 1, "late Tuesday", null), false);
  delayed.feed(2400, false);
  assert.equal(delayed.sent.finals.length, 1);
  assert.equal(delayed.sent.finals[0][1], freshRevision + 1);
  await delayed.voice.end();

  const unfinished = harness();
  assert.equal(await unfinished.voice.start(), true);
  unfinished.feed(1500, true);
  const unfinishedId = unfinished.sent.status[0][0];
  assert.equal(unfinished.voice.previewResult(
    unfinishedId, 1, "Book Tuesday, actually", null), true);
  unfinished.feed(2600, false);
  assert.equal(unfinished.sent.finals.length, 0,
    "an explicit correction cue cannot become a final request on quiet alone");
  unfinished.feed(400, true);
  assert.equal(unfinished.sent.previews.length, 2);
  assert.equal(unfinished.voice.previewResult(
    unfinishedId, 2, "Book Tuesday, actually Wednesday at five", null), true);
  unfinished.feed(2300, false);
  assert.equal(unfinished.sent.finals.length, 1,
    "the completed correction still finishes hands-free");
  await unfinished.voice.end();

  const abandoned = harness();
  assert.equal(await abandoned.voice.start(), true);
  abandoned.feed(1500, true);
  const abandonedId = abandoned.sent.status[0][0];
  abandoned.voice.previewResult(abandonedId, 1, "Book Tuesday, actually...", null);
  abandoned.feed(5600, false);
  assert.equal(abandoned.sent.finals.length, 0,
    "a never-completed correction must not authorize final audio");
  assert.deepEqual(abandoned.sent.status[1].slice(1), [2, "failed"]);
  assert.match(abandoned.sent.errors.at(-1), /unfinished/i);
  await abandoned.voice.end();

  const extended = harness();
  assert.equal(await extended.voice.start(), true);
  extended.feed(1500, true);
  const extendedId = extended.sent.status[0][0];
  for (let revision = 1; revision <= 3; revision += 1) {
    assert.equal(extended.voice.previewResult(
      extendedId, revision, `prefix ${revision}`, null), true);
    extended.feed(1600, true);
  }
  assert.equal(extended.sent.previews.length, 4,
    "speech continuing after three previews still needs a fresh bounded preview");
  assert.equal(extended.voice.previewResult(
    extendedId, 4, "complete corrected request", null), true);
  extended.feed(2300, false);
  assert.equal(extended.sent.finals.length, 1);
  assert.equal(extended.sent.finals[0][1], 5);
  await extended.voice.end();

  const bounded = harness({ maxTurnMs: 3000 });
  assert.equal(await bounded.voice.start(), true);
  bounded.feed(3400, true);
  assert.equal(bounded.sent.finals.length, 0);
  assert.equal(bounded.sent.status.at(-1)[2], "failed");
  assert.match(bounded.sent.errors.at(-1), /too long/i);
  bounded.feed(1000, true);
  assert.equal(bounded.sent.status.length, 2,
    "continuous speech after a capped turn must not start a suffix-only request");
  bounded.feed(700, false);
  bounded.feed(400, true);
  assert.equal(bounded.sent.status.length, 3,
    "a new turn may start only after the speaker has gone quiet");
  await bounded.voice.end();

  assert.throws(() => harness({ quietCompleteMs: 6000, quietFailureMs: 5500 }),
    /quietFailureMs must exceed/i);
  const patient = harness({ quietCompleteMs: 3000, quietFailureMs: 6500 });
  assert.equal(await patient.voice.start(), true);
  patient.feed(1500, true);
  const patientId = patient.sent.status[0][0];
  patient.voice.previewResult(patientId, 1, "complete informational question", null);
  patient.feed(2300, false);
  assert.equal(patient.sent.finals.length, 0,
    "a configured patient pause must override the default completion point");
  patient.feed(800, false);
  assert.equal(patient.sent.finals.length, 1);
  await patient.voice.end();

  const previewLimited = harness({ maxPreviewsPerTurn: 1 });
  assert.equal(await previewLimited.voice.start(), true);
  previewLimited.feed(1500, true);
  const limitedId = previewLimited.sent.status[0][0];
  previewLimited.voice.previewResult(limitedId, 1, "early prefix", null);
  previewLimited.feed(400, true);
  previewLimited.feed(5600, false);
  assert.equal(previewLimited.sent.finals.length, 0);
  assert.match(previewLimited.sent.errors.at(-1), /preview capacity/i);
  await previewLimited.voice.end();

  live.feed(400, true);
  assert.equal(live.sent.status.length, 2);
  await live.voice.end();
  assert.equal(live.voice.active, false);
  assert.equal(live.sent.finals.length, 1, "End session discards unfinished second turn");
  assert.deepEqual(live.resources, {
    tracksStopped: 1, contextsClosed: 1, portsClosed: 1,
  });
  live.advance(6000);
  assert.equal(live.sent.finals.length, 1, "late timer cannot flush audio");

  let grant;
  let lateStops = 0;
  const pending = harness();
  pending.voice.options.getUserMedia = () => new Promise((resolve) => { grant = resolve; });
  const starting = pending.voice.start();
  await pending.voice.end();
  grant({ getTracks: () => [{ stop() { lateStops += 1; } }] });
  assert.equal(await starting, false);
  assert.equal(lateStops, 1, "late permission grant releases its track");
  assert.equal(pending.sent.finals.length, 0);
})().catch((error) => { console.error(error); process.exitCode = 1; });
