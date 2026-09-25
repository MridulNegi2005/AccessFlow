/* Opt-in browser capture. Previews are never controller-final speech. */
(function (root) {
  class AccessFlowLiveVoice {
    constructor(options) {
      this.options = options;
      this.active = false;
      this.startPending = false;
      this.generation = 0;
      this.turnNumber = 0;
      this.turn = null;
      this.preRoll = [];
      this.preRollSamples = 0;
      this.activeMs = 0;
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
        this.failTurn("This voice turn exceeded the 8 MiB limit. Please try a shorter request.");
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
      if (!turn.previewInFlight && turn.previewCount < 3 &&
          turn.samples >= rate * 0.4 &&
          (now - turn.startedAt >= 1200 || quietMs >= 450) &&
          turn.previewText === null && now - turn.lastPreviewAt >= 1000) {
        const revision = ++turn.previewRevision;
        turn.previewCount += 1;
        turn.previewInFlight = true;
        turn.lastPreviewAt = now;
        const wav = this.options.encodeWav(turn.chunks, rate);
        if (!this.options.sendPreview(turn.id, revision, wav)) {
          turn.previewInFlight = false;
          this.failTurn("The speech preview could not be sent. Please reconnect and try again.");
          return;
        }
        this.options.onState("previewing");
      }
      if (quietMs >= 2200 && turn.previewText) {
        this.completeTurn();
      } else if (quietMs >= 5500) {
        this.failTurn("Speech was not recognized. Please try again or type the request.");
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

    failTurn(message) {
      const turn = this.turn;
      if (!this.active || !turn) return;
      this.turn = null;
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
