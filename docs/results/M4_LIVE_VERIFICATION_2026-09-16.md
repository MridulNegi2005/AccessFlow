# Live check of the write-authority fix, 16 September 2026

Commit under test: `d47d9f3`
Scenario: `scenarios/live_dev/support_then_service.json`
Backend: `groq` `qwen/qwen3.8-27b`, `ACCESSFLOW_MAX_OUTPUT_TOKENS=950`, `--request-timeout 30`

## Why this run happened

Commit `6caa889` closed finding M4. Write authority is now established only by a proposal made
on fresh user speech. A replan that follows a tool result may keep authority already granted.
It may not create it.

That raised a risk the offline tests could not answer. The controller now depends on the model
declaring write intent on its first turn, even when the write itself happens later. The
project's own fixture did not declare it, which is weak evidence that the model might not
either. Committed traces do not record the `write_requested` flag, so no existing evidence
could settle the question.

If the model does not declare intent on the first turn, every live read-then-write request
stalls.

## Result

The run completed and the oracle passed.

| Field | Value |
|---|---|
| `completion_status` | `completed` |
| `task_oracle.passed` | `true` |
| Committed mock effects | 1 |
| Model | `qwen/qwen3.8-27b` |

Output sequence:

```
acknowledge
tool_call  inspect_support_notes
acknowledge
tool_call  file_visit_request
final
```

The person said "Check the support notes and book a Wednesday five PM visit if service is
recommended." The model read the notes first, then filed the visit request. The write
dispatched, so the model declared write intent on its first turn. A first turn without that
flag would have blocked `file_visit_request` under the new policy.

## Limits of this evidence

This is one run of one scenario with one model. It shows that this model declares intent on
this request shape. It does not prove that every phrasing, every model or every request shape
behaves the same way. A request that authorizes a write less explicitly may still stall.

The trace is in the ignored `artifacts/` directory, so a clean clone does not carry it.

No other live run was made for this check.
