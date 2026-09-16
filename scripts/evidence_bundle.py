"""Deterministic eligibility classification for evidence-bundle run traces.

`classify_eligibility(row)` looks only at fields already present in a run_metadata
row (the same dict scripts/model_scoreboard.py parses from a trace .jsonl file) and
returns one label plus a one-line basis quoting the evidence for it. Nothing here
hand-types a verdict into a manifest; every label is reproducible by re-running this
function against the trace on disk, so `docs/evidence/*/manifest.json` can be
regenerated and checked instead of trusted.

Two denominators matter and must never collapse into one:

  - attempted-run reliability: every run that was ever dispatched, whatever the
    outcome. This is just `len(records)` in the scoreboard; every label counts here.
  - model-output quality: only runs where the evidence does not show the request
    was blocked before the model had a chance to generate anything.

A run is removed from the quality denominator only on positive evidence of that
block: a rate-limit/admission-control rejection (HTTP 429) recorded, with no
evidence anywhere else in the same run that the model ever generated anything.
A run that shows a successful request (`outcome: "success"`), or a failed
request whose body shows the provider rejected output the model already
generated, is not a "never invoked" run, no matter where a 429 falls relative
to it: that run keeps `GENERATION_THEN_INFRA_FAILURE` or
`SCORED_FAIL_GENERATED_OUTPUT` and stays in the quality denominator. Absence of
evidence is not evidence of absence, either way. A failure with no captured
status code or body does not prove infrastructure was at fault, so it stays
inside the quality denominator, as a failure, rather than being excused.
`QUALITY_EXCLUDED_LABELS` is the single place this policy lives.

Join key: run identity is the sha256 of the trace file's text content
(`content_sha256`), not `source_sha256` (a hash of the accessflow source tree,
identical across every run built from the same commit and therefore useless to
tell two runs apart) and not the filename (bundle files get renamed/copied).
"""
import hashlib
import json
from pathlib import Path

SCORED_PASS = "scored_pass"
SCORED_FAIL_OUTPUT_MISMATCH = "scored_fail_output_mismatch"
SCORED_FAIL_GENERATED_OUTPUT = "scored_fail_generated_output"
GENERATION_THEN_INFRA_FAILURE = "generation_then_infra_failure"
TIMEOUT_UNDETERMINED_CAUSE = "timeout_undetermined_cause"
INFRA_ADMISSION_FAILURE = "infra_admission_failure"
UNDETERMINED_FAILURE = "undetermined_failure"
UNSCORED = "unscored"

LABEL_MEANINGS = {
    SCORED_PASS: "Completed run; task oracle passed.",
    SCORED_FAIL_OUTPUT_MISMATCH: "Completed run; task oracle failed on the recorded output.",
    SCORED_FAIL_GENERATED_OUTPUT: "Provider rejected the model's own generated output "
                                   "(HTTP 4xx carrying a failed_generation body). Not infrastructure.",
    GENERATION_THEN_INFRA_FAILURE: "The model already generated output (a request in this run "
                                    "recorded outcome=success) before a later HTTP 429. The 429 "
                                    "did not block generation; it stopped the run from completing "
                                    "afterward. Not an admission refusal.",
    TIMEOUT_UNDETERMINED_CAUSE: "Scenario-level timeout. The trace does not establish "
                                 "whether the model or its environment stalled.",
    INFRA_ADMISSION_FAILURE: "HTTP 429 from the provider before any output existed: "
                              "admission control, not a model response.",
    UNDETERMINED_FAILURE: "Run failed with no status code or body captured. This does not "
                           "prove the request never reached the model, so it is not "
                           "classified as infrastructure; it stays undetermined.",
    UNSCORED: "Completed run with no task oracle verdict recorded.",
}

# Excluded from the model-output quality denominator because the evidence shows the
# request was blocked before the model could generate anything. Every other label,
# including UNDETERMINED_FAILURE and GENERATION_THEN_INFRA_FAILURE, stays in the
# quality denominator: the trace does not clear the model, so the run counts against
# it rather than disappearing.
QUALITY_EXCLUDED_LABELS = frozenset({INFRA_ADMISSION_FAILURE, UNSCORED})

DIAG_LIMIT = 200


def _truncate(value):
    text = str(value)
    if len(text) <= DIAG_LIMIT:
        return text
    return text[:DIAG_LIMIT] + "...(truncated)"


