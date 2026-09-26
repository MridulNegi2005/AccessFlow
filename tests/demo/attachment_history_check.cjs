const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { AccessFlowAttachmentHistory } = require("../../demo/attachment-history.js");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
assert.match(html, /<script src="\/attachment-history\.js"><\/script>/);
const inline = html.match(/<script>\s*([\s\S]*?)<\/script>/);
assert.ok(inline, "the browser application script is present");
new vm.Script(inline[1]);
const renderStart = html.indexOf("function renderAttachmentHistory(items) {");
const renderEnd = html.indexOf("function formatBytes(bytes)", renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart);
function element() {
  return {
    children: [],
    append(...children) { this.children.push(...children); },
    replaceChildren() { this.children = []; },
  };
}
const section = element();
const list = element();
const renderContext = {
  document: {
    querySelector(selector) {
      return selector === "#session-images" ? section :
        selector === "#session-image-list" ? list : null;
    },
    createElement: element,
  },
};
vm.createContext(renderContext);
vm.runInContext(html.slice(renderStart, renderEnd), renderContext);
const render = (items) => {
  renderContext.items = items;
  vm.runInContext("renderAttachmentHistory(items)", renderContext);
};

const revoked = [];
const history = new AccessFlowAttachmentHistory({
  createObjectURL: (file) => `blob:${file.name}`,
  revokeObjectURL: (url) => revoked.push(url),
});

history.startSession("session-a");
history.prepare("frame-a", { name: "first.png" });
history.prepare("frame-b", { name: "second.png" });
assert.deepEqual(history.items(), [], "sending alone must not imply server acceptance");
render(history.items());
assert.equal(section.hidden, true);
assert.equal(history.accept("session-old", "frame-a", "event-a", 0), false);
assert.equal(history.accept("session-a", "frame-a", "event-a", 0), true);
assert.equal(history.accept("session-a", "frame-a", "event-a", 0), false);
assert.equal(history.accept("session-a", "frame-b", "event-b", 0), true);
assert.deepEqual(history.items().map((item) => item.sourceId), ["frame-a", "frame-b"]);
assert.deepEqual(history.items().map((item) => item.status), ["received", "received"]);
render(history.items());
assert.equal(section.hidden, false);
assert.equal(list.children.length, 2);
assert.equal(list.children[0].children[1].children[0].textContent, "first.png");
assert.equal(list.children[1].children[1].children[2].textContent, "Source ID: frame-b");
assert.doesNotMatch(list.children[0].children[1].children[0].textContent, /Image 1/,
  "the browser cannot invent an authoritative server ordinal");
assert.equal(history.observe("session-a", "frame-a", "event-a", 0, "vision/real"), true);
assert.equal(history.fail("session-old", "event-b"), false);
assert.equal(history.fail("session-a", "event-b"), true);
assert.deepEqual(history.items().map((item) => item.status), ["observed", "failed"]);
assert.equal(history.fail("session-a", "event-a"), false,
  "an observed PNG remains usable evidence after a later task error");
render(history.items());
assert.match(list.children[1].children[1].children[1].textContent, /not available as evidence/);
assert.equal(history.items()[1].url, "blob:second.png",
  "a failed accepted image keeps its preview and identity");
assert.equal(history.observe("session-a", "frame-b", "event-b", 0, "late/vision"), false,
  "late success cannot relabel a failed image");
history.prepare("never-accepted", { name: "third.png" });
history.discardPending();
assert.equal(history.accept("session-a", "never-accepted", "event-c", 0), false);
history.prepare("end-pending", { name: "end-pending.png" });
history.endSession();
assert.equal(history.accept("session-a", "end-pending", "late-after-end", 0), false,
  "End session must discard pending images and reject late receipts");
assert.equal(history.fail("session-a", "event-a"), false);
assert.equal(history.items().length, 2, "End session leaves existing conversation visible");
history.startSession("session-b");
assert.deepEqual(history.items(), []);
assert.deepEqual(revoked, ["blob:first.png", "blob:second.png"]);
for (let index = 1; index <= 8; index += 1) {
  const source = `bounded-${index}`;
  assert.equal(history.prepare(source, { name: `${source}.png` }), true);
  assert.equal(history.accept("session-b", source, `event-${index}`, 0), true);
}
assert.equal(history.prepare("bounded-9", { name: "ninth.png" }), false,
  "the browser must reject display overflow before an upload is sent");
assert.equal(history.items().length, 8);

const responseHistory = new AccessFlowAttachmentHistory({
  createObjectURL: (file) => `blob:${file.name}`,
  revokeObjectURL() {},
});
responseHistory.startSession("response-session");
responseHistory.prepare("image-source", { name: "current.png" });
responseHistory.accept("response-session", "image-source", "image-event", 0);
responseHistory.observe("response-session", "image-source", "image-event", 0, "vision/real");
const responseStart = html.indexOf("function renderResponse(event) {");
const responseEnd = html.indexOf("function finishRun() {", responseStart);
assert.ok(responseStart >= 0 && responseEnd > responseStart);
const responseNodes = new Map();
const responseContext = {
  attachmentHistory: responseHistory,
  document: {
    querySelector(selector) {
      if (!responseNodes.has(selector)) {
        const node = element();
        node.classList = { add() {}, remove() {}, toggle() {} };
        responseNodes.set(selector, node);
      }
      return responseNodes.get(selector);
    },
    createElement: element,
  },
};
vm.createContext(responseContext);
vm.runInContext(
  `let previewMode = false;
   let stagedImageUrl = "blob:stale-staged.png";
   let requestSourceIds = new Set(["text-source"]);
   let activeInputKinds = ["text"];
   let responseBackend = "reasoner/real";
   let ttsEnabled = false;
   function modeLabel() { return "Configured agent"; }
   function speak() {}
   ${html.slice(responseStart, responseEnd)}`,
  responseContext,
);
responseContext.answer = { kind: "final", payload: { text: "Current answer." } };
vm.runInContext("renderResponse(answer)", responseContext);
assert.equal(responseNodes.get("#answer-image-button").hidden, true,
  "a later text-only answer must not show an old staged picture");
vm.runInContext('requestSourceIds = new Set(["image-source"]); renderResponse(answer)',
  responseContext);
assert.equal(responseNodes.get("#answer-image-button").hidden, false);
assert.equal(responseNodes.get("#answer-image").src, "blob:current.png");
