"""Guard the committed R8 evidence bundle.

docs/evidence/model-comparison-2026-09-15/ holds sanitised copies of raw traces so a
clean clone can inspect and regenerate the Groq-hosted rows of MODEL_COMPARISON.md
without artifacts/. These tests protect the two properties that matter: the bundle
stays free of the Groq organization id, and the manifest stays an accurate index of
what is actually on disk.
"""
import json
import re
from pathlib import Path

from scripts.evidence_bundle import (QUALITY_EXCLUDED_LABELS, classify_eligibility, content_sha256,
                                     recompute_bundle_report)
from scripts.model_scoreboard import collect_records

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "docs/evidence/model-comparison-2026-09-15"
TRACES = BUNDLE / "traces"
MANIFEST = BUNDLE / "manifest.json"

ORG_ID_PATTERN = re.compile(r"org_[0-9a-zA-Z]{10,}")


def test_bundle_exists():
    assert BUNDLE.is_dir()
    assert TRACES.is_dir()
    assert MANIFEST.is_file()


def test_no_organization_id_anywhere_in_the_bundle():
    offenders = []
    for path in BUNDLE.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if ORG_ID_PATTERN.search(text):
            offenders.append(str(path.relative_to(BUNDLE)))
    assert offenders == [], f"organization id leaked into: {offenders}"


def test_manifest_run_count_matches_run_list():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["run_count"] == len(manifest["runs"])
    assert sum(manifest["eligibility_counts"].values()) == manifest["run_count"]


def test_every_manifest_entry_points_at_a_real_sanitized_file():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for run in manifest["runs"]:
        bundle_file = BUNDLE / run["bundle_path"]
        assert bundle_file.is_file(), f"missing {run['bundle_path']}"
        assert run["bundle_path"].startswith("traces/")


def test_every_traced_file_is_indexed_in_the_manifest():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    indexed = {(BUNDLE / run["bundle_path"]).resolve() for run in manifest["runs"]}
    on_disk = {p.resolve() for p in TRACES.rglob("*.jsonl")}
    assert on_disk == indexed


def test_sanitized_runs_carry_a_429_admission_control_body():
    # A sanitized run is one whose raw 429 body carried the Groq organization id.
    # It is either a pure admission refusal (infra_admission_failure) or a run
    # that already generated output before that same 429 arrived
    # (generation_then_infra_failure, M6): both are HTTP 429 bodies, just with
    # different generation evidence recorded earlier in the same trace.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sanitized = {run["bundle_path"] for run in manifest["runs"] if run["sanitized"]}
    assert len(sanitized) == manifest["sanitization"]["files_sanitized_in_bundle"]
    for run in manifest["runs"]:
        if run["sanitized"]:
            assert run["eligibility"] in ("infra_admission_failure", "generation_then_infra_failure")


def test_scoreboard_reads_the_bundle_with_no_exclusions():
    records, exclusions = collect_records(TRACES)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert exclusions == []
    assert len(records) == manifest["run_count"]


def test_bundle_is_self_contained_no_artifacts_reference_required():
    # The whole point of R8: a clean clone reads this bundle, not a user's local
    # artifacts/. Every path recorded for scoreboard consumption must live under the
    # bundle itself.
    for path in TRACES.rglob("*.jsonl"):
        assert "artifacts" not in path.relative_to(TRACES).parts


# --- A4: manifest eligibility must be reproducible from trace content, not hand-typed ---

