const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const start = html.indexOf("function show(event) {");
const end = html.indexOf("function renderResponse(event)", start);
assert.ok(start >= 0 && end > start, "answer projection function exists");

const nodes = new Map();
for (const selector of ["#announcements", "#request-summary"]) {
  nodes.set(selector, { textContent: selector === "#request-summary" ? "Current request" : "" });
}
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
   function announce(event) { return event.kind; }
   function renderResponse(event) { rendered.push(event); }
   function finishRun() { runInProgress = false; }
   ${html.slice(start, end)}`,
  context,
);

const show = (event) => vm.runInContext(`show(${JSON.stringify(event)})`, context);
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
