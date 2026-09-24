const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const start = html.indexOf("function cancelPendingMicrophoneStart()");
const end = html.indexOf("async function stopMicrophone", start);
assert.ok(start >= 0 && end > start, "microphone start function exists");

let resolvePermission;
let rejectPermission;
let requests = 0;
let permission = new Promise((resolve, reject) => {
  resolvePermission = resolve;
  rejectPermission = reject;
});
const toggle = { disabled: false };
const oldMicButton = { disabled: false };
const state = { textContent: "Ready when you are" };
const help = { textContent: "" };
const captions = [];
const errors = [];
const context = {
  navigator: { mediaDevices: { getUserMedia() { requests += 1; return permission; } } },
  document: {
    querySelector(selector) {
      if (selector === "#speak-pill") return { classList: { contains: () => false } };
      if (selector === "#voice-toggle") return toggle;
      if (selector === "#voice-state") return state;
      if (selector === "#voice-help") return help;
      throw new Error(`Unexpected selector: ${selector}`);
    },
  },
  micButton: oldMicButton,
  cancelSpeech() {},
  setVoiceCaption(...args) { captions.push(args); },
  show(event) { errors.push(event); },
};
vm.createContext(context);
vm.runInContext(
  `let microphone = null;
   let microphoneStartPending = false;
   let microphoneStartGeneration = 0;
   let runInProgress = false;
   ${html.slice(start, end)}`,
  context,
);

(async () => {
  const first = vm.runInContext("startMicrophone()", context);
  const second = vm.runInContext("startMicrophone()", context);
  assert.equal(requests, 1, "only one browser permission request is outstanding");
  assert.equal(toggle.disabled, true);
  assert.equal(oldMicButton.disabled, true);
  assert.equal(state.textContent, "Waiting for microphone permission");
  assert.ok(captions.some(([title]) => title === "Waiting for microphone"));

  rejectPermission(new Error("Permission denied"));
  await Promise.all([first, second]);
  assert.equal(toggle.disabled, false, "denial restores the capture control");
  assert.equal(oldMicButton.disabled, false);
  assert.equal(state.textContent, "Microphone not started");
  assert.equal(errors.length, 1, "one rejection has one recoverable error");

  permission = new Promise((resolve, reject) => {
    resolvePermission = resolve;
    rejectPermission = reject;
  });
  const late = vm.runInContext("startMicrophone()", context);
  assert.equal(requests, 2);
  vm.runInContext("cancelPendingMicrophoneStart()", context);
  let stopped = 0;
  resolvePermission({ getTracks: () => [{ stop() { stopped += 1; } }] });
  await late;
  assert.equal(stopped, 1, "a late permission grant cannot leave a live track");
  assert.equal(errors.length, 1, "cancelled permission does not show a false error");
  assert.equal(toggle.disabled, false);
})().catch((error) => { console.error(error); process.exitCode = 1; });
