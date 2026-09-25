const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../../demo/index.html"), "utf8");
const sendStart = html.indexOf("function sendFile(kind, selector, fallback) {");
const sendEnd = html.indexOf("function canRun() {", sendStart);
const stageStart = html.indexOf("function stageImage(file) {");
const stageEnd = html.indexOf("function renderStagedMedia() {", stageStart);
assert.ok(sendStart >= 0 && sendEnd > sendStart && stageStart >= 0 && stageEnd > stageStart);

const picker = { files: [], value: "" };
const nodes = new Map([
  ["#image", picker],
  ["#processing", { lastElementChild: { textContent: "" } }],
  ["#dock-error", { textContent: "" }],
  ["#answer-image", { hidden: true }],
  ["#answer-image-button", { hidden: true }],
  ["#answer-grid", { classList: { remove() {} } }],
]);
const sent = [];
const revoked = [];
const prepared = [];
const errors = [];
let acceptMore = true;
const context = {
  document: { querySelector(selector) {
    assert.ok(nodes.has(selector), `Unexpected selector: ${selector}`);
    return nodes.get(selector);
  } },
  URL: {
    createObjectURL: (file) => `blob:${file.name}`,
    revokeObjectURL: (url) => revoked.push(url),
  },
  sent,
  errors,
  attachmentHistory: {
    current() { return true; },
    prepare(sourceId, file) {
      if (!acceptMore) return false;
      prepared.push([sourceId, file.name]);
      return true;
    },
    discard() {},
  },
};
vm.createContext(context);
vm.runInContext(
  `let runInProgress = false;
   let stagedImageFile = null;
   let stagedImageUrl = null;
   let activeSessionId = "test-session";
   let latestMediaSourceId = null;
   const maxMediaBytes = 8 * 1024 * 1024;
   function renderStagedMedia() {}
   function updateRunButton() {}
   function enqueueMediaAction(action) { return action(); }
   async function fileToBase64(file) { return "encoded:" + file.name; }
   function nextMediaId() { return "frame-source-1"; }
   function registerRequestSource() {}
   function show(event) { errors.push(event); }
   function send(kind, payload) { sent.push({ kind, payload: payload() }); return true; }
   ${html.slice(sendStart, sendEnd)}
   ${html.slice(stageStart, stageEnd)}`,
  context,
);

(async () => {
  const dropped = { name: "dropped.png", type: "image/png", size: 128 };
  context.dropped = dropped;
  vm.runInContext("stageImage(dropped)", context);
  assert.equal(vm.runInContext("stagedImageFile.name", context), "dropped.png");
  assert.equal(vm.runInContext("stagedImageUrl", context), "blob:dropped.png");
  assert.equal(picker.files.length, 0, "drag-and-drop need not populate the file picker");
  vm.runInContext("runInProgress = true", context);
  assert.equal(await vm.runInContext('sendFile("frame", "#image")', context), true);
  assert.equal(sent[0].kind, "frame");
  assert.equal(sent[0].payload.data_base64, "encoded:dropped.png");
  assert.equal(sent[0].payload.filename, "dropped.png");
  assert.equal(sent[0].payload.frame_id, "frame-source-1");
  assert.deepEqual(prepared[0], ["frame-source-1", "dropped.png"]);

  const picked = { name: "picked.png", type: "image/png", size: 256 };
  picker.files = [picked];
  context.picked = picked;
  vm.runInContext("runInProgress = false; stageImage(picked)", context);
  assert.deepEqual(revoked, ["blob:dropped.png"]);
  vm.runInContext("runInProgress = true", context);
  assert.equal(await vm.runInContext('sendFile("frame", "#image")', context), true);
  assert.equal(sent[1].payload.filename, "picked.png");
  assert.equal(sent[1].payload.data_base64, "encoded:picked.png");
  assert.deepEqual(prepared[1], ["frame-source-1", "picked.png"]);
  acceptMore = false;
  assert.equal(await vm.runInContext('sendFile("frame", "#image")', context), false);
  assert.equal(sent.length, 2, "local capacity failure must not send another frame");
  assert.match(errors.at(-1).payload.message, /eight images/i);
})().catch((error) => { console.error(error); process.exitCode = 1; });
