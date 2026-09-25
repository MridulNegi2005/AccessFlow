const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const modeStart = html.indexOf("function modeLabel() {");
const start = html.indexOf("function show(event) {");
const end = html.indexOf("function renderResponse(event)", start);
assert.ok(modeStart >= 0 && start > modeStart && end > start,
  "answer projection and mode label functions exist");

const nodes = new Map();
for (const selector of [
  "#announcements",
  "#request-summary",
  "#backend-status",
  "#answer-context",
  "#voice-state",
  "#voice-help",
  "#voice-toggle",
]) {
  nodes.set(selector, {
    textContent: selector === "#request-summary" ? "Current request" : "",
    classList: { add() {}, remove() {} },
  });
}
nodes.set("#answer-error", {
  textContent: "",
  classList: {
    values: new Set(),
    add(value) { this.values.add(value); },
    remove(value) { this.values.delete(value); },
    contains(value) { return this.values.has(value); },
  },
});
nodes.set("#processing", { lastElementChild: { textContent: "" } });
const rendered = [];
const context = {
  document: {
    querySelector(selector) {
      assert.ok(nodes.has(selector), `Unexpected selector: ${selector}`);
      return nodes.get(selector);
    },
  },
  rendered,
};
vm.createContext(context);
vm.runInContext(
  `let runInProgress = true;
   let finalSourceId = "current-source";
   let requestSourceIds = new Set(["current-source"]);
   let requestEventIds = new Map();
   let requestRevisions = new Map();
   let requestResolvedSources = new Set();
   let activeSessionId = null;
   let pendingAnswers = [];
   let inputsDispatched = true;
   let responseBackend = "demo/mock";
   let agentMode = "mock";
   let previewMode = false;
   let sessionEnded = false;
   let liveVoice = null;
   let livePreviewAvailable = false;
   let playbackCancellations = 0;
   function cancelSpeech() { playbackCancellations += 1; }
   function setVoiceCaption() {}
   function announce(event) { return event.kind; }
    function renderResponse(event) { rendered.push(event); }
    function finishRun() { runInProgress = false; }
    ${html.slice(modeStart, start)}
    ${html.slice(start, end)}`,
  context,
);

const show = (event) => vm.runInContext(`show(${JSON.stringify(event)})`, context);
show({ kind: "demo_status", payload: {
  perception_backend: "local/Faster Whisper CPU INT8 audio",
  reasoner_backend: "demo/mock-reasoner",
} });
assert.equal(
  nodes.get("#backend-status").textContent,
  "Perception: local/Faster Whisper CPU INT8 audio · Reasoner: demo/mock-reasoner",
);
assert.equal(nodes.get("#answer-context").textContent, "Demo · mock tools · Conversation");
show({ kind: "demo_status", session_id: "configured-session", payload: {
  agent_mode: "configured", tool_environment: "mock",
  perception_backend: "faster-whisper/cpu-int8", reasoner_backend: "ollama/gemma3:4b",
} });
assert.equal(nodes.get("#answer-context").textContent,
  "Configured agent · mock tools · Conversation");
vm.runInContext('activeSessionId = null; agentMode = "mock";', context);

show({ kind: "demo_observation", payload: {
  source_id: "old-source", event_id: "old-event", modality: "text", text: "Old request", final: true,
} });
assert.equal(nodes.get("#request-summary").textContent, "Current request");
show({ kind: "demo_observation", payload: {
  source_id: "current-source", event_id: "current-event", modality: "text", text: "Current request", final: true,
} });
show({ kind: "final", payload: { caused_by_event_id: "old-event", text: "Stale answer" } });
show({ kind: "final", payload: { text: "Unattributed answer" } });
assert.equal(rendered.length, 0);
assert.equal(nodes.get("#announcements").textContent, "demo_observation");

vm.runInContext("inputsDispatched = false", context);
show({ kind: "final", payload: { caused_by_event_id: "current-event", text: "Early answer" } });
assert.equal(rendered.length, 0);
assert.equal(vm.runInContext("pendingAnswers.length", context), 1);
vm.runInContext("inputsDispatched = true", context);
show({ kind: "final", payload: { caused_by_event_id: "current-event", text: "Current answer" } });
assert.equal(rendered.length, 1);
assert.equal(rendered[0].payload.text, "Current answer");
show({ kind: "final", payload: { caused_by_event_id: "current-event", text: "Duplicate answer" } });
assert.equal(rendered.length, 1);