def test_manifest_eligibility_is_reproducible_from_each_traces_own_content():
    """This is the test that must fail if someone hand-edits a label in manifest.json
    without the trace changing, or if a trace changes without the manifest being
    regenerated. Recomputes classify_eligibility() straight from each trace file on
    disk and compares against what the manifest claims for that same file.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    checked = 0
    for run in manifest["runs"]:
        path = BUNDLE / run["bundle_path"]
        text = path.read_text(encoding="utf-8")
        row = None
        for line in text.splitlines():
            if not line.strip():
                continue
            candidate = json.loads(line)
            if isinstance(candidate, dict) and candidate.get("type") == "run_metadata":
                row = candidate
                break
        assert row is not None, f"no run_metadata row in {run['bundle_path']}"
        label, basis = classify_eligibility(row)
        assert label == run["eligibility"], (
            f"{run['bundle_path']}: manifest says {run['eligibility']!r}, "
            f"recomputed from the trace says {label!r} ({basis})")
        assert basis == run["eligibility_basis"]
        checked += 1
    assert checked == manifest["run_count"]


def test_manifest_trace_hash_matches_recomputed_content_hash():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for run in manifest["runs"]:
        path = BUNDLE / run["bundle_path"]
        assert content_sha256(path) == run["trace_sha256_in_bundle"], run["bundle_path"]


def test_recompute_bundle_report_matches_manifest_run_count_and_counts():
    report = recompute_bundle_report(BUNDLE)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert report["run_count"] == manifest["run_count"]
    assert report["eligibility_counts"] == manifest["eligibility_counts"]


def test_legacy_infra_failure_unspecified_label_is_gone():
    # The review found this label overstated the evidence (no captured status/body
    # does not prove the request never reached the model). It must not reappear.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    labels = {run["eligibility"] for run in manifest["runs"]}
    assert "infra_failure_unspecified" not in labels
    assert "undetermined_failure" in labels


def test_eligibility_counts_sum_to_run_count_and_every_label_is_placed_in_exactly_one_denominator():
    # M6: a 429 after a request already succeeded is not an admission refusal. Three
    # of the previously-11 infra_admission_failure runs recorded a successful request
    # before their 429 and are now generation_then_infra_failure, which stays in the
    # quality denominator. That raises quality_total from 46 to 49; quality_pass (43)
    # is unchanged because all three reclassified runs failed their task oracle anyway.
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    counts = manifest["eligibility_counts"]
    assert sum(counts.values()) == manifest["run_count"]
    quality_total = sum(n for label, n in counts.items() if label not in QUALITY_EXCLUDED_LABELS)
    quality_pass = counts.get("scored_pass", 0)
    assert quality_total == 49
    assert quality_pass == 43
    # generated-output failures and unresolved timeouts must stay counted, not dropped
    assert counts.get("scored_fail_generated_output", 0) == 1
    assert counts.get("timeout_undetermined_cause", 0) == 1
    assert counts.get("undetermined_failure", 0) == 1
    assert counts.get("infra_admission_failure", 0) == 8
    assert counts.get("generation_then_infra_failure", 0) == 3


def test_scoreboard_quality_pass_rate_over_the_bundle_is_43_of_49_not_43_of_57():
    records, exclusions = collect_records(TRACES)
    assert exclusions == []
    non_ablated = [r for r in records if not r["ablated"]]
    assert len(non_ablated) == 57
    quality_scored = [r for r in non_ablated
                      if r["oracle"] is not None and r["eligibility"] not in QUALITY_EXCLUDED_LABELS]
    assert len(quality_scored) == 49
    assert sum(1 for r in quality_scored if r["oracle"]) == 43


def test_generation_then_429_runs_stay_in_quality_not_excluded():
    # M6 regression: these three committed traces record a successful request
    # before the HTTP 429 that ended the run. They must not be excluded from
    # quality the way a pure admission refusal is.
    records, exclusions = collect_records(TRACES)
    assert exclusions == []
    changed_names = {
        "groq-gptoss120b/scenario-003.jsonl",
        "groq-qwen36-27b_redo_lost_response_reconcile.jsonl",
        "groq-qwen3-8-27b-run2/scenario-003.jsonl",
    }
    found = {name: r for r in records
             for name in changed_names if r["path"].endswith(name)}
    assert set(found) == changed_names
    for name, record in found.items():
        assert record["eligibility"] == "generation_then_infra_failure", name
        assert record["eligibility"] not in QUALITY_EXCLUDED_LABELS, name
        assert record["oracle"] is not None, name
