# Corpus boundary review and bounded-read repair — 23 September 2026

Owner: Mridul. Scope: installed document access and existing engine evidence/permission
checks. Baseline: `30e90de`; implementation was unchanged since `9a3eb84`.
This completes the previously interrupted scoped source/test review. It does not
certify an adversarial filesystem, native reparse-point behavior on every platform,
or general immunity to model prompt injection.

## Trust boundary established from actual callers

- Installation controls `corpus_root`, explicitly or through `ACCESSFLOW_CORPUS_ROOT`.
  Replay/CLI configuration validates directories; recorded replay metadata omits the
  absolute path. Root and contents are documented as trusted and immutable.
- A session declares logical document filenames through `Start.corpus`. Shared contract
  validation rejects traversal and reserved device names. The engine installs the
  built-in tool only for a nonempty corpus and rejects manifest-name collisions.
- The planner supplies a document name and query. `CorpusStore.read` independently
  revalidates the name, applies exact session allowlist membership and checks resolved
  containment. `_corpus_lookup` bounds queries before accessing the file.
- Reads run in a thread through the normal bounded tool path. Retrieved passages remain
  evidence; successful retrieval cannot authorize a write. Cancellation stops waiting
  and invalidates results but cannot forcibly terminate a running OS-thread read.
- Store/allowlist/evidence reset at session boundaries. An external tool sharing the
  name `search_corpus` is not intercepted when the built-in corpus is absent.

Files inspected: `src/accessflow/corpus.py`, corpus branches of `engine.py`, shared
corpus-name validation, CLI/replay configuration and the tests named below.

## Findings and repairs

### 1. File-size admission did not bound the actual allocation

Previously, the code checked `stat().st_size`, then called unrestricted `read_text`.
A deterministic reproduction replaces a five-byte file with 4096 bytes immediately
before open, while the configured limit is 16. The original implementation accepts
the oversized text. This is defense in depth against accidental installation mutation;
the test deliberately violates immutability and does not establish a session-controlled
escape under the documented supported deployment.

The repair retains rejection of already oversized files before open, reads at most
`max_document_bytes + 1` bytes, rejects an overflow sentinel and only then decodes.
Replacement decoding and universal newline behavior are preserved. No oversized
content is silently truncated and presented as a complete document.

The byte-budget constructor now rejects non-positive/non-integer values, including
booleans. This is configuration validation protecting the bounded-read invariant;
it is not a previously demonstrated remote attack.

### 2. Path-resolution errors bypassed the store's normalized error contract

`Path.resolve()` ran outside the `OSError` handler. Injected permission/OS failures and
the `RuntimeError` used for resolution loops in supported Python versions escaped
the store as raw exceptions. The engine's existing generic handler already reduced
them to exception type names, so this was not a demonstrated path disclosure to the
planner through the current engine.

The store now returns `CorpusAccessError("document_unreadable")` without chained raw
error text for these resolution failures. Allowlist/name errors and resolved escapes
remain distinct. Existing open errors still use the same normalized code.

### 3. Retained guarantees and explicit exclusions

Focused tests retain traversal, device-name and allowlist rejection; real retrieval;
query/size bounds; sanitized open errors; cancellation; session reset; and malicious
corpus prose versus write authority/slot provenance. Additional tests cover resolved
escape before open, UTF-8 byte boundaries, malformed-byte replacement and newlines.

The new native symlink escape test is skipped when Windows creation privileges are
unavailable. The mocked resolved-escape test passes but is not a native NTFS junction
or reparse-point integration test. No native junction test was performed in this slice.

Hardlinks planted in the installation, malicious replacement between resolve/open,
special-device/mount behavior and hostile network filesystems are not newly certified.
The byte cap limits allocation, not wall-clock completion of arbitrary OS I/O. Deploy
from a trusted, immutable corpus directory and do not place user uploads there.
These limits remain documented assumptions; the patch does not claim to eliminate them.

## Reproductions and verification

Baseline existing corpus/config suites: **87 passed** in 12.56 seconds.

New tests run against the unmodified source: **11 failed, 5 passed, 1 skipped** in
2.10 seconds. Failures: one growth case, three resolution-error cases and seven
invalid-budget cases. The native symlink case was skipped for platform permission.

After repair:

```powershell
uv run --offline --frozen --extra dev pytest tests/engine/test_corpus_boundary.py tests/engine/test_corpus.py tests/engine/test_corpus_config.py tests/engine/test_write_authority_evidence.py tests/engine/test_slot_provenance.py -q
uv run --offline --frozen --extra dev ruff check src/accessflow/corpus.py tests/engine/test_corpus.py tests/engine/test_corpus_boundary.py
```

**116 passed, 1 skipped**, 14.46 seconds; scoped Ruff clean. Existing open-error and
early-size tests now intercept the binary open boundary rather than the removed
`read_text` call; their error/early-rejection assertions were retained.

Full regression: **1086 passed, 2 skipped, 1 xfailed**, two dependency deprecation
warnings, 89.55 seconds. Repository-wide Ruff also passed. Command:
`uv run --offline --frozen --extra dev pytest -q --junitxml=artifacts/corpus-review-2026-09-23.xml`.
The XML is an ignored local artifact; the reproducing tests and this result summary
are committed. Both skips concern native Windows symlink privileges; the existing
conflicting-frame expected failure remains open, not a passing check.
No live model, organizer scoring or Atishay-owned code/tests were used or modified for
this repair. Existing deterministic adversarial-planner tests are controlled enforcement
evidence, not a broad prompt-injection success rate.

## Disposition

The scoped review is complete with two implementation repairs and explicit deployment/
platform limits. Native platform behavior and broader submission/evaluation gates remain
separate. The earlier incomplete review is preserved as historical context and links here.
