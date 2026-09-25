# Configured queue runtime — 24 September 2026

Later on 24 September: the optional native builder/installer and real ASR warm-up
are now verified; see [Native package checkpoint](NATIVE_PACKAGE_2026-09-24.md).
The text-only builder limitation below describes the earlier checkpoint. MP3 and
full multimodal task completion remain open.

## Scope and current limit

`accessflow.adapters.configured_agent.build_configured_agent` now composes the
Samsung participant's real reasoner, turn policy, perception and controller.
It never chooses a mock backend on failure. Text remains the explicit default.
Process perception is opt-in and requires installed resources and successful
setup-time inference. This completes configuration/warm-up wiring, not media
submission readiness: official MP3 assembly and a portable media package are
still unfinished. The generated package is explicitly text-only for now.

No Atishay-owned source or tests changed. His existing process worker supports
the supplied vision arguments. Model training is not part of this change.

## Native runtime settings

These settings apply when constructing the queue participant directly from the
repository. Paths resolve against its `media_root`; absolute installed-resource
paths are also accepted. Scenario media continue through the separate rooted
Samsung protocol boundary. Environment values are configuration, never scenario
inputs or tool-result instructions.

| Setting | Required value or meaning |
| --- | --- |
| `ACCESSFLOW_SAMSUNG_BACKEND` | Explicit supported reasoning provider, with its existing model/credential settings |
| `ACCESSFLOW_SAMSUNG_PERCEPTION` | `process` to enable native perception; otherwise `text` |
| `ACCESSFLOW_SAMSUNG_ASR_MODEL_PATH` | Existing local Faster Whisper model directory |
| `ACCESSFLOW_SAMSUNG_WARMUP_AUDIO` | Existing installation WAV with recognizable speech |
| `ACCESSFLOW_SAMSUNG_PERCEPTION_TIMEOUT_S` | Finite positive seconds, maximum 110; default 30 |
| `ACCESSFLOW_SAMSUNG_VISION_PROVIDER` | `none` or `ollama`; default `none` |
| `ACCESSFLOW_SAMSUNG_VISION_MODEL` | Required explicit model when enabling Ollama vision |
| `ACCESSFLOW_SAMSUNG_VISION_URL` | HTTP(S) origin; default `http://127.0.0.1:11434`; no credentials, path, query or fragment |
| `ACCESSFLOW_SAMSUNG_WARMUP_IMAGE` | Existing installation PNG, required for vision |

Set reasoning credentials outside tracked files. Native settings in text mode
are rejected, as are vision settings with vision disabled. Missing dependencies,
model files, unavailable service, empty transcription or failed vision output
cause setup failure. There is no implicit download, paid fallback or substitution
of scenario annotations for pixels/audio.

Warm-up runs declared installation media through the same worker used at runtime,
then warms the reasoning backend. Their **combined** budget is 290 seconds,
leaving cleanup time under the kit's 300-second setup limit. Each configured media
deadline also applies to the controller inference boundary. Warm-up requires final,
nonempty, revision-zero observations with matching event/source/modality identities.
Their content never enters a user session. Backend labels are retained on the
agent in `perception_warmup_backends`; configuration is available as
`perception_configuration`. Setup failure/cancellation closes the worker.

The warm-up fixtures must be installation assets with known provenance, not a
hidden scenario or its expected answer. This change does not ship such assets or
prove that the requested models are installed on a clean machine.

## Coordination with Atishay: shared runtime adoption

**Both Mridul and Atishay must coordinate this step.** The callable is available
for his demo adapter; it does not change his frontend or automatically connect it.

```python
agent = await build_configured_agent(
    root=installed_assets_root,
    authorization=demo_authorization,
    executor=demo_tool_executor,
    tool_documentation=declared_documentation,
)
```

Mridul owns this factory, queue translation, authority and executor integration.
Atishay owns selecting it in his demo, microphone transport/turn handling and
displaying actual backend provenance. He must send the agreed manifests, retain
event/utterance/frame identity, and close perception when the session ends. The
Samsung path deliberately supplies no executor: tools are run by the harness.
The demo must use its explicitly selected mock external executor and must label
those effects. Do not use harness authorization blindly for browser actions.

Before claiming the demo and evaluator match, jointly verify that both select
the same provider/model/profile, retain causal source identity and yield matching
results for the same recorded input. Microphone streaming, endpointing and barge-in
remain separate B-owned deliverables; this factory does not implement them.

## Remaining code-completion order

1. Mridul: finish the official MP3-to-internal-audio route, respecting chunk/turn
   boundaries and interruptions. Coordinate ownership/semantics with Atishay;
   do not reinterpret partial audio as a completed request.
2. Mridul: portable native dependency/model/fixture installation and frozen media
   profiles in the package. The current builder refuses native overrides rather
   than silently changing a text package into an uninstalled media configuration.
3. Both: real media to completed task through the common runtime. Atishay supplies
   owned ASR/vision/microphone checks; Mridul verifies official queue execution,
   tool outcomes, cancellation and reproducible package behavior.
4. Mridul: run all available public cases in the supported installed environment,
   preserve failures and repeat the official evaluation. Prompt/accuracy tuning
   follows functional completion. Safety/protocol defects remain blockers.

PPT, video and presentation work are excluded from this code milestone.

## Evidence

See `docs/evidence/configured-runtime-2026-09-24/README.md`. Tests include config
rejection, both warm-up routes, failure cleanup, total deadline, profile isolation
and a real child process passing an official-shaped PNG event to the controller
and reasoner. Their inference is deliberately fake, and fixture bytes are not
real image/audio evaluation. No live ASR, vision, microphone, Docker or full public
multimodal result is claimed by this checkpoint.
