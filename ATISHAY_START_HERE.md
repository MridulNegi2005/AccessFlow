# Atishay: start independently

You own perception, turn policy and the minimal demo. Mridul owns the controller,
tool execution and packaging. You do not need his engine, his API key or his machine.

## Continue from the integrated checkpoint

Your d61d4dc checkpoint is integrated on `mridul/engine`. In your own checkout, commit
or otherwise preserve your current work before merging the tested shared engine:

```powershell
git fetch origin
git switch atishay/perception
git merge origin/mridul/engine
uv sync --frozen --extra dev
uv run pytest -q
uv run accessflow suite scenarios/dev --components local --output-dir artifacts/integration-local
```

Read [the integration report](docs/INTEGRATION_2026-09-13.md). It records A-side fixes and
B review items for browser utterance revisions, graceful shutdown and activity timing.
Your owned implementation was preserved unchanged during integration. GitHub Actions is
disabled; run checks locally. The initial setup instructions below remain a reference.

## First 30 minutes

1. Clone the shared GitHub repository using the commands below.
2. Clone it into your own directory. Do not use Mridul's working checkout.
3. Create your branch from the common bootstrap:

   ```powershell
   git clone https://github.com/MridulNegi2005/AccessFlow.git
   cd AccessFlow
   git switch atishay/perception
   git merge origin/main
   uv python install 3.11
   uv sync --extra dev
   uv run pytest tests/test_contract.py
   ```

   The repository is public, so cloning and reading the code do not require an
   invitation. `origin` points to the shared GitHub repository. Push directly with
   `git push -u origin atishay/perception` only if Mridul has granted you collaborator
   access; otherwise create your own fork, push `atishay/perception` there, and open a
   pull request back to the shared repository.

   This repository is public. Atishay9828 has been invited with write permission;
   accept https://github.com/MridulNegi2005/AccessFlow/invitations before your first push.
   The merge command above brings the shared engine/bootstrap updates onto your local
   work branch; it does not modify any remote branch until you push.

4. Read `docs/CONTRACT.md`, `src/accessflow/interfaces.py`, `src/accessflow/fakes.py`
   and the golden event in `tests/fixtures/transcript.json`.
5. Record RAM, Python version and available audio/model backends in
   `docs/handoffs/atishay.md`. API access is optional; no paid fallback.

## Your first independently testable slice

Implement `src/accessflow/perception/local.py` with a `LocalPerception` class exposing
`observe(event)` as an async iterator of `Observation`. Begin with transcript pass-through
and WAV validation. Add Faster Whisper CPU int8 transcription behind a lazy import.
Run blocking decoding in a worker; never block the event loop. Models are installed
explicitly, not downloaded during scenario execution. Return real backend names.

For text and audio, `Observation.source_id` is the utterance ID, with the input revision.
For images, it is the frame ID with revision 0. Preserve originating event ID and timing.
For PNGs add a replaceable vision provider; do not return a canned caption as perception.
`observe()` does not mutate session state or dispatch tools.

Implement your policies under `src/accessflow/turn_policy/`. The interface is synchronous
`update(observation, session_view) -> TurnDecision`. If semantic inference is necessary,
compute it asynchronously in perception or propose an additive contract extension.
The synchronous policy must stay cheap. The current final-flag fake is only a baseline;
it does not infer silence or semantic completion. Timer-driven observations will need
an additive contract proposal if the existing observations are insufficient.

Create a standalone `demo/` using a fake WebSocket agent under your owned directory.
Render `OutputEvent` objects; do not reimplement authoritative slot or action state in JS.
Provide input controls for text, WAV/mic and PNG and visibly label mock/live backends.
Use existing browser TTS only optionally. Keep UI work small.

## Your tests and evidence

- Own `tests/perception/` and `tests/demo/`; run them without Mridul's implementation.
- Test revision replacement, raw WAV/PNG ingestion, source identity, malformed files,
  long pauses, repetitions, fluent requests and ambiguous image evidence.
- Use fake providers for unit tests; mark actual model tests explicitly and report them
  separately. Never silently transcribe an audio fixture from its filename or labels.
- Keep team recording provenance in `docs/feedback/PROVENANCE.md`; do not distribute
  participant recordings without specific consent. Written anonymized feedback is enough.
- Propose dependencies in your handoff. You may use a separate local environment for
  experiments, but do not change the committed `uv.lock` unilaterally.

## Share progress

Small commits on `atishay/perception`. Integrate a tested slice every 1–2 days. Your PR
must list exact tests, backend, known failures and contract changes. Put proposals in
`docs/CONTRACT_PROPOSALS.md`, not changes to engine.py. Do not wait for the engine to
finish: use fakes and golden events from day one.

### Copy-paste prompt for your AI

> Read AGENTS.md, ATISHAY_START_HERE.md, docs/CONTRACT.md, docs/STATUS.md and the shared
> sync context. Implement only Workstream B in your owned paths. Start with an independent
> WAV/transcript adapter and its tests, then turn policy, PNG perception and a fake-agent
> demo. Use Python 3.11, async Observation streams and contract v0.1. Preserve revisions,
> timestamps and evidence IDs. Keep real models optional and honestly distinguish fake
> from live tests. Do not wait for the engine or change shared contracts/root dependencies
> without proposing an additive change. Update your handoff and AI-use log after each slice.
