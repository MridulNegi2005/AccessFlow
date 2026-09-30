# Development scenario inventory

Generated from local development fixtures. This inventory is separate from the
100-input FDB-v3 benchmark and makes no held-out accuracy claim. Regenerate with
`python scripts/scenario_inventory.py --write docs/SCENARIO_INVENTORY.md`.

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