vm.runInContext(
  `runInProgress = true;
   finalSourceId = "latest-source";
   requestSourceIds = new Set(["earlier-source", "latest-source"]);
   requestEventIds = new Map([
     ["earlier-source", "earlier-current-event"],
     ["latest-source", "latest-current-event"],
   ]);
   requestResolvedSources = new Set(["earlier-source", "latest-source"]);
   inputsDispatched = true;`,
  context,
);
show({
  kind: "final",
  payload: {
    caused_by_event_id: "earlier-current-event",
    text: "Reply to an earlier input in this task",
  },
});
assert.equal(rendered.length, 2);
assert.equal(rendered[1].payload.text, "Reply to an earlier input in this task");

vm.runInContext(
  `runInProgress = true;
   finalSourceId = "new-source";
   requestSourceIds = new Set(["earlier-source", "latest-source"]);
   requestEventIds = new Map([["earlier-source", "earlier-event"]]);
   requestResolvedSources = new Set(["earlier-source"]);
   pendingAnswers = [];
   inputsDispatched = false;`,
  context,
);
show({ kind: "final", payload: { caused_by_event_id: "earlier-event", text: "Early valid answer" } });
assert.equal(rendered.length, 2);
assert.equal(vm.runInContext("pendingAnswers.length", context), 1);
show({ kind: "demo_observation", payload: {
  source_id: "latest-source", event_id: "latest-event", modality: "image", final: true,
} });
vm.runInContext("inputsDispatched = true", context);
assert.equal(vm.runInContext("replayPendingAnswer()", context), true);
assert.equal(rendered.length, 3);
assert.equal(rendered[2].payload.text, "Early valid answer");

vm.runInContext(
  `runInProgress = true;
   finalSourceId = "new-source";
   requestSourceIds = new Set(["new-source"]);
   requestEventIds = new Map([["new-source", "new-event"]]);
   requestResolvedSources = new Set(["new-source"]);
   pendingAnswers = [];
   inputsDispatched = true;`,
  context,
);
show({
  kind: "error",
  payload: { caused_by_event_id: "old-event", message: "Late old failure" },
});
assert.equal(vm.runInContext("runInProgress", context), true);
assert.equal(nodes.get("#answer-error").textContent, "");
assert.equal(nodes.get("#answer-error").classList.contains("visible"), false);
show({
  kind: "error",
  payload: { caused_by_event_id: "new-event", message: "Current failure" },
});
assert.equal(vm.runInContext("runInProgress", context), false);
assert.equal(
  nodes.get("#answer-error").textContent,
  "The request could not be completed. Please try again.",
);
assert.equal(nodes.get("#answer-error").classList.contains("visible"), true);

vm.runInContext(
  `runInProgress = true;
   requestSourceIds = new Set(["submitted-audio"]);
   requestEventIds = new Map();
   requestRevisions = new Map();
   activeSessionId = "current-session";
   inputsDispatched = true;`,
  context,
);
nodes.get("#answer-error").textContent = "";
nodes.get("#answer-error").classList.values.clear();
show({
  kind: "demo_status",
  session_id: "current-session",
  accepted_event_id: "accepted-audio-event",
  accepted_revision: 2,
  payload: { media_received: "audio", source_id: "submitted-audio" },
});
assert.equal(
  vm.runInContext('requestEventIds.get("submitted-audio")', context),
  "accepted-audio-event",
  "the receipt must establish causality before ASR returns",
);
show({
  kind: "demo_status",
  session_id: "current-session",
  accepted_event_id: "older-audio-event",
  accepted_revision: 1,
  payload: { media_received: "audio", source_id: "submitted-audio" },
});
assert.equal(
  vm.runInContext('requestEventIds.get("submitted-audio")', context),
  "accepted-audio-event",
  "a delayed older revision must not replace the current event",
);
show({
  kind: "error",
  session_id: "current-session",
  payload: {
    caused_by_event_id: "older-audio-event",
    code: "backend_failure",
    detail: "Do not display backend internals",
  },
});
assert.equal(vm.runInContext("runInProgress", context), true);
show({
  kind: "error",
  session_id: "old-session",
  payload: {
    caused_by_event_id: "accepted-audio-event",
    code: "backend_failure",
    detail: "Old session failure",
  },
});
assert.equal(vm.runInContext("runInProgress", context), true);
show({
  kind: "error",
  session_id: "current-session",
  payload: {
    caused_by_event_id: "accepted-audio-event",
    code: "backend_failure",
    detail: "Do not display backend internals",
  },
});
assert.equal(vm.runInContext("runInProgress", context), false);
assert.equal(nodes.get("#answer-error").classList.contains("visible"), true);
assert.match(nodes.get("#answer-error").textContent, /could not process/i);

