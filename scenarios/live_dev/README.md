# Live development fixtures

These are four variants of `../dev`, not four additional independent user examples.
They use the same mock effects and task criteria. Scripted proposals remain available
for an offline plumbing check; the live runner supplies ModelReasoner and never sends
those proposals, task criteria or environment internals to the model.

Differences from the original deterministic orchestration fixtures:

- Completion wait is 100 seconds, within the scenario budget. The original three-second
  waits for three cases were appropriate for scripted planners, not multi-step inference.
  Backend request and controller inference timeouts are unchanged.
- Tool manifests explicitly require 24-hour HH:MM where the oracle expects that format.
  Lookup vocabulary and receipt identity are described in the supplied schemas. A hidden
  exact string expectation without a corresponding tool requirement is not a fair model test.
- Device correction is a new utterance containing the request, not an ASR hypothesis that
  silently replaces the original command with a fragment. The rapid delivery is labelled
  correction-before-plan. It does not establish cancellation during a dispatched write.

The original pilot fixtures and failed traces are preserved separately for comparison.
Changing these fixtures does not retroactively convert those failures into passes.
No held-out, audio, image, clinical or official-kit score is claimed here.
