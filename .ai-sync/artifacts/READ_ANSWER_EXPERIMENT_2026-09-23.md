# Evidence-selected read answers — 23 September 2026

Status: opt-in A-side experiment. Default remains prose; the package profile is unchanged.

## Problem and bounded claim

The compact-v2 baseline again turned a hotel result `price_usd: 189` into
“$189 per night.” The tool supplied no billing period. Earlier prompt-only
attempts failed too; see the retained September 22 grounding evidence. A Samsung
keyword score of 100 does not catch this factual error.

This experiment lets the reasoner select successful read-result fields in its
existing planning call. The controller resolves and presents their actual values.
It prevents model-authored additions to this selected-field final-answer path.
It does not certify source truth, selection relevance, completeness, semantic
understanding or the contents of free-form clarifying questions.

This is deliberately not the default: the result is a readable field/value
summary, less fluent than conversational prose. Voice usability and broader task
coverage still need evaluation before adopting it for the product.

## Interface and behavior

`PlanProposal.evidence_answer` is optional and defaults to null. It contains
`selections`, each with an accepted read `call_id` and an RFC6901 `pointer`.
An empty pointer selects the whole result; arrays permit canonical numeric indices.
The model cannot supply replacement values, labels or surrounding prose.

An evidence-answer proposal cannot also contain intent changes, slot updates,
calls, write contracts, write intent, a prose response or a clarification. The
shared Pydantic contract and model schema enforce this. The controller revalidates
the variant before applying any state updates, including for a custom reasoner
that bypasses Pydantic using model_construct/model_copy.

The controller resolves each selected source immediately before output. It requires
an admitted successful result and a matching successful read call from the active
request, with unchanged dependency-slot revisions. Failed, cancelled, unknown,
pending, stale, historical and write sources cannot supply an answer. Duplicate
sources in the accepted evidence set and duplicate selections are rejected.

Read pointers have their own resolver; the stricter delegated-write selector is
unchanged. A display selection never authorizes a tool action. Outstanding writes
and uncertain historical effects retain the existing final-answer barriers.

The renderer labels each selection separately and groups nested fields by their
relative path. It preserves literal numbers, strings, false, zero, null and empty
containers. It does not infer currency symbols, billing periods, totals or other
field semantics. Strings are quoted/escaped so a newline in source data cannot
forge another displayed field. Untrusted quoted instructions are still only data.

Limits: 8 selections, 512-character pointers, 8 levels, 48 leaf fields and 6,000
output characters. Invalid pointers, unsupported values and oversized selections
fail explicitly; they are not silently truncated into an apparently complete answer.
A controller-side rejection emits an error and a fixed clarification, not invented
facts, a model-only final or an unbounded extra model retry. Existing model-schema
rejection uses the existing bounded correction policy.

## Configuration and compatibility

```powershell
$env:ACCESSFLOW_SAMSUNG_READ_ANSWER_MODE = "evidence"
$env:ACCESSFLOW_SAMSUNG_PROMPT_PROFILE = "compact-v2"
```

The answer mode is independent of the prompt profile. Omit it, or set `prose`,
for the original final-answer behavior. Unknown modes fail setup. The Samsung
adapter passes one validated mode to both controller and model reasoner. Direct
Python callers must configure both; known component mismatches fail construction.

Before a current read attempt, ordinary no-tool prose remains available. After a
read attempt in evidence mode, a lookup final must use evidence selection. The
planner can still continue with tools or ask for missing user information. Confirmed
write results retain their existing deterministic effect path. No model/provider
switch, second verifier call, new dependency or B-side code change is involved.

The internal final carries `basis=read_evidence`, `backend=literal_renderer`,
`evidence_sources` and the existing text/state. The official adapter continues to
emit the documented text response; it does not add fields to Samsung's wire schema.

## Limitations and coordination

- A model can omit a relevant field, choose an irrelevant record or omit a qualifier
  elsewhere in a parent/sibling object. Whole-record selection is requested, not
  guaranteed. “Selected lookup fields” explicitly avoids presenting it as complete.
- Explicit units survive when their fields are selected. This is not proof that
  every model-selected answer includes all necessary units.
- Free-form clarifications, no-tool prose, images and source truth are outside this
  safeguard. Do not describe it as universal hallucination prevention.
- Read results are bounded in the model's session view; an older result omitted
  from that view is unavailable rather than silently accepted from history.
- Keeping source text literal does not make it safe to render through HTML. The UI
  must continue escaping it. Rich formatting is B-owned and was not changed here.
- Both teammates must coordinate before making this default or adding result cards:
  Mridul owns evidence resolution/final metadata; Atishay owns display, speech and
  usability. Do not rebuild argument validation or evidence authority in the UI.

## Evidence and next steps

Exact reports and verification results are recorded in
[evidence/samsung-read-answer-2026-09-23](evidence/samsung-read-answer-2026-09-23/README.md).
All external tools remain mocks. Synthetic probes are exposed development checks,
not Samsung scenarios, held-out data or end-to-end task scores.

Next A work: compare relevance/completeness and quota across more read, write and
interruption cases; explore clearer speech presentation without restoring arbitrary
factual prose. Broader/repeated official evaluation, B integration, media/timing,
platform/Docker and human submission gates remain separate.
