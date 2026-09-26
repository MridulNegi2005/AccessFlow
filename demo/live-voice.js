/* Opt-in browser capture. Previews are never controller-final speech. */
(function (root) {
  function timingSetting(value, fallback, minimum, maximum, name) {
    if (value === undefined) return fallback;
    if (!Number.isSafeInteger(value) || value < minimum || value > maximum)
      throw new RangeError(`${name} must be an integer from ${minimum} to ${maximum}.`);
    return value;
  }

  function awaitsMoreSpeech(text) {
    const words = text.toLowerCase().trim().replace(/[.,!?]+$/, "").trim();
    return /\b(?:actually|instead|but|and|or)$/.test(words);
  }

  function needsActionPause(text) {
    if (/\b(?:actually|instead)\b/i.test(text)) return false;
    const actionPrefix = /^(?:(?:please|could you|can you|i want to|i need to)\s+)*(?:book|schedule|reserve|reschedule|cancel|delete|send|pay|buy|order|transfer|set|create|change|move)\b/i;
    return actionPrefix.test(text.trim());
  }

  class AccessFlowLiveVoice {
    constructor(options) {
      this.options = options;
      const configured = options.timing || {};
      this.timing = {
        quietCompleteMs: timingSetting(configured.quietCompleteMs, 2200, 800, 10000, "quietCompleteMs"),
        actionQuietMs: timingSetting(configured.actionQuietMs, 4200, 800, 15000, "actionQuietMs"),
        quietFailureMs: timingSetting(configured.quietFailureMs, 5500, 1500, 15000, "quietFailureMs"),
        previewIntervalMs: timingSetting(configured.previewIntervalMs, 1000, 500, 5000, "previewIntervalMs"),
        maxPreviewsPerTurn: timingSetting(configured.maxPreviewsPerTurn, 12, 1, 30, "maxPreviewsPerTurn"),
        maxTurnMs: timingSetting(configured.maxTurnMs, 60000, 3000, 120000, "maxTurnMs"),
      };
      if (this.timing.quietFailureMs <= this.timing.quietCompleteMs)
        throw new RangeError("quietFailureMs must exceed quietCompleteMs.");
      this.active = false;
      this.startPending = false;
      this.generation = 0;
      this.turnNumber = 0;
      this.turn = null;
      this.preRoll = [];
      this.preRollSamples = 0;
      this.activeMs = 0;
      this.awaitingQuietReset = false;
      this.quietResetMs = 0;
      this.timer = null;
      this.capture = null;
    }

    async start() {
      if (this.active || this.startPending) return false;
      this.startPending = true;
      const generation = ++this.generation;
      let stream;
      let context;
      let source;
      let recorder;
      let silentGain;
      try {
        stream = await this.options.getUserMedia({ audio: true });
        if (generation !== this.generation) return false;
        context = this.options.createAudioContext();
        if (!context.audioWorklet)
          throw new Error("AudioWorklet capture is unavailable in this browser.");
        await context.audioWorklet.addModule("/recorder-worklet.js");
        if (generation !== this.generation) return false;
        source = context.createMediaStreamSource(stream);
        recorder = this.options.createRecorder(context);
        silentGain = context.createGain();
        silentGain.gain.value = 0;
        source.connect(recorder);
        recorder.connect(silentGain);
        silentGain.connect(context.destination);
        recorder.port.onmessage = (event) => {
          if (generation === this.generation && this.active)
            this.acceptSamples(new Float32Array(event.data));
        };
        this.capture = { stream, context, source, recorder, silentGain };
        this.active = true;
        this.startPending = false;
        this.options.onState("listening");
        this.timer = this.options.setInterval(() => this.tick(), 100);
        return true;
      } catch (_error) {
        if (generation === this.generation) {
          this.options.onError("Microphone capture could not start. Check permission and browser support.");
          this.options.onState("unavailable");
        }
        return false;
      } finally {
        if (!this.active || generation !== this.generation) {
          recorder?.port.close();
          recorder?.disconnect();
          source?.disconnect();
          silentGain?.disconnect();
          stream?.getTracks().forEach((track) => track.stop());
          await context?.close();
          if (generation === this.generation) this.startPending = false;
        }
      }
    }

    acceptSamples(samples) {
      if (!this.active || !this.capture || !samples.length) return;
      const rate = this.capture.context.sampleRate;
      const durationMs = samples.length * 1000 / rate;
      let sum = 0;
      for (const sample of samples) sum += sample * sample;
      const voice = Math.sqrt(sum / samples.length) >= 0.018;
      const now = this.options.now();
      if (!this.turn) {
        if (this.awaitingQuietReset) {
          this.quietResetMs = voice ? 0 : this.quietResetMs + durationMs;
          if (this.quietResetMs < 500) return;
          this.awaitingQuietReset = false;
          this.quietResetMs = 0;
          this.preRoll = [];
          this.preRollSamples = 0;
          this.activeMs = 0;
          return;
        }
        this.preRoll.push(samples);
        this.preRollSamples += samples.length;
        while (this.preRollSamples > rate * 0.25 && this.preRoll.length > 1)
          this.preRollSamples -= this.preRoll.shift().length;
        this.activeMs = voice ? this.activeMs + durationMs : 0;
        if (this.activeMs >= 280) this.beginTurn(now);
        return;
      }
      this.turn.chunks.push(samples);
      this.turn.samples += samples.length;
      if (voice) {
        if (this.turn.previewInFlight && now - this.turn.lastVoiceAt >= 450) {
          // Speech resumed after a pause: a late preview describes an older
          // prefix and must not update the current turn's displayed words.
          this.turn.previewRevision += 1;
          this.turn.previewInFlight = false;
        }
        this.turn.lastVoiceAt = now;
        if (this.turn.previewText !== null) this.turn.previewText = null;
      }
      if (this.turn.samples > (8 * 1024 * 1024 - 44) / 2)
        this.failTurn("This voice turn exceeded the 8 MiB limit. Please try a shorter request.", true);
    }

    beginTurn(now) {
      const id = "live-turn-" + (++this.turnNumber);
      this.turn = {
        id, chunks: this.preRoll, samples: this.preRollSamples,
        startedAt: now, lastVoiceAt: now, previewRevision: 0,
        previewCount: 0, previewInFlight: false, previewText: null,
        lastPreviewAt: -Infinity,
      };
      this.preRoll = [];
      this.preRollSamples = 0;
      this.activeMs = 0;
      this.options.onSpeechStart(id);
      if (!this.options.sendStatus(id, 0, "pending")) {
        this.turn = null;
        this.options.onError("The session is disconnected. Start a fresh session.");
        return;
      }
      this.options.onState("speaking");
    }

    tick() {
      const turn = this.turn;
      if (!this.active || !turn) return;
      const now = this.options.now();
      const quietMs = now - turn.lastVoiceAt;
      const rate = this.capture.context.sampleRate;
      if (now - turn.startedAt >= this.timing.maxTurnMs) {
        this.failTurn("This voice turn took too long. Please try a shorter request.", true);
        return;
      }
      if (!turn.previewInFlight && turn.previewCount < this.timing.maxPreviewsPerTurn &&
          turn.samples >= rate * 0.4 &&
          (now - turn.startedAt >= 1200 || quietMs >= 450) &&
          turn.previewText === null && now - turn.lastPreviewAt >= this.timing.previewIntervalMs) {
        const revision = ++turn.previewRevision;
        turn.previewCount += 1;
        turn.previewInFlight = true;
        turn.lastPreviewAt = now;
        const wav = this.options.encodeWav(turn.chunks, rate);
        if (!this.options.sendPreview(turn.id, revision, wav)) {
          turn.previewInFlight = false;
          this.failTurn("The speech preview could not be sent. Please reconnect and try again.", true);
          return;
        }
        this.options.onState("previewing");
      }
      const quietCompleteMs = turn.previewText && needsActionPause(turn.previewText)
        ? Math.max(this.timing.quietCompleteMs,
          Math.min(this.timing.actionQuietMs, this.timing.quietFailureMs - 100))
        : this.timing.quietCompleteMs;
      if (quietMs >= quietCompleteMs && turn.previewText &&
          !awaitsMoreSpeech(turn.previewText)) {
        this.completeTurn();
      } else if (quietMs >= this.timing.quietFailureMs) {
        this.failTurn(turn.previewText && awaitsMoreSpeech(turn.previewText)
          ? "That request sounded unfinished. Please continue or try again."
          : turn.previewCount >= this.timing.maxPreviewsPerTurn
            ? "This voice turn exceeded live preview capacity. Please start a new request."
          : "Speech was not recognized. Please try again or type the request.");
      }
    }

    previewResult(sourceId, revision, text, error) {
      const turn = this.turn;
      if (!this.active || !turn || sourceId !== turn.id || revision !== turn.previewRevision)
        return false;
      turn.previewInFlight = false;
      turn.previewText = typeof text === "string" && text.trim() ? text.trim() : null;
      if (turn.previewText) this.options.onPreview(turn.previewText);
      else if (error) this.options.onState("listening");
      return true;
    }

    completeTurn() {
      const turn = this.turn;
      if (!this.active || !turn) return false;
      this.turn = null;
      const wav = this.options.encodeWav(turn.chunks, this.capture.context.sampleRate);
      const sent = this.options.sendFinal(turn.id, turn.previewRevision + 1, wav);
      this.options.onState(sent ? "processing" : "unavailable");
      if (!sent) this.options.onError("The completed voice turn could not be sent.");
      return sent;
    }

    failTurn(message, requireQuietReset = false) {
      const turn = this.turn;
      if (!this.active || !turn) return;
      this.turn = null;
      if (requireQuietReset) {
        this.awaitingQuietReset = true;
        this.quietResetMs = 0;
        this.preRoll = [];
        this.preRollSamples = 0;
        this.activeMs = 0;
      }
      this.options.sendStatus(turn.id, turn.previewRevision + 1, "failed");
      this.options.onError(message);
      this.options.onState("listening");
    }

    async end() {
      if (!this.active && !this.startPending) return;
      ++this.generation;
      this.active = false;
      this.startPending = false;
      this.turn = null; // Never encode, flush or send unfinished audio.
      this.preRoll = [];
      this.preRollSamples = 0;
      this.awaitingQuietReset = false;
      this.quietResetMs = 0;
      if (this.timer !== null) this.options.clearInterval(this.timer);
      this.timer = null;
      const capture = this.capture;
      this.capture = null;
      if (capture) {
        capture.recorder.port.close();
        capture.recorder.disconnect();
        capture.source.disconnect();
        capture.silentGain.disconnect();
        capture.stream.getTracks().forEach((track) => track.stop());
      }
      this.options.onState("ended");
      await capture?.context.close();
    }
  }

  root.AccessFlowLiveVoice = AccessFlowLiveVoice;
  if (typeof module !== "undefined" && module.exports) module.exports = AccessFlowLiveVoice;
})(typeof window !== "undefined" ? window : globalThis);
