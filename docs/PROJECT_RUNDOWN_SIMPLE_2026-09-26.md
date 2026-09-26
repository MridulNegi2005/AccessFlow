# AccessFlow, in plain English

**Updated:** 26 September 2026

**Code checkpoint:** `30ea60d` on `atishay/perception`, pushed to GitHub

## The short version

AccessFlow is a voice helper for device support. It should listen patiently, handle
corrections, understand a spoken request and pictures, and avoid taking an action
until the request is clear.

There is a substantial working base and a large automated test suite. The product
is **not accepted as complete yet**. The biggest remaining gaps are getting the
shared engine to reason about several pictures safely, checking live voice with
people and devices, and running the real Samsung evaluation procedure.

## What we set out to build

The example is a person describing a device problem and asking for a service
appointment. They may pause, repeat themselves, correct a day, say “wait,” or send
one or more pictures. The helper should keep the useful information, ask when it is
unsure, and keep old or unfinished instructions from causing the wrong action.

The plan is a small Python agent with two message queues, replaceable speech and
picture processing, a shared session controller, and a simple browser demo. Real
bookings are outside the development demo; its tools are mocks.

## The two work areas

| Person | Main responsibility | Plain-English version |
|---|---|---|
| **Mridul (Workstream A)** | Shared contracts, controller, action safety, tool/runtime adapters, Samsung package and evaluation | The shared “brain” and the official test/package connection |
| **AJ / Atishay (Workstream B)** | Browser demo, microphone and speech handling, timing policy, picture handling and owned tests | The “ears,” “eyes,” and user-facing controls |

Both sides need to agree how the browser’s messages map into the shared controller.
The current GitHub branch contains a jointly scoped stop-behavior update along with
AJ’s demo changes.

## The four agreed behaviors

| Name | What it means | Current state |
|---|---|---|
| **D1: stop and clarify** | “Stop speaking” stops the voice. An unclear “stop” pauses new actions and asks what the person means. A clear cancel cancels the named task. | The shared code and automatic tests now cover the main cases. It still needs integrated, real-use acceptance. |
| **D2: hands-free voice** | Once voice is started, the person can pause and correct themselves without pressing Send after every turn. | Some capture, preview, and automatic-turn pieces exist. The required four physical-microphone checks are still open. |
| **D3: End session** | Ending voice closes that session, discards unfinished speech, and prevents late results from speaking or acting. | The browser has shutdown behavior; the server now ends the agent before waiting on an unfinished upload. A deterministic regression covers the disconnect race. Full browser/device acceptance is still open. |
| **D4: multiple pictures** | Keep pictures in order so the person can refer to “the first one” or select details from different pictures. | The browser and picture-processing pieces keep image identities. The shared controller still lacks the complete ordered image/source-selection behavior. This is the main known expected failure. |

## What has actually been checked

- The full current repository suite ran under **Python 3.13.14**: **1,395 passed,
  11 skipped, 1 expected failure**, in 84.65 seconds. The expected failure is the
  known multi-picture/source-selection gap. One existing FastAPI/Starlette warning
  remains.
- Ruff passed for the changed Python files. All seven browser regression scripts
  passed.
- These are mostly repeatable software checks. They do not prove live model
  accuracy, physical-microphone behavior, or a Samsung score. The project still
  declares Python 3.11 support; the Python 3.13 run is extra compatibility evidence.
- The scenario plan calls for 60 examples: 30 text, 18 audio and 12 picture cases.
  The current inventory has 15 text, 2 audio and 1 picture case. The two audio
  cases use the same recording; the one picture case does not yet run through the
  process adapter. There are 10 distinct tool combinations, and no scenario is
  longer than two user turns.
- The four held-out text probes were already used once. Sixteen more were planned,
  and there is no unseen picture/audio set. Reusing those four for tuning would
  make them practice examples, not fresh proof.

## What the Samsung folder tells us

The supplied `participant-kit/student_kit` folder contains a list of 20 requests,
20 example responses, a response schema, a sample output, and 578 deeplinks. The
20 example responses fit the supplied schema.

That is useful reference material for understanding the response shape and content.
The folder does **not** contain the runnable evaluator files the package builder
expects (`eval_submission.py`, `run_local.py`, the evaluator harness, or its tool
guide). So it cannot yet produce an official score or prove that AccessFlow matches
the Samsung test protocol. It also describes a response made of support goals,
steps and deeplinks; the older AccessFlow plan describes a two-queue agent protocol.
The files alone do not establish that these are the same test interface.

The supplied JSON test/reference data was left out of the GitHub push.

## The separate Colab/Grok work

The Colab notebook is a separate FDB-v3 experiment. Its T4/Python 3.13 setup and
public audio data are prepared, and one local speech-recognition example ran. The
full 100-example Grok run has **not** been made. The notebook runs FDB’s own agent
with mock tools; it does not run AccessFlow’s shared controller. It is useful setup
work, but it does not count as AccessFlow or Samsung acceptance evidence.

## What is left, and who owns it

| Next work | Owner | Why it matters |
|---|---|---|
| Add the shared, ordered picture history and safe source/field selection; keep picture identities when results arrive late. | Mridul, with AJ’s browser integration | Without this, “use the date from picture one and the address from picture two” is not reliably supported. |
| Finish the live-voice flow and run the four planned physical-microphone checks. | AJ, with Mridul on shared turn/dispatch behavior | Automated audio fixtures cannot tell us whether real pauses and corrections feel right. |
| Check End session in a real browser and microphone session: stop capture/output, discard unfinished speech and ignore late results. | AJ; coordinate server/controller closure with Mridul | The automated disconnect case passes, but real-device closure is not yet signed off. |
| Run the 12 planned real reasoning/vision attempts and record exact model, settings, outputs and failures. | AJ for evidence; Mridul for runtime/evaluation support | No current result proves real model quality on the planned cases. |
| Obtain or locate the runnable Samsung evaluator and confirm how this `student_kit` relates to AccessFlow’s queue protocol. | Mridul for package/evaluator; AJ can map sample inputs | The current folder supplies examples and a schema, not a scoring command. |
| Expand and run the scenario set, then package the code and check the final demo/presentation. | Both, with ownership above | Current coverage is much smaller than the original 60-case plan. Demo and presentation work comes after the product core. |

## The next steps in simple order

1. Confirm the actual Samsung evaluator/interface from the complete kit.
2. Finish and integrate the shared multi-picture behavior.
3. Run the live microphone and real reasoning/vision checks.
4. Fill the largest scenario gaps and run the official evaluation.
5. Prepare the demo and presentation after the core behavior is accepted.

Your current working target is **30 September**. The older plan’s 24–25 September
submission dates are already past and are not confirmation of the current official
deadline. The right progress description today is **strong automated foundation,
partial product acceptance, official score still unavailable**. There is no useful
single completion percentage because tests, real-device checks and official scoring
measure different things.
