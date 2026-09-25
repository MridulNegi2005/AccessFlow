/* Session-local browser display of server-receipted images, not agent authority. */
(function (root) {
  class AccessFlowAttachmentHistory {
    constructor(options) {
      this.options = options;
      this.maxItems = options.maxItems ?? 8;
      this.sessionId = null;
      this.closed = false;
      this.pending = new Map();
      this.accepted = [];
    }

    startSession(sessionId) {
      if (typeof sessionId !== "string" || !sessionId) return false;
      if (sessionId === this.sessionId) return !this.closed;
      this.clear();
      this.sessionId = sessionId;
      this.closed = false;
      return true;
    }

    prepare(sourceId, file) {
      if (this.closed || !this.sessionId || typeof sourceId !== "string" ||
          !sourceId || !file) return false;
      if (!this.pending.has(sourceId) &&
          !this.accepted.some((item) => item.sourceId === sourceId) &&
          this.accepted.length + this.pending.size >= this.maxItems) return false;
      this.pending.set(sourceId, file);
      return true;
    }

    accept(sessionId, sourceId, eventId, revision) {
      if (!this.current(sessionId) || typeof sourceId !== "string" ||
          typeof eventId !== "string" || !eventId ||
          !Number.isSafeInteger(revision) || revision < 0) return false;
      const file = this.pending.get(sourceId);
      if (!file) return false;
      const existing = this.accepted.find((item) => item.sourceId === sourceId);
      if (existing && revision <= existing.revision) return false;
      const url = this.options.createObjectURL(file);
      if (existing) {
        this.options.revokeObjectURL(existing.url);
        Object.assign(existing, {
          name: file.name, url, eventId, revision, status: "received", backend: null,
        });
      } else {
        this.accepted.push({
          sourceId, name: file.name, url, eventId, revision,
          status: "received", backend: null,
        });
      }
      this.pending.delete(sourceId);
      this.notify();
      return true;
    }

    observe(sessionId, sourceId, eventId, revision, backend) {
      if (!this.current(sessionId)) return false;
      const item = this.accepted.find((entry) => entry.sourceId === sourceId);
      if (!item || item.eventId !== eventId || item.revision !== revision ||
          item.status === "failed") return false;
      item.status = "observed";
      item.backend = typeof backend === "string" ? backend : null;
      this.notify();
      return true;
    }

    fail(sessionId, eventId) {
      if (!this.current(sessionId)) return false;
      const item = this.accepted.find((entry) => entry.eventId === eventId);
      if (!item || item.status === "failed") return false;
      item.status = "failed";
      item.backend = null;
      this.notify();
      return true;
    }

    discard(sourceId) { this.pending.delete(sourceId); }
    discardPending() { this.pending.clear(); }
    items() { return this.accepted.map((item) => ({ ...item })); }
    current(sessionId) {
      return !this.closed && Boolean(sessionId) && sessionId === this.sessionId;
    }
    endSession() {
      this.closed = true;
      this.pending.clear();
    }
    clear() {
      for (const item of this.accepted) this.options.revokeObjectURL(item.url);
      this.accepted = [];
      this.pending.clear();
      this.notify();
    }
    notify() { this.options.onChange?.(this.items()); }
  }

  root.AccessFlowAttachmentHistory = AccessFlowAttachmentHistory;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { AccessFlowAttachmentHistory };
  }
})(typeof window !== "undefined" ? window : globalThis);
