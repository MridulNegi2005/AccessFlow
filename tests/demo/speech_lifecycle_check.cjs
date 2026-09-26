const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const liveVoiceStart = html.indexOf("liveVoice = new window.AccessFlowLiveVoice(");
const liveVoiceStartEnd = html.indexOf("onSpeechStart: beginLiveRun", liveVoiceStart);
assert.ok(liveVoiceStart >= 0 && liveVoiceStartEnd > liveVoiceStart);
assert.match(html.slice(liveVoiceStart, liveVoiceStartEnd),
  /onVoiceActivity:\s*interruptLiveOutputForVoice/,
  "live voice connects detected speech onset to playback cancellation");
const start = html.indexOf("function cancelSpeech()");
const end = html.indexOf("function announce(event)", start);
assert.ok(start >= 0 && end > start, "speech lifecycle functions exist");

const pill = {
  visible: false,
  classList: {
    add() { pill.visible = true; },
    remove() { pill.visible = false; },
  },
};
const status = { textContent: "Ready" };
const help = { textContent: "" };
const interrupts = [];
const synthesis = {
  canceled: 0,
  spoken: [],
  cancel() { this.canceled += 1; },
  speak(utterance) { this.spoken.push(utterance.text); },
};
const context = {
  window: { speechSynthesis: synthesis },
  SpeechSynthesisUtterance: function (text) { this.text = text; },
  interrupts,
  sendInterrupt(scope) { interrupts.push(scope); },
  document: {
    querySelector(selector) {
      if (selector === "#speak-pill") return pill;
      if (selector === "#voice-state") return status;
      if (selector === "#voice-help") return help;
      throw new Error(`Unexpected selector: ${selector}`);
    },
  },
};
vm.createContext(context);
vm.runInContext(
  "let speechGeneration = 0; let ttsUtterance = null; let liveVoice = null; let runInProgress = false; " + html.slice(start, end),
  context,
);

const first = vm.runInContext('speak("first"); ttsUtterance', context);
first.onstart();
assert.equal(status.textContent, "AccessFlow is speaking");

const second = vm.runInContext('speak("second"); ttsUtterance', context);
second.onstart();
vm.runInContext("liveVoice = { active: true, turn: null, voiceDetected: true }; interruptLiveOutputForVoice(); speak('during voice onset'); liveVoice.turn = { id: 'next' }; speak('during live speech')", context);
assert.equal(vm.runInContext("ttsUtterance", context), null,
  "a late answer must not start read-aloud over a newer microphone turn");
assert.deepEqual(interrupts, [],
  "voice onset stops browser playback without cancelling task authority before words are known");
assert.equal(status.textContent, "Listening to you…",
  "the visible state changes as soon as assistant playback stops");
assert.deepEqual(synthesis.spoken, ["first", "second"]);
first.onend();
assert.equal(status.textContent, "Listening to you…",
  "a late speech-end callback cannot overwrite the barge-in state");
assert.equal(pill.visible, false);

vm.runInContext("cancelSpeech()", context);
status.textContent = "Playback stopped";
second.onstart();
second.onend();
assert.equal(status.textContent, "Playback stopped");
assert.equal(pill.visible, false);
assert.equal(synthesis.canceled, 4);
