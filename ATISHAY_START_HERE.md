# Atishay: start independently

You own `src/accessflow/perception/`, `src/accessflow/turn_policy/`, `demo/`,
`tests/perception/`, `tests/demo/`, `docs/feedback/`, `docs/presentation/` and
`docs/handoffs/atishay.md`, plus `tests/fixtures/audio/` for audio fixtures. Mridul owns the controller, contracts, interfaces,
fakes, clock, tool execution, adapters, evaluation, CI, Docker, root configuration,
lockfile, release documentation and packaging. You do not need his API key or machine.

## Current handoff — 16 September 2026

The published `atishay/perception` branch carries this handoff. The verified
baseline at this snapshot is **188 passed, 4 strict expected failures**.
Read `docs/STATUS.md` before changing anything. The multimodal path now covers text,
validated WAV, validated PNG, injected local ASR and vision providers, source IDs,
event IDs, revisions, timestamps, session isolation, recovery, cleanup and bounded
worker admission. The owned timing seam accepts optional `ActivitySummary` metadata.

The four expected failures are controller integration examples for image-only
informational output, two active-frame replacement cases and conflicting visual
evidence. Upstream `origin/mridul/engine` at `919ed27` resolves the first two
targeted cases. The conflict proposal still needs a controller-side pre-replacement
comparison or provenance signal. Do not edit the controller or shared contracts to
resolve these gaps; keep the failing example and proposal additive.

The branch is clean and the remote is synchronized. Direct inspection of the existing
browser captures and a current-head 1280x1600 headless Chrome capture found no visible
clipping, overlap or broken text in the inspected viewports; live interactive device behavior,
live model quality, human speech quality, feedback and final packaging remain open.
A fresh shallow public-clone check on 16 September 2026 checked out
`atishay/perception`, resolved `origin` to the shared GitHub repository and included
this guide at commit `4892c185`.

## First 30 minutes

1. Clone the shared GitHub repository using the commands below.
2. Clone it into your own directory. Do not use Mridul's working checkout.
3. Create your branch from the common bootstrap:

   ```powershell
   git clone https://github.com/MridulNegi2005/AccessFlow.git
   cd AccessFlow
   git switch atishay/perception
   uv python install 3.11
   uv sync --extra dev
   uv run pytest tests/test_contract.py
   ```

   The repository is public, so cloning and reading the code do not require an
   invitation. `origin` points to the shared GitHub repository. Push directly with
   `git push -u origin atishay/perception` only if Mridul has granted you collaborator
   access; otherwise create your own fork, push `atishay/perception` there, and open a
   pull request back to the shared repository.
   If `uv python install 3.11` reports a stale or missing interpreter link, repair that
   uv-managed Python or use a clean local Python 3.11 environment before running
   `uv sync`; the existing development environment on the handoff machine is Python
   3.12.10 and is only a fallback for local verification.

4. Read `docs/CONTRACT.md`, `src/accessflow/interfaces.py`, `src/accessflow/fakes.py`
   and the golden event in `tests/fixtures/transcript.json`.
5. Record RAM, Python version and available audio/model backends in
   `docs/handoffs/atishay.md`. API access is optional; no paid fallback.

## Completed capabilities and next gaps

`LocalPerception`, the deterministic turn policy, PNG vision seam, minimal fake-agent
demo, owned tests and multimodal evidence are already implemented. Preserve their
boundaries while working on the remaining gaps: broader engine race and status
reconciliation coverage, live reasoning adapters, replay and metrics, official-kit
integration after the kit is supplied, the 60-scenario authored set, Docker/CI,
voluntary feedback, disclosure, demo video and final release assembly.

The perception boundary exposes `observe(event)` as an async iterator of
`Observation`. Keep blocking decoding in a worker; models are installed explicitly,
not downloaded during scenario execution. Return real backend names and keep fake,
injected and live evidence distinguishable.

For text and audio, `Observation.source_id` is the utterance ID, with the input revision.
For images, it is the frame ID with revision 0. Preserve originating event ID and timing.
For PNGs add a replaceable vision provider; do not return a canned caption as perception.
`observe()` does not mutate session state or dispatch tools.

Implement your policies under `src/accessflow/turn_policy/`. The shared interface remains
synchronous and two-argument compatible: `update(observation, session_view) -> TurnDecision`.
The owned `HeuristicTurnPolicy` also accepts optional `ActivitySummary` timing metadata;
it keeps pauses separate from `TurnDecision.complete`. If semantic inference is necessary,
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
