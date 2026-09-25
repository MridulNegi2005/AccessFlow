const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const start = html.indexOf("async function discardMicrophone()");
const end = html.indexOf("async function stopMicrophone", start);
assert.ok(start >= 0 && end > start, "microphone discard helper exists");
assert.match(html, /socket\.onclose = \(\) => \{[\s\S]*?void discardMicrophone\(\);/);
assert.match(html, /window\.addEventListener\("beforeunload", \(\) => \{[\s\S]*?void discardMicrophone\(\);/);

const calls = [];
const microphone = {
  stream: { getTracks: () => [{ stop: () => calls.push("track.stop") }] },
  context: { close: async () => { calls.push("context.close"); } },
  recorder: {
    port: { close: () => calls.push("port.close") },
    disconnect: () => calls.push("recorder.disconnect"),
  },
  source: { disconnect: () => calls.push("source.disconnect") },
  silentGain: { disconnect: () => calls.push("gain.disconnect") },
};
const context = {
  setMicrophoneButtons(recording) { calls.push(`buttons:${recording}`); },
};
vm.createContext(context);
vm.runInContext(
  `let microphone = globalThis.testMicrophone;
   let recordedWavBytes = new Uint8Array([1, 2, 3]);
   ${html.slice(start, end)}`,
  Object.assign(context, { testMicrophone: microphone }),
);

(async () => {
  await vm.runInContext("discardMicrophone()", context);
  assert.equal(vm.runInContext("microphone", context), null);
  assert.equal(vm.runInContext("recordedWavBytes", context), null);
  assert.deepEqual(calls, [
    "port.close", "recorder.disconnect", "source.disconnect",
    "gain.disconnect", "track.stop", "buttons:false", "context.close",
  ]);
  await vm.runInContext("discardMicrophone()", context);
  assert.equal(calls.length, 7, "duplicate disconnect is idempotent");

  const stopStart = html.indexOf("async function stopMicrophone(reason = null)");
  const stopEnd = html.indexOf("function enqueueMediaAction", stopStart);
  assert.ok(stopStart >= 0 && stopEnd > stopStart);
  let releaseClose;
  const closePending = new Promise((resolve) => { releaseClose = resolve; });
  let encoded = 0;
  let staged = 0;
  const stopContext = {
    testMicrophone: {
      stream: { getTracks: () => [{ stop() {} }] },
      context: { close: () => closePending },
      recorder: { port: { close() {} }, disconnect() {} },
      source: { disconnect() {} },
      silentGain: { disconnect() {} },
      chunks: [new Float32Array([0.1])],
      sampleRate: 16000,
    },
    socket: { readyState: 1 },
    WebSocket: { CLOSING: 2 },
    setMicrophoneButtons() {},
    encodeWav() { encoded += 1; return new Uint8Array([1]); },
    setVoiceCaption() {},
    document: { querySelector() { return { textContent: "" }; } },
    renderStagedMedia() { staged += 1; },
    updateRunButton() {},
    show() {},
  };
  vm.createContext(stopContext);
  vm.runInContext(
    `let microphone = globalThis.testMicrophone;
     let recordedWavBytes = null;
     ${html.slice(stopStart, stopEnd)}`,
    stopContext,
  );
  const stopping = vm.runInContext("stopMicrophone()", stopContext);
  stopContext.socket.readyState = 3;
  releaseClose();
  await stopping;
  assert.equal(encoded, 0, "disconnect during close cannot stage a WAV");
  assert.equal(staged, 0);
  assert.equal(vm.runInContext("recordedWavBytes", stopContext), null);
})().catch((error) => { console.error(error); process.exitCode = 1; });
