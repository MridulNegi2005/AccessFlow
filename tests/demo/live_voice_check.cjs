const assert = require("node:assert/strict");
const LiveVoice = require("../../demo/live-voice.js");

function harness() {
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