def content_sha256(path):
    """Hash a trace file the same way regardless of the checkout's line-ending
    settings: read as text (universal newlines), encode as UTF-8, then hash.
    Reading raw bytes would make the digest depend on CRLF/LF, which git's
    autocrlf setting can flip on checkout; this must not change with that.
    """
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def classify_eligibility(row):
    """Return (label, basis) for one run_metadata row, using only fields recorded
    in that row. Deterministic: the same row always yields the same label.
    """
    requests = ((row.get("reasoner_evidence") or {}).get("requests")) or []
    if not isinstance(requests, list):
        requests = []
    oracle = row.get("task_oracle")
    passed = oracle.get("passed") if isinstance(oracle, dict) else None
    status = row.get("completion_status")

    if status == "completed":
        if passed is None:
            return UNSCORED, LABEL_MEANINGS[UNSCORED]
        if passed:
            return SCORED_PASS, LABEL_MEANINGS[SCORED_PASS]
        return SCORED_FAIL_OUTPUT_MISMATCH, LABEL_MEANINGS[SCORED_FAIL_OUTPUT_MISMATCH]

    failed = [r for r in requests if isinstance(r, dict) and r.get("outcome") == "failure"]

    # Positive evidence the model was invoked at some point in this run: either a
    # request that actually succeeded, or a failed request whose body shows the
    # provider generated output and then rejected it. Checked before any 429, and
    # regardless of that 429's position in the list -- a later admission-control
    # rejection cannot retroactively erase evidence that generation already
    # happened somewhere in this run's request history.
    generated_at_some_point = any(
        isinstance(r, dict) and r.get("outcome") == "success" for r in requests)

    for entry in failed:
        code = entry.get("status_code")
        detail = entry.get("error_detail") or ""
        if code is not None and 400 <= code < 500 and code != 429 and "failed_generation" in detail:
            return SCORED_FAIL_GENERATED_OUTPUT, f"HTTP {code}, provider rejected generated output: {_truncate(detail)}"

    for entry in failed:
        if entry.get("status_code") == 429:
            detail = _truncate(entry.get("error_detail") or "no body captured")
            if generated_at_some_point:
                return GENERATION_THEN_INFRA_FAILURE, (
                    "A request in this run recorded outcome=success (the model already "
                    f"generated output) before this HTTP 429: {detail}. Partial progress "
                    "existed, so this is not an admission refusal.")
            return INFRA_ADMISSION_FAILURE, f"HTTP 429 before any output existed: {detail}"

    if status == "timeout":
        return TIMEOUT_UNDETERMINED_CAUSE, LABEL_MEANINGS[TIMEOUT_UNDETERMINED_CAUSE]

    if failed:
        entry = failed[-1]
        exc = entry.get("exception_type") or "unknown exception"
        elapsed = entry.get("elapsed_seconds")
        elapsed_text = f"{elapsed}s" if elapsed is not None else "unknown duration"
        return UNDETERMINED_FAILURE, (f"{exc} with no captured status/body, failing in {elapsed_text}; "
                                       f"cause not established by this trace alone.")
    return UNDETERMINED_FAILURE, (f"completion_status={_truncate(status)!s} with no failed request "
                                   f"recorded in reasoner_evidence; cause not established.")


def load_frozen_times(bundle_root):
    """Read `<bundle_root>/manifest.json` if present and return
    {content_sha256: selected_time_utc_raw_string}.

    Committed trace files carry no reliable mtime: a git checkout sets every
    file's mtime to checkout time, not the original run's. The manifest froze
    each run's `selected_time_utc` at bundle-build time specifically so this
    fallback signal is not lost to a later checkout. Returns {} if there is no
    manifest, it cannot be parsed, or a run entry lacks the fields needed to
    build the mapping -- callers must keep working with no frozen times at all.
    """
    manifest_path = Path(bundle_root) / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    frozen = {}
    for run in manifest.get("runs", []):
        digest = run.get("trace_sha256_in_bundle")
        when = run.get("selected_time_utc")
        if digest and when:
            frozen[digest] = when
    return frozen


def recompute_bundle_report(bundle_root):
    """Recompute run_count/eligibility_counts/per-run classification straight from
    the trace files under `<bundle_root>/traces/`, independent of manifest.json.

    Used to check the committed manifest against the traces it claims to describe,
    and to prove the classification does not depend on file mtime (the mtime
    experiment copies a bundle, scrambles every mtime, and compares this report
    before and after).
    """
    bundle_root = Path(bundle_root)
    traces = bundle_root / "traces"
    runs = []
    counts = {}
    for path in sorted(traces.rglob("*.jsonl")):
        text = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        row = None
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict) and candidate.get("type") == "run_metadata":
                row = candidate
                break
        bundle_path = path.relative_to(bundle_root).as_posix()
        if row is None:
            runs.append({"bundle_path": bundle_path, "content_sha256": digest,
                        "eligibility": None, "eligibility_basis": "no run_metadata row found"})
            continue
        label, basis = classify_eligibility(row)
        counts[label] = counts.get(label, 0) + 1
        runs.append({
            "bundle_path": bundle_path,
            "content_sha256": digest,
            "eligibility": label,
            "eligibility_basis": basis,
        })
    return {"run_count": len(runs), "eligibility_counts": counts, "runs": runs}
