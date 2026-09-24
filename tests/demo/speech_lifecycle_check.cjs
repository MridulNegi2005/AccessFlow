const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
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
const synthesis = {
  canceled: 0,
  cancel() { this.canceled += 1; },
  speak() {},
};
const context = {
  window: { speechSynthesis: synthesis },
  SpeechSynthesisUtterance: function (text) { this.text = text; },
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
  "let speechGeneration = 0; let ttsUtterance = null; " + html.slice(start, end),
  context,
);

const first = vm.runInContext('speak("first"); ttsUtterance', context);
first.onstart();
assert.equal(status.textContent, "AccessFlow is speaking");

const second = vm.runInContext('speak("second"); ttsUtterance', context);
second.onstart();
first.onend();
assert.equal(status.textContent, "AccessFlow is speaking");
assert.equal(pill.visible, true);

vm.runInContext("cancelSpeech()", context);
status.textContent = "Playback stopped";
second.onstart();
second.onend();
assert.equal(status.textContent, "Playback stopped");
assert.equal(pill.visible, false);
assert.equal(synthesis.canceled, 3);
