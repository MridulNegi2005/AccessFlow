# Scenario inventory

This is the corpus record. Answer any question about coverage from this file, and regenerate
it after adding or changing a scenario. Everything below the generated marker is read from
the scenario files, not written by hand.

## How to read it

A file count is not coverage. Two files that drive the same tools through the same workflow
are one workflow measured twice. `scenarios/live_dev` is mostly a set of variants of
`scenarios/dev` with model-sized deadlines and explicit argument formats, not additional
independent examples. The distinct-tool-set count is the closer measure.

Exposure labels state whether the engine has been tuned against a fixture. A fixture used
during development is no longer unseen, whatever its directory is called. The four planner
probes were the only unseen set. They ran once on 16 September 2026, after the request
contract and the primary profile stopped changing. They are spent: tuning against them now
converts them to development data, so treat their one recorded result as the measurement.

Faults name the environment bindings that inject a failure, such as a lost response or a
commit that reports an unknown outcome.

## Known gaps

- Multimodal coverage is 2 audio files and 1 visual file, against a planned 18 audio plus
  12 visual. The hidden set is half multimodal at a 1.5 multiplier, so this remains the
  largest unclaimed score.
- Both audio files use the same committed WAV. `audio_correction.json` is an ASR and
  turn-correction smoke check. `audio_correction_ambiguous_hour_clarification.json` scores
  write safety when the spoken hour is ambiguous. Two files over one recording are not two
  independent audio cases. More audio evidence needs more recordings, which are Workstream
  B media fixtures.
- The visual file `frame_device_panel.json` cannot run through the process adapter. The
  perception worker rejects the vision options the parent sends. See finding A2 in
  `reviews/MRIDUL_REAUDIT_2026-09-15.md` and the ownership note in `CONTRACT_PROPOSALS.md`.
  The one recorded vision run used a temporary worker edit that is reverted.
- No scenario exceeds two user turns. Longer interruption chains are untested.
- The only fault injected is an unresolved write outcome. Perception failures, tool timeouts
  and authorization refusals have unit coverage but no end-to-end scenario.
- Held-out coverage is spent. The four planner probes ran once on 16 September 2026 and
  passed 4 of 4 on `groq/qwen/qwen3.8-27b`. All four are text. The plan calls for twenty
  held out, so 16 remain unwritten and there is no unseen multimodal case at all. Four text
  cases are a real generalization signal, not evidence of broad correctness.

<!-- generated -->
Generated from 17 scenario files.
Regenerate with `python scripts/scenario_inventory.py --write docs/SCENARIO_INVENTORY.md`.

## Coverage against the plan

| Modality | Planned | Present |
|---|---|---|
| text (`transcript`) | 30 | 15 |
| audio (`audio`) | 18 | 2 |
| visual (`frame`) | 12 | 1 |

Distinct tool sets: **10** across 17 files. Longest scenario: **2** user turns.

## Every scenario

| Set | Scenario | Turns | Modalities | Faults | Exposure |
|---|---|---|---|---|---|
| dev | `device-correction-during-pending-write` | 2 | transcript | - | development |
| dev | `lost-response-status-reconciliation` | 1 | transcript | submit_ticket_v3 | development |
| dev | `support-read-then-service` | 1 | transcript | - | development |
| dev | `development-text-correction-01` | 2 | transcript | - | development |
| live_dev | `live-dev-audio-correction-01` | 1 | audio | - | development |
| live_dev | `live-dev-audio-correction-clarify-01` | 1 | audio | - | development |
| live_dev | `live-dev-device-correction-before-plan` | 2 | transcript | - | development |
| live_dev | `live-dev-frame-device-panel-01` | 2 | frame, transcript | - | development |
| live_dev | `live-dev-lost-response-status-reconciliation` | 1 | transcript | submit_ticket_v3 | development |
| live_dev | `live-dev-stale-read-after-correction` | 2 | transcript | - | development |
| live_dev | `live-dev-stale-read-after-device-correction` | 2 | transcript | - | development |
| live_dev | `live-dev-support-read-then-service` | 1 | transcript | - | development |
| live_dev | `live-dev-development-text-correction-01` | 2 | transcript | - | development |
| planner_probes | `planner-probe-corrected-24h` | 2 | transcript | - | spent, run once 16 Sep 2026 |
| planner_probes | `planner-probe-fluent-noon` | 1 | transcript | - | spent, run once 16 Sep 2026 |
| planner_probes | `planner-probe-incomplete-clarification` | 1 | transcript | - | spent, run once 16 Sep 2026 |
| planner_probes | `planner-probe-new-utterance-preserves-time` | 2 | transcript | - | spent, run once 16 Sep 2026 |

## Workflows measured more than once

Each group drives the same tool set. A group of more than one is one workflow measured repeatedly, not independent coverage.

| Tool set | Files |
|---|---|
| reserve_service_slot | 4: `development-text-correction-01`, `live-dev-audio-correction-01`, `live-dev-audio-correction-clarify-01`, `live-dev-development-text-correction-01` |
| reserve_repair_window | 2: `device-correction-during-pending-write`, `live-dev-device-correction-before-plan` |
| query_receipt_v3, submit_ticket_v3 | 2: `lost-response-status-reconciliation`, `live-dev-lost-response-status-reconciliation` |
| file_visit_request, inspect_support_notes | 2: `support-read-then-service`, `live-dev-support-read-then-service` |
| file_visit_request, inspect_support_notes, order_replacement_part | 2: `live-dev-stale-read-after-correction`, `live-dev-stale-read-after-device-correction` |
| file_visit_request | 1: `live-dev-frame-device-panel-01` |
| enqueue_calibration_visit | 1: `planner-probe-corrected-24h` |
| queue_technician_visit | 1: `planner-probe-fluent-noon` |
| open_service_case | 1: `planner-probe-incomplete-clarification` |
| commit_care_window | 1: `planner-probe-new-utterance-preserves-time` |
