# Next A-side slice: explicit delegated result bindings

Status: implemented; one live public chained case completed. Broader reliability remains unproven. Date:
22 September 2026. Owner: Mridul. Luna high reviewed the mechanism read-only;
Codex refined the selection and validation boundaries below.

## Reproduced problem

`docs/evidence/samsung-text-2026-09-22/pub_03_first.json` records a live Qwen run:
the user authorized a booking, a read returned the requested identifier, and
the controller refused that identifier because it originated in a tool result.
Total 56.9; task credit 0.3. The existing guard also blocks real attacks, so
removing it or allowing any value merely found in a tool result is not acceptable.

## Authority before results

Introduce an optional internal `WriteContract` on a fresh, complete **speech**
proposal. Existing proposals without contracts keep the current behavior.
Neither an image nor a tool-result-triggered replan may create or broaden one.
Capture only while the existing spoken write authorization is valid.

Each contract pins:

- Exact target write tool from the current manifest.
- Every user-controlled argument's mapping to its user slot. This covers differing
  parameter names: a fixed `day` slot must not become Friday through a new
  `chosen_day` alias, even if the tool's parameter is named `booking_date`.
- Every delegated argument's source read, value selector and explicit match
  constraints against user slots. Reject unaccounted-for non-constant arguments.
- Request ID, relevant intent and slot revisions; bind the source to an actual
  read call, not only a tool name that several unrelated calls share.

Prefer recording the read call from the same fresh proposal as the contract,
by proposal-call index resolved to a generated call ID at dispatch. A declaration
whose source did not dispatch must never become active accidentally. Reusing an
earlier read on a later fresh correction needs an explicit validated source-call
reference; it must not be inferred by searching for whichever result fits.

## Generic selectors

Use data paths and a small closed comparator vocabulary, not executable strings,
tool-specific conditions or a rule named after the public flight example.
A useful shape is a collection JSON pointer, a value pointer relative to each
candidate, and field-to-user-slot match rules. A single matching row is required
unless the fresh request explicitly authorizes a selection policy. Multiple
matches require clarification rather than silently choosing the first.

For illustration with arbitrary names: target parameter `item_id` takes `/id`
from the unique item in `/items` whose `/start` matches user slot `requested_time`.
The caller-provided passenger/customer argument remains pinned to its original
user slot. A literal path with an array index is acceptable only when that index
itself is an authorized selection, not as a shortcut for a semantic preference.

Comparators must be deterministic and independently tested. Default to typed
JSON equality. If clock normalization is needed, support a narrowly documented
format set with range checks; never ask a model whether two values match inside
the final authorization check. Reject malformed pointers, missing paths, null
or ambiguous matches, unsupported comparator names and over-limit traversal.

## Validate at dispatch

The later write proposal references the bound source call. The controller must
check all of these again before allowing a tool-origin argument:

1. Contract was captured from fresh complete speech, remains in the same active
   request, and names this exact write tool and parameter.
2. Source call was a read, succeeded, remains accepted/current, and was neither
   invalidated nor replaced. Failed/error payloads cannot supply values.
3. Source dependency revisions and every declared match slot still match the
   contract/current state. Do not rely only on the read's original dependencies;
   a selection preference may not have been an argument to the read.
4. The selector resolves under the contract's rules and equals the proposed
   argument and its tracked slot value. A model-provided reference alone proves
   nothing.
5. Fixed arguments retain their pinned parameter-to-slot mappings and values.
   A non-fresh proposal cannot relabel a fixed argument as delegated.
6. Existing write-intent, clarification, schema, cancellation, duplicate-operation
   and unknown-outcome checks still pass. The binding is an argument-provenance
   exception, not a substitute for these checks.

Request/observation epoch changes expire delegation. The old target record remains
as a write barrier until fresh complete speech supersedes it; simply deleting it
would let an image fall back to legacy argument rules. Corrections must explicitly
replace affected contracts. Cancellation is still not rollback. Preserve all
existing authority and conflicting-write-result regressions unchanged.

## Required evidence before a live retry

- A generic read-to-write positive example with arbitrary names.
- Refusal of new delegation introduced only after a result arrived.
- Same-name and different-parameter-name Wednesday-to-Friday alias attacks.
- Wrong/unrelated source, stale source, failed source, missing path, mismatched
  selection, ambiguous selection and malformed pointer: no write.
- Fresh correction can replace a contract and reach the corrected action.
- No cross-request reuse; no permission from partial speech or an image.
- Model proposal schema/prompt includes the optional mechanism and real tool
  schemas. No canned booking, fixed public tool names or benchmark answer keys.
- Full regression suite, then a new retained live attempt against the same public
  case with normal clock/tail. Preserve the failing baseline report.

This guarantees only the checked provenance, scope, structural matches and
argument mapping. It cannot prove the model understood the original request,
that a tool reported truthful data, or that an undeclared semantic constraint
was satisfied. These assumptions must stay explicit in the report.

## Ownership and independent next work

Mridul owns contracts, a pure binding resolver, engine integration, model schema
and prompt, engine tests and evaluation. No Atishay source edits are needed.
This does not resolve image authority or C1–C4 coordination.

Separately, `pub_08_first.json` shows a successful read retry followed by a final
model request canceled at the normal tail. Investigate a bounded fast retry for
transient reads using the same validated arguments and operation identity, only
while the source/request remains current. Keep that change separate from write
binding and from retries of uncertain writes. Measure it without extending the
tail or replacing model-grounded answers with canned output.


## Implementation and review checkpoint

Implemented in `contracts.py`, `result_binding.py`, `write_binding.py`, `engine.py`
and `adapters/models.py`. Selection bounds: at most 256 rows, 16 match constraints,
16 pointer components, 512 characters per pointer, 4096 JSON nodes and depth 16.
Typed equality distinguishes booleans, integers and floating-point numbers. Missing,
ambiguous, malformed, nonfinite or over-limit evidence is rejected.

The initial implementation passed 936 tests / one existing xfail after two scoped
Astra findings were repaired: an image could remove the contract barrier, and a
success-labelled result with a non-null error could supply a value. Both have
reproductions and regressions. This was a bounded binding review, not certification
of the complete application, documentation loader or corpus file boundary.

A subsequent live public attempt scored 38.5 with zero task credit: no model plan
validated, so no tool executed. The retained trace records ValidationError but lacks
field details; do not infer its cause from the exception name. Follow-up work adds
sanitized validation diagnostics, one same-input recovery attempt, an explicit
exclusive-source JSON Schema, and optional provenance-labelled interface documentation.
The published tool document contains return shapes absent from public runtime
manifests. Documents are interface evidence, never results or authorization.


## Latest measured outcome

The complete chain now succeeded in one retained public run using documented
return examples, a one-second speculative partial debounce and the explicit hosted
context cap. See `docs/evidence/samsung-binding-2026-09-22/README.md` for all three
new attempts, including failures, timings and configuration differences. Final
source validation: 996 passed, one Windows symlink skip, one existing frame xfail.
Do not interpret one public success as broader generality or safety certification.