vm.runInContext(
  `runInProgress = true;
   requestSourceIds = new Set(["stop-source"]);
   requestEventIds = new Map([["stop-source", "stop-event"]]);
   requestRevisions = new Map([["stop-source", 0]]);
   requestResolvedSources = new Set(["stop-source"]);
   inputsDispatched = true;`,
  context,
);
show({
  kind: "acknowledge", session_id: "old-session",
  payload: { caused_by_event_id: "stop-event", stop_output: true },
});
show({
  kind: "acknowledge", session_id: "current-session",
  payload: { caused_by_event_id: "old-event", stop_output: true },
});
assert.equal(vm.runInContext("playbackCancellations", context), 0);
show({
  kind: "acknowledge", session_id: "current-session",
  payload: { caused_by_event_id: "stop-event", stop_output: true },
});
assert.equal(vm.runInContext("playbackCancellations", context), 1);
assert.equal(vm.runInContext("runInProgress", context), true);
show({
  kind: "acknowledge", session_id: "current-session", state: { status: "stopped" },
  payload: { caused_by_event_id: "stop-event", stop_output: true },
});
assert.equal(vm.runInContext("runInProgress", context), false);
assert.doesNotMatch(nodes.get("#answer-error").textContent, /backend internals/i);

const renderedBeforeMixedInput = rendered.length;
vm.runInContext(
  `runInProgress = true;
   requestSourceIds = new Set(["good-frame", "failed-audio"]);
   requestEventIds = new Map([
     ["good-frame", "good-frame-event"],
     ["failed-audio", "failed-audio-event"],
   ]);
   requestRevisions = new Map([["good-frame", 0], ["failed-audio", 0]]);
   requestResolvedSources = new Set(["good-frame"]);
   inputsDispatched = true;`,
  context,
);
show({
  kind: "final",
  session_id: "current-session",
  payload: { caused_by_event_id: "good-frame-event", text: "Incomplete success" },
});
assert.equal(rendered.length, renderedBeforeMixedInput);
assert.equal(vm.runInContext("runInProgress", context), true);
show({
  kind: "error",
  session_id: "current-session",
  payload: { caused_by_event_id: "failed-audio-event", code: "backend_failure" },
});
assert.equal(vm.runInContext("runInProgress", context), false);
assert.equal(rendered.length, renderedBeforeMixedInput);
assert.match(nodes.get("#answer-error").textContent, /could not process/i);
vm.runInContext(
  `runInProgress = true;
   requestEventIds = new Map([["new-source", "new-event"]]);
   requestResolvedSources = new Set(["new-source"]);
   pendingAnswers = [];
   inputsDispatched = true;`,
  context,
);
nodes.get("#answer-error").textContent = "";
nodes.get("#answer-error").classList.values.clear();
show({
  kind: "demo_error",
  payload: { backend: "demo/input", message: "Current input rejected" },
});
assert.equal(vm.runInContext("runInProgress", context), false);
assert.equal(nodes.get("#answer-error").textContent, "Current input rejected");

const duplicateBaseline = rendered.length;
show({
  kind: "error", session_id: "current-session",
  payload: { caused_by_event_id: "new-event", code: "backend_failure" },
});
assert.equal(rendered.length, duplicateBaseline);
assert.equal(nodes.get("#answer-error").textContent, "Current input rejected");
vm.runInContext(
  `runInProgress = true;
   requestSourceIds = new Set(["recovered-source"]);
   requestEventIds = new Map([["recovered-source", "recovered-event"]]);
   requestRevisions = new Map([["recovered-source", 0]]);
   requestResolvedSources = new Set(["recovered-source"]);
   inputsDispatched = true;`,
  context,
);
show({
  kind: "final", session_id: "current-session",
  payload: { caused_by_event_id: "recovered-event", text: "Recovered request" },
});
assert.equal(rendered.length, duplicateBaseline + 1);
assert.equal(rendered.at(-1).payload.text, "Recovered request");
