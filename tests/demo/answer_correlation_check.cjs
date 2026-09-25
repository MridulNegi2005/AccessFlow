const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const start = html.indexOf("function show(event) {");
const end = html.indexOf("function renderResponse(event)", start);
assert.ok(start >= 0 && end > start, "answer projection function exists");

const nodes = new Map();
for (const selector of [
  "#announcements",
  "#request-summary",
  "#backend-status",
  "#answer-context",
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
   let pendingAnswers = [];
   let inputsDispatched = true;
   let responseBackend = "demo/mock";
   function announce(event) { return event.kind; }
    function modeLabel() {
      return responseBackend.toLowerCase().includes("mock") ? "Mock tools" : "Live backend";
    }
    function renderResponse(event) { rendered.push(event); }
    function finishRun() { runInProgress = false; }
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
assert.equal(nodes.get("#answer-context").textContent, "Mock tools · Conversation");

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
assert.equal(nodes.get("#answer-error").textContent, "Current failure");
assert.equal(nodes.get("#answer-error").classList.contains("visible"), true);
vm.runInContext(
  `runInProgress = true;
   requestEventIds = new Map([["new-source", "new-event"]]);
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
